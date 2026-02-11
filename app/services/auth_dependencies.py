from __future__ import annotations

import uuid

from fastapi import Cookie, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import User
from app.db.session import get_db
from app.services.auth_service import decode_session_token


def get_current_user(
    db: Session = Depends(get_db),
    session_cookie: str | None = Cookie(default=None, alias="rag_session"),
) -> User:
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = decode_session_token(session_cookie)
        user_id = payload.get("sub")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="Invalid session") from exc

    try:
        user_uuid = uuid.UUID(str(user_id))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="Invalid session") from exc

    user = db.execute(select(User).where(User.id == user_uuid)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

