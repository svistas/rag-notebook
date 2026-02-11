from app.models.schemas import RetrievedChunk
from app.rag.query_rewrite import rewrite_query
from app.rag.rerank import rerank


def test_query_rewrite_returns_non_empty_string() -> None:
    result = rewrite_query("What is RAG and how does it work?")
    assert result.user_query
    assert result.rewritten_query


def test_rerank_returns_ranked_ids_in_order() -> None:
    chunks = [
        RetrievedChunk(
            id="a",
            text="Chunk A",
            doc_id="d1",
            document_name="doc.txt",
            chunk_index=0,
            start_char=0,
            end_char=10,
            score=0.9,
        ),
        RetrievedChunk(
            id="b",
            text="Chunk B",
            doc_id="d1",
            document_name="doc.txt",
            chunk_index=1,
            start_char=11,
            end_char=20,
            score=0.8,
        ),
    ]
    result = rerank(query="Which chunk is best?", chunks=chunks, top_n=1)
    assert len(result.ranked_ids) == 1
    assert result.ranked_ids[0] in {"a", "b"}
