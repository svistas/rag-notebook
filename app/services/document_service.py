from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings
from app.db.vector_store import add_chunks, delete_document
from app.models.schemas import DocumentMetadata
from app.rag.chunking import chunk_text
from app.rag.embedding import get_embeddings

_ALLOWED_EXTENSIONS = {".txt", ".md"}

logger = logging.getLogger(__name__)


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


def _find_stored_path(doc_id: str, stored_filename: str | None) -> Path | None:
    settings = get_settings()
    if stored_filename:
        candidate = settings.upload_path / stored_filename
        if candidate.exists():
            return candidate

    pattern = f"{doc_id}_"
    for path in settings.upload_path.glob(f"{doc_id}_*"):
        if path.is_file() and path.name.startswith(pattern):
            return path
    return None


def get_document(doc_id: str) -> DocumentMetadata | None:
    for doc in _load_documents():
        if doc.id == doc_id:
            return doc
    return None


def _upsert_document(updated: DocumentMetadata) -> DocumentMetadata:
    documents = _load_documents()
    replaced = False
    for idx, doc in enumerate(documents):
        if doc.id == updated.id:
            documents[idx] = updated
            replaced = True
            break
    if not replaced:
        documents.append(updated)
    _save_documents(documents)
    return updated


def create_document_record(filename: str, content: bytes) -> DocumentMetadata:
    settings = get_settings()
    safe_name = _sanitize_filename(filename)
    extension = Path(safe_name).suffix.lower()
    if extension not in _ALLOWED_EXTENSIONS:
        raise ValueError("Only .txt and .md files are supported")

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise ValueError(f"File exceeds {settings.max_upload_size_mb} MB limit")

    # Early decode check so we fail fast for non-UTF8 input.
    try:
        content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("File must be UTF-8 encoded text") from exc

    doc_id = str(uuid.uuid4())
    destination = settings.upload_path / f"{doc_id}_{safe_name}"
    destination.write_bytes(content)

    metadata = DocumentMetadata(
        id=doc_id,
        filename=safe_name,
        stored_filename=destination.name,
        chunk_count=0,
        uploaded_at=datetime.now(timezone.utc),
        status="queued",
    )
    logger.info("upload.accepted", extra={"doc_id": doc_id, "filename": safe_name})
    return _upsert_document(metadata)


def index_document(doc_id: str) -> DocumentMetadata:
    existing = get_document(doc_id)
    if existing is None:
        raise ValueError("Document not found")

    existing.status = "indexing"
    existing.error_message = None
    _upsert_document(existing)

    logger.info("index.start", extra={"doc_id": doc_id, "filename": existing.filename})

    stored_path = _find_stored_path(doc_id, existing.stored_filename)
    if stored_path is None:
        existing.status = "failed"
        existing.error_message = "Stored file not found on disk"
        _upsert_document(existing)
        return existing

    try:
        content = stored_path.read_bytes()
        text = content.decode("utf-8")

        chunks = chunk_text(text=text, chunk_size=get_settings().chunk_size, overlap=get_settings().chunk_overlap)
        if not chunks:
            raise ValueError("Document is empty after preprocessing")

        chunk_texts = [chunk.text for chunk in chunks]
        embeddings = get_embeddings(chunk_texts)
        add_chunks(doc_id=doc_id, document_name=existing.filename, chunks=chunks, embeddings=embeddings)

        existing.chunk_count = len(chunks)
        existing.indexed_at = datetime.now(timezone.utc)
        existing.status = "indexed"
        _upsert_document(existing)
        logger.info(
            "index.complete",
            extra={"doc_id": doc_id, "filename": existing.filename, "chunk_count": existing.chunk_count},
        )
        return existing
    except Exception as exc:  # noqa: BLE001 - persist failure for UI debugging
        existing.status = "failed"
        existing.error_message = str(exc)
        _upsert_document(existing)
        logger.exception("index.failed", extra={"doc_id": doc_id, "filename": existing.filename})
        return existing


def ingest_document(filename: str, content: bytes) -> DocumentMetadata:
    """
    Backward-compatible synchronous ingest (Week 1 behavior).

    Week 2 uses background indexing, but keeping this avoids breaking callers/tests
    that may rely on a single-call ingestion path.
    """
    record = create_document_record(filename=filename, content=content)
    return index_document(record.id)


def list_documents() -> list[DocumentMetadata]:
    return _load_documents()


def delete_document_everywhere(doc_id: str) -> None:
    doc = get_document(doc_id)
    if doc is None:
        raise ValueError("Document not found")

    # Remove vectors first (safe to call even if nothing exists).
    delete_document(doc_id)

    stored_path = _find_stored_path(doc_id, doc.stored_filename)
    if stored_path and stored_path.exists():
        stored_path.unlink()

    documents = [d for d in _load_documents() if d.id != doc_id]
    _save_documents(documents)


def mark_queued(doc_id: str) -> DocumentMetadata:
    doc = get_document(doc_id)
    if doc is None:
        raise ValueError("Document not found")

    # Reindex should start from a clean slate.
    delete_document(doc_id)

    doc.status = "queued"
    doc.error_message = None
    doc.indexed_at = None
    doc.chunk_count = 0
    return _upsert_document(doc)
