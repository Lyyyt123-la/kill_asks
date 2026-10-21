"""FastAPI 入口。

开发：uvicorn app.main:app --reload --port 8000
生产：前端 build 后由本服务直接托管（frontend/dist）
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config, store
from .routers import chat, datasets


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
    }


# 生产模式：直接托管前端构建产物（npm run build 之后生效）
if config.FRONTEND_DIST.exists():
    assets_dir = config.FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        candidate = config.FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(config.FRONTEND_DIST / "index.html")
