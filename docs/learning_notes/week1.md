# Week 1 Learning Notes: Hello RAG

## 1) RAG Pipeline Basics

RAG combines retrieval and generation:
1. Ingest and chunk documents
2. Embed chunks into vectors
3. Retrieve top-k relevant chunks for a query
4. Prompt the LLM with retrieved context
5. Return an answer grounded in that context with citations

This architecture improves factual grounding compared to raw LLM prompting.

## 2) Embeddings

Embeddings map text into high-dimensional vectors where similar meanings are near each other.

In Week 1:
- Document chunks are embedded once during ingestion
- User query is embedded at question time
- Similarity search compares query vector against chunk vectors

## 3) Cosine Similarity

Cosine similarity measures the angle between vectors:
- Closer to `1.0` means more semantically similar
- Closer to `0.0` means less related

ChromaDB handles the distance computations and ranking in our MVP.

## 4) Chunking Strategy

Week 1 uses fixed-size chunking with overlap:
- `chunk_size`: max chars per chunk
- `overlap`: shared chars between adjacent chunks

Why overlap helps:
- Preserves context crossing chunk boundaries
- Reduces answer failures caused by split concepts

Trade-off:
- More chunks means better recall but higher embedding/storage cost

## 5) Prompting for Grounded Answers

The system prompt enforces:
- Use only provided context
- Cite sources inline (`[1]`, `[2]`)
- Admit uncertainty when context is weak

This is a foundational production pattern: constrain generation, expose evidence.

## 6) Why This Vertical Slice Matters

Week 1 delivers an end-to-end user-visible feature:
- Upload
- Chat
- Citations

It proves the full RAG loop works locally and creates a base for quality, multi-user support, and observability in later weeks.

