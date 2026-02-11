from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.models.schemas import DocumentMetadata, DocumentsResponse
from app.services.document_service import (
    delete_document_everywhere,
    get_document,
    index_document,
    list_documents,
    mark_queued,
)

router = APIRouter(prefix="/api", tags=["documents"])


@router.get("/documents", response_model=DocumentsResponse)
async def get_documents() -> DocumentsResponse:
    return DocumentsResponse(documents=list_documents())


@router.get("/documents/{doc_id}", response_model=DocumentMetadata)
async def get_document_by_id(doc_id: str) -> DocumentMetadata:
    doc = get_document(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str) -> dict[str, str]:
    try:
        delete_document_everywhere(doc_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "deleted"}


@router.post("/documents/{doc_id}/reindex", response_model=DocumentMetadata)
async def reindex_document(doc_id: str, background_tasks: BackgroundTasks) -> DocumentMetadata:
    try:
        doc = mark_queued(doc_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    background_tasks.add_task(index_document, doc_id)
    return doc
