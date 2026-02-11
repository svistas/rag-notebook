# RAG Notebook

Production-style RAG (Retrieval-Augmented Generation) web app: upload documents, ask questions, and get grounded answers with citations. Built as weekly vertical slices with a focus on real-world concerns: auth/multi-tenancy, retrieval quality, evaluation, observability, and deployment.

- Demo: `https://<your-railway-app>.up.railway.app` (deploying; link will be updated)
- Contact (consulting): `<your-linkedin-url>`

If you need help shipping an LLM/RAG feature from prototype to production (architecture, retrieval quality, evals, observability, deployment), this repo is a representative example of my approach.

RAG is a strong fit when your users need answers grounded in your domain content: policy docs, product manuals, internal wikis, SOPs, support tickets, contracts, or technical knowledge bases. It’s especially valuable when “search results” aren’t enough and you want a natural-language interface with citations, traceability, and access control. If your problem is purely creative generation or you don’t have reliable source material, a simpler LLM workflow may be a better starting point.

## Consulting Services

I help teams build and ship RAG systems that are:

- Grounded (citations, defensible retrieval behavior)
- Measurable (evals, failure-mode visibility, cost/latency tracking)
- Deployable (repeatable environments, migrations, reliability basics)

Typical engagements:

- RAG architecture + implementation (FastAPI + Postgres/pgvector, chunking/retrieval/rerank/prompting)
- Retrieval quality audits (debug traces, eval suite setup, targeted fixes)
- Production readiness (observability, deployment to Railway, CI-friendly testing)

If you want to discuss a project, message me on LinkedIn: `<your-linkedin-url>`.

## What's This Project About

- End-to-end RAG pipeline: chunking, embeddings, retrieval, reranking, prompting, citations
- Multi-user SaaS basics: auth, session cookies, tenant isolation, access control
- Quality tooling: lightweight offline eval harness to catch regressions
- Observability: request IDs, structured logs, and simple metrics for cost/latency tracking
- Deployment readiness: Dockerfile, Docker Compose, and Railway configuration

## Architecture

```mermaid
flowchart TD
  Browser[Browser_UI] -->|HTTP| FastAPI[FastAPI_App]

  subgraph api [FastAPI]
    Mw[RequestContextMiddleware]
    Auth[get_current_user]
    Routes[API_Routes]
    MetricsUI[Metrics_Page]
  end

  FastAPI --> Mw --> Routes
  Routes --> Auth

  subgraph rag [RAG_Pipeline]
    Chunking[Chunking]
    Embeddings[Embeddings_OpenAI]
    Retrieval[Vector_Retrieval]
    Rewrite[Query_Rewrite]
    Rerank[Rerank]
    Prompt[Prompting_Answer]
  end

  Routes --> Chunking
  Routes --> Embeddings
  Routes --> Retrieval
  Routes --> Rewrite
  Routes --> Rerank
  Routes --> Prompt

  subgraph storage [Storage]
    Postgres[(Postgres_pgvector)]
    Uploads[(Uploaded_Files)]
  end

  Routes --> Postgres
  Routes --> Uploads
  Retrieval --> Postgres
  Embeddings --> Postgres

  subgraph obs [Observability]
    Logs[Structured_JSON_Logs]
    MetricsAPI[/api/metrics]
    InMem[InMemory_Metrics]
  end

  Mw --> Logs
  Mw --> InMem
  Routes --> MetricsAPI --> InMem
  Browser --> MetricsUI --> MetricsAPI
```

## Key Decisions (And Why)

- JWT in an HTTP-only cookie for sessions: simple, UI-friendly, and realistic for a small app.
- Postgres + pgvector for vectors: single system of record, easy tenant filtering, deployment-friendly.
- Query rewrite + rerank: improves grounding and citation quality versus naive top-k similarity.
- Debug mode in UI: makes RAG behavior explainable and tunable.
- In-memory metrics (Week 6): intentionally lightweight; enough to reason about request/OpenAI cost and latency locally.
- Railway + Docker (Week 7): repeatable deployments with a pre-deploy migration command.


## Feature Highlights (By Week)

- Week 1: upload + chunk + embed + chat with citations
- Week 2: document library + background indexing + delete/reindex
- Week 3: query rewrite + rerank + UI debug trace
- Week 4: auth + user isolation + Postgres/pgvector
- Week 5: offline eval harness (mock mode for deterministic CI-style tests)
- Week 6: observability (request IDs, structured logs, `/api/metrics`, `/metrics` page)
- Week 7: deployment (Dockerfile, Compose stack, Railway config-as-code)

## Tech Stack

- Python 3.11, FastAPI, Jinja2
- Postgres + pgvector, SQLAlchemy, Alembic
- OpenAI Python SDK
- structlog (JSON logs)
- pytest + httpx

## Quickstart (Local Dev)

```bash
poetry install --no-root
cp .env.example .env
docker compose up -d db
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Run With Docker Compose

```bash
export OPENAI_API_KEY="..."
export JWT_SECRET="..."
docker compose up --build
```

## Deploy To Railway

This repo includes `railway.toml` (config-as-code) for Dockerfile deployments.

- Add Railway Postgres and set `DATABASE_URL` for the app service (Railway provides it).
- Add a Railway Volume mounted at `/data` and set:
  - `UPLOAD_DIR=/data/uploads`
  - Optional: `CHROMA_DIR=/data/chroma` (kept for legacy/local experiments; primary vectors live in Postgres)
- Set secrets:
  - `OPENAI_API_KEY`
  - `JWT_SECRET`

Deploy behavior:
- Start command: `bash docker/start.sh` (binds to Railway-provided `PORT`)
- Pre-deploy command: `bash docker/migrate.sh` (runs `alembic upgrade head`)

## Observability

- Every response includes `X-Request-ID` (use it to correlate client errors with server logs).
- Metrics:
  - UI: `GET /metrics`
  - API: `GET /api/metrics` (auth required)

## Testing

```bash
poetry run pytest -q
```


