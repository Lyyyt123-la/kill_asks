"""FastAPI 入口。

开发：uvicorn app.main:app --reload --port 8000
生产：前端 build 后由本服务直接托管（frontend/dist）
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from . import config, store
from .routers import chat, datasets, documents

# Windows 下 Python 的 mimetypes 会把 .js 识别成 text/plain（读取注册表），
# 导致浏览器拒绝加载 ESM 前端资源。这里为构建产物显式指定 MIME 类型。
ASSET_MEDIA = {
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".css": "text/css",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".json": "application/json",
    ".map": "application/json",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".txt": "text/plain",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.ensure_dirs()
    store.init_db()
    yield


app = FastAPI(
    title="问数 AskData API",
    description="基于自然语言的数据分析平台：上传数据 → 对话提问 → 自动 SQL → 图表 → 洞察。",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(datasets.router)
app.include_router(chat.router)
app.include_router(documents.router)


class ApiGuardMiddleware(BaseHTTPMiddleware):
    """公网保护：访问口令 + 每分钟限流（未配置时自动不生效）。"""

    def __init__(self, app):
        super().__init__(app)
        self._hits: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
        path = request.url.path
        if path.startswith("/api") and path != "/api/health":
            if config.APP_ACCESS_CODE:
                provided = request.headers.get("x-access-code") or request.query_params.get("code") or ""
                if provided != config.APP_ACCESS_CODE:
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "访问口令错误，请在网址后加 ?code=你的口令"},
                    )
            limit = config.RATE_LIMIT_PER_MIN
            if limit > 0:
                ip = request.client.host if request.client else "unknown"
                now = time.time()
                bucket = self._hits[ip]
                while bucket and now - bucket[0] >= 60:
                    bucket.popleft()
                if len(bucket) >= limit:
                    return JSONResponse(
                        status_code=429,
                        content={"detail": f"请求过于频繁（每分钟上限 {limit} 次），请稍后再试"},
                    )
                bucket.append(now)
        return await call_next(request)


app.add_middleware(ApiGuardMiddleware)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """保证任何未捕获异常都返回 JSON，而不是空响应的 500。"""
    return JSONResponse(
        status_code=500,
        content={"detail": f"服务内部异常：{type(exc).__name__}: {exc}"},
    )


@app.get("/api/health", tags=["system"], summary="健康检查")
def health():
    return {
        "ok": True,
        "app": "问数 AskData",
        "version": app.version,
        "llm_enabled": config.llm_enabled(),
        "model": config.LLM_MODEL,
        "mock_mode": not config.llm_enabled(),
        "demo_ready": config.DEMO_DATASET_FILE.exists(),
        "max_rows": config.MAX_ROWS,
        "max_upload_mb": config.MAX_UPLOAD_MB,
        "vision_model": config.VISION_MODEL,
        "embedding_model": config.EMBED_MODEL,
    }


# ---------------- 生产模式：托管前端构建产物 ----------------
if config.FRONTEND_DIST.exists():
    DIST_ROOT = config.FRONTEND_DIST.resolve()
    ASSETS_ROOT = (config.FRONTEND_DIST / "assets").resolve()

    def _safe_file(root, relative: str):
        candidate = (root / relative).resolve()
        if not str(candidate).startswith(str(root)):
            return None
        return candidate if candidate.is_file() else None

    @app.get("/assets/{asset_path:path}", include_in_schema=False)
    def serve_asset(asset_path: str):
        candidate = _safe_file(ASSETS_ROOT, asset_path)
        if not candidate:
            raise HTTPException(status_code=404, detail="asset not found")
        media = ASSET_MEDIA.get(candidate.suffix.lower(), "application/octet-stream")
        return FileResponse(candidate, media_type=media)

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        if full_path:
            candidate = _safe_file(DIST_ROOT, full_path)
            if candidate:
                media = ASSET_MEDIA.get(candidate.suffix.lower())
                return FileResponse(candidate, media_type=media)
        return FileResponse(DIST_ROOT / "index.html", media_type="text/html")
