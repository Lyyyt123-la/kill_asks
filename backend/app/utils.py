"""通用工具：类型归一、JSON 序列化、计时。"""
from __future__ import annotations

import datetime as _dt
import decimal
import math
from typing import Any

import numpy as np
import pandas as pd


def to_jsonable(value: Any) -> Any:
    """把 DuckDB / pandas 返回的各种类型转成可 JSON 序列化的原生类型。"""
    if value is None:
        return None
    if isinstance(value, (str, bool, int, float)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        return value
    if isinstance(value, (_dt.datetime, _dt.date, _dt.time)):
        return value.isoformat(sep=" ") if isinstance(value, _dt.datetime) else value.isoformat()
    if isinstance(value, _dt.timedelta):
        return str(value)
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, np.generic):
        return to_jsonable(value.item())
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if value is pd.NaT or (isinstance(value, float) and math.isnan(value)):
        return None
    return str(value)


def rows_to_jsonable(rows: list[tuple[Any, ...]]) -> list[list[Any]]:
    return [[to_jsonable(v) for v in row] for row in rows]


def dtype_name(series: pd.Series) -> str:
    """把 pandas dtype 转成对 LLM 更友好的 SQL 类型名。"""
    dtype = series.dtype
    if pd.api.types.is_bool_dtype(dtype):
        return "BOOLEAN"
    if pd.api.types.is_integer_dtype(dtype):
        return "BIGINT"
    if pd.api.types.is_float_dtype(dtype):
        return "DOUBLE"
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "TIMESTAMP"
    if pd.api.types.is_timedelta64_dtype(dtype):
        return "INTERVAL"
    try:
        if pd.api.types.is_string_dtype(dtype):
            return "VARCHAR"
        if pd.api.types.is_numeric_dtype(dtype):
            return "DOUBLE"
    except Exception:
        pass
    return "VARCHAR"


def human_dtype(dtype: str) -> str:
    mapping = {
        "int64": "整数", "Int64": "整数", "float64": "浮点数", "float32": "浮点数",
        "bool": "布尔", "boolean": "布尔", "object": "文本", "string": "文本",
        "datetime64[ns]": "时间", "datetime64[us]": "时间",
    }
    return mapping.get(str(dtype), str(dtype))


def safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def fmt_num(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "-"
    if abs(value) >= 1_0000_0000:
        return f"{value / 1_0000_0000:.{digits}f} 亿"
    if abs(value) >= 1_0000:
        return f"{value / 1_0000:.{digits}f} 万"
    return f"{value:,.{digits}f}"
