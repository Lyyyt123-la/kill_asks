"""Pydantic 数据模型：API 入参/出参。"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------- 数据集 ----------------
class ColumnInfo(BaseModel):
    name: str
    dtype: str
    nullable: bool = True
    samples: list[str] = Field(default_factory=list)
    distinct: int | None = None
    enum_values: list[str] | None = None
    null_ratio: float | None = None
    min_value: str | None = None
    max_value: str | None = None


class DatasetInfo(BaseModel):
    id: str
    name: str
    table_name: str
    source_file: str
    rows: int
    cols: int
    created_at: str
    sheet: str | None = None
    columns: list[ColumnInfo] = Field(default_factory=list)


class DatasetListItem(BaseModel):
    id: str
    name: str
    rows: int
    cols: int
    created_at: str
    source_file: str


class PreviewResponse(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
    total: int
    truncated: bool = False


# ---------------- 对话 ----------------
class HistoryTurn(BaseModel):
    question: str
    sql: str | None = None
    columns: list[str] = Field(default_factory=list)
    summary: str | None = None


class ChatRequest(BaseModel):
    dataset_id: str
    question: str = Field(min_length=1, max_length=2000)
    history: list[HistoryTurn] = Field(default_factory=list)


class ChartSpec(BaseModel):
    type: Literal["line", "bar", "pie", "scatter", "table"] = "table"
    title: str = ""
    x: str | None = None
    y: list[str] = Field(default_factory=list)
    series: str | None = None
    sort: Literal["x", "y_desc"] | None = None


class StepInfo(BaseModel):
    key: str
    label: str
    status: Literal["pending", "running", "done", "error"] = "done"
    detail: str | None = None
    elapsed_ms: int | None = None


class Insight(BaseModel):
    headline: str = ""
    bullets: list[str] = Field(default_factory=list)
    followups: list[str] = Field(default_factory=list)


class QueryResult(BaseModel):
    columns: list[str] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)
    total_rows: int = 0
    truncated: bool = False
    elapsed_ms: int = 0


class ChatResponse(BaseModel):
    ok: bool = True
    intent: Literal["query", "clarify", "unsupported", "error"] = "query"
    question: str = ""
    plan: str = ""
    sql: str | None = None
    result: QueryResult | None = None
    chart: ChartSpec | None = None
    insight: Insight | None = None
    assumptions: list[str] = Field(default_factory=list)
    clarification: dict[str, Any] | None = None
    steps: list[StepInfo] = Field(default_factory=list)
    error: str | None = None
    attempts: int = 0
    model: str = ""
    mock: bool = False
    elapsed_ms: int = 0


class RawQueryRequest(BaseModel):
    dataset_id: str
    sql: str
