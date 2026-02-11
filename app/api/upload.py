from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile

from app.models.schemas import UploadResponse
from app.services.document_service import ingest_document

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile) -> UploadResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    content = await file.read()
    try:
        metadata = ingest_document(filename=file.filename, content=content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return UploadResponse(document=metadata)
