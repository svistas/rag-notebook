# RAG Notebook (Week 1)

RAG Notebook is a production-style Retrieval-Augmented Generation portfolio project built in weekly vertical slices.

Week 1 delivers an end-to-end MVP:
- Upload `.txt` or `.md` documents
- Chunk and embed them with OpenAI embeddings
- Store vectors locally in ChromaDB
- Ask questions and receive citation-based answers

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
4. Ask a question in the chat panel.
5. Verify the response includes inline citation markers (`[1]`, `[2]`) and expandable source excerpts.

## Week 1 Security Baselines

- File type validation (`.txt`, `.md`)
- Upload size limit via config (`MAX_UPLOAD_SIZE_MB`)
- Filename sanitization before saving
- Secrets excluded via `.env` and `.gitignore`

## Week 2 Backlog

- Add document delete endpoint and UI action
- Reindex flow for updated documents
- Indexing status field and progress states
- Move ingest to FastAPI background tasks
- Add optional PDF parsing (basic support)
- Persist richer metadata schema (e.g., content hash, timestamps, source type)

