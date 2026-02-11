# Week 2 Learning Notes: Document Management

## 1) Why document management matters

In a real RAG product, indexing is not a one-time toy step. Users need:
- visibility into what is indexed
- the ability to delete content
- the ability to reindex after changing chunking or fixing a bad upload

Week 2 adds the product surface area that makes RAG feel like a SaaS.

## 2) Indexing lifecycle states

We represent indexing as a small state machine:
- `queued`: upload accepted, indexing not started yet
- `indexing`: background job is running
- `indexed`: vectors are present and retrieval should work
- `failed`: indexing failed; error message stored for debugging

This is the minimum set of states that lets the UI be honest about what is happening.

## 3) Background tasks tradeoffs

FastAPI `BackgroundTasks` is a good Week 2 tool because it is simple and has no extra infra.

Tradeoffs:
- runs in the same process as the web server (not durable across restarts)
- not suitable for heavy workloads at scale

Later weeks can replace this with a real job queue (Celery/RQ) if needed.

## 4) Idempotency and reindexing

Reindexing should be safe and repeatable:
- delete old vectors for the document
- re-run chunking + embedding
- store the new vectors

This avoids a common failure mode: duplicated chunks in the vector store that bias retrieval.

## 5) Minimal metadata persistence

Week 2 keeps metadata persistence intentionally simple:
- `data/documents.json` is the source of truth for the library

This is not the final architecture (Week 4+ will need a database), but it keeps the slice small while demonstrating the lifecycle patterns.

