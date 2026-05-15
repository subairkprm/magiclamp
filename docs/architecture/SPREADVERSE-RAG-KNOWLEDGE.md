# SpreadVerse RAG Knowledge Layer

> **How MagicLamp understands SpreadVerse — via local retrieval-augmented generation.**

---

## Overview

MagicLamp maintains a local RAG (Retrieval-Augmented Generation) knowledge index that encodes the structure, behaviour, and business rules of the SpreadVerse CRM platform.

This knowledge layer allows MagicLamp agents to answer questions about SpreadVerse accurately without hallucinating — by grounding every answer in retrieved, versioned documents rather than relying on LLM memory alone.

---

## What Is Indexed

The SpreadVerse RAG index contains:

| Knowledge Domain | Examples |
|-----------------|---------|
| **Module Descriptions** | What each SpreadVerse module does (Leads, Customers, Finance, etc.) |
| **Field Definitions** | Field names, types, validation rules, display labels |
| **Business Rules** | Eligibility criteria, escalation triggers, approval conditions |
| **Workflow Definitions** | Standard operating procedures, process flows |
| **API Contracts** | Approved API endpoints and their input/output schemas |
| **Customization Boundaries** | What can and cannot be customized per module |
| **Decision History** | Key architectural and product decisions |
| **Workstream Summaries** | WS-01 through WS-18 summaries and outcomes |

---

## Technical Stack

| Component | Technology | Location |
|-----------|-----------|----------|
| Embeddings | Local embedding model via Ollama | UAE VPS |
| Vector Store | ChromaDB | UAE VPS — local directory |
| Retrieval | `brain/core/vector_store.py` | In-process |
| Indexing | `brain/core/embedder.py` | In-process |
| Fact Store | `brain/repositories/fact.py` (FactRepository) | DB-backed |

### Key Code Paths

```
Ingest document
       │
       ▼
brain/core/embedder.py
  embed_text(text) → vector
       │
       ▼
brain/core/vector_store.py
  upsert(id, vector, metadata)
       │
       ▼
ChromaDB (local)

─────────────────────────────────

Query
       │
       ▼
brain/core/vector_store.py
  search(query_vector, top_k=5)
       │
       ▼
brain/repositories/fact.py
  semantic_search(tenant_id, query)
       │
       ▼
Retrieved context injected into LLM prompt
```

---

## RAG Toggle

RAG is gated by `settings.RAG_ENABLED`. This flag can be used to:

- Disable RAG during initial setup or when ChromaDB is unavailable.
- Run in "facts-only" mode where only the structured fact store is used.

```bash
# In .env
RAG_ENABLED=true
```

---

## Knowledge Curation Workflow

1. **Source documents** are added to the knowledge base by the Knowledge Curator agent or a developer.
2. Documents are chunked, embedded, and stored in ChromaDB.
3. Fact entries are created in the structured fact store for key-value lookups.
4. The RAG index is versioned — each ingestion run creates a snapshot.
5. Stale or incorrect knowledge is flagged and re-indexed.

---

## SpreadVerse Integration Safety Rules

MagicLamp uses RAG knowledge to *understand* SpreadVerse — it does **not** directly query live SpreadVerse CRM tables.

| Action | Allowed? |
|--------|---------|
| Read from RAG index about SpreadVerse schema | ✅ Yes |
| Query live SpreadVerse API (approved read endpoints) | ✅ Yes (future, via approved contract) |
| Write to SpreadVerse CRM tables directly | ❌ Never |
| Generate SQL against SpreadVerse Postgres directly | ❌ Never |
| Approve production changes to SpreadVerse | ❌ Requires human approval |

---

## Keeping Knowledge Current

The RAG index must be re-indexed when:

- SpreadVerse modules are added or changed.
- Field definitions or business rules change.
- New workstreams complete and produce new knowledge.
- API contracts are updated.

Re-indexing is triggered by the Knowledge Curator agent on a schedule or manually.

---

## Vector ID Convention

Vector IDs follow the convention: `fact_vector_id(tenant_id, key)`

This ensures:
- Multi-tenant isolation — no cross-tenant vector contamination.
- Idempotent upserts — re-indexing the same document produces the same ID.

---

## Related Documents

- [`docs/architecture/OFFLINE-AGENT-ARCHITECTURE.md`](OFFLINE-AGENT-ARCHITECTURE.md)
- [`docs/architecture/AGENT-REGISTRY.md`](AGENT-REGISTRY.md)
- [`docs/security/UAE-DATA-RESIDENCY-POLICY.md`](../security/UAE-DATA-RESIDENCY-POLICY.md)
