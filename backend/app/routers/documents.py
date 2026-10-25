"""文档 / 图片 API：上传解析、列表、详情、RAG 问答。"""
from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from .. import store
from ..models import DocAskRequest, DocAskResponse, DocumentInfo
from ..services import document_service, rag_service

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentInfo, summary="上传 PDF / Word / 图片并解析")
async def upload_document(file: UploadFile = File(...)):
    data = await file.read()
    try:
        return await document_service.save_document(file.filename or "document", data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"文档解析失败：{exc}") from exc


@router.get("", response_model=list[DocumentInfo], summary="文档列表")
def list_documents():
    return document_service.list_documents()


@router.get("/{doc_id}", response_model=DocumentInfo, summary="文档详情")
def get_document(doc_id: str):
    info = document_service.get_document_info(doc_id)
    if not info:
        raise HTTPException(status_code=404, detail="文档不存在")
    return info


@router.delete("/{doc_id}", summary="删除文档")
def delete_document(doc_id: str):
    try:
        document_service.delete_document(doc_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/{doc_id}/ask", response_model=DocAskResponse, summary="文档 RAG 问答")
async def ask_document(doc_id: str, req: DocAskRequest):
    row = store.get_document(doc_id)
    if not row:
        raise HTTPException(status_code=404, detail="文档不存在")
    return await rag_service.answer_question(row, req.question, req.history)
