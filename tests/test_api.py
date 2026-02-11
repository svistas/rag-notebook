import io

from app.services.document_service import index_document


async def test_upload_endpoint_accepts_text_file(api_client) -> None:
    files = {"file": ("notes.txt", io.BytesIO(b"RAG stands for Retrieval Augmented Generation."), "text/plain")}
    response = await api_client.post("/api/upload", files=files)
    assert response.status_code == 200
    payload = response.json()
    assert payload["document"]["filename"] == "notes.txt"
    assert payload["document"]["status"] == "queued"
    assert payload["document"]["chunk_count"] == 0


async def test_upload_endpoint_rejects_invalid_file_extension(api_client) -> None:
    files = {"file": ("malware.exe", io.BytesIO(b"not allowed"), "application/octet-stream")}
    response = await api_client.post("/api/upload", files=files)
    assert response.status_code == 400


async def test_chat_endpoint_returns_answer_with_citations(api_client) -> None:
    files = {"file": ("guide.md", io.BytesIO(b"RAG uses retrieval and generation with grounding."), "text/markdown")}
    upload_response = await api_client.post("/api/upload", files=files)
    assert upload_response.status_code == 200
    doc_id = upload_response.json()["document"]["id"]
    index_document(doc_id)

    response = await api_client.post("/api/chat", json={"query": "What is RAG?"})
    assert response.status_code == 200
    payload = response.json()
    assert "answer" in payload
    assert isinstance(payload["citations"], list)
    assert len(payload["citations"]) >= 1


async def test_documents_endpoint_lists_uploaded_documents(api_client) -> None:
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
    files = {"file": ("doc.txt", io.BytesIO(b"Apples are fruits."), "text/plain")}
    upload_resp = await api_client.post("/api/upload", files=files)
    doc_id = upload_resp.json()["document"]["id"]
    index_document(doc_id)

    del_resp = await api_client.delete(f"/api/documents/{doc_id}")
    assert del_resp.status_code == 200

    list_resp = await api_client.get("/api/documents")
    docs = list_resp.json()["documents"]
    assert all(d["id"] != doc_id for d in docs)


async def test_reindex_endpoint_queues_and_allows_reindex(api_client) -> None:
    files = {"file": ("doc.txt", io.BytesIO(b"FastAPI builds APIs."), "text/plain")}
    upload_resp = await api_client.post("/api/upload", files=files)
    doc_id = upload_resp.json()["document"]["id"]
    index_document(doc_id)

    re_resp = await api_client.post(f"/api/documents/{doc_id}/reindex")
    assert re_resp.status_code == 200
    queued_doc = re_resp.json()
    assert queued_doc["status"] == "queued"
    assert queued_doc["chunk_count"] == 0

    index_document(doc_id)
    doc_resp = await api_client.get(f"/api/documents/{doc_id}")
    assert doc_resp.status_code == 200
    indexed = doc_resp.json()
    assert indexed["status"] == "indexed"
    assert indexed["chunk_count"] >= 1
