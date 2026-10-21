"""NL2SQL 主链路：理解问题 → 生成 SQL → 安全校验 → 执行 → （失败修复）→ 图表 → 洞察。"""
from __future__ import annotations

import asyncio
import time
from datetime import date
from typing import Any

from pydantic import BaseModel, Field

from .. import config, prompts
from ..models import (
    ChatRequest, ChatResponse, ChartSpec, ColumnInfo, HistoryTurn,
    QueryResult, StepInfo,
)
from ..utils import safe_float
from . import dataset_service, executor, insight, llm, mock_planner, sql_guard

ALLOWED_CHARTS = {"line", "bar", "pie", "scatter", "table"}


class LLMChart(BaseModel):
    type: str = "table"
    title: str = ""
    x: str | None = None
    y: list[str] = Field(default_factory=list)
    series: str | None = None
    sort: str | None = None


class LLMOutput(BaseModel):
    intent: str = "query"
    plan: str = ""
    sql: str | None = None
    chart: LLMChart | None = None
    insight_focus: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    clarification: dict[str, Any] | None = None


def _parse_llm_output(data: dict[str, Any]) -> LLMOutput:
    allowed = set(LLMOutput.model_fields.keys())
    out = LLMOutput(**{k: v for k, v in data.items() if k in allowed})
    if out.intent not in {"query", "clarify", "unsupported"}:
        out.intent = "query"
    if out.intent == "query" and not (out.sql and out.sql.strip()):
        out.intent = "clarify"
        out.clarification = out.clarification or {
            "question": "能再具体一点吗？例如说明想看的时间范围和指标。",
            "options": ["按区域看销售额", "按品类看销售额", "最近 30 天销售趋势"],
        }
    return out


def _build_history(history: list[HistoryTurn]) -> str:
    if not history:
        return "（无，本轮为新对话）"
    lines: list[str] = []
    for turn in history[-config.MAX_HISTORY_TURNS:]:
        lines.append(f"- 用户：{turn.question}")
        if turn.sql:
            lines.append(f"  上一轮 SQL：{turn.sql}")
        if turn.columns:
            lines.append(f"  结果列：{', '.join(turn.columns)}")
        if turn.summary:
            lines.append(f"  上一轮结论：{turn.summary}")
    return "\n".join(lines)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _numeric_indexes(columns: list[str], rows: list[list[Any]]) -> list[int]:
    indexes: list[int] = []
    for idx in range(len(columns)):
        values = [row[idx] for row in rows[:10] if idx < len(row) and row[idx] is not None]
        if values and all(_is_number(v) for v in values):
            indexes.append(idx)
    return indexes


def _looks_like_time(columns: list[str], rows: list[list[Any]], idx: int) -> bool:
    values = [str(row[idx]) for row in rows[:5] if idx < len(row) and row[idx] is not None]
    if not values:
        return False
    text = values[0]
    return any(sep in text for sep in ("-", "/", ":")) and any(ch.isdigit() for ch in text)


def _normalize_chart(preferred: LLMChart | None, columns: list[str], rows: list[list[Any]],
                     question: str) -> ChartSpec:
    column_set = set(columns)

    def build(kind: str, title: str, x: str | None, y: list[str], sort: str | None = None,
              series: str | None = None) -> ChartSpec:
        return ChartSpec(
            type=kind if kind in ALLOWED_CHARTS else "table",
            title=title or "查询结果",
            x=x, y=y, series=series,
            sort=sort if sort in {"x", "y_desc"} else None,
        )

    if preferred and preferred.type in ALLOWED_CHARTS:
        valid_y = [c for c in preferred.y if c in column_set]
        x_ok = preferred.x is None or preferred.x in column_set
        if x_ok and (preferred.y == [] or valid_y):
            if preferred.type == "table" or preferred.x:
                return build(preferred.type, preferred.title, preferred.x, valid_y,
                             preferred.sort, preferred.series)

    if not rows:
        return build("table", "查询结果", None, [], None)

    numeric = _numeric_indexes(columns, rows)
    non_numeric = [i for i in range(len(columns)) if i not in numeric]

    if numeric and non_numeric:
        cat_idx = non_numeric[0]
        y_name = columns[numeric[0]]
        x_name = columns[cat_idx]
        if _looks_like_time(columns, rows, cat_idx):
            return build("line", preferred.title if preferred else "趋势", x_name, [y_name], "x")
        if "占比" in question or "构成" in question or "比例" in question:
            return build("pie", preferred.title if preferred else f"{x_name} 占比", x_name, [y_name], "y_desc")
        return build("bar", preferred.title if preferred else f"各{x_name}对比", x_name, [y_name], "y_desc")
    if len(numeric) >= 2 and not non_numeric:
        return build("scatter", "数值关系", columns[numeric[0]], [columns[numeric[1]]], None)
    return build("table", "查询结果", None, [], None)


