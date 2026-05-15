# Offline Agent Architecture

> **MagicLamp operates offline-first. All AI inference and agent state remain on UAE VPS.**

---

## Core Principle

MagicLamp is designed to function entirely without external API dependencies in its MVP phase. This means:

- No calls to OpenAI, Anthropic, Google, or any hosted LLM API for production inference.
- No hosted vector databases (Pinecone, Weaviate Cloud, etc.).
- No cloud-based agent memory or session stores.
- All reasoning, retrieval, and memory operations run on-premises on UAE VPS.

This is both a **security requirement** (UAE data residency) and a **reliability requirement** (the system must not degrade when internet connectivity is limited or when cloud APIs are unavailable or repriced).

---

## Offline Infrastructure Stack

| Component | Technology | Location |
|-----------|-----------|----------|
| LLM Inference | Ollama (Hermes 3 / qwen2.5) | UAE VPS — local |
| Vector Store | ChromaDB | UAE VPS — local |
| Knowledge / Memory | SQLite (dev) / Supabase Postgres (prod) | UAE VPS |
| Agent State | In-process + DB-backed | UAE VPS |
| Web Search (optional) | Controlled, rate-limited, result-sanitised | Outbound only — no data sent to LLM cloud |
| Workflow Automation | N8N (self-hosted) | UAE VPS |

---

## System Architecture Diagram

```
┌────────────────────────────────────────────────────────┐
│                   NGINX Reverse Proxy                  │
│                  (SSL Termination)                     │
└────────────────────────────────────────────────────────┘
                            │
           ┌────────────────┼────────────────┐
           │                │                │
     ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐
     │   Brain   │   │  Desktop  │   │    N8N    │
     │  API :9000│   │ Agent:8000│   │    :5678  │
     └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
           │                │                │
           └────────────────┼────────────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
        ┌─────▼─────┐ ┌─────▼────┐ ┌─────▼─────┐
        │  Ollama   │ │ChromaDB  │ │ Supabase  │
        │  :11434   │ │(vectors) │ │(Postgres) │
        └───────────┘ └──────────┘ └───────────┘
```

---

## 5-Phase Platform Evolution

MagicLamp is not a static tool. It is designed to evolve through five phases:

### Phase 1 — Internal Technical AI Command Center *(Current)*

**Who uses it:** Founder, lead developer, internal team  
**What it does:**
- Answers technical questions about the codebase, infrastructure, and deployments
- Stores and retrieves business and technical facts (memory)
- Explains and summarises PRs, workstreams, and decisions
- Monitors agent health and surfaces alerts
- Runs entirely offline on UAE VPS
- All AI actions are advisory — no autonomous production changes

**Key constraint:** Human approves every consequential action.

---

### Phase 2 — Admin Customization Console

**Who uses it:** Business admins, operations leads  
**What it does:**
- Provides a guided interface for proposing software customizations
- Drafts field changes, module configurations, and permission adjustments
- Presents proposals for founder/admin review before any change is applied
- Maintains an audit trail of all proposed and applied customizations
- Integrates with SpreadVerse v2 to communicate approved changes via API contracts

**Key constraint:** No customization is applied without explicit approval.

---

### Phase 3 — No-Code / Low-Code Workflow and Rule Builder

**Who uses it:** Operations teams, business analysts, power users  
**What it does:**
- Visual or AI-guided workflow builder (triggers → conditions → actions)
- Plain-language rule authoring ("escalate lead if no contact in 7 days")
- Approval flow designer
- Notification rule editor
- All created workflows are stored as versioned configuration — not hard-coded logic

**Key constraint:** Workflows are validated and sandbox-tested before activation.

---

### Phase 4 — Customer / Admin-Facing Customization Platform

**Who uses it:** SpreadVerse customer admins  
**What it does:**
- Exposes a safe subset of Phase 2 and Phase 3 capabilities to customer admins
- Customers can customize their own SpreadVerse instance (within permitted bounds)
- AI assistant helps customers understand what they can customize and how
- All customer customizations are scoped to their tenant — cross-tenant isolation enforced

**Key constraint:** Customer customization cannot affect system-level configuration or other tenants.

---

### Phase 5 — Multi-Vertical Software Customization Generator

**Who uses it:** New SpreadVerse verticals, new product lines, enterprise clients  
**What it does:**
- MagicLamp becomes the customization layer for any SpreadVerse-powered product
- New vertical deployments (real estate, legal, healthcare, logistics) are configured through MagicLamp
- AI-assisted configuration generators help new clients set up their instance
- Reusable customization templates and pattern libraries

**Key constraint:** Each vertical operates in an isolated customization namespace.

---

## Agent Isolation Model

All MagicLamp agents operate within strict isolation:

```
Agent
  │
  ├── reads: knowledge base, facts, RAG index  ✅
  ├── reads: approved API responses             ✅
  ├── proposes: drafts, plans, config changes   ✅ (AMBER — needs approval)
  │
  ├── writes: production code                  ❌ BLOCKED
  ├── writes: production database              ❌ BLOCKED
  ├── executes: VPS shell commands             ❌ BLOCKED
  ├── merges: pull requests                    ❌ BLOCKED
  └── applies: customizations without approval ❌ BLOCKED
```

See [`docs/security/AGENT-PERMISSION-MODEL.md`](../security/AGENT-PERMISSION-MODEL.md) for the full permission matrix.

---

## Failure Modes & Resilience

| Failure | Behaviour |
|---------|-----------|
| Ollama unavailable | API returns 503 with structured error; no fallback to cloud LLM |
| ChromaDB unavailable | RAG degrades gracefully; fact recall falls back to keyword search |
| Supabase unavailable | SQLite backend takes over (if configured) |
| N8N unavailable | Scheduled triggers queue or skip; alert sent to Telegram |
| Internet unavailable | System continues operating; web search tools disabled |

---

## Related Documents

- [`docs/architecture/MODEL-ROUTER.md`](MODEL-ROUTER.md)
- [`docs/architecture/HERMES-OLLAMA-USAGE.md`](HERMES-OLLAMA-USAGE.md)
- [`docs/architecture/AGENT-REGISTRY.md`](AGENT-REGISTRY.md)
- [`docs/security/UAE-DATA-RESIDENCY-POLICY.md`](../security/UAE-DATA-RESIDENCY-POLICY.md)
- [`docs/product/MAGICLAMP-COMMAND-CENTER.md`](../product/MAGICLAMP-COMMAND-CENTER.md)
