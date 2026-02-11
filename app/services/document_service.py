from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings
from app.db.vector_store import add_chunks
from app.models.schemas import DocumentMetadata
from app.rag.chunking import chunk_text
from app.rag.embedding import get_embeddings

_ALLOWED_EXTENSIONS = {".txt", ".md"}


def _metadata_file() -> Path:
    settings = get_settings()
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    return settings.upload_path / "documents.json"


def _load_documents() -> list[DocumentMetadata]:
    metadata_path = _metadata_file()
    if not metadata_path.exists():
        return []

    raw = json.loads(metadata_path.read_text(encoding="utf-8"))
    return [DocumentMetadata.model_validate(item) for item in raw]


def _save_documents(documents: list[DocumentMetadata]) -> None:
    metadata_path = _metadata_file()
    payload = [doc.model_dump(mode="json") for doc in documents]
    metadata_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _sanitize_filename(filename: str) -> str:
    base = Path(filename).name
    sanitized = re.sub(r"[^A-Za-z0-9._-]", "_", base)
    return sanitized or "document.txt"


def ingest_document(filename: str, content: bytes) -> DocumentMetadata:
    settings = get_settings()
    safe_name = _sanitize_filename(filename)
    extension = Path(safe_name).suffix.lower()
    if extension not in _ALLOWED_EXTENSIONS:
        raise ValueError("Only .txt and .md files are supported")

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise ValueError(f"File exceeds {settings.max_upload_size_mb} MB limit")

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("File must be UTF-8 encoded text") from exc

    chunks = chunk_text(text=text, chunk_size=settings.chunk_size, overlap=settings.chunk_overlap)
    if not chunks:
        raise ValueError("Document is empty after preprocessing")

    doc_id = str(uuid.uuid4())
    destination = settings.upload_path / f"{doc_id}_{safe_name}"
    destination.write_bytes(content)

    chunk_texts = [chunk.text for chunk in chunks]
    embeddings = get_embeddings(chunk_texts)
    add_chunks(doc_id=doc_id, document_name=safe_name, chunks=chunks, embeddings=embeddings)

    metadata = DocumentMetadata(
        id=doc_id,
        filename=safe_name,
        chunk_count=len(chunks),
        uploaded_at=datetime.now(timezone.utc),
        status="indexed",
    )
    documents = _load_documents()
    documents.append(metadata)
    _save_documents(documents)
    return metadata


def list_documents() -> list[DocumentMetadata]:
    return _load_documents()
