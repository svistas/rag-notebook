from __future__ import annotations

from dataclasses import dataclass

from app.config import get_settings
from app.db.vector_store import query_by_embedding
from app.models.schemas import ChatDebug
from app.models.schemas import RetrievedChunk
from app.rag.embedding import get_embeddings
from app.rag.query_rewrite import rewrite_query
from app.rag.rerank import rerank


def retrieve(query: str, top_k: int | None = None) -> list[RetrievedChunk]:
    settings = get_settings()
    k = top_k or settings.top_k
    query_embedding = get_embeddings([query])[0]
    return query_by_embedding(query_embedding=query_embedding, top_k=k)


@dataclass(frozen=True)
class RetrievalWithDebugResult:
    final_chunks: list[RetrievedChunk]
    debug: ChatDebug


def retrieve_with_debug(user_query: str) -> RetrievalWithDebugResult:
    settings = get_settings()
    rewrite_enabled = bool(settings.enable_query_rewrite)
    rerank_enabled = bool(settings.enable_rerank)

    rewritten_query = user_query
    if rewrite_enabled:
        rewritten_query = rewrite_query(user_query).rewritten_query or user_query

    initial_chunks_raw = retrieve(query=rewritten_query, top_k=settings.top_k)
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
