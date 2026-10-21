"""对话与 SQL 执行 API。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import config
from ..models import ChatRequest, ChatResponse, RawQueryRequest
from ..services import executor, llm, nl2sql, sql_guard

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse, summary="自然语言对话分析")
async def chat(req: ChatRequest):
    return await nl2sql.analyze(req)


@router.post("/query", summary="检查器：手动执行 SQL")
async def run_sql(req: RawQueryRequest):
    try:
        return await nl2sql.run_raw_sql(req.dataset_id, req.sql)
    except (ValueError, sql_guard.SqlGuardError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except executor.QueryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/llm/status", summary="大模型配置状态")
def llm_status():
    return {
        "enabled": config.llm_enabled(),
        "mock_mode": not config.llm_enabled(),
        "model": config.LLM_MODEL,
        "base_url": config.LLM_BASE_URL,
        "message": "已配置真实模型" if config.llm_enabled() else "未配置 LLM_API_KEY，当前为演示模式",
    }


@router.post("/llm/test", summary="测试大模型连通性")
async def llm_test():
    if not config.llm_enabled():
        raise HTTPException(status_code=400, detail="未配置 LLM_API_KEY，当前为演示模式")
    try:
        data = await llm.chat_json(
            "你是一个连通性测试助手。",
            '只输出一个 JSON：{"ok": true, "msg": "pong"}',
            max_tokens=100,
        )
        return {"ok": True, "model": config.LLM_MODEL, "reply": data}
    except llm.LLMError as exc:
        raise HTTPException(status_code=502, detail=f"模型调用失败：{exc}") from exc

