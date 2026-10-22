"""对比百炼上不同模型的 NL2SQL 速度与 JSON 稳定性（不经过后端服务，直接调用 pipeline 组件）。

用法：backend\\.venv\\Scripts\\python.exe scripts/bench_models.py
"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app import config, prompts  # noqa: E402
from app.services import dataset_service, llm  # noqa: E402
from app.services.nl2sql import _parse_llm_output  # noqa: E402

MODELS = [
    "qwen3.8-flash",
    "deepseek-v4.1-flash-1017",
    "qwen-plus",
    "qwen3.7-flash",
    "glm-5.2-fast-preview",
]
QUESTIONS = [
    "2025年双11当天各小时销售额趋势",
    "各渠道的退款率排名",
]


async def main() -> None:
    info = dataset_service.get_dataset_info("demo_double11")
    if not info:
        print("示例数据不存在，请先 POST /api/datasets/demo")
        return
    schema_block = dataset_service.build_schema_block(info)
    metric_block = dataset_service.build_metric_dict(info)
    system = prompts.render(
        prompts.NL2SQL_SYSTEM,
        DB_ENGINE="DuckDB",
        TODAY="2026-10-22",
        DATA_TIME_RANGE=dataset_service.get_data_time_range(info),
        MAX_ROWS=str(config.MAX_ROWS),
        SCHEMA_BLOCK=schema_block,
        METRIC_DICT=metric_block,
        HISTORY_BLOCK="（无，本轮为新对话）",
    )

    original_model = config.LLM_MODEL
    original_timeout = config.LLM_TIMEOUT_S
    config.LLM_TIMEOUT_S = 90
    for model in MODELS:
        config.LLM_MODEL = model
        print(f"\n===== {model} =====")
        for question in QUESTIONS:
            started = time.time()
            try:
                raw = await llm.chat_json(system, question, max_tokens=900)
                elapsed = int((time.time() - started) * 1000)
                parsed = _parse_llm_output(raw)
                valid = bool(parsed.sql) and parsed.intent == "query"
                sql_preview = (parsed.sql or "").replace("\n", " ")[:110]
                print(f"  {'✅' if valid else '⚠️'} {elapsed:>6d}ms  {question[:18]:20s} -> {sql_preview}")
            except Exception as exc:  # noqa: BLE001
                elapsed = int((time.time() - started) * 1000)
                print(f"  ❌ {elapsed:>6d}ms  {question[:18]:20s} -> {type(exc).__name__}: {str(exc)[:120]}")
    config.LLM_MODEL = original_model
    config.LLM_TIMEOUT_S = original_timeout


if __name__ == "__main__":
    asyncio.run(main())
