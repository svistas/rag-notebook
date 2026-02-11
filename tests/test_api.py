import io


async def test_upload_endpoint_accepts_text_file(api_client) -> None:
    files = {"file": ("notes.txt", io.BytesIO(b"RAG stands for Retrieval Augmented Generation."), "text/plain")}
    response = await api_client.post("/api/upload", files=files)
    assert response.status_code == 200
    payload = response.json()
    assert payload["document"]["filename"] == "notes.txt"
    assert payload["document"]["chunk_count"] >= 1


async def test_upload_endpoint_rejects_invalid_file_extension(api_client) -> None:
    files = {"file": ("malware.exe", io.BytesIO(b"not allowed"), "application/octet-stream")}
    response = await api_client.post("/api/upload", files=files)
    assert response.status_code == 400


async def test_chat_endpoint_returns_answer_with_citations(api_client) -> None:
    files = {"file": ("guide.md", io.BytesIO(b"RAG uses retrieval and generation with grounding."), "text/markdown")}
    upload_response = await api_client.post("/api/upload", files=files)
    assert upload_response.status_code == 200

    response = await api_client.post("/api/chat", json={"query": "What is RAG?"})
    assert response.status_code == 200
    payload = response.json()
    assert "answer" in payload
    assert isinstance(payload["citations"], list)
    assert len(payload["citations"]) >= 1


async def test_documents_endpoint_lists_uploaded_documents(api_client) -> None:
    files = {"file": ("doc.txt", io.BytesIO(b"Document content"), "text/plain")}
    await api_client.post("/api/upload", files=files)

    response = await api_client.get("/api/documents")
    assert response.status_code == 200
    payload = response.json()
    assert "documents" in payload
    assert len(payload["documents"]) >= 1
