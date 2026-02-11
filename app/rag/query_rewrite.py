from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from app.config import get_settings
from app.observability.openai import instrument_openai_call

_rewrite_client: Any | None = None


@dataclass(frozen=True)
class RewriteResult:
    user_query: str
    rewritten_query: str


def set_rewrite_client(client: Any | None) -> None:
    global _rewrite_client
    _rewrite_client = client


def get_rewrite_client() -> Any:
    global _rewrite_client
    if _rewrite_client is None:
        settings = get_settings()
        _rewrite_client = OpenAI(api_key=settings.openai_api_key)
    return _rewrite_client


def rewrite_query(user_query: str, model: str | None = None) -> RewriteResult:
    """
    Rewrite the user's query to improve retrieval.

    Output is a single plain-text query string (no JSON).
    """
    cleaned = (user_query or "").strip()
    if not cleaned:
        return RewriteResult(user_query=user_query, rewritten_query="")

    settings = get_settings()
    client = get_rewrite_client()

    system_prompt = (
        "You rewrite user questions into concise search queries for retrieving relevant document chunks. "
        "Keep key nouns, names, dates, and constraints. Remove filler. "
        "Output ONLY the rewritten query text. Do not add quotes or extra commentary."
    )
    user_prompt = f"User question:\n{cleaned}\n\nRewritten retrieval query:"

    actual_model = model or getattr(settings, "rewrite_model", settings.openai_model)
    response = instrument_openai_call(
        operation="chat.completions.create",
        model=actual_model,
        fn=lambda: client.chat.completions.create(
            model=actual_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
        ),
    )
    rewritten = (response.choices[0].message.content or "").strip()
    if not rewritten:
        rewritten = cleaned

    return RewriteResult(user_query=cleaned, rewritten_query=rewritten)

