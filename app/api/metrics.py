from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.config import get_settings
from app.db.models import User
from app.observability.metrics import get_metrics
from app.services.auth_dependencies import get_current_user


router = APIRouter(prefix="/api", tags=["metrics"])


@router.get("/metrics")
async def metrics(user: User = Depends(get_current_user)) -> dict:
    _ = user  # auth gate; also binds user_id in auth dependency for logs
    settings = get_settings()
    if not settings.enable_metrics_endpoint:
        raise HTTPException(status_code=404, detail="Not found")
    return get_metrics().snapshot()

