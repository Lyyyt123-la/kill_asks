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
