"""智能洞察：优先用 LLM 生成，失败/演示模式时用本地统计启发式生成。"""
from __future__ import annotations

import json
import re
from typing import Any

from .. import config, prompts
from ..models import Insight, QueryResult
from ..utils import fmt_num, safe_float
from . import llm

RATE_HINTS = ("rate", "率", "ratio", "percent", "pct")
TIME_HINTS = ("time", "date", "日期", "时间", "period", "月", "日")


def _summarize_for_llm(result: QueryResult, max_rows: int = 30) -> str:
    payload = {
        "columns": result.columns,
        "rows": result.rows[:max_rows],
        "truncated": result.truncated,
        "total_rows": result.total_rows,
    }
    return json.dumps(payload, ensure_ascii=False)[:6000]


def _numeric_columns(result: QueryResult) -> list[int]:
    indexes: list[int] = []
    for idx in range(len(result.columns)):
        values = [row[idx] for row in result.rows[:10]]
        numeric = [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if numeric and len(numeric) >= max(1, len(values) // 2):
            indexes.append(idx)
    return indexes


def _looks_time(column_name: str, values: list[Any]) -> bool:
    name = column_name.lower()
    if any(hint in name for hint in TIME_HINTS):
        return True
    sample = [str(v) for v in values[:3] if v is not None]
    return bool(sample) and bool(re.match(r"^\d{4}-\d{2}-\d{2}", sample[0]))


def _is_rate(column_name: str, question: str) -> bool:
    name = column_name.lower()
    return any(hint in name for hint in RATE_HINTS) or any(
        keyword in question for keyword in ("退款率", "退货率", "转化率", "占比率")
    )


def heuristic_insight(question: str, result: QueryResult) -> Insight:
    if not result.rows:
        return Insight(
            headline="没有查询到符合条件的数据",
            bullets=["可以检查一下时间范围、筛选条件或字段口径是否合适。"],
            followups=["换成最近 30 天看看", "不加筛选条件看全量数据", "换个维度再试一次"],
        )

    columns = result.columns
    numeric_idx = _numeric_columns(result)
    x_idx = next((i for i in range(len(columns)) if i not in numeric_idx), None)
    bullets: list[str] = []
    headline = ""

    if not numeric_idx:
        return Insight(
            headline=f"查询返回 {len(result.rows)} 行结果",
            bullets=["结果中没有可汇总的数值字段，建议直接查看明细或换个问题。"],
            followups=["按区域拆分看看", "统计一下各品类数量", "换成最近 30 天"],
        )

    y_idx = numeric_idx[0]
    y_name = columns[y_idx]
    x_name = columns[x_idx] if x_idx is not None else ""
    y_label = y_name
    if any(keyword in question for keyword in ("销售额", "销售", "GMV", "gmv", "收入")):
        y_label = "销售额"
    elif "退款率" in question or "退货率" in question:
        y_label = "退款率"
    elif "订单量" in question or "订单数" in question:
        y_label = "订单量"

    pairs = [
        (safe_float(row[y_idx]), row)
        for row in result.rows
        if safe_float(row[y_idx]) is not None
    ]
    is_rate = _is_rate(y_name, question)
    is_time = bool(x_name) and _looks_time(x_name, [row[x_idx] for row in result.rows])

    if is_rate:
        top_value, top_row = max(pairs, key=lambda item: item[0] or 0)
        low_value, low_row = min(pairs, key=lambda item: item[0] or 0)
        top_label = str(top_row[x_idx]) if x_idx is not None else "整体"
        low_label = str(low_row[x_idx]) if x_idx is not None else "整体"
        headline = f"{top_label} 的{y_label}最高，为 {top_value:.2f}%"
        bullets.append(f"最高为「{top_label}」{top_value:.2f}%，最低为「{low_label}」{low_value:.2f}%，相差 {top_value - low_value:.2f} 个百分点。")
        avg = sum(v or 0 for v, _ in pairs) / len(pairs)
        bullets.append(f"各组平均{y_label}约 {avg:.2f}%，可重点优化高于均值且占比大的分组。")
    elif is_time and len(pairs) >= 2:
        top_value, top_row = max(pairs, key=lambda item: item[0] or 0)
        top_label = str(top_row[x_idx])
        first, last = pairs[0][0] or 0, pairs[-1][0] or 0
        change = (last - first) / abs(first) * 100 if first else 0
        headline = f"峰值出现在 {top_label}，{y_label}为 {fmt_num(top_value)}"
        bullets.append(f"「{top_label}」达到峰值 {fmt_num(top_value)}，是这段区间内最高点。")
        bullets.append(
            f"期末较期初{'增长' if change >= 0 else '下降'} {abs(change):.1f}%"
            f"（{fmt_num(first)} → {fmt_num(last)}）。"
        )
        avg = sum(v or 0 for v, _ in pairs) / len(pairs)
        bullets.append(f"区间平均{y_label}为 {fmt_num(avg)}。")
    else:
        top_value, top_row = max(pairs, key=lambda item: item[0] or 0)
        top_label = str(top_row[x_idx]) if x_idx is not None else "当前结果"
        total = sum(v or 0 for v, _ in pairs)
        share = (top_value or 0) / total * 100 if total else 0
        headline = f"{top_label} 的{y_label}最高，为 {fmt_num(top_value)}"
        bullets.append(f"「{top_label}」排名第一，占可见分组的 {share:.1f}%。")
        if len(pairs) >= 2:
            second = sorted(pairs, key=lambda item: item[0] or 0, reverse=True)[1]
            gap = (top_value or 0) - (second[0] or 0)
            second_label = str(second[1][x_idx]) if x_idx is not None else "第二名"
            bullets.append(f"领先第二名「{second_label}」{fmt_num(gap)}。")
        bullets.append(f"当前展示 {len(pairs)} 个分组，可继续按区域/品类下钻定位原因。")

    followups = ["按区域拆分看看", "换成最近 30 天再对比", "导出明细数据"]
    return Insight(headline=headline, bullets=[b for b in bullets if b][:3], followups=followups)


async def generate_insight(question: str, sql: str, result: QueryResult, mock: bool) -> Insight:
    if mock or not config.llm_enabled():
        return heuristic_insight(question, result)
    try:
        user = (
            f"用户问题：{question}\n\n执行的 SQL：\n{sql}\n\n"
            f"结果摘要（JSON）：\n{_summarize_for_llm(result)}"
        )
        data = await llm.chat_json(prompts.INSIGHT_SYSTEM, user, max_tokens=800)
        headline = str(data.get("headline", "")).strip()
        bullets = [str(b).strip() for b in data.get("bullets", []) if str(b).strip()][:4]
        followups = [str(f).strip() for f in data.get("followups", []) if str(f).strip()][:3]
        if not headline or not bullets:
            raise llm.LLMError("洞察字段不完整")
        return Insight(headline=headline, bullets=bullets, followups=followups)
    except llm.LLMError:
        return heuristic_insight(question, result)
