# RAG Notebook (Weeks 1-3)

RAG Notebook is a production-style Retrieval-Augmented Generation portfolio project built in weekly vertical slices.

Week 1 delivers an end-to-end MVP:
- Upload `.txt` or `.md` documents
- Chunk and embed them with OpenAI embeddings
- Store vectors locally in ChromaDB
- Ask questions and receive citation-based answers

Week 2 adds document management:
- Document library shows indexing state (`queued`, `indexing`, `indexed`, `failed`)
- Upload returns immediately and indexing runs in the background
- Delete and reindex document actions

Week 3 improves retrieval quality:
- Query rewriting before vector search
- Lightweight reranking of retrieved chunks
- Debug mode in UI showing rewritten query + chunk selection

## Tech Stack

- Python 3.11+
- FastAPI + Jinja2 templates
- OpenAI Python SDK
- ChromaDB (local persistent vector store)
- Pydantic Settings
- pytest + httpx
- Poetry dependency management

## Project Structure

```text
app/
  api/            # Upload, chat, documents endpoints
  services/       # Ingestion orchestration
  models/         # Pydantic schemas
  rag/            # Chunking, embedding, retrieval, prompting
  db/             # Chroma vector store wrapper
  templates/      # HTML UI
data/             # Local uploaded files + metadata
tests/            # Unit and API tests
docs/             # Learning notes
```

## Local Setup

1. Install dependencies:

```bash
poetry install --no-root
```

2. Create your environment file:

```bash
cp .env.example .env
```

3. Add your OpenAI key in `.env`:

```env
OPENAI_API_KEY=your-real-key
```

## Run the App

```bash
poetry run uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Run Tests

```bash
poetry run pytest -q
```

## Demo Instructions

1. Start the app.
2. Upload a `.txt` or `.md` document from the left panel.
3. Confirm it appears in the document library.
4. Watch the document status move from `queued` -> `indexing` -> `indexed`.
5. Ask a question in the chat panel.
6. Verify the response includes inline citation markers (`[1]`, `[2]`) and expandable source excerpts.
7. Try `Reindex` and `Delete` from the library.
8. Toggle `Debug mode` and ask the same question again to inspect rewritten query and retrieved chunks.

## Week 1 Security Baselines

- File type validation (`.txt`, `.md`)
- Upload size limit via config (`MAX_UPLOAD_SIZE_MB`)
- Filename sanitization before saving
- Secrets excluded via `.env` and `.gitignore`

## Week 2 Notes

- Upload immediately returns a `queued` document and indexing happens asynchronously using FastAPI background tasks.
- Document metadata is stored locally in `data/documents.json` (kept intentionally simple for Week 2).

## Week 3 Notes

- Debug mode adds a `debug` flag to `/api/chat` responses so you can see:\n  - rewritten query\n  - initial retrieved chunk list\n  - final reranked chunk list\n+- Query rewriting and reranking are controlled by env flags:\n  - `ENABLE_QUERY_REWRITE`\n  - `ENABLE_RERANK`\n  - `RERANK_TOP_N`\n  - `REWRITE_MODEL`\n  - `RERANK_MODEL`\n+
## Week 4 Backlog (Preview)

- Authentication + multi-user document isolation
- Migrate to Postgres + pgvector
- Access control tests

