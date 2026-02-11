# Week 3 Learning Notes: Retrieval Quality Upgrade

Week 3 focuses on a common production issue: naive vector search often retrieves \"kinda related\" chunks, which leads to worse answers even when the document contains the truth.

## 1) Query rewriting (why it helps)

User questions often contain:
- filler words
- ambiguous references (\"it\", \"that section\", \"the thing\")\n- multiple intents

Query rewriting uses an LLM to produce a retrieval-optimized query that keeps:
- key entities\n- constraints\n- exact terms likely to appear in the source

Then embedding + vector search runs on the rewritten query instead of the raw user text.

## 2) Reranking (why it helps)

Vector similarity is a good first pass but not perfect.\nA lightweight reranker takes the initial top-k chunks and chooses the best top-n for answering.

This can improve:\n- relevance\n- grounding quality\n- citation quality

Tradeoffs:\n- extra model call (cost + latency)\n- needs fallback behavior when model output is invalid

## 3) Debug mode (how to trust RAG behavior)

The Week 3 UI has a Debug mode that shows:\n- the rewritten query\n- the initial retrieved chunks and scores\n- the final reranked chunk list

This makes it much easier to:\n- spot retrieval misses\n- tune chunking and top_k/top_n\n- explain system behavior to a reviewer/interviewer\n+
## 4) Common failure modes\n+\n+- The document is indexed but question is out of scope\n+- Chunking split key facts across chunk boundaries\n+- Rewriter removed an important constraint\n+- Reranker picked chunks that are \"topical\" but not \"answerable\"\n+\n+Debug mode is your first tool to diagnose these issues.\n+
