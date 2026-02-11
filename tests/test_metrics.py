import io

from app.services.document_service import index_document_task


async def _register_and_login(api_client, email: str, password: str) -> str:
    resp = await api_client.post("/auth/register", data={"email": email, "password": password})
    assert resp.status_code == 200

    me = await api_client.get("/auth/me")
    assert me.status_code == 200
    return me.json()["id"]


async def test_metrics_endpoint_requires_auth(api_client) -> None:
    resp = await api_client.get("/api/metrics")
    assert resp.status_code == 401


async def test_metrics_endpoint_returns_snapshot_and_counts_requests(api_client) -> None:
    _ = await _register_and_login(api_client, "metrics@example.com", "password123")

    m1 = await api_client.get("/api/metrics")
    assert m1.status_code == 200
    payload1 = m1.json()
    assert "counters" in payload1
    assert "latency_ms" in payload1

    # /api/metrics itself should NOT affect http_requests_total.
    m1b = await api_client.get("/api/metrics")
    assert m1b.status_code == 200
    payload1b = m1b.json()
    assert payload1b["counters"]["http_requests_total"] == payload1["counters"]["http_requests_total"]

    # One arbitrary request we can control between snapshots.
    health = await api_client.get("/health")
    assert health.status_code == 200

    m2 = await api_client.get("/api/metrics")
    payload2 = m2.json()

    # Between m1 and m2 we made one countable request: /health.
    assert payload2["counters"]["http_requests_total"] >= payload1["counters"]["http_requests_total"] + 1


async def test_openai_calls_are_counted_in_metrics(api_client) -> None:
    user_id = await _register_and_login(api_client, "openai-metrics@example.com", "password123")

    files = {"file": ("notes.txt", io.BytesIO(b"RAG stands for Retrieval Augmented Generation."), "text/plain")}
    upload = await api_client.post("/api/upload", files=files)
    assert upload.status_code == 200
    doc_id = upload.json()["document"]["id"]

    # Triggers embeddings calls (mocked in tests).
    index_document_task(user_id, doc_id)

    metrics = await api_client.get("/api/metrics")
    assert metrics.status_code == 200
    payload = metrics.json()
    assert payload["counters"]["openai_calls_total"] >= 1

