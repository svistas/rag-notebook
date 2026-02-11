from __future__ import annotations

import math
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.db.vector_store import set_chroma_client
from app.main import app
from app.rag.embedding import set_embedding_client
from app.rag.prompting import set_chat_client


def _text_to_vector(text: str, dims: int = 8) -> list[float]:
    values = [0.0] * dims
    for i, char in enumerate(text.lower()):
        values[i % dims] += (ord(char) % 31) / 31.0
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]


class _EmbeddingData:
    def __init__(self, embedding: list[float]) -> None:
        self.embedding = embedding


class _EmbeddingsResponse:
    def __init__(self, vectors: list[list[float]]) -> None:
        self.data = [_EmbeddingData(v) for v in vectors]


class MockEmbeddingsApi:
    def create(self, model: str, input: list[str]) -> _EmbeddingsResponse:
        _ = model
        return _EmbeddingsResponse([_text_to_vector(item) for item in input])


class _Message:
    def __init__(self, content: str) -> None:
        self.content = content


class _Choice:
    def __init__(self, content: str) -> None:
        self.message = _Message(content)


class _ChatResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_Choice(content)]


class MockChatCompletionsApi:
    def create(self, model: str, messages: list[dict], temperature: float) -> _ChatResponse:
        _ = model, temperature
        question = messages[-1]["content"].split("Question:\n", 1)[-1].split("\n\nContext:", 1)[0]
        return _ChatResponse(f"Mock answer for: {question} [1]")


class MockChatApi:
    def __init__(self) -> None:
        self.completions = MockChatCompletionsApi()


class MockOpenAIClient:
    def __init__(self) -> None:
        self.embeddings = MockEmbeddingsApi()
        self.chat = MockChatApi()


def _cosine_distance(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
    norm_b = math.sqrt(sum(y * y for y in b)) or 1.0
    return 1.0 - (dot / (norm_a * norm_b))


class MockCollection:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def add(self, ids: list[str], embeddings: list[list[float]], documents: list[str], metadatas: list[dict]) -> None:
        for row_id, emb, doc, meta in zip(ids, embeddings, documents, metadatas):
            self.rows.append(
                {
                    "id": row_id,
                    "embedding": emb,
                    "document": doc,
                    "metadata": meta,
                }
            )

    def query(self, query_embeddings: list[list[float]], n_results: int) -> dict:
        query = query_embeddings[0]
        ranked = sorted(self.rows, key=lambda row: _cosine_distance(query, row["embedding"]))
        top = ranked[:n_results]
        return {
            "ids": [[row["id"] for row in top]],
            "documents": [[row["document"] for row in top]],
            "metadatas": [[row["metadata"] for row in top]],
            "distances": [[_cosine_distance(query, row["embedding"]) for row in top]],
        }

    def delete(self, where: dict) -> None:
        doc_id = where.get("doc_id")
        self.rows = [row for row in self.rows if row["metadata"].get("doc_id") != doc_id]


class MockChromaClient:
    def __init__(self) -> None:
        self.collection = MockCollection()

    def get_or_create_collection(self, name: str, metadata: dict) -> MockCollection:
        _ = name, metadata
        return self.collection


@pytest.fixture(autouse=True)
def test_environment(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path / "chroma"))
    get_settings.cache_clear()

    mock_client = MockOpenAIClient()
    set_embedding_client(mock_client)
    set_chat_client(mock_client)
    set_chroma_client(MockChromaClient())

    settings = get_settings()
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    settings.chroma_path.mkdir(parents=True, exist_ok=True)

    yield

    set_embedding_client(None)
    set_chat_client(None)
    set_chroma_client(None)
    get_settings.cache_clear()


@pytest.fixture
async def api_client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
