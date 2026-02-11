from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


_CONFIGURED = False


def configure_logging(level: int = logging.INFO) -> None:
    """Configure structlog + stdlib logging for JSON output.

    Safe to call multiple times (no-op after first call).
    """

    global _CONFIGURED
    if _CONFIGURED:
        return

    pre_chain: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=[
            *pre_chain,
            # Let ProcessorFormatter render JSON for stdlib log records too.
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=pre_chain,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    # Keep uvicorn's own loggers consistent with our handler.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers = [handler]
        logger.propagate = False
        logger.setLevel(level)

    _CONFIGURED = True

