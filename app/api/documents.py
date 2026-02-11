from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import DocumentsResponse
from app.services.document_service import list_documents

router = APIRouter(prefix="/api", tags=["documents"])


@router.get("/documents", response_model=DocumentsResponse)
async def get_documents() -> DocumentsResponse:
    return DocumentsResponse(documents=list_documents())
