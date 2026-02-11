# Week 5 Learning Notes: Offline Evaluation Harness

Week 5 adds a minimal, offline evaluation harness so we can detect regressions in RAG behavior.

## 1) Why evaluate RAG?

RAG systems can regress quietly:\n- retrieval changes (pgvector, filters, query rewriting)\n- prompt tweaks\n- model upgrades\n- chunking changes\n\nAn eval suite gives you a repeatable, versioned signal.

## 2) What we evaluate in Week 5

We intentionally keep Week 5 simple and cheap:\n- run a small golden dataset (JSONL)\n- compute heuristic metrics (keywords, citations, abstention)\n- write a JSON report\n\nThis is not \"perfect truth\" evaluation; it is regression detection.

## 3) What these heuristics miss

- Paraphrases/synonyms (keyword checks can be too strict)\n- Hallucinations that still contain expected keywords\n- Citation quality beyond document name matching\n\nFuture weeks can add better judging (LLM-as-judge), richer datasets, and tracking across runs.

## 4) Real vs mock mode

- Real mode: good for manual validation, costs money, depends on current model behavior.\n- Mock mode: deterministic and cheap, good for CI smoke tests.

