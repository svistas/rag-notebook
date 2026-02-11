# RAG Notebook (Weeks 1-6)

RAG Notebook is a production-style Retrieval-Augmented Generation portfolio project built in weekly vertical slices.

Week 1 delivers an end-to-end MVP:
- Upload `.txt` or `.md` documents (Week 2 stretch adds basic `.pdf`)
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

Week 4 adds auth + multi-user isolation:
- Register/login/logout with JWT cookie sessions
- Per-user document isolation for upload/list/delete/chat
- Storage backed by Postgres + pgvector (dev via Docker Compose)

Week 6 adds lightweight observability:
- `X-Request-ID` on every HTTP response
- Structured JSON logs with request-scoped fields (`request_id`, `user_id`, etc.)
- Auth-required `/api/metrics` endpoint for basic request + OpenAI counters/latencies

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
  observability/  # Request context, structured logs, in-memory metrics
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

4. Start Postgres (Week 4):

```bash
docker compose up -d db
```

5. Run DB migrations:

```bash
poetry run alembic upgrade head
```

## Run the App

```bash
poetry run uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Run With Docker Compose (Week 7)

This runs the full stack (app + Postgres) and automatically applies migrations on startup.

```bash
docker compose up --build
```

- App: `http://127.0.0.1:8000`
- Postgres: exposed on `localhost:5432`
- Persistent data:
  - uploads: `rag_notebook_uploads` volume
  - chroma: `rag_notebook_chroma` volume

Environment variables are read from your shell (and you can still use `.env` locally). At minimum, set:

```bash
export OPENAI_API_KEY="..."
export JWT_SECRET="..."
```

## Deploy To Railway (Week 7)

Deployment uses the repo `Dockerfile`, Railway Postgres, a Railway Volume mounted at `/data`, and a Pre-deploy Command to run migrations.

1. Create a new Railway project and connect this repo.
2. Add a Postgres service/plugin and set `DATABASE_URL` for the app service (Railway provides this).
3. Add a Railway Volume to the app service:
   - mount path: `/data`
4. Set environment variables on the app service:
   - `OPENAI_API_KEY`: your key
   - `JWT_SECRET`: a long random secret
   - `UPLOAD_DIR=/data/uploads`
   - `CHROMA_DIR=/data/chroma`
5. Configure commands:
   - Start Command: `bash docker/start.sh`
   - Pre-deploy Command: `bash docker/migrate.sh`

Notes:
- Railway sets `PORT` automatically; the start script binds to it.
- If you don’t attach a Volume, uploads and Chroma data will be ephemeral.

## Observability (Week 6)

- `X-Request-ID`: included on every response. Use it to correlate a client error with server logs.
- Structured logs: emitted as JSON and include `request_id` and (when authenticated) `user_id`.
- Metrics endpoint:
  - `GET /api/metrics` (auth required)
  - Toggle with `ENABLE_METRICS_ENDPOINT=True|False` (default true)
  - Metrics are in-memory and reset on server restart

## Offline Evaluation (Week 5)

Run a small golden dataset through the RAG pipeline and write a JSON report:

```bash
poetry run python -m app.eval --dataset eval/golden.jsonl --out eval/results/latest.json --cleanup
```

Deterministic mode (no network, good for CI):

```bash
poetry run python -m app.eval --mock --max-cases 2
```

What it checks (lightweight heuristics):
- `retrieval_hit`: required document appears in retrieved chunks
- `citations_match`: required document appears in citations list
- `keyword_coverage`: answer contains expected keywords
- `no_forbidden_keywords`: answer avoids forbidden keywords
- `abstention_ok`: for \"not in docs\" cases, answer shows uncertainty

## Run Tests

```bash
poetry run pytest -q
```

## Demo Instructions

1. Start the app.
2. Upload a `.txt` or `.md` document from the left panel.
   - PDFs are supported as a basic stretch (text extraction quality depends on the PDF).
3. Confirm it appears in the document library.
4. Watch the document status move from `queued` -> `indexing` -> `indexed`.
5. Ask a question in the chat panel.
6. Verify the response includes inline citation markers (`[1]`, `[2]`) and expandable source excerpts.
7. Try `Reindex` and `Delete` from the library.
8. Toggle `Debug mode` and ask the same question again to inspect rewritten query and retrieved chunks.
9. Log out, register a second user, and confirm documents are private per account.

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
## Future Backlog (Preview)

- Persist metrics (Prometheus / StatsD) instead of in-memory only
- Distributed tracing (OpenTelemetry) for deeper performance debugging

