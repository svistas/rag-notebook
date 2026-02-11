# Week 6 Learning Notes: Observability + Metrics

Week 6 adds lightweight observability to make debugging and performance tracking practical during local development.

## 1) Why request IDs?

When something goes wrong in a web app, the client usually only has:
- the failing endpoint
- a timestamp
- maybe a screenshot

Adding a `X-Request-ID` to every response gives you a stable correlation key you can copy from DevTools and search for in logs.

## 2) Why `contextvars` for logging?

Request-specific fields (like `request_id` and `user_id`) should be automatically attached to logs emitted deeper in the call stack (services, RAG helpers, database code).

Using `structlog.contextvars` avoids threading that data through every function signature, while still keeping the data isolated per request.

## 3) In-memory metrics: useful, but limited

The Week 6 `/api/metrics` endpoint exposes a small snapshot:
- HTTP request count + latency aggregates
- OpenAI call count + latency aggregates
- token usage totals when available

Trade-offs:
- resets on server restart
- only visible from the single running process
- not suitable for multi-worker deployments

## 4) What to improve later

- Export metrics to Prometheus (or another backend) and add per-route dimensions
- Track error rates separately from success counts
- Add distributed tracing (OpenTelemetry) to connect requests to database + OpenAI spans

