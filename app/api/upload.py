from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile

from app.models.schemas import UploadResponse
from app.services.document_service import create_document_record, index_document

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile, background_tasks: BackgroundTasks) -> UploadResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    content = await file.read()
    try:
        metadata = create_document_record(filename=file.filename, content=content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    background_tasks.add_task(index_document, metadata.id)
    return UploadResponse(document=metadata)
