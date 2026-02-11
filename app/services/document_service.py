from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db.models import Chunk, ChunkEmbedding, Document, User
from app.db.session import get_engine
from app.models.schemas import DocumentMetadata
from app.rag.chunking import chunk_text
from app.rag.embedding import get_embeddings
from app.services import pdf_service

_ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf"}

logger = logging.getLogger(__name__)


def _sanitize_filename(filename: str) -> str:
    base = Path(filename).name
    sanitized = re.sub(r"[^A-Za-z0-9._-]", "_", base)
    return sanitized or "document.txt"


def _user_upload_dir(user_id: str) -> Path:
    settings = get_settings()
    path = settings.upload_path / user_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _find_stored_path(user_id: str, doc_id: str, stored_filename: str | None) -> Path | None:
    settings = get_settings()
    if stored_filename:
        candidate = settings.upload_path / user_id / stored_filename
        if candidate.exists():
            return candidate

    pattern = f"{doc_id}_"
    for path in (settings.upload_path / user_id).glob(f"{doc_id}_*"):
        if path.is_file() and path.name.startswith(pattern):
            return path
    return None


def _to_metadata(doc: Document) -> DocumentMetadata:
    return DocumentMetadata(
        id=str(doc.id),
        filename=doc.filename,
        stored_filename=doc.stored_filename,
        chunk_count=doc.chunk_count,
        uploaded_at=doc.uploaded_at,
        indexed_at=doc.indexed_at,
        error_message=doc.error_message,
        status=doc.status,  # type: ignore[arg-type]
    )


def create_document_record(db: Session, user: User, filename: str, content: bytes) -> DocumentMetadata:
    settings = get_settings()
    safe_name = _sanitize_filename(filename)
    extension = Path(safe_name).suffix.lower()
    if extension not in _ALLOWED_EXTENSIONS:
        raise ValueError("Only .txt, .md, and .pdf files are supported")

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise ValueError(f"File exceeds {settings.max_upload_size_mb} MB limit")

    # Early decode check so we fail fast for non-UTF8 input (text formats only).
    if extension in {".txt", ".md"}:
        try:
            content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("File must be UTF-8 encoded text") from exc

    doc_id = str(uuid.uuid4())
    destination = _user_upload_dir(str(user.id)) / f"{doc_id}_{safe_name}"
    destination.write_bytes(content)

    now = datetime.now(timezone.utc)
    doc = Document(
        id=uuid.UUID(doc_id),
        user_id=user.id,
        filename=safe_name,
        stored_filename=destination.name,
        status="queued",
        chunk_count=0,
        uploaded_at=now,
        indexed_at=None,
        error_message=None,
    )
    db.add(doc)
    db.commit()

    logger.info("upload.accepted", extra={"doc_id": doc_id, "document_name": safe_name, "user_id": str(user.id)})
    return _to_metadata(doc)


