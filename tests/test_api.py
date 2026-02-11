import io

from app.services.document_service import index_document_task


async def _register_and_login(api_client, email: str, password: str) -> str:
    # Register (also sets session cookie)
    resp = await api_client.post("/auth/register", data={"email": email, "password": password})
    assert resp.status_code == 200

    me = await api_client.get("/auth/me")
    assert me.status_code == 200
    return me.json()["id"]


async def test_responses_include_x_request_id(api_client) -> None:
    resp = await api_client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("x-request-id")


async def test_upload_endpoint_accepts_text_file(api_client) -> None:
    user_id = await _register_and_login(api_client, "a@example.com", "password123")
    files = {"file": ("notes.txt", io.BytesIO(b"RAG stands for Retrieval Augmented Generation."), "text/plain")}
    response = await api_client.post("/api/upload", files=files)
    assert response.status_code == 200
    payload = response.json()
    assert payload["document"]["filename"] == "notes.txt"
    assert payload["document"]["status"] == "queued"
    assert payload["document"]["chunk_count"] == 0


async def test_upload_endpoint_rejects_invalid_file_extension(api_client) -> None:
    _ = await _register_and_login(api_client, "a2@example.com", "password123")
    files = {"file": ("malware.exe", io.BytesIO(b"not allowed"), "application/octet-stream")}
    response = await api_client.post("/api/upload", files=files)
    assert response.status_code == 400


async def test_upload_endpoint_accepts_pdf_file(api_client, monkeypatch) -> None:
    # Avoid having to construct a real PDF in tests; just ensure the pipeline calls the extractor.
    from app.services import pdf_service

    monkeypatch.setattr(pdf_service, "extract_text_from_pdf", lambda _b: "PDF extracted text")

    user_id = await _register_and_login(api_client, "pdf@example.com", "password123")
    files = {"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")}
    upload_resp = await api_client.post("/api/upload", files=files)
    assert upload_resp.status_code == 200
    doc_id = upload_resp.json()["document"]["id"]

    index_document_task(user_id, doc_id)
    doc_resp = await api_client.get(f"/api/documents/{doc_id}")
    assert doc_resp.status_code == 200
    assert doc_resp.json()["status"] == "indexed"


async def test_chat_endpoint_returns_answer_with_citations(api_client) -> None:
    user_id = await _register_and_login(api_client, "chat@example.com", "password123")
    files = {"file": ("guide.md", io.BytesIO(b"RAG uses retrieval and generation with grounding."), "text/markdown")}
    upload_response = await api_client.post("/api/upload", files=files)
    assert upload_response.status_code == 200
    doc_id = upload_response.json()["document"]["id"]
    index_document_task(user_id, doc_id)

    response = await api_client.post("/api/chat", json={"query": "What is RAG?"})
    assert response.status_code == 200
    payload = response.json()
    assert "answer" in payload
    assert isinstance(payload["citations"], list)
    assert len(payload["citations"]) >= 1
    assert payload.get("debug") is None


async def test_documents_endpoint_lists_uploaded_documents(api_client) -> None:
    _ = await _register_and_login(api_client, "list@example.com", "password123")
    files = {"file": ("doc.txt", io.BytesIO(b"Document content"), "text/plain")}
    upload_resp = await api_client.post("/api/upload", files=files)
    assert upload_resp.status_code == 200

    response = await api_client.get("/api/documents")
    assert response.status_code == 200
    payload = response.json()
    assert "documents" in payload
    assert len(payload["documents"]) >= 1
    assert payload["documents"][0]["status"] in {"queued", "indexing", "indexed", "failed"}


async def test_delete_endpoint_removes_document_and_vectors(api_client) -> None:
    user_id = await _register_and_login(api_client, "del@example.com", "password123")
    files = {"file": ("doc.txt", io.BytesIO(b"Apples are fruits."), "text/plain")}
    upload_resp = await api_client.post("/api/upload", files=files)
    doc_id = upload_resp.json()["document"]["id"]
    index_document_task(user_id, doc_id)

    del_resp = await api_client.delete(f"/api/documents/{doc_id}")
    assert del_resp.status_code == 200

    list_resp = await api_client.get("/api/documents")
    docs = list_resp.json()["documents"]
    assert all(d["id"] != doc_id for d in docs)


async def test_reindex_endpoint_queues_and_allows_reindex(api_client) -> None:
    user_id = await _register_and_login(api_client, "reindex@example.com", "password123")
    files = {"file": ("doc.txt", io.BytesIO(b"FastAPI builds APIs."), "text/plain")}
    upload_resp = await api_client.post("/api/upload", files=files)
    doc_id = upload_resp.json()["document"]["id"]
    index_document_task(user_id, doc_id)

    re_resp = await api_client.post(f"/api/documents/{doc_id}/reindex")
    assert re_resp.status_code == 200
    queued_doc = re_resp.json()
    assert queued_doc["status"] == "queued"
    assert queued_doc["chunk_count"] == 0

    index_document_task(user_id, doc_id)
    doc_resp = await api_client.get(f"/api/documents/{doc_id}")
    assert doc_resp.status_code == 200
    indexed = doc_resp.json()
    assert indexed["status"] == "indexed"
    assert indexed["chunk_count"] >= 1


async def test_chat_debug_mode_returns_retrieval_trace(api_client) -> None:
    user_id = await _register_and_login(api_client, "debug@example.com", "password123")
    files = {"file": ("guide.md", io.BytesIO(b"RAG uses retrieval and generation with grounding."), "text/markdown")}
    upload_response = await api_client.post("/api/upload", files=files)
    assert upload_response.status_code == 200
    doc_id = upload_response.json()["document"]["id"]
    index_document_task(user_id, doc_id)

    response = await api_client.post("/api/chat", json={"query": "What is RAG?", "debug": True})
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("debug") is not None
    dbg = payload["debug"]
    assert dbg["user_query"] == "What is RAG?"
    assert "rewritten_query" in dbg
    assert isinstance(dbg["initial_chunks"], list)
    assert isinstance(dbg["final_chunks"], list)


async def test_access_control_user_cannot_delete_other_users_document(api_client) -> None:
    # user A registers and uploads
    user_a_id = await _register_and_login(api_client, "a_acl@example.com", "password123")
    files = {"file": ("doc.txt", io.BytesIO(b"Private A content"), "text/plain")}
    upload_resp = await api_client.post("/api/upload", files=files)
    doc_id = upload_resp.json()["document"]["id"]
    index_document_task(user_a_id, doc_id)

    # log out and register user B
    await api_client.post("/auth/logout")
    _ = await _register_and_login(api_client, "b_acl@example.com", "password123")

    # user B cannot see or delete user A's doc
    get_resp = await api_client.get(f"/api/documents/{doc_id}")
    assert get_resp.status_code == 404
    del_resp = await api_client.delete(f"/api/documents/{doc_id}")
    assert del_resp.status_code == 404
