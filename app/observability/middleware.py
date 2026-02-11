from __future__ import annotations

import uuid
from time import perf_counter
from typing import Any, Callable

import structlog
from starlette.datastructures import MutableHeaders

from app.observability.metrics import get_metrics


class RequestContextMiddleware:
    """Adds request_id context, access logs, and basic HTTP metrics."""

    def __init__(self, app: Callable[..., Any]) -> None:
        self.app = app
        # Avoid self-observing the observability endpoints.
        self._excluded_metric_paths = {"/api/metrics", "/metrics"}

    async def __call__(self, scope: dict[str, Any], receive: Callable[..., Any], send: Callable[..., Any]) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid.uuid4())
        path = scope.get("path")
        method = scope.get("method")

        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            path=path,
            method=method,
        )

        start = perf_counter()
        status_code: int = 500

        async def send_wrapper(message: dict[str, Any]) -> None:
            nonlocal status_code

            if message.get("type") == "http.response.start":
                status_code = int(message.get("status", 500))
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id

            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed_ms = (perf_counter() - start) * 1000.0

            # Update metrics first so they update even if logging misbehaves.
            # Exclude the metrics endpoints to avoid feedback loops in dashboards.
            if path not in self._excluded_metric_paths:
                get_metrics().observe_http_request(elapsed_ms=elapsed_ms)

            structlog.get_logger("access").info(
                "http_request",
                status_code=status_code,
                elapsed_ms=round(elapsed_ms, 2),
            )

            structlog.contextvars.clear_contextvars()

