"""数据集相关 API。"""
from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..models import DatasetInfo, DatasetListItem, PreviewResponse
from ..services import dataset_service

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.post("/upload", response_model=DatasetInfo, summary="上传 CSV / Excel 并建表")
async def upload_dataset(file: UploadFile = File(...)):
    data = await file.read()
    try:
        return dataset_service.save_upload(file.filename or "dataset.csv", data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/demo", response_model=DatasetInfo, summary="载入内置示例数据集")
def load_demo_dataset():
    try:
        return dataset_service.load_demo()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=list[DatasetListItem], summary="数据集列表")
def list_datasets():
    return dataset_service.list_datasets()


@router.get("/{dataset_id}", response_model=DatasetInfo, summary="数据集详情")
def get_dataset(dataset_id: str):
    info = dataset_service.get_dataset_info(dataset_id)
    if not info:
        raise HTTPException(status_code=404, detail="数据集不存在")
    return info


@router.get("/{dataset_id}/preview", response_model=PreviewResponse, summary="数据预览")
def preview_dataset(dataset_id: str, limit: int = 50):
    try:
        return dataset_service.get_preview(dataset_id, limit=max(1, min(limit, 500)))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{dataset_id}", summary="删除数据集")
def delete_dataset(dataset_id: str):
    try:
        dataset_service.delete_dataset(dataset_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True}
