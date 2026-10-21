"""SQL 安全校验：只读、单语句、表/字段白名单、禁止危险函数、强制 LIMIT。"""
from __future__ import annotations

import re
from typing import Iterable

from .. import config

try:
    import sqlglot
    from sqlglot import exp

    HAS_SQLGLOT = True
except Exception:  # pragma: no cover - 环境缺包时降级
    HAS_SQLGLOT = False


class SqlGuardError(ValueError):
    """SQL 未通过安全校验。"""


_FORBIDDEN_NODE_NAMES = {
    "Insert", "Update", "Delete", "Create", "Drop", "Alter", "Command",
    "Pragma", "Attach", "Detach", "Copy", "Export", "Transaction",
    "Commit", "Rollback", "Merge", "Use", "Set", "Grant", "Revoke",
}

_FORBIDDEN_FUNCTIONS = {
    "read_csv", "read_csv_auto", "read_parquet", "read_json", "read_json_auto",
    "read_text", "read_blob", "glob", "parquet_scan", "csv_scan", "json_scan",
    "sqlite_scan", "postgres_scan", "mysql_scan", "httpfs", "load", "install",
    "shell", "system", "getenv", "sniff_csv", "read_xlsx",
}


def _fallback_validate(sql: str, allowed_tables: Iterable[str]) -> str:
    """sqlglot 不可用时的最小校验：只允许 SELECT/WITH，禁止多语句与危险关键字。"""
    text = sql.strip().rstrip(";").strip()
    if not text:
        raise SqlGuardError("SQL 为空")
    if ";" in text:
        raise SqlGuardError("只允许单条 SQL 语句")
    lowered = text.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise SqlGuardError("只允许 SELECT / WITH 查询")
    forbidden = ["insert ", "update ", "delete ", "drop ", "create ", "alter ",
                 "attach ", "copy ", "pragma ", "export ", "install ", "load "]
    for word in forbidden:
        if word in lowered:
            raise SqlGuardError(f"SQL 中包含不允许的操作：{word.strip()}")
    tables = set(re.findall(r"(?:from|join)\s+([\w\".`]+)", lowered))
    allowed = {t.lower() for t in allowed_tables}
    for table in tables:
        clean = table.strip('"`').split(".")[-1]
        if clean not in allowed:
            raise SqlGuardError(f"不允许访问表：{table}")
    if not re.search(r"\blimit\s+\d+", lowered):
        text += f" LIMIT {config.MAX_ROWS}"
    return text


def validate_sql(sql: str, allowed_tables: Iterable[str]) -> str:
    """校验并规范化 SQL，返回可直接执行的 SQL。"""
    if not sql or not str(sql).strip():
        raise SqlGuardError("SQL 为空")
    allowed = {t.lower() for t in allowed_tables}

    if not HAS_SQLGLOT:
        return _fallback_validate(sql, allowed)

    try:
        statements = sqlglot.parse(sql, read="duckdb")
    except Exception as exc:
        raise SqlGuardError(f"SQL 语法解析失败：{exc}") from exc

    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        raise SqlGuardError("只允许单条 SQL 语句")

    stmt = statements[0]
    if not isinstance(stmt, (exp.Select, exp.Union)):
        raise SqlGuardError("只允许 SELECT / WITH 查询")

    for node in stmt.walk():
        name = type(node).__name__
        if name in _FORBIDDEN_NODE_NAMES:
            raise SqlGuardError(f"SQL 中包含不允许的操作：{name}")
        if isinstance(node, exp.Anonymous):
            fn = (node.name or "").lower()
            if fn in _FORBIDDEN_FUNCTIONS:
                raise SqlGuardError(f"SQL 中包含不允许的函数：{fn}")
        if isinstance(node, exp.Table):
            table = (node.name or "").lower()
            if table and table not in allowed:
                raise SqlGuardError(f"不允许访问表：{node.name}")

    # 强制 LIMIT
    if not stmt.args.get("limit"):
        stmt = stmt.limit(config.MAX_ROWS)

    return stmt.sql(dialect="duckdb")
