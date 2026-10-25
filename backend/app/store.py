"""轻量元数据存储（SQLite）：数据集信息。"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

from . import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS datasets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    table_name TEXT NOT NULL,
    source_file TEXT NOT NULL,
    rows INTEGER NOT NULL,
    cols INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    sheet TEXT,
    columns_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    file_type TEXT NOT NULL,
    source_file TEXT NOT NULL,
    created_at TEXT NOT NULL,
    chars INTEGER NOT NULL DEFAULT 0,
    text TEXT NOT NULL DEFAULT '',
    chunks_json TEXT NOT NULL DEFAULT '[]',
    tables_json TEXT NOT NULL DEFAULT '[]'
);
"""


def _conn() -> sqlite3.Connection:
    config.ensure_dirs()
    conn = sqlite3.connect(config.META_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.executescript(_SCHEMA)


def save_dataset(meta: dict[str, Any]) -> None:
    with _conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO datasets
               (id, name, table_name, source_file, rows, cols, created_at, sheet, columns_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                meta["id"], meta["name"], meta["table_name"], meta["source_file"],
                meta["rows"], meta["cols"], meta["created_at"], meta.get("sheet"),
                meta["columns_json"],
            ),
        )


def get_dataset(dataset_id: str) -> dict[str, Any] | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
    return dict(row) if row else None


def list_datasets() -> list[dict[str, Any]]:
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM datasets ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def delete_dataset(dataset_id: str) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM datasets WHERE id = ?", (dataset_id,))


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------- 文档（PDF / Word / 图片） ----------------
def save_document(meta: dict[str, Any]) -> None:
    with _conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO documents
               (id, name, file_type, source_file, created_at, chars, text, chunks_json, tables_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                meta["id"], meta["name"], meta["file_type"], meta["source_file"],
                meta["created_at"], meta["chars"], meta["text"],
                meta["chunks_json"], meta["tables_json"],
            ),
        )


def get_document(doc_id: str, with_text: bool = True) -> dict[str, Any] | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    if not row:
        return None
    data = dict(row)
    if not with_text:
        data.pop("text", None)
        data.pop("chunks_json", None)
    return data


def list_documents() -> list[dict[str, Any]]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, name, file_type, source_file, created_at, chars, tables_json "
            "FROM documents ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def delete_document(doc_id: str) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
