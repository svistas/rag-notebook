from __future__ import annotations

import re
from typing import Any

from openai import OpenAI

from app.config import get_settings
from app.models.schemas import ChatResponse, Citation, RetrievedChunk
from app.observability.openai import instrument_openai_call

_chat_client: Any | None = None


def set_chat_client(client: Any | None) -> None:
    global _chat_client
    _chat_client = client


def get_chat_client() -> Any:
    global _chat_client
    if _chat_client is None:
        settings = get_settings()
        _chat_client = OpenAI(api_key=settings.openai_api_key)
    return _chat_client


def build_prompt(query: str, chunks: list[RetrievedChunk]) -> list[dict[str, str]]:
    context_blocks: list[str] = []
    for idx, chunk in enumerate(chunks, start=1):
        context_blocks.append(
            f"[{idx}] document={chunk.document_name} chunk_index={chunk.chunk_index}\n{chunk.text}"
        )

    context = "\n\n".join(context_blocks) if context_blocks else "No context available."

    system_prompt = (
        "You are a grounded assistant for document Q&A. "
        "Answer ONLY from the provided context. "
        "If context is missing or weak, say you are unsure and ask a clarifying question. "
        "Always cite supporting sources inline like [1], [2]. "
        "Do not fabricate citations or facts."
    )

    user_prompt = f"Question:\n{query}\n\nContext:\n{context}"
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _extract_citation_numbers(answer: str) -> list[int]:
    seen: set[int] = set()
    ordered: list[int] = []
    for match in re.finditer(r"\\[(\\d+)\\]", answer):
        number = int(match.group(1))
        if number not in seen:
            seen.add(number)
            ordered.append(number)
    return ordered


def generate_answer(query: str, chunks: list[RetrievedChunk]) -> ChatResponse:
    messages = build_prompt(query=query, chunks=chunks)
    settings = get_settings()
    client = get_chat_client()

    response = instrument_openai_call(
        operation="chat.completions.create",
        model=settings.openai_model,
        fn=lambda: client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            temperature=0.1,
        ),
    )
    answer = response.choices[0].message.content or "I am unsure based on the available context."

    citation_numbers = _extract_citation_numbers(answer)
    if not citation_numbers and chunks:
        citation_numbers = [1]
        answer = f"{answer}\\n\\n[1]"

    citations: list[Citation] = []
    for number in citation_numbers:
        source_idx = number - 1
        if 0 <= source_idx < len(chunks):
            source = chunks[source_idx]
            citations.append(
                Citation(
                    number=number,
                    text=source.text,
                    document_name=source.document_name,
                    chunk_index=source.chunk_index,
                )
            )

    return ChatResponse(answer=answer, citations=citations)

