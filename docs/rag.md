# MagicLamp RAG Layer

This document describes the Retrieval-Augmented Generation (RAG) pipeline added
on top of `brain_facts` and how to operate it.

## Overview

Before this change, `POST /brain/reason/ask` simply loaded the **20 most recent
facts** for a tenant and stuffed them into the prompt. There was no embedding,
no semantic search, and no relevance ranking — even though `chromadb` and
`sentence-transformers` were already declared as dependencies and the embedding
model was pre-downloaded in `brain/Dockerfile`.

The new pipeline:

```
question
   │
   ▼
Embedder (local sentence-transformers | Ollama /api/embeddings)
   │
   ▼
VectorStore.query(text, tenant_id, k)        ← Chroma (persistent) or in-memory
   │
   ▼
FactRepository.get_by_key(...)               ← canonical row from SQL
   │
   ▼
prompt with cited facts: "[#1] key: value"
   │
   ▼
Ollama (qwen2.5:7b)
```

All vector operations are **tenant-scoped**: ids are derived from
`(tenant_id, key)` (`fact_vector_id` in `brain/core/vector_store.py`) and every
query/delete is filtered by `tenant_id`.

## Configuration

All settings live in `brain/core/config.py` and may be overridden with env vars.

| Setting              | Default              | Purpose                                            |
|----------------------|----------------------|----------------------------------------------------|
| `RAG_ENABLED`        | `false`              | Master feature flag. When false, `/reason/ask` keeps the legacy "recent facts" behavior. |
| `EMBEDDING_PROVIDER` | `local`              | `local` (sentence-transformers) or `ollama`.       |
| `EMBEDDING_MODEL`    | `all-MiniLM-L6-v2`   | Model name. Must match `EMBEDDING_DIM`.            |
| `EMBEDDING_DIM`      | `384`                | Vector dimension (used by `pgvector` migrations).  |
| `VECTOR_STORE`       | `chroma`             | `chroma` (persistent) or `memory` (tests/dev).     |
| `VECTOR_STORE_PATH`  | `${DATA_DIR}/chroma` | Persistent Chroma path.                            |
| `VECTOR_COLLECTION`  | `brain_facts`        | Single collection name; tenants are filtered by metadata. |
| `RAG_TOP_K`          | `5`                  | Number of facts retrieved per question.            |
| `RAG_MIN_SIMILARITY` | `0.0`                | Cosine similarity floor for retrieved facts.       |

## Code layout

| Module                              | Responsibility                                                     |
|-------------------------------------|--------------------------------------------------------------------|
| `brain/core/embedder.py`            | `Embedder` ABC + `LocalEmbedder` + `OllamaEmbedder` + singleton.   |
| `brain/core/vector_store.py`        | `VectorStore` ABC + `ChromaVectorStore` + `InMemoryVectorStore`.   |
| `brain/repositories/fact.py`        | Dual-write on `save_fact`, propagating `delete`, `semantic_search`, `reindex_all`. |
| `brain/api/v1/brain.py`             | `_process_reason_ask` selects RAG vs. recent-facts based on `RAG_ENABLED`. |
| `scripts/backfill_embeddings.py`    | Idempotent backfill of embeddings for existing facts.              |
| `tests/test_rag.py`                 | Unit + behavioural tests using `FakeEmbedder` and `InMemoryVectorStore`. |

## Operational guarantees

- **Dual-write is best-effort.** A vector-store failure logs a warning and is
  swallowed; the relational write still succeeds. This avoids a vector outage
  taking down the API surface.
- **`semantic_search` falls back to `[]`** if the vector store is unavailable
  or RAG is disabled, and `_process_reason_ask` then falls back to the legacy
  recent-facts path. There is never a hard outage caused by RAG.
- **Stale vectors are filtered out.** `semantic_search` re-fetches each match
  from SQL by key, so any vector entry without a corresponding row is dropped
  from the result set.
- **Tenant isolation.** All vector operations require a `tenant_id`; the
  Chroma backend uses `where={"tenant_id": ...}` on every read/write/delete.

## Rollout

1. Deploy with `RAG_ENABLED=false` (default). No behavioural change.
2. Run the backfill once per environment:
   ```
   python scripts/backfill_embeddings.py
   ```
   The script is idempotent — re-run safely after a crash. Pass `--tenant <id>`
   to limit it to a single tenant.
3. Set `RAG_ENABLED=true` and restart the brain service.
4. Verify in the logs:
   ```
   reason_ask task=... tenant=... retrieval=rag hits=N k=...
   ```
   New `save_fact` calls now keep the vector store hot; the backfill is only
   needed once.

## Switching backends

Both the embedder and the vector store are pluggable singletons:

```python
from core.vector_store import set_vector_store
from my_pkg import QdrantVectorStore

set_vector_store(QdrantVectorStore(...))
```

For tests, `set_vector_store(InMemoryVectorStore(embedder=FakeEmbedder()))`
gives a deterministic, dependency-free environment — see `tests/test_rag.py`.

## Future work (not in this change)

- `PgVectorStore` for single-store deployments (eliminates dual-write drift).
- Hybrid retrieval (BM25 + vector with reciprocal-rank fusion).
- Cross-encoder reranker over top-20 → top-5.
- Chunking long `/memory/observe` events before embedding.
