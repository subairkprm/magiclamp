# UAE Data Residency Policy

> **All production data remains on UAE VPS. No exceptions in MVP.**

---

## Policy Statement

MagicLamp is a private, UAE-hosted AI platform. The UAE data residency policy governs where data is stored, processed, and transmitted. This policy applies to all MagicLamp agents, services, and integrations.

**Policy Version:** 1.0  
**Effective Date:** 2026-05-15  
**Scope:** All MagicLamp production environments  
**Authority:** Founder / System Owner

---

## Core Rules

### 1. No Cloud LLM APIs in MVP

| Provider | Status |
|----------|--------|
| OpenAI (GPT-4, GPT-3.5, etc.) | ❌ Blocked in production |
| Anthropic (Claude) | ❌ Blocked in production |
| Google (Gemini) | ❌ Blocked in production |
| Groq (cloud) | ❌ Blocked in production |
| OpenRouter | ❌ Blocked in production |
| Ollama (local, UAE VPS) | ✅ Required — only permitted inference endpoint |

No production request payload, customer data, business data, or internal system data may be sent to a cloud LLM API.

### 2. No Hosted Vector Database

| Vector DB | Status |
|-----------|--------|
| Pinecone (hosted) | ❌ Not permitted |
| Weaviate Cloud | ❌ Not permitted |
| Qdrant Cloud | ❌ Not permitted |
| ChromaDB (local, UAE VPS) | ✅ Required |

All vector embeddings and semantic indexes must be stored locally on UAE VPS.

### 3. No Hosted Agent Memory

| Memory Service | Status |
|----------------|--------|
| Any third-party agent memory API | ❌ Not permitted |
| Mem0, Zep, LangSmith (hosted) | ❌ Not permitted |
| SQLite / Supabase on UAE VPS | ✅ Required |
| In-process + DB-backed local store | ✅ Required |

Agent memory, session state, and conversation history must remain on UAE infrastructure.

### 4. No Production Data in External Services

| Data Type | External Services | Status |
|-----------|-----------------|--------|
| Customer PII (name, EID, mobile, email) | Any external API | ❌ Strictly prohibited |
| SpreadVerse CRM records | Any external API | ❌ Strictly prohibited |
| Business rules and workflows | Any external API | ❌ Strictly prohibited |
| Financial data (AED billing, invoices) | Any external API | ❌ Strictly prohibited |
| Internal agent state and decisions | Any external API | ❌ Strictly prohibited |

### 5. Ollama / Hermes is Local-Only

- Ollama serves inference exclusively on `http://ollama:11434` (internal Docker network).
- The Ollama port is **not exposed** to the public internet.
- No Ollama API key is sent to an external service.
- Models are pulled from ollama.com during setup but run entirely locally after installation.

### 6. Production Data Remains on UAE VPS

- All Postgres data (Supabase) resides on the UAE VPS.
- All SQLite data (dev/fallback) resides on the UAE VPS.
- All backups are stored on UAE VPS (and optionally encrypted to UAE-controlled storage).
- No automated sync to foreign cloud storage providers.

### 7. MagicLamp Does Not Directly Write SpreadVerse CRM Tables

- MagicLamp agents must not issue direct SQL or ORM writes to SpreadVerse CRM tables.
- All CRM data changes are routed through SpreadVerse v2 approved APIs.
- MagicLamp may read approved summary/reporting views only.
- Direct database access credentials for SpreadVerse Postgres are not held by MagicLamp agents.

---

## Permitted External Connections (MVP)

| Connection | Purpose | Data Sent | Approved |
|-----------|---------|-----------|---------|
| ollama.com (setup only) | Pull model weights | None (model metadata only) | ✅ Yes |
| GitHub.com | Code repository access (advisor only) | None (no customer data) | ✅ Yes (read-only, internal use) |
| Telegram API | Admin notifications | Alert text (no PII) | ✅ Yes (non-PII alerts only) |
| N8N webhooks (local) | Internal automation | Internal signals only | ✅ Yes (internal only) |

---

## Web Search

Web search is permitted under the following conditions only:

- The search query contains **no customer data, no PII, no business-sensitive data**.
- The search result is returned to MagicLamp for local processing — it is **not forwarded to a cloud LLM**.
- Web search is rate-limited and logged.
- Web search results are treated as untrusted input and sanitised before use.

See [`docs/security/WEB-SEARCH-SAFETY.md`](WEB-SEARCH-SAFETY.md) for full controls.

---

## Future Policy Evolution

In future phases, a **data classification framework** may permit specific, non-sensitive query types to use cloud LLMs (e.g. public knowledge lookups). Any such change requires:

1. Explicit written approval from the founder.
2. A data classification review showing the specific data types involved.
3. An update to this policy document.
4. A re-audit of all agent flows that would use the new capability.

---

## Compliance Notes

- This policy is aligned with UAE PDPL (Personal Data Protection Law) requirements for data localisation.
- UAE Central Bank CBUAE guidelines for AI-assisted banking operations require data processing within UAE jurisdiction.
- No transfer of banking customer data outside UAE is permitted without explicit regulatory approval.

---

## Related Documents

- [`docs/security/AGENT-PERMISSION-MODEL.md`](AGENT-PERMISSION-MODEL.md)
- [`docs/security/WEB-SEARCH-SAFETY.md`](WEB-SEARCH-SAFETY.md)
- [`docs/security/SECURITY-BASELINE.md`](SECURITY-BASELINE.md)
- [`docs/architecture/HERMES-OLLAMA-USAGE.md`](../architecture/HERMES-OLLAMA-USAGE.md)
