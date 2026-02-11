from __future__ import annotations

from dataclasses import asdict, dataclass
from threading import Lock
from typing import Any


@dataclass
class _LatencyAgg:
    count: int = 0
    sum_ms: float = 0.0
    max_ms: float = 0.0

    def observe(self, elapsed_ms: float) -> None:
        self.count += 1
        self.sum_ms += float(elapsed_ms)
        if elapsed_ms > self.max_ms:
            self.max_ms = float(elapsed_ms)


class InMemoryMetrics:
    """Thread-safe, process-local metrics (resets on restart)."""

    def __init__(self) -> None:
        self._lock = Lock()
        self.http_requests_total: int = 0
        self.openai_calls_total: int = 0
        self.openai_tokens_total: int = 0
        self.http_request_ms = _LatencyAgg()
        self.openai_call_ms = _LatencyAgg()

    def observe_http_request(self, elapsed_ms: float) -> None:
        with self._lock:
            self.http_requests_total += 1
            self.http_request_ms.observe(elapsed_ms)

    def observe_openai_call(self, elapsed_ms: float, tokens_total: int | None = None) -> None:
        with self._lock:
            self.openai_calls_total += 1
            self.openai_call_ms.observe(elapsed_ms)
            if tokens_total is not None:
                try:
                    self.openai_tokens_total += int(tokens_total)
                except Exception:
                    # Don't let strange usage shapes break the app.
                    pass

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "counters": {
                    "http_requests_total": self.http_requests_total,
                    "openai_calls_total": self.openai_calls_total,
                    "openai_tokens_total": self.openai_tokens_total,
                },
                "latency_ms": {
                    "http_request_ms": asdict(self.http_request_ms),
                    "openai_call_ms": asdict(self.openai_call_ms),
                },
            }

    def reset(self) -> None:
        with self._lock:
            self.http_requests_total = 0
            self.openai_calls_total = 0
            self.openai_tokens_total = 0
            self.http_request_ms = _LatencyAgg()
            self.openai_call_ms = _LatencyAgg()


_METRICS: InMemoryMetrics | None = None


def get_metrics() -> InMemoryMetrics:
    global _METRICS
    if _METRICS is None:
        _METRICS = InMemoryMetrics()
    return _METRICS


def reset_metrics() -> None:
    """Reset metrics counters/aggregates (used by tests)."""

    get_metrics().reset()