def _as_query_result(data: dict[str, Any]) -> QueryResult:
    return QueryResult(
        columns=data.get("columns", []),
        rows=data.get("rows", []),
        total_rows=data.get("total_rows", 0),
        truncated=data.get("truncated", False),
        elapsed_ms=data.get("elapsed_ms", 0),
    )


def _error_response(question: str, message: str, steps: list[StepInfo], sql: str | None = None,
                    attempts: int = 0, mock: bool = False) -> ChatResponse:
    return ChatResponse(
        ok=False, intent="error", question=question, sql=sql, steps=steps,
        error=message, attempts=attempts, mock=mock,
        model=llm.model_label() if not mock else "演示模式",
    )


async def analyze(req: ChatRequest) -> ChatResponse:
    started = time.perf_counter()
    info = dataset_service.get_dataset_info(req.dataset_id)
    if not info:
        return _error_response(req.question, "数据集不存在，请先上传数据或载入示例数据。", [])

    schema_block = dataset_service.build_schema_block(info)
    metric_block = dataset_service.build_metric_dict(info)
    history_block = _build_history(req.history)

    system_prompt = prompts.render(
        prompts.NL2SQL_SYSTEM,
        DB_ENGINE="DuckDB",
        TODAY=date.today().isoformat(),
        MAX_ROWS=str(config.MAX_ROWS),
        SCHEMA_BLOCK=schema_block,
        METRIC_DICT=metric_block,
        HISTORY_BLOCK=history_block,
    )

    steps: list[StepInfo] = []
    used_mock = not config.llm_enabled()
    note: str | None = None

    # ---------- 1. 理解问题 + 生成 SQL ----------
    t0 = time.perf_counter()
    if used_mock:
        raw = mock_planner.plan(req.question, info)
    else:
        try:
            raw = await llm.chat_json(system_prompt, req.question, max_tokens=1800)
        except llm.LLMUnavailable:
            used_mock = True
            raw = mock_planner.plan(req.question, info)
        except llm.LLMError as exc:
            used_mock = True
            raw = mock_planner.plan(req.question, info)
            note = f"模型调用失败，已自动切换演示模式（{exc}）"

    try:
        out = _parse_llm_output(raw)
    except Exception:
        out = LLMOutput(
            intent="clarify", plan="模型输出格式异常",
            clarification={"question": "能换个说法再问一次吗？", "options": ["按区域看销售额", "最近 30 天趋势"]},
        )

    steps.append(StepInfo(key="understand", label="理解问题", status="done",
                          detail=(out.plan or "")[:80] or None,
                          elapsed_ms=int((time.perf_counter() - t0) * 1000)))

    if out.intent in {"clarify", "unsupported"}:
        return ChatResponse(
            ok=True, intent=out.intent, question=req.question, plan=out.plan,
            assumptions=out.assumptions, clarification=out.clarification,
            steps=steps, model=llm.model_label(), mock=used_mock,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
            insight=None, error=note,
        )

    # ---------- 2. 校验 + 执行（含自动修复） ----------
    sql = (out.sql or "").strip()
    attempts = 0
    result: QueryResult | None = None
    last_error: str | None = None
    max_attempts = 1 + config.MAX_RETRY
    execute_started = time.perf_counter()

    for attempt in range(max_attempts):
        attempts = attempt + 1
        try:
            safe_sql = sql_guard.validate_sql(sql, [info.table_name])
            executed = await asyncio.to_thread(executor.execute_sql, info.id, safe_sql)
            sql = safe_sql
            result = _as_query_result(executed)
            break
        except (sql_guard.SqlGuardError, executor.QueryError) as exc:
            last_error = str(exc)
            if used_mock or attempt >= max_attempts - 1:
                break
            repair_system = prompts.render(
                prompts.SQL_REPAIR_SYSTEM,
                DB_ENGINE="DuckDB",
                MAX_ROWS=str(config.MAX_ROWS),
                SCHEMA_BLOCK=schema_block,
                METRIC_DICT=metric_block,
            )
            repair_user = (
                f"用户问题：{req.question}\n\n原 SQL：\n{sql}\n\n"
                f"执行错误：\n{last_error}\n\n请修复后只输出 JSON。"
            )
            try:
                repaired = _parse_llm_output(await llm.chat_json(repair_system, repair_user, max_tokens=1600))
                if repaired.sql:
                    sql = repaired.sql
                else:
                    break
            except llm.LLMError:
                break

    if result is None:
        steps.append(StepInfo(key="execute", label="执行查询", status="error",
                              detail=last_error[:120] if last_error else "SQL 执行失败",
                              elapsed_ms=int((time.perf_counter() - execute_started) * 1000)))
        return _error_response(
            req.question, f"SQL 执行失败：{last_error or '未知错误'}", steps, sql, attempts, used_mock,
        )

    steps.append(StepInfo(key="sql", label="生成 SQL", status="done",
                          detail=f"第 {attempts} 次{('（已自动修复）' if attempts > 1 else '')}",
                          elapsed_ms=None))
    steps.append(StepInfo(key="execute", label="执行查询", status="done",
                          detail=f"{result.total_rows} 行 · {result.elapsed_ms} ms",
                          elapsed_ms=result.elapsed_ms))

    # ---------- 3. 图表 ----------
    chart = _normalize_chart(out.chart, result.columns, result.rows, req.question)
    steps.append(StepInfo(key="chart", label="生成图表", status="done",
                          detail={"line": "折线图", "bar": "柱状图", "pie": "环形图",
                                  "scatter": "散点图", "table": "表格"}.get(chart.type)))

    # ---------- 4. 洞察 ----------
    t_insight = time.perf_counter()
    try:
        ins = await insight.generate_insight(req.question, sql, result, used_mock)
    except Exception:  # 洞察失败不影响主查询
        ins = insight.heuristic_insight(req.question, result)
    steps.append(StepInfo(key="insight", label="撰写洞察", status="done",
                          detail=ins.headline[:60] or None,
                          elapsed_ms=int((time.perf_counter() - t_insight) * 1000)))

    return ChatResponse(
        ok=True, intent="query", question=req.question, plan=out.plan, sql=sql,
        result=result, chart=chart, insight=ins, assumptions=out.assumptions,
        steps=steps, attempts=attempts,
        model=("演示模式" if used_mock else llm.model_label()),
        mock=used_mock, error=note,
        elapsed_ms=int((time.perf_counter() - started) * 1000),
    )


async def run_raw_sql(dataset_id: str, sql: str) -> dict[str, Any]:
    """检查器里手动执行 SQL。"""
    info = dataset_service.get_dataset_info(dataset_id)
    if not info:
        raise ValueError("数据集不存在")
    safe_sql = sql_guard.validate_sql(sql, [info.table_name])
    return await asyncio.to_thread(executor.execute_sql, dataset_id, safe_sql)
