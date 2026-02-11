from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import ChatRequest, ChatResponse
from app.rag.prompting import generate_answer
from app.rag.retrieval import retrieve, retrieve_with_debug

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat_with_documents(payload: ChatRequest) -> ChatResponse:
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query must not be empty")

    debug_requested = bool(payload.debug)
    if debug_requested:
        result = retrieve_with_debug(user_query=query)
        chunks = result.final_chunks
    else:
        chunks = retrieve(query=query)

    if not chunks:
        return ChatResponse(
            answer="I could not find relevant context in uploaded documents. Could you clarify your question?",
            citations=[],
        )

    response = generate_answer(query=query, chunks=chunks)
    if debug_requested:
        response.debug = result.debug
    return response
