"""查询执行器：只读连接 DuckDB，带超时与行数上限。"""
from __future__ import annotations

import threading
import time
from typing import Any

import duckdb

from .. import config, store
from ..utils import rows_to_jsonable


class QueryError(RuntimeError):
    """SQL 执行失败（数据库返回的错误）。"""


def execute_sql(dataset_id: str, sql: str, max_rows: int | None = None,
                timeout_s: int | None = None) -> dict[str, Any]:
    meta = store.get_dataset(dataset_id)
    if not meta:
        raise QueryError("数据集不存在")

    db_path = config.DATASETS_DIR / f"{dataset_id}.duckdb"
    if not db_path.exists():
        raise QueryError("数据文件缺失，请重新上传数据集")

    max_rows = max_rows or config.MAX_ROWS
    timeout_s = timeout_s or config.QUERY_TIMEOUT_S

    conn = duckdb.connect(str(db_path), read_only=True)
    timer = threading.Timer(timeout_s, conn.interrupt)
    timer.start()
    started = time.perf_counter()
    try:
        cursor = conn.execute(sql)
        columns = [d[0] for d in (cursor.description or [])]
        fetched = cursor.fetchmany(max_rows + 1)
        truncated = len(fetched) > max_rows
        rows = rows_to_jsonable([tuple(r) for r in fetched[:max_rows]])
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return {
            "columns": columns,
            "rows": rows,
            "total_rows": len(rows),
            "truncated": truncated,
            "elapsed_ms": elapsed_ms,
        }
    except duckdb.Error as exc:
        raise QueryError(str(exc)) from exc
    finally:
        timer.cancel()
        try:
            conn.close()
        except Exception:
            pass
