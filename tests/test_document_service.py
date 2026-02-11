import uuid

from sqlalchemy import select

from app.db.models import User
from app.db.session import get_db
from app.services.auth_service import hash_password
from app.services.document_service import create_document_record, index_document


def test_index_document_transitions_statuses() -> None:
    # Use the SQLite DB created by the autouse conftest fixture.
    db = next(get_db())
    try:
        user = User(id=uuid.uuid4(), email="svc@example.com", password_hash=hash_password("password123"))
        db.add(user)
        db.commit()

        doc = create_document_record(db=db, user=user, filename="a.txt", content=b"Hello world")
        assert doc.status == "queued"
        assert doc.chunk_count == 0

        indexed = index_document(db=db, user=user, doc_id=doc.id)
        assert indexed.status == "indexed"
        assert indexed.chunk_count >= 1
        assert indexed.indexed_at is not None
        assert indexed.error_message is None
    finally:
        db.close()