def index_document(db: Session, user: User, doc_id: str) -> DocumentMetadata:
    doc_uuid = uuid.UUID(doc_id)
    doc = db.execute(select(Document).where(Document.id == doc_uuid, Document.user_id == user.id)).scalar_one_or_none()
    if not doc:
        raise ValueError("Document not found")

    doc.status = "indexing"
    doc.error_message = None
    db.add(doc)
    db.commit()

    logger.info("index.start", extra={"doc_id": doc_id, "document_name": doc.filename, "user_id": str(user.id)})

    stored_path = _find_stored_path(str(user.id), doc_id, doc.stored_filename)
    if stored_path is None:
        doc.status = "failed"
        doc.error_message = "Stored file not found on disk"
        db.add(doc)
        db.commit()
        return _to_metadata(doc)

    try:
        content = stored_path.read_bytes()
        ext = stored_path.suffix.lower()
        if ext in {".txt", ".md"}:
            text = content.decode("utf-8")
        elif ext == ".pdf":
            text = pdf_service.extract_text_from_pdf(content)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        chunks = chunk_text(text=text, chunk_size=get_settings().chunk_size, overlap=get_settings().chunk_overlap)
        if not chunks:
            raise ValueError("Document is empty after preprocessing")

        # Clear any existing chunks/embeddings for idempotency.
        chunk_ids_subq = select(Chunk.id).where(Chunk.document_id == doc.id)
        db.execute(delete(ChunkEmbedding).where(ChunkEmbedding.chunk_id.in_(chunk_ids_subq)))
        db.execute(delete(Chunk).where(Chunk.document_id == doc.id))
        db.commit()

        chunk_texts = [chunk.text for chunk in chunks]
        embeddings = get_embeddings(chunk_texts)
        for chunk_model, embedding in zip(chunks, embeddings):
            chunk_row = Chunk(
                id=uuid.uuid4(),
                document_id=doc.id,
                chunk_index=chunk_model.chunk_index,
                start_char=chunk_model.start_char,
                end_char=chunk_model.end_char,
                text=chunk_model.text,
            )
            db.add(chunk_row)
            db.flush()
            db.add(ChunkEmbedding(chunk_id=chunk_row.id, embedding=embedding))
        db.commit()

        doc.chunk_count = len(chunks)
        doc.indexed_at = datetime.now(timezone.utc)
        doc.status = "indexed"
        doc.error_message = None
        db.add(doc)
        db.commit()
        logger.info(
            "index.complete",
            extra={"doc_id": doc_id, "document_name": doc.filename, "chunk_count": doc.chunk_count, "user_id": str(user.id)},
        )
        return _to_metadata(doc)
    except Exception as exc:  # noqa: BLE001 - persist failure for UI debugging
        doc.status = "failed"
        doc.error_message = str(exc)
        db.add(doc)
        db.commit()
        logger.exception("index.failed", extra={"doc_id": doc_id, "document_name": doc.filename, "user_id": str(user.id)})
        return _to_metadata(doc)


def index_document_task(user_id: str, doc_id: str) -> None:
    """
    BackgroundTasks entrypoint: create a new DB session, load user, index.
    """
    engine = get_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    with SessionLocal() as db:
        user_uuid = uuid.UUID(user_id)
        user = db.execute(select(User).where(User.id == user_uuid)).scalar_one()
        index_document(db=db, user=user, doc_id=doc_id)


def list_documents(db: Session, user: User) -> list[DocumentMetadata]:
    docs = db.execute(select(Document).where(Document.user_id == user.id).order_by(Document.uploaded_at.desc())).scalars().all()
    return [_to_metadata(d) for d in docs]


def get_document(db: Session, user: User, doc_id: str) -> DocumentMetadata | None:
    doc_uuid = uuid.UUID(doc_id)
    d = db.execute(select(Document).where(Document.id == doc_uuid, Document.user_id == user.id)).scalar_one_or_none()
    return _to_metadata(d) if d else None


def delete_document_everywhere(db: Session, user: User, doc_id: str) -> None:
    doc_uuid = uuid.UUID(doc_id)
    d = db.execute(select(Document).where(Document.id == doc_uuid, Document.user_id == user.id)).scalar_one_or_none()
    if not d:
        raise ValueError("Document not found")

    stored_path = _find_stored_path(str(user.id), doc_id, d.stored_filename)
    if stored_path and stored_path.exists():
        stored_path.unlink()

    db.execute(delete(Document).where(Document.id == d.id))
    db.commit()


def mark_queued(db: Session, user: User, doc_id: str) -> DocumentMetadata:
    doc_uuid = uuid.UUID(doc_id)
    d = db.execute(select(Document).where(Document.id == doc_uuid, Document.user_id == user.id)).scalar_one_or_none()
    if not d:
        raise ValueError("Document not found")

    chunk_ids_subq = select(Chunk.id).where(Chunk.document_id == d.id)
    db.execute(delete(ChunkEmbedding).where(ChunkEmbedding.chunk_id.in_(chunk_ids_subq)))
    db.execute(delete(Chunk).where(Chunk.document_id == d.id))

    d.status = "queued"
    d.error_message = None
    d.indexed_at = None
    d.chunk_count = 0
    db.add(d)
    db.commit()
    return _to_metadata(d)
