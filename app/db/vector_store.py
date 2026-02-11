from __future__ import annotations

import os
from typing import Any

from app.config import get_settings
from app.models.schemas import Chunk, RetrievedChunk

_client: Any | None = None


def set_chroma_client(client: Any | None) -> None:
    global _client
    _client = client


def get_chroma_client() -> Any:
    global _client
    if _client is None:
        # Chroma's PostHog integration can be incompatible with newer `posthog` versions
        # (signature mismatch for `capture()`), which produces noisy warnings. Since we
        # don't want product telemetry in this portfolio app, force-disable PostHog and
        # provide a no-op `capture` that accepts any args.
        try:
            import posthog  # type: ignore

            posthog.disabled = True

            def _capture_noop(*args: object, **kwargs: object) -> None:
                return None

            posthog.capture = _capture_noop  # type: ignore[attr-defined]
        except Exception:
            pass

        # Disable Chroma anonymized telemetry as early as possible.
        # This prevents noisy "Failed to send telemetry event ..." warnings in some environments.
        # Chroma docs show `ANONYMIZED_TELEMETRY=False` (capital F) as the expected form.
        os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
        # Extra guard: Chroma uses PostHog under the hood for product telemetry.
        # Disabling PostHog prevents capture attempts from printing warnings.
        os.environ.setdefault("POSTHOG_DISABLED", "1")

        # Lazy import keeps startup memory lower until vector operations are needed.
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        settings = get_settings()
        # Disable Chroma anonymized telemetry to avoid noisy log warnings in some environments.
        _client = chromadb.PersistentClient(
            path=str(settings.chroma_path),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def get_collection(name: str | None = None) -> Any:
    settings = get_settings()
    collection_name = name or settings.chroma_collection
    client = get_chroma_client()
    return client.get_or_create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})


def add_chunks(
    doc_id: str,
    document_name: str,
    chunks: list[Chunk],
    embeddings: list[list[float]],
) -> None:
    if len(chunks) != len(embeddings):
        raise ValueError("chunks and embeddings must have the same length")

    if not chunks:
        return

    collection = get_collection()
    ids = [f"{doc_id}:{chunk.chunk_index}" for chunk in chunks]
    documents = [chunk.text for chunk in chunks]
    metadatas = [
        {
            "doc_id": doc_id,
            "document_name": document_name,
            "chunk_index": chunk.chunk_index,
            "start_char": chunk.start_char,
            "end_char": chunk.end_char,
        }
        for chunk in chunks
    ]
    collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)


def query_by_embedding(query_embedding: list[float], top_k: int) -> list[RetrievedChunk]:
    collection = get_collection()
    result = collection.query(query_embeddings=[query_embedding], n_results=top_k)

    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]
    ids = result.get("ids", [[]])[0]

    rows: list[RetrievedChunk] = []
    seen_ids: set[str] = set()
    for doc, meta, distance, chunk_id in zip(documents, metadatas, distances, ids):
        if chunk_id in seen_ids:
            continue
        seen_ids.add(chunk_id)
        score = 1 - distance if distance is not None else 0.0
        rows.append(
            RetrievedChunk(
                id=chunk_id,
                text=doc,
                doc_id=meta.get("doc_id", ""),
                document_name=meta.get("document_name", "Unknown"),
                chunk_index=int(meta.get("chunk_index", 0)),
                start_char=int(meta.get("start_char", 0)),
                end_char=int(meta.get("end_char", 0)),
                score=float(score),
            )
        )

    return rows


def delete_document(doc_id: str) -> None:
    collection = get_collection()
    collection.delete(where={"doc_id": doc_id})
