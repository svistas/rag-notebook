from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Chunk(BaseModel):
    text: str
    chunk_index: int
    start_char: int
    end_char: int


class RetrievedChunk(BaseModel):
    id: str
    text: str
    doc_id: str
    document_name: str
    chunk_index: int
    start_char: int
    end_char: int
    score: float


class Citation(BaseModel):
    number: int
    text: str
    document_name: str
    chunk_index: int


class ChatRequest(BaseModel):
    query: str = Field(min_length=1)


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]


class DocumentMetadata(BaseModel):
    id: str
    filename: str
    chunk_count: int
    uploaded_at: datetime
    status: Literal["queued", "indexing", "indexed", "failed"] = "indexed"
    stored_filename: str | None = None
    indexed_at: datetime | None = None
    error_message: str | None = None


class UploadResponse(BaseModel):
    document: DocumentMetadata


class DocumentsResponse(BaseModel):
    documents: list[DocumentMetadata]
