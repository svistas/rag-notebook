from __future__ import annotations

from app.config import get_settings
from app.db.vector_store import query_by_embedding
from app.models.schemas import RetrievedChunk
from app.rag.embedding import get_embeddings


def retrieve(query: str, top_k: int | None = None) -> list[RetrievedChunk]:
    settings = get_settings()
    k = top_k or settings.top_k
    query_embedding = get_embeddings([query])[0]
    return query_by_embedding(query_embedding=query_embedding, top_k=k)
