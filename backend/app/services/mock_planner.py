"""演示模式（无 API Key 时兜底）：基于字段类型 + 关键词的规则版 NL2SQL。

用途：保证比赛现场断网 / 模型超时 / 未配置 Key 时依然能完整演示。
真实模型可用时（配置了 LLM_API_KEY）不会走这里。
"""
from __future__ import annotations

import re
from typing import Any

from ..models import ColumnInfo, DatasetInfo

TIME_KEYWORDS = ("趋势", "走势", "每月", "各月", "按月", "每天", "按天", "按小时", "每小时", "时间", "日报")
SHARE_KEYWORDS = ("占比", "比例", "构成", "分布")
RATE_KEYWORDS = ("退款率", "退货率", "转化率", "占比率", "率")
TOP_KEYWORDS = ("最高", "最多", "最大", "排名", "前三", "前五", "top", "最好", "排行")
LOW_KEYWORDS = ("最低", "最小", "最少", "最差", "倒数", "垫底")
COUNT_KEYWORDS = ("订单量", "订单数", "多少单", "单量", "人数", "用户数", "多少")
AMOUNT_HINTS = ("amount", "sales", "gmv", "revenue", "price", "金额", "销售额", "收入", "价格", "单价", "费用")
AMOUNT_EXCLUDE = ("id", "quantity", "qty", "count", "num", "数量", "人数", "次数", "编号", "用户")


