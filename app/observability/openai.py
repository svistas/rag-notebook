from __future__ import annotations

from time import perf_counter
from typing import Any, Callable, TypeVar

import structlog

from app.observability.metrics import get_metrics


T = TypeVar("T")


def _extract_total_tokens(resp: Any) -> int | None:
    usage = getattr(resp, "usage", None)
    if usage is None:
        return None

    # OpenAI SDK usage can be a pydantic model-like object or a dict-like.
    total = getattr(usage, "total_tokens", None)
    if isinstance(total, int):
        return total

    if isinstance(usage, dict):
        total = usage.get("total_tokens")
        if isinstance(total, int):
            return total

    return None


def instrument_openai_call(*, operation: str, model: str, fn: Callable[[], T]) -> T:
    """Time a call, update metrics, and emit a structured log event."""

    start = perf_counter()
    try:
        resp = fn()
        return resp
    except Exception:
        elapsed_ms = (perf_counter() - start) * 1000.0
        get_metrics().observe_openai_call(elapsed_ms=elapsed_ms, tokens_total=None)
        structlog.get_logger("openai").exception(
            "openai_call_failed",
            operation=operation,
            model=model,
            elapsed_ms=round(elapsed_ms, 2),
        )
        raise
    finally:
        # If fn() raised, we already observed + logged exception above; keep this branch for success only.
        # (Avoid double-counting by checking for 'resp' in locals.)
        if "resp" in locals():
            elapsed_ms = (perf_counter() - start) * 1000.0
            tokens_total = _extract_total_tokens(locals()["resp"])
            get_metrics().observe_openai_call(elapsed_ms=elapsed_ms, tokens_total=tokens_total)
            structlog.get_logger("openai").info(
                "openai_call",
                operation=operation,
                model=model,
                elapsed_ms=round(elapsed_ms, 2),
                tokens_total=tokens_total,
            )

