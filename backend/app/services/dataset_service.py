"""数据接入：上传 CSV / Excel → pandas 解析 → DuckDB 建表 → 元数据登记。"""
from __future__ import annotations

import io
import json
import uuid
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from .. import config, store
from ..models import ColumnInfo, DatasetInfo
from ..utils import dtype_name, rows_to_jsonable

CSV_ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "gbk")
EXCEL_EXT = {".xlsx", ".xlsm", ".xls"}
MAX_DATA_ROWS = 500_000


def _read_csv(data: bytes) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in CSV_ENCODINGS:
        try:
            return pd.read_csv(io.BytesIO(data), encoding=encoding, sep=None, engine="python")
        except Exception as exc:  # noqa: PERF203
            last_error = exc
    raise ValueError(f"CSV 解析失败（已尝试 utf-8/gb18030/gbk）：{last_error}")


def _read_excel(data: bytes, filename: str) -> pd.DataFrame:
    if filename.lower().endswith(".xls"):
        raise ValueError("暂不支持旧版 .xls，请另存为 .xlsx 或 .csv 后重新上传")
    return pd.read_excel(io.BytesIO(data), sheet_name=0)


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    seen: dict[str, int] = {}
    columns: list[str] = []
    for index, raw in enumerate(df.columns):
        name = str(raw).strip() or f"col_{index + 1}"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        columns.append(name)
    df.columns = columns
    return df


def _infer_datetimes(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        series = df[col]
        # pandas 3.0 的字符串列 dtype 不再是 object，需要同时兼容
        if not (series.dtype == object or pd.api.types.is_string_dtype(series)):
            continue
        if pd.api.types.is_bool_dtype(series):
            continue
        sample = series.dropna()
        if len(sample) < 5:
            continue
        sample = sample.head(200).astype(str)
        try:
            parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
        except (ValueError, TypeError):
            continue
        if parsed.notna().mean() >= 0.85:
            df[col] = pd.to_datetime(series, errors="coerce", format="mixed")
    return df


def _column_infos(df: pd.DataFrame) -> list[ColumnInfo]:
    infos: list[ColumnInfo] = []
    for col in df.columns:
        series = df[col]
        non_null = series.dropna()
        try:
            distinct = int(non_null.nunique())
        except TypeError:
            distinct = None
        samples = [str(v) for v in non_null.unique()[:3]] if len(non_null) else []
        enum_values = None
        if distinct is not None and 1 < distinct <= 20:
            enum_values = [str(v) for v in non_null.unique()[:20]]
        null_ratio = float(series.isna().mean()) if len(series) else 0.0
        min_value = max_value = None
        if len(non_null):
            try:
                if pd.api.types.is_datetime64_any_dtype(series):
                    min_value = str(non_null.min())[:19]
                    max_value = str(non_null.max())[:19]
                elif pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
                    min_value = f"{float(non_null.min()):.4g}"
                    max_value = f"{float(non_null.max()):.4g}"
            except (TypeError, ValueError):
                min_value = max_value = None
        infos.append(
            ColumnInfo(
                name=str(col),
                dtype=dtype_name(series),
                nullable=bool(series.isna().any()),
                samples=samples,
                distinct=distinct,
                enum_values=enum_values,
                null_ratio=round(null_ratio, 4),
                min_value=min_value,
                max_value=max_value,
            )
        )
    return infos


def _write_duckdb(dataset_id: str, df: pd.DataFrame) -> str:
    table_name = dataset_id
    db_path = config.DATASETS_DIR / f"{dataset_id}.duckdb"
    con = duckdb.connect(str(db_path))
    try:
        view_name = "_upload_df"
        con.register(view_name, df)
        con.execute(f'CREATE OR REPLACE TABLE "{table_name}" AS SELECT * FROM {view_name}')
        con.unregister(view_name)
        count = con.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]
    finally:
        con.close()
    if count == 0:
        raise ValueError("数据为空，无法创建数据集")
    return table_name


