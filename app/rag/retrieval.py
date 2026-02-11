from __future__ import annotations

import math
from dataclasses import dataclass

from sqlalchemy import Float, cast, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.schemas import ChatDebug
from app.models.schemas import RetrievedChunk
from app.db.models import Chunk, ChunkEmbedding, Document, User
from app.rag.embedding import get_embeddings
from app.rag.query_rewrite import rewrite_query
from app.rag.rerank import rerank


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
    norm_b = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (norm_a * norm_b)


def retrieve(db: Session, user: User, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
    settings = get_settings()
    k = top_k or settings.top_k
    query_embedding = get_embeddings([query])[0]

    # Postgres+pgvector path.
    if db.bind and db.bind.dialect.name == "postgresql":
        # Try pgvector SQLAlchemy comparator first; fall back to cosine-distance operator.
        try:
            distance_expr = ChunkEmbedding.embedding.cosine_distance(query_embedding)
        except Exception:
            # `<=>` returns a float distance, but SQLAlchemy may infer the type as VECTOR
            # (because it's an op on a VECTOR-typed column). Force-cast to Float so the
            # pgvector result processor doesn't try to parse a float as a vector.
            distance_expr = ChunkEmbedding.embedding.op("<=>")(query_embedding)

        distance_expr = cast(distance_expr, Float)

        stmt = (
            select(Chunk, Document, distance_expr.label("distance"))
            .join(Document, Chunk.document_id == Document.id)
            .join(ChunkEmbedding, ChunkEmbedding.chunk_id == Chunk.id)
            .where(Document.user_id == user.id)
            .order_by(distance_expr.asc())
            .limit(k)
        )
        rows = db.execute(stmt).all()
        results: list[RetrievedChunk] = []
        for chunk, doc, distance in rows:
            score = 1.0 - float(distance) if distance is not None else 0.0
            results.append(
                RetrievedChunk(
                    id=str(chunk.id),
                    text=chunk.text,
                    doc_id=str(doc.id),
                    document_name=doc.filename,
                    chunk_index=chunk.chunk_index,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                    score=score,
                )
            )
        return results

    # SQLite/dev fallback: compute cosine similarity in Python (used for tests).
    stmt = (
        select(Chunk, Document, ChunkEmbedding.embedding)
        .join(Document, Chunk.document_id == Document.id)
        .join(ChunkEmbedding, ChunkEmbedding.chunk_id == Chunk.id)
        .where(Document.user_id == user.id)
    )
    candidates = db.execute(stmt).all()
    scored: list[tuple[float, Chunk, Document]] = []
    for chunk, doc, emb in candidates:
        if not isinstance(emb, list):
            continue
        score = _cosine_similarity(query_embedding, emb)
        scored.append((score, chunk, doc))
    scored.sort(key=lambda t: t[0], reverse=True)

    results = []
    for score, chunk, doc in scored[:k]:
        results.append(
            RetrievedChunk(
                id=str(chunk.id),
                text=chunk.text,
                doc_id=str(doc.id),
                document_name=doc.filename,
                chunk_index=chunk.chunk_index,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
                score=float(score),
            )
        )
    return results


@dataclass(frozen=True)
class RetrievalWithDebugResult:
    final_chunks: list[RetrievedChunk]
    debug: ChatDebug


def retrieve_with_debug(db: Session, user: User, user_query: str) -> RetrievalWithDebugResult:
    settings = get_settings()
    rewrite_enabled = bool(settings.enable_query_rewrite)
    rerank_enabled = bool(settings.enable_rerank)

    rewritten_query = user_query
    if rewrite_enabled:
        rewritten_query = rewrite_query(user_query).rewritten_query or user_query

    initial_chunks_raw = retrieve(db=db, user=user, query=rewritten_query, top_k=settings.top_k)
    # Defensive dedupe in case the vector store returns duplicates.
    initial_chunks: list[RetrievedChunk] = []
    seen: set[str] = set()
    for ch in initial_chunks_raw:
        if ch.id in seen:
            continue
        seen.add(ch.id)
        initial_chunks.append(ch)

    final_chunks = initial_chunks
    if rerank_enabled and initial_chunks:
        rr = rerank(query=user_query, chunks=initial_chunks, top_n=settings.rerank_top_n)
        id_to_chunk = {c.id: c for c in initial_chunks}
        final_chunks = []
        seen_final: set[str] = set()
        for cid in rr.ranked_ids:
            if cid in id_to_chunk and cid not in seen_final:
                final_chunks.append(id_to_chunk[cid])
                seen_final.add(cid)
        if not final_chunks:
            final_chunks = initial_chunks[: settings.rerank_top_n]

    debug = ChatDebug(
        user_query=user_query,
        rewritten_query=rewritten_query,
        initial_chunks=initial_chunks,
        final_chunks=final_chunks,
        rewrite_enabled=rewrite_enabled,
        rerank_enabled=rerank_enabled,
    )
    return RetrievalWithDebugResult(final_chunks=final_chunks, debug=debug)
