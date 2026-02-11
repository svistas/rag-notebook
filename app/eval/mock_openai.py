from __future__ import annotations

import json
import math


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
        system = (messages[0].get("content") or "").lower()
        user = messages[-1].get("content") or ""

        # Week 3 query rewriting: return plain rewritten query.
        if "rewrite user questions" in system or "rewrite user question" in system:
            cleaned = user.split("User question:\n", 1)[-1].split("\n\nRewritten retrieval query:", 1)[0].strip()
            return _ChatResponse(f"retrieval: {cleaned}")

        # Week 3 reranking: return strict JSON {"ranked_ids":[...]}
        if "reranking model" in system and "ranked_ids" in system:
            try:
                payload = json.loads(user)
                candidates = payload.get("candidates", [])
                ids = [c.get("id") for c in candidates if isinstance(c, dict) and isinstance(c.get("id"), str)]
                top_n = int(payload.get("top_n", 5))
                ranked = ids[:top_n]
            except Exception:
                ranked = []
            return _ChatResponse(json.dumps({"ranked_ids": ranked}))

        # Default answering behavior with a citation marker.
        question = user.split("Question:\n", 1)[-1].split("\n\nContext:", 1)[0]
        return _ChatResponse(f"Mock answer for: {question} [1]")


class MockChatApi:
    def __init__(self) -> None:
        self.completions = MockChatCompletionsApi()


class MockOpenAIClient:
    def __init__(self) -> None:
        self.embeddings = MockEmbeddingsApi()
        self.chat = MockChatApi()

