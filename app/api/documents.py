from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.schemas import DocumentMetadata, DocumentsResponse
from app.db.models import User
from app.db.session import get_db
from app.services.auth_dependencies import get_current_user
from app.services.document_service import (
    delete_document_everywhere,
    get_document,
    index_document_task,
    list_documents,
    mark_queued,
)

router = APIRouter(prefix="/api", tags=["documents"])


@router.get("/documents", response_model=DocumentsResponse)
async def get_documents(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentsResponse:
    return DocumentsResponse(documents=list_documents(db=db, user=user))


@router.get("/documents/{doc_id}", response_model=DocumentMetadata)
async def get_document_by_id(
    doc_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentMetadata:
    doc = get_document(db=db, user=user, doc_id=doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    try:
        delete_document_everywhere(db=db, user=user, doc_id=doc_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "deleted"}


@router.post("/documents/{doc_id}/reindex", response_model=DocumentMetadata)
async def reindex_document(
    doc_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentMetadata:
    try:
        doc = mark_queued(db=db, user=user, doc_id=doc_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    background_tasks.add_task(index_document_task, str(user.id), doc_id)
    return doc
