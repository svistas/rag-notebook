# Week 4 Learning Notes: Auth + Multi-User + pgvector

Week 4 moves the app toward \"real SaaS\" behavior: users log in, and their documents are private.

## 1) Why multi-tenancy changes everything

Once multiple users exist, every query becomes user-scoped:\n- list documents\n- delete/reindex\n- retrieval\n- chat\n\nA single missing filter (e.g. `WHERE user_id = ...`) becomes a data leak.

## 2) Session model: JWT cookie

We use a signed JWT stored in an HTTP-only cookie:\n- server sets cookie on login/register\n- requests include the cookie automatically\n- `get_current_user()` validates signature + loads user\n\nThis is simple, demo-friendly, and works well for template-based UIs.

## 3) Postgres + pgvector basics

We store chunk embeddings in Postgres using the `vector` extension.\nFor retrieval, we compute a query embedding and order chunks by cosine distance.\n\nKey benefits:\n- single database for metadata + vectors\n- SQL-level filtering by user/tenant\n- easier path to production deployment

## 4) Testing strategy

Production uses Postgres + pgvector.\nTests use SQLite with a JSON embedding fallback and Python cosine similarity.\n\nThis keeps tests fast and deterministic while still validating:\n- auth flow\n- access control\n- user-scoped retrieval behavior\n+
