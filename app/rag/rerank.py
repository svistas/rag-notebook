from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from app.config import get_settings
from app.models.schemas import RetrievedChunk

_rerank_client: Any | None = None


@dataclass(frozen=True)
class RerankResult:
    ranked_ids: list[str]
    used_fallback: bool


def set_rerank_client(client: Any | None) -> None:
    global _rerank_client
    _rerank_client = client


def get_rerank_client() -> Any:
    global _rerank_client
    if _rerank_client is None:
        settings = get_settings()
        _rerank_client = OpenAI(api_key=settings.openai_api_key)
    return _rerank_client


def rerank(query: str, chunks: list[RetrievedChunk], top_n: int, model: str | None = None) -> RerankResult:
    if top_n <= 0:
        return RerankResult(ranked_ids=[], used_fallback=True)

    if not chunks:
        return RerankResult(ranked_ids=[], used_fallback=True)

    settings = get_settings()
    client = get_rerank_client()

    candidates = []
    for chunk in chunks:
        candidates.append(
            {
                "id": chunk.id,
                "document_name": chunk.document_name,
                "chunk_index": chunk.chunk_index,
                "text": chunk.text[:1200],
            }
        )

    system_prompt = (
        "You are a reranking model for retrieval-augmented QA. "
        "Given a user question and candidate chunks, select the best chunks to answer the question. "
        "Return ONLY valid JSON with key \"ranked_ids\" as a list of chunk ids in best-first order. "
        "Do not include any other keys."
    )
    user_prompt = json.dumps(
        {
            "query": query,
            "top_n": top_n,
            "candidates": candidates,
        }
    )

    try:
        response = client.chat.completions.create(
            model=model or getattr(settings, "rerank_model", settings.openai_model),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
        )
        content = (response.choices[0].message.content or "").strip()
        parsed = json.loads(content)
        ranked = parsed.get("ranked_ids", [])
        if not isinstance(ranked, list) or not all(isinstance(x, str) for x in ranked):
            raise ValueError("Invalid ranked_ids")

        # Filter to known ids and keep order.
        known = {c.id for c in chunks}
        ranked_filtered = [rid for rid in ranked if rid in known]
        if not ranked_filtered:
            raise ValueError("Empty rerank result")

        return RerankResult(ranked_ids=ranked_filtered[:top_n], used_fallback=False)
    except Exception:
        # Fallback: preserve original similarity order.
        return RerankResult(ranked_ids=[c.id for c in chunks[:top_n]], used_fallback=True)

