"""文档/图片解析：PDF、Word、图片 → 表格数据集成 + 正文切片（RAG）。

- PDF：pdfplumber 提取文字与表格；扫描件回退为「渲染页面 → 视觉模型 OCR」
- Word：python-docx 提取段落与表格
- 图片：调用视觉模型（qwen3-vl-plus 等）识别表格，输出 CSV / Markdown 后转 DataFrame
"""
from __future__ import annotations

import base64
import io
import json
import re
import uuid
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import pdfplumber
from docx import Document

from .. import config, store
from ..models import DocTableInfo, DocumentInfo
from . import dataset_service, rag_service

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
PDF_EXT = {".pdf"}
DOCX_EXT = {".docx"}
SUPPORTED_EXT = PDF_EXT | DOCX_EXT | IMAGE_EXT

VISION_PROMPT = """你是专业的表格识别助手。请识别图片中的内容，优先输出 CSV 格式：
1. 如果图片中有表格：第一行为表头，使用英文逗号分隔；不要输出 Markdown 代码块或解释，只输出 CSV 文本。
2. 如果没有表格但有文字：提取全部文字内容，保留段落换行。
3. 数字保留原样（不要加单位或千分位），空单元格留空。
"""


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:csv|markdown|md|text)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _table_to_df(rows: list[list[Any]]) -> pd.DataFrame | None:
    if not rows or len(rows) < 2:
        return None
    cleaned = [[("" if cell is None else str(cell)).strip() for cell in row] for row in rows]
    cleaned = [row for row in cleaned if any(cell for cell in row)]
    if len(cleaned) < 2:
        return None
    width = max(len(row) for row in cleaned)
    cleaned = [row + [""] * (width - len(row)) for row in cleaned]
    header = [cell or f"col_{index + 1}" for index, cell in enumerate(cleaned[0])]
    # 去重表头
    seen: dict[str, int] = {}
    unique_header: list[str] = []
    for name in header:
        if name in seen:
            seen[name] += 1
            unique_header.append(f"{name}_{seen[name]}")
        else:
            seen[name] = 0
            unique_header.append(name)
    body = [row for row in cleaned[1:] if any(cell for cell in row)]
    if not body:
        return None
    df = pd.DataFrame(body, columns=unique_header)
    df = df.replace("", pd.NA).dropna(how="all").dropna(axis=1, how="all")
    if df.empty or df.shape[1] < 2:
        return None
    return df.reset_index(drop=True)


def _parse_tabular_text(text: str) -> pd.DataFrame | None:
    """把模型输出的 Markdown 表格或 CSV 文本解析成 DataFrame。"""
    text = _strip_code_fences(text)
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    markdown_lines = [line for line in lines if line.strip().startswith("|")]
    if len(markdown_lines) >= 2:
        rows = []
        for line in markdown_lines:
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if all(set(cell) <= set("-: ") for cell in cells):
                continue
            rows.append(cells)
        return _table_to_df(rows)
    if len(lines) >= 2 and any("," in line for line in lines):
        try:
            return _table_to_df([line.split(",") for line in lines])
        except Exception:  # noqa: BLE001
            return None
    return None


def extract_pdf(data: bytes) -> tuple[str, list[pd.DataFrame]]:
    texts: list[str] = []
    tables: list[pd.DataFrame] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception:  # noqa: BLE001
                text = ""
            if text.strip():
                texts.append(f"【第 {page_index} 页】\n{text.strip()}")
            try:
                page_tables = page.extract_tables() or []
            except Exception:  # noqa: BLE001
                page_tables = []
            for rows in page_tables:
                df = _table_to_df(rows)
                if df is not None and len(df) >= 2:
                    tables.append(df)
    return "\n\n".join(texts), tables


def extract_docx(data: bytes) -> tuple[str, list[pd.DataFrame]]:
    document = Document(io.BytesIO(data))
    texts = [p.text.strip() for p in document.paragraphs if p.text.strip()]
    tables: list[pd.DataFrame] = []
    for table in document.tables:
        rows = [[cell.text.strip() for cell in row.cells] for row in table.rows]
        df = _table_to_df(rows)
        if df is not None and len(df) >= 2:
            tables.append(df)
    return "\n".join(texts), tables


def render_pdf_pages(data: bytes, max_pages: int = 3) -> list[bytes]:
    """扫描版 PDF 回退：渲染前几页为 PNG，交给视觉模型 OCR。"""
    try:
        import pypdfium2 as pdfium
    except Exception:  # noqa: BLE001
        return []
    images: list[bytes] = []
    try:
        pdf = pdfium.PdfDocument(data)
        for index in range(min(len(pdf), max_pages)):
            page = pdf[index]
            bitmap = page.render(scale=2.0)
            image = bitmap.to_pil()
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            images.append(buffer.getvalue())
    except Exception:  # noqa: BLE001
        return images
    return images


