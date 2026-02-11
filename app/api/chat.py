from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.schemas import ChatRequest, ChatResponse
from app.db.models import User
from app.db.session import get_db
from app.rag.prompting import generate_answer
from app.rag.retrieval import retrieve_with_debug
from app.services.auth_dependencies import get_current_user

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat_with_documents(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ChatResponse:
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query must not be empty")

    debug_requested = bool(payload.debug)
    result = retrieve_with_debug(db=db, user=user, user_query=query)
    chunks = result.final_chunks

    if not chunks:
        return ChatResponse(
            answer="I could not find relevant context in uploaded documents. Could you clarify your question?",
            citations=[],
        )

    response = generate_answer(query=query, chunks=chunks)
    if debug_requested:
        response.debug = result.debug
    return response
