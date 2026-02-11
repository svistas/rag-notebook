from app.db.vector_store import add_chunks
from app.models.schemas import Chunk
from app.rag.embedding import get_embeddings
from app.rag.retrieval import retrieve


def test_similarity_ranking_prefers_relevant_chunk() -> None:
    chunks = [
        Chunk(text="FastAPI is a Python framework for APIs.", chunk_index=0, start_char=0, end_char=40),
        Chunk(text="Bananas are yellow fruits.", chunk_index=1, start_char=41, end_char=70),
    ]
    embeddings = get_embeddings([chunk.text for chunk in chunks])
    add_chunks(doc_id="doc-1", document_name="sample.md", chunks=chunks, embeddings=embeddings)

    results = retrieve("What framework helps build Python APIs?", top_k=2)
    assert len(results) == 2
    assert "FastAPI" in results[0].text
    assert results[0].score >= results[1].score
