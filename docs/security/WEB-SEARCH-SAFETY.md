# Web Search Safety

> **Controlled, rate-limited, sanitised web search — no customer data leaves the VPS.**

---

## Purpose

Some MagicLamp agents may require current public information (e.g. regulatory updates, market data, public API documentation). Web search is permitted under strict conditions to support these use cases.

This document defines the safety controls that govern all web search activity.

---

## Governing Principle

> Web search results are untrusted, external input. They must not carry customer data outbound, and they must not be forwarded raw to an LLM without sanitisation.

---

## What Is Permitted

| Use Case | Allowed |
|----------|---------|
| Search for public regulatory information (UAE PDPL, CBUAE guidelines) | ✅ Yes |
| Search for public technical documentation (library docs, API specs) | ✅ Yes |
| Search for public market or industry news | ✅ Yes |
| Search for answers to internal technical questions using public keywords only | ✅ Yes |

---

## What Is Prohibited

| Use Case | Allowed |
|----------|---------|
| Search query contains customer name, EID, mobile, or email | ❌ Never |
| Search query contains SpreadVerse CRM record data | ❌ Never |
| Search query contains internal business rules or financial data | ❌ Never |
| Search result forwarded directly to a cloud LLM API | ❌ Never |
| Search used to bypass local knowledge base (RAG) | ❌ Not permitted — RAG is always queried first |

---

## Safety Controls

### 1. Query Sanitisation

Before any web search is executed, the query string is checked against a blocklist of patterns:
- Patterns matching UAE national ID format (784-YYYY-NNNNNNN-C)
- Patterns matching UAE mobile numbers (+9715XXXXXXXX)
- Patterns matching email addresses (contains `@`)
- Numeric sequences longer than 10 digits
- Any field name that is marked as PII in the data classification register

If a blocked pattern is found, the search is rejected with an audit log entry.

### 2. Rate Limiting

Web search is rate-limited per agent and per time window:

| Limit | Value |
|-------|-------|
| Per agent, per minute | 5 searches |
| Per agent, per hour | 30 searches |
| Global, per minute | 20 searches |

Exceeding the rate limit returns a temporary block with exponential backoff.

### 3. Result Sanitisation

Search results are sanitised before being passed to any LLM or stored:
- HTML tags are stripped.
- JavaScript and executable content is removed.
- External links are not followed automatically.
- Results exceeding a maximum character limit are truncated.
- No redirect chains are followed.

### 4. Local Processing Only

Search results are processed **locally** on UAE VPS. They are:
- Injected into the local Ollama prompt context — not sent to a cloud LLM.
- Stored temporarily in the agent's working memory — not persisted long-term unless explicitly curated.
- Not logged in full (to avoid storing untrusted content in production logs).

### 5. Audit Trail

Every web search is logged:

```json
{
  "event": "web_search",
  "agent_id": "knowledge-curator",
  "query_hash": "sha256_of_query",
  "result_count": 5,
  "timestamp": "2026-05-15T08:00:00Z",
  "sanitisation_passed": true
}
```

The full query text is **not** stored in logs — only a hash — to avoid log-based data leakage.

---

## RAG-First Policy

Web search is a fallback, not a primary source:

1. Agent receives a question.
2. RAG index is searched first (`brain/core/vector_store.py`).
3. Fact store is checked (`brain/repositories/fact.py`).
4. Only if both return insufficient results, and the query is classified as safe, is web search attempted.

---

## Disabling Web Search

Web search can be disabled entirely via environment variable:

```bash
# In .env
WEB_SEARCH_ENABLED=false
```

In MVP, web search is disabled by default. It must be explicitly enabled by the founder.

---

## Related Documents

- [`docs/security/UAE-DATA-RESIDENCY-POLICY.md`](UAE-DATA-RESIDENCY-POLICY.md)
- [`docs/security/AGENT-PERMISSION-MODEL.md`](AGENT-PERMISSION-MODEL.md)
- [`docs/security/SECURITY-BASELINE.md`](SECURITY-BASELINE.md)
