from __future__ import annotations

from typing import Any

from openai import OpenAI

from app.config import get_settings
from app.observability.openai import instrument_openai_call

_client: Any | None = None


def set_embedding_client(client: Any | None) -> None:
    global _client
    _client = client


def get_embedding_client() -> Any:
    global _client
    if _client is None:
        settings = get_settings()
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def get_embeddings(texts: list[str], batch_size: int = 100) -> list[list[float]]:
    if not texts:
        return []

    settings = get_settings()
    client = get_embedding_client()
    vectors: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = instrument_openai_call(
            operation="embeddings.create",
            model=settings.embedding_model,
            fn=lambda: client.embeddings.create(model=settings.embedding_model, input=batch),
        )
        vectors.extend([item.embedding for item in response.data])

    return vectors