async def _vision_extract_image(data: bytes, mime: str) -> tuple[str, list[pd.DataFrame]]:
    if not config.LLM_API_KEY:
        raise ValueError("图片识别需要配置视觉模型（LLM_API_KEY），当前为演示模式")
    image_url = f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"
    payload = {
        "model": config.VISION_MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": VISION_PROMPT},
                {"type": "image_url", "image_url": {"url": image_url}},
            ],
        }],
        "temperature": 0.0,
        "max_tokens": 2500,
    }
    endpoint = config.LLM_BASE_URL.rstrip("/") + "/chat/completions"
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            endpoint,
            headers={"Authorization": f"Bearer {config.LLM_API_KEY}", "Content-Type": "application/json"},
            json=payload,
        )
    if resp.status_code >= 400:
        raise ValueError(f"视觉模型调用失败（HTTP {resp.status_code}）：{resp.text[:200]}")
    content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
    if not content:
        raise ValueError("视觉模型没有返回内容")
    text = _strip_code_fences(content)
    df = _parse_tabular_text(text)
    tables = [df] if df is not None else []
    return text, tables


def _document_info_from_row(row: dict[str, Any]) -> DocumentInfo:
    tables = json.loads(row.get("tables_json") or "[]")
    text = row.get("text") or ""
    return DocumentInfo(
        id=row["id"],
        name=row["name"],
        file_type=row["file_type"],
        source_file=row["source_file"],
        created_at=row["created_at"],
        chars=int(row.get("chars") or 0),
        chunks=len(json.loads(row.get("chunks_json") or "[]")),
        tables=[DocTableInfo(**table) for table in tables],
        text_preview=text[:400],
    )


def get_document_info(doc_id: str) -> DocumentInfo | None:
    row = store.get_document(doc_id)
    return _document_info_from_row(row) if row else None


def list_documents() -> list[DocumentInfo]:
    return [_document_info_from_row(row) for row in store.list_documents()]


async def save_document(filename: str, data: bytes) -> DocumentInfo:
    if not data:
        raise ValueError("文件为空")
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXT:
        raise ValueError("仅支持 .pdf / .docx / .png / .jpg / .jpeg / .webp 文件")
    if len(data) > config.MAX_DOC_MB * 1024 * 1024:
        raise ValueError(f"文件超过 {config.MAX_DOC_MB}MB 限制")
    if ext == ".doc":
        raise ValueError("旧版 .doc 不支持，请另存为 .docx")

    if ext in PDF_EXT:
        text, tables = extract_pdf(data)
        if not text.strip() and not tables:
            # 扫描版 PDF：渲染页面 → 视觉模型
            pages = render_pdf_pages(data)
            for page_image in pages[:2]:
                page_text, page_tables = await _vision_extract_image(page_image, "image/png")
                text += "\n" + page_text
                tables.extend(page_tables)
    elif ext in DOCX_EXT:
        text, tables = extract_docx(data)
    else:
        mime = "image/jpeg" if ext in {".jpg", ".jpeg"} else f"image/{ext.lstrip('.')}"
        text, tables = await _vision_extract_image(data, mime)

    text = (text or "").strip()
    if not text and not tables:
        raise ValueError("没有从文档中识别到文字或表格，请检查文件内容")

    doc_id = "doc_" + uuid.uuid4().hex[:10]
    table_infos: list[DocTableInfo] = []
    for index, df in enumerate(tables[:6], start=1):
        try:
            info = dataset_service.save_dataframe(
                df,
                name=f"{Path(filename).stem} · 表格{index}",
                source_file=Path(filename).name,
            )
        except ValueError:
            continue
        table_infos.append(DocTableInfo(
            dataset_id=info.id, name=info.name, rows=info.rows, cols=info.cols,
        ))

    chunks = rag_service.chunk_text(text)
    chunk_payload: list[dict[str, Any]] = [
        {"index": index + 1, "text": chunk}
        for index, chunk in enumerate(chunks)
    ]
    if chunk_payload and config.llm_enabled():
        try:
            vectors = await rag_service.embed_texts([c["text"] for c in chunk_payload])
            for chunk, vector in zip(chunk_payload, vectors):
                chunk["emb"] = vector
        except Exception:  # noqa: BLE001 - 向量失败时退化为关键词检索
            pass

    created_at = store.now_iso()
    doc_dir = config.DOC_DIR / doc_id
    doc_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(filename).name
    (doc_dir / safe_name).write_bytes(data)

    meta = {
        "id": doc_id,
        "name": Path(filename).stem[:60] or "文档",
        "file_type": ext.lstrip("."),
        "source_file": safe_name,
        "created_at": created_at,
        "chars": len(text),
        "text": text,
        "chunks_json": json.dumps(chunk_payload, ensure_ascii=False),
        "tables_json": json.dumps([t.model_dump() for t in table_infos], ensure_ascii=False),
    }
    store.save_document(meta)
    return _document_info_from_row({**meta, "text": text})


def delete_document(doc_id: str) -> None:
    row = store.get_document(doc_id, with_text=False)
    if not row:
        raise ValueError("文档不存在")
    doc_dir = config.DOC_DIR / doc_id
    if doc_dir.exists():
        import shutil
        shutil.rmtree(doc_dir, ignore_errors=True)
    store.delete_document(doc_id)