def _q(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _pick_time(columns: list[ColumnInfo]) -> ColumnInfo | None:
    for col in columns:
        if col.dtype == "TIMESTAMP":
            return col
    return None


def _pick_numeric(columns: list[ColumnInfo]) -> list[ColumnInfo]:
    return [c for c in columns if c.dtype in {"BIGINT", "DOUBLE"}]


def _pick_amount(columns: list[ColumnInfo]) -> ColumnInfo | None:
    numerics = _pick_numeric(columns)
    for col in numerics:
        low = col.name.lower()
        if any(h in low or h in col.name for h in AMOUNT_HINTS):
            return col
    candidates = [
        c for c in numerics
        if not any(h in c.name.lower() or h in c.name for h in AMOUNT_EXCLUDE)
    ]
    return candidates[0] if candidates else (numerics[0] if numerics else None)


def _string_columns(columns: list[ColumnInfo]) -> list[ColumnInfo]:
    return [c for c in columns if c.dtype == "VARCHAR" and c.distinct and c.distinct <= 60]


def _pick_category(columns: list[ColumnInfo], question: str) -> ColumnInfo | None:
    """优先匹配问题里出现的维度关键词，其次按常见字段名兜底。"""
    strings = _string_columns(columns)
    keyword_map = [
        ("品类", ("category", "品类", "product", "产品", "类目")),
        ("产品", ("product", "产品", "品类")),
        ("渠道", ("channel", "渠道", "来源")),
        ("城市", ("city", "城市")),
        ("区域", ("region", "区域", "地区", "大区")),
        ("地区", ("region", "区域", "地区", "大区")),
        ("平台", ("platform", "平台", "channel", "渠道")),
    ]
    for keyword, hints in keyword_map:
        if keyword in question:
            for col in strings:
                if any(hint in col.name.lower() or hint in col.name for hint in hints):
                    return col
    for hint in ("region", "区域", "category", "品类", "channel", "渠道", "city", "城市", "product", "产品"):
        for col in strings:
            if hint in col.name.lower() or hint in col.name:
                return col
    return strings[0] if strings else None


def _pick_bool(columns: list[ColumnInfo]) -> ColumnInfo | None:
    for col in columns:
        if col.dtype == "BOOLEAN":
            return col
    return None


def _time_filter(question: str, time_col: ColumnInfo, table: str) -> str | None:
    """演示数据专用的一些时间口径（真实模型由 Prompt 处理）。"""
    t = _q(time_col.name)
    tbl = _q(table)
    if any(keyword in question for keyword in ("双11", "双十一", "11.11", "11月11")):
        return f"CAST({t} AS DATE) = DATE '2025-11-11'"
    if "上个月" in question:
        return (
            f"{t} >= date_trunc('month', (SELECT MAX({t}) FROM {tbl}) - INTERVAL '1 month') "
            f"AND {t} < date_trunc('month', (SELECT MAX({t}) FROM {tbl}))"
        )
    if any(keyword in question for keyword in ("最近30天", "近30天", "最近一个月", "近一个月")):
        return f"{t} >= (SELECT MAX({t}) FROM {tbl}) - INTERVAL '30 days'"
    if any(keyword in question for keyword in ("最近7天", "近7天", "最近一周")):
        return f"{t} >= (SELECT MAX({t}) FROM {tbl}) - INTERVAL '7 days'"
    return None


def _with_filter(base: str, where: str | None) -> str:
    if not where:
        return base
    return base.replace(" GROUP BY ", " WHERE " + where + " GROUP BY ", 1)


def _dim_where(category_col: ColumnInfo | None, where: str | None) -> str | None:
    """维度聚合时排除维度为空的分组（如 category 为 NULL 的行）。"""
    if not category_col:
        return where
    cond = f"{_q(category_col.name)} IS NOT NULL"
    return f"{where} AND {cond}" if where else cond


def plan(question: str, info: DatasetInfo, table: str | None = None) -> dict[str, Any]:
    q = question.lower()
    table = table or info.table_name
    time_col = _pick_time(info.columns)
    amount_col = _pick_amount(info.columns)
    category_col = _pick_category(info.columns, question)
    bool_col = _pick_bool(info.columns)
    is_rate = any(keyword in question for keyword in RATE_KEYWORDS) and bool_col is not None
    cat_label = category_col.name if category_col else "分组"
    for keyword in ("品类", "产品", "渠道", "城市", "区域", "地区"):
        if keyword in question:
            cat_label = keyword
            break
    where = _time_filter(question, time_col, table) if time_col else None

    def finish(sql: str, chart: dict[str, Any], plan_text: str,
               assumptions: list[str] | None = None) -> dict[str, Any]:
        return {
            "intent": "query",
            "plan": plan_text,
            "sql": sql,
            "chart": chart,
            "insight_focus": ["趋势", "峰值", "对比", "贡献度"],
            "assumptions": assumptions or [],
            "clarification": None,
        }

    # 1) 退款率 / 比率类
    if is_rate and category_col and bool_col:
        dim_where = _dim_where(category_col, where)
        sql = (
            f'SELECT {_q(category_col.name)} AS "{cat_label}", '
            f'ROUND(SUM(CASE WHEN {_q(bool_col.name)} THEN 1 ELSE 0 END) * 100.0 '
            f'/ NULLIF(COUNT(*), 0), 2) AS "退款率(%)" '
            f'FROM {_q(table)}'
            + (f" WHERE {dim_where}" if dim_where else "")
            + ' GROUP BY 1 ORDER BY 2 DESC LIMIT 20'
        )
        return finish(sql, {
            "type": "bar", "title": f"各{cat_label}退款率（%）",
            "x": cat_label, "y": ["退款率(%)"], "series": None, "sort": "y_desc",
        }, f"按{cat_label}计算退款率并降序排列", ["退款率 = 退款订单数 / 订单总数"])

    # 2) 占比 / 构成
    if category_col and amount_col and any(keyword in question for keyword in SHARE_KEYWORDS):
        dim_where = _dim_where(category_col, where)
        sql = (
            f'SELECT {_q(category_col.name)} AS "{cat_label}", '
            f'ROUND(SUM({_q(amount_col.name)}), 2) AS "销售额" '
            f'FROM {_q(table)}'
            + (f" WHERE {dim_where}" if dim_where else "")
            + ' GROUP BY 1 ORDER BY 2 DESC LIMIT 20'
        )
        return finish(sql, {
            "type": "pie", "title": f"{cat_label}销售额占比",
            "x": cat_label, "y": ["销售额"], "series": None, "sort": "y_desc",
        }, f"按{cat_label}汇总销售额并查看占比")

    # 3) 时间趋势
    if time_col and any(keyword in question for keyword in TIME_KEYWORDS):
        if any(keyword in question for keyword in ("每月", "各月", "按月")):
            trunc, label = "month", "按月"
        elif "小时" in question:
            trunc, label = "hour", "按小时"
        else:
            trunc, label = "day", "按天"
        has_count_kw = any(keyword in question for keyword in COUNT_KEYWORDS)
        if has_count_kw and not amount_col:
            agg, alias = 'COUNT(*) AS "订单量"', "订单量"
        elif has_count_kw:
            agg, alias = f'COUNT(*) AS "订单量", ROUND(SUM({_q(amount_col.name)}), 2) AS "销售额"', "销售额"
        else:
            agg = f'ROUND(SUM({_q(amount_col.name)}), 2) AS "销售额"' if amount_col else 'COUNT(*) AS "订单量"'
            alias = "销售额" if amount_col else "订单量"
        sql = (
            f'SELECT date_trunc(\'{trunc}\', {_q(time_col.name)}) AS "时间", {agg} '
            f'FROM {_q(table)}'
        )
        if where:
            sql += f" WHERE {where}"
        sql += " GROUP BY 1 ORDER BY 1 LIMIT 1000"
        title = f"{label}销售额趋势" if amount_col else f"{label}订单量趋势"
        return finish(sql, {
            "type": "line", "title": title,
            "x": "时间", "y": [alias], "series": None, "sort": "x",
        }, f"{label}聚合{amount_col.name if amount_col else '记录数'}")

    # 4) Top N / 排名（支持最高/最低两个方向）
    if category_col and amount_col and (
        any(keyword in question for keyword in TOP_KEYWORDS)
        or any(keyword in question for keyword in LOW_KEYWORDS)
    ):
        low_intent = any(keyword in question for keyword in LOW_KEYWORDS)
        limit = 5
        match = re.search(r"(\d+)\s*(个|名|条|位)?", question)
        if match:
            limit = max(1, min(int(match.group(1)), 20))
        direction = "ASC" if low_intent else "DESC"
        dim_where = _dim_where(category_col, where)
        sql = (
            f'SELECT {_q(category_col.name)} AS "{cat_label}", '
            f'ROUND(SUM({_q(amount_col.name)}), 2) AS "销售额" '
            f'FROM {_q(table)}'
        )
        if dim_where:
            sql += f" WHERE {dim_where}"
        sql += f" GROUP BY 1 ORDER BY 2 {direction} LIMIT {limit}"
        if low_intent:
            return finish(sql, {
                "type": "bar", "title": f"销售额最低的 {limit} 个{cat_label}",
                "x": cat_label, "y": ["销售额"], "series": None, "sort": None,
            }, f"按{cat_label}汇总后取销售额最低的 {limit} 个")
        return finish(sql, {
            "type": "bar", "title": f"销售额 Top {limit} {cat_label}",
            "x": cat_label, "y": ["销售额"], "series": None, "sort": "y_desc",
        }, f"按{cat_label}汇总后取销售额前 {limit}")

    # 5) 客单价
    order_col = next((c for c in info.columns if "order_id" in c.name.lower() or "订单" in c.name), None)
    if order_col and amount_col and "客单价" in question:
        sql = (
            f'SELECT ROUND(SUM({_q(amount_col.name)}) / NULLIF(COUNT(DISTINCT {_q(order_col.name)}), 0), 2) '
            f'AS "客单价" FROM {_q(table)}'
        )
        return finish(sql, {
            "type": "table", "title": "客单价", "x": None,
            "y": ["客单价"], "series": None, "sort": None,
        }, "销售额 / 订单数", ["客单价 = 销售额 / 去重订单数"])

    # 6) 默认：维度汇总
    if category_col and amount_col:
        dim_where = _dim_where(category_col, where)
        sql = (
            f'SELECT {_q(category_col.name)} AS "{cat_label}", '
            f'ROUND(SUM({_q(amount_col.name)}), 2) AS "销售额", COUNT(*) AS "订单量" '
            f'FROM {_q(table)}'
        )
        if dim_where:
            sql += f" WHERE {dim_where}"
        sql += ' GROUP BY 1 ORDER BY 2 DESC LIMIT 20'
        return finish(sql, {
            "type": "bar", "title": f"各{cat_label}销售额",
            "x": cat_label, "y": ["销售额"], "series": None, "sort": "y_desc",
        }, f"按{cat_label}汇总销售额")

    # 7) 兜底：数据预览
    sql = f'SELECT * FROM {_q(table)} LIMIT 20'
    return finish(
        sql,
        {"type": "table", "title": "数据预览", "x": None, "y": [], "series": None, "sort": None},
        "未匹配到明确聚合意图，先返回数据样例", [],
    )
