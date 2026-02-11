import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import Chunk as ChunkRow
from app.db.models import ChunkEmbedding, Document, User
from app.db.session import get_db
from app.rag.embedding import get_embeddings
from app.rag.retrieval import retrieve
from app.services.auth_service import hash_password


def test_similarity_ranking_prefers_relevant_chunk() -> None:
    db: Session = next(get_db())
    try:
        user = User(id=uuid.uuid4(), email="retr@example.com", password_hash=hash_password("password123"), created_at=datetime.now(timezone.utc))
        db.add(user)
        db.commit()

        doc = Document(
            id=uuid.uuid4(),
            user_id=user.id,
            filename="sample.md",
            stored_filename="x",
            status="indexed",
            chunk_count=2,
            uploaded_at=datetime.now(timezone.utc),
            indexed_at=datetime.now(timezone.utc),
            error_message=None,
        )
        db.add(doc)
        db.flush()

        texts = ["FastAPI is a Python framework for APIs.", "Bananas are yellow fruits."]
        embs = get_embeddings(texts)
        for idx, (text, emb) in enumerate(zip(texts, embs)):
            chunk = ChunkRow(
                id=uuid.uuid4(),
                document_id=doc.id,
                chunk_index=idx,
                start_char=0,
                end_char=10,
                text=text,
            )
            db.add(chunk)
            db.flush()
            db.add(ChunkEmbedding(chunk_id=chunk.id, embedding=emb))
        db.commit()

        results = retrieve(db=db, user=user, query="What framework helps build Python APIs?", top_k=2)
        assert len(results) == 2
        assert "FastAPI" in results[0].text
        assert results[0].score >= results[1].score
    finally:
        db.close()