def save_upload(filename: str, data: bytes, display_name: str | None = None,
                dataset_id: str | None = None) -> DatasetInfo:
    if not data:
        raise ValueError("文件为空")
    ext = Path(filename).suffix.lower()
    if ext not in {".csv", *EXCEL_EXT}:
        raise ValueError("仅支持 .csv / .xlsx / .xlsm 文件")
    if len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise ValueError(f"文件超过 {config.MAX_UPLOAD_MB}MB 限制")

    df = _read_csv(data) if ext == ".csv" else _read_excel(data, filename)
    df = _normalize_columns(df)
    df = _infer_datetimes(df)
    df = df.dropna(how="all").reset_index(drop=True)
    if df.empty:
        raise ValueError("文件没有有效数据行")
    if len(df) > MAX_DATA_ROWS:
        raise ValueError(f"数据行数超过 {MAX_DATA_ROWS:,} 行，请先抽样后上传")

    dataset_id = dataset_id or ("ds_" + uuid.uuid4().hex[:10])
    table_name = _write_duckdb(dataset_id, df)
    infos = _column_infos(df)

    upload_dir = config.UPLOADS_DIR / dataset_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_file = Path(filename).name
    (upload_dir / safe_file).write_bytes(data)

    created_at = store.now_iso()
    meta = {
        "id": dataset_id,
        "name": (display_name or Path(filename).stem).strip()[:60] or dataset_id,
        "table_name": table_name,
        "source_file": safe_file,
        "rows": int(len(df)),
        "cols": int(len(df.columns)),
        "created_at": created_at,
        "sheet": None,
        "columns_json": json.dumps([c.model_dump() for c in infos], ensure_ascii=False),
    }
    store.save_dataset(meta)
    return DatasetInfo(
        id=dataset_id,
        name=meta["name"],
        table_name=table_name,
        source_file=safe_file,
        rows=meta["rows"],
        cols=meta["cols"],
        created_at=created_at,
        sheet=None,
        columns=infos,
    )


def save_dataframe(df: pd.DataFrame, name: str, source_file: str = "document_table") -> DatasetInfo:
    """把内存中的 DataFrame 直接注册为可分析数据集（用于 PDF/Word/图片表格提取）。"""
    if df is None or df.empty:
        raise ValueError("表格为空")
    df = _normalize_columns(df.copy())
    df = _infer_datetimes(df)
    df = df.dropna(how="all").reset_index(drop=True)
    if df.empty:
        raise ValueError("表格没有有效数据行")
    if len(df) > MAX_DATA_ROWS:
        raise ValueError(f"表格行数超过 {MAX_DATA_ROWS:,} 行")

    dataset_id = "ds_" + uuid.uuid4().hex[:10]
    table_name = _write_duckdb(dataset_id, df)
    infos = _column_infos(df)
    created_at = store.now_iso()
    safe_source = Path(source_file).name if source_file else "document_table"
    meta = {
        "id": dataset_id,
        "name": (name or "文档表格")[:60],
        "table_name": table_name,
        "source_file": safe_source,
        "rows": int(len(df)),
        "cols": int(len(df.columns)),
        "created_at": created_at,
        "sheet": None,
        "columns_json": json.dumps([c.model_dump() for c in infos], ensure_ascii=False),
    }
    store.save_dataset(meta)
    return DatasetInfo(
        id=dataset_id, name=meta["name"], table_name=table_name,
        source_file=safe_source, rows=meta["rows"], cols=meta["cols"],
        created_at=created_at, sheet=None, columns=infos,
    )


def get_dataset_info(dataset_id: str) -> DatasetInfo | None:
    meta = store.get_dataset(dataset_id)
    if not meta:
        return None
    columns = [ColumnInfo(**c) for c in json.loads(meta["columns_json"])]
    return DatasetInfo(
        id=meta["id"], name=meta["name"], table_name=meta["table_name"],
        source_file=meta["source_file"], rows=meta["rows"], cols=meta["cols"],
        created_at=meta["created_at"], sheet=meta["sheet"], columns=columns,
    )


def list_datasets() -> list[dict[str, Any]]:
    return [
        {
            "id": m["id"], "name": m["name"], "rows": m["rows"],
            "cols": m["cols"], "created_at": m["created_at"],
            "source_file": m["source_file"],
        }
        for m in store.list_datasets()
    ]


