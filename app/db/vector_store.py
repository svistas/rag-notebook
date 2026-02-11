from __future__ import annotations

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
        # Lazy import keeps startup memory lower until vector operations are needed.
        import chromadb

        settings = get_settings()
        _client = chromadb.PersistentClient(path=str(settings.chroma_path))
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
    for doc, meta, distance, chunk_id in zip(documents, metadatas, distances, ids):
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