def get_preview(dataset_id: str, limit: int = 50) -> dict[str, Any]:
    meta = store.get_dataset(dataset_id)
    if not meta:
        raise ValueError("数据集不存在")
    db_path = config.DATASETS_DIR / f"{dataset_id}.duckdb"
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        cursor = con.execute(f'SELECT * FROM "{meta["table_name"]}" LIMIT {int(limit)}')
        columns = [d[0] for d in cursor.description]
        rows = rows_to_jsonable([tuple(r) for r in cursor.fetchall()])
    finally:
        con.close()
    return {
        "columns": columns,
        "rows": rows,
        "total": meta["rows"],
        "truncated": meta["rows"] > limit,
    }


def build_schema_block(info: DatasetInfo) -> str:
    """把数据集结构渲染成给 LLM 的文本。"""
    lines = [f"表名：{info.table_name}（行数：{info.rows:,}，列数：{info.cols}）", "字段："]
    for col in info.columns:
        sample = " | ".join(col.samples[:2]) if col.samples else "无样例"
        extra = []
        if col.min_value is not None and col.max_value is not None:
            extra.append(f"范围 {col.min_value} ~ {col.max_value}")
        if col.enum_values:
            extra.append("枚举=" + "/".join(col.enum_values[:12]))
        if col.null_ratio:
            extra.append(f"空值率={col.null_ratio * 100:.1f}%")
        tail = f"  （{'; '.join(extra)}）" if extra else ""
        lines.append(f"- {col.name}  {col.dtype}  样例：{sample}{tail}")
    lines.append("注意：SQL 中的中文标识符必须使用双引号包裹。")
    return "\n".join(lines)


def get_data_time_range(info: DatasetInfo) -> str:
    """返回数据里时间字段的实际范围（用于让模型按数据日期理解“上个月/双11”）。"""
    ranges = []
    for col in info.columns:
        if col.dtype == "TIMESTAMP" and col.min_value and col.max_value:
            ranges.append(f"{col.name}: {col.min_value} ~ {col.max_value}")
    return "；".join(ranges) if ranges else "未知（数据中没有时间字段）"


def build_metric_dict(info: DatasetInfo) -> str:
    """根据字段类型自动生成口径提示。"""
    numeric = [c.name for c in info.columns if c.dtype in {"BIGINT", "DOUBLE"}]
    booleans = [c.name for c in info.columns if c.dtype == "BOOLEAN"]
    lines = [
        "- 通用聚合：数值字段求和用 SUM(col)，均值用 AVG(col)，计数用 COUNT(*) 或 COUNT(DISTINCT col)。",
        "- 比率计算：SUM(条件表达式) * 1.0 / COUNT(*) · 100，注意用 NULLIF 防止除零。",
        "- 金额字段保留 2 位小数：ROUND(SUM(col), 2)。",
    ]
    if numeric:
        lines.append("- 可用数值字段：" + "、".join(numeric))
    if booleans:
        lines.append("- 布尔字段（可用于计算比率）：" + "、".join(booleans))
    return "\n".join(lines)


def load_demo() -> DatasetInfo:
    """载入内置示例数据集（幂等）。"""
    existing = store.get_dataset(config.DEMO_DATASET_ID)
    if existing:
        info = get_dataset_info(config.DEMO_DATASET_ID)
        if info:
            return info
    if not config.DEMO_DATASET_FILE.exists():
        raise ValueError("示例数据文件不存在，请先运行 scripts/gen_demo_data.py 生成")
    data = config.DEMO_DATASET_FILE.read_bytes()
    return save_upload(
        config.DEMO_DATASET_FILE.name,
        data,
        display_name=config.DEMO_DATASET_NAME,
        dataset_id=config.DEMO_DATASET_ID,
    )


def delete_dataset(dataset_id: str) -> None:
    meta = store.get_dataset(dataset_id)
    if not meta:
        raise ValueError("数据集不存在")
    db_path = config.DATASETS_DIR / f"{dataset_id}.duckdb"
    for path in (db_path,):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
    upload_dir = config.UPLOADS_DIR / dataset_id
    if upload_dir.exists():
        import shutil
        shutil.rmtree(upload_dir, ignore_errors=True)
    store.delete_dataset(dataset_id)
