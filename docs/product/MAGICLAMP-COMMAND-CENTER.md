# MagicLamp Command Center

> **Private UAE-Hosted AI Development & Business Command Center**

---

## Overview

MagicLamp is a private, UAE-hosted AI command center that gives a founder and their team full control over software development, business operations, agent behaviour, and knowledge management — all without requiring direct access to code, servers, GitHub, or production databases.

It starts as an internal tool. It is designed to grow into a **controlled software customization platform**.

---

## Current Role (MVP — Phase 1)

In its initial phase, MagicLamp operates as:

| Function | Description |
|----------|-------------|
| **AI Development Assistant** | Answers technical questions, explains code, reviews PRs, summarises workstreams |
| **Business Knowledge Brain** | Stores and retrieves facts, decisions, customer context, and business rules |
| **Repo & Deployment Advisor** | Guides deployments, explains Docker/Nginx/VPS configuration, surfaces deployment risks |
| **Agent Operations Console** | Registers agents, monitors their activity, controls their permissions |
| **SpreadVerse Integration Layer** | Understands SpreadVerse CRM structure and answers questions about data, processes, and workflows |

All operations in Phase 1 are **advisory and read-only** at the production level. MagicLamp does not directly push code, modify the database, or change live configurations.

---

## Long-Term Role: Controlled Software Customization Platform

### Vision

MagicLamp will evolve into the **primary interface through which users and admins safely customize their software** — without ever needing to directly touch production code, GitHub repositories, a VPS terminal, or a CRM database.

This is a fundamental expansion of purpose. MagicLamp is not merely a developer convenience tool. It is the **future software-shaping layer** that sits between human intent and production change.

### What MagicLamp Will Enable

Authorized users and admins will be able to:

| Domain | Capability |
|--------|-----------|
| **Modules** | Enable, disable, or configure software modules through a UI or guided AI flow |
| **Fields** | Add, rename, hide, or reorder fields in forms and views — without touching database migrations |
| **Workflows** | Build, edit, and activate business workflows using a visual or AI-guided no-code interface |
| **Rules** | Define business rules, validation logic, and escalation conditions in plain language |
| **Permissions** | Adjust role-based access controls and approval hierarchies |
| **Automations** | Configure trigger-based automations (e.g. send notification when lead status changes) |
| **Dashboards** | Compose dashboards and reports by selecting metrics and layout components |
| **Notifications** | Configure notification channels, recipients, and conditions |
| **Approval Flows** | Define multi-step approval chains for sensitive operations |

### Safety Constraints (Non-Negotiable)

MagicLamp as a customization platform operates under strict safety rules:

1. **No direct production code edits.** MagicLamp prepares drafts, plans, and configuration proposals — it does not commit or push to any repository on its own.
2. **No direct VPS or infrastructure changes.** MagicLamp cannot SSH into a server or execute shell commands in production.
3. **No direct CRM/database writes.** MagicLamp does not write to SpreadVerse CRM tables. All database changes are applied by the SpreadVerse v2 backend through approved APIs or configuration contracts.
4. **No self-approvals.** An AI agent cannot approve its own proposed change. All customization proposals require an authorized human to review and approve.
5. **All customization changes start as drafts.** A proposed change exists in DRAFT or AMBER state until it passes review.
6. **Approved changes are applied by SpreadVerse v2.** The SpreadVerse v2 platform is the enforcement layer. MagicLamp supplies the intent and the plan; SpreadVerse v2 executes it.

### How Customization Works (Future Flow)

```
User/Admin Intent
       │
       ▼
MagicLamp Agent
  (understands intent, checks permissions, prepares safe draft)
       │
       ▼
Draft Customization Plan
  (stored, versioned, visible in MagicLamp console)
       │
       ▼
Founder / Admin Review & Approval
       │
       ▼
SpreadVerse v2
  (applies change via approved API / configuration contract)
       │
       ▼
Production System Updated
  (audit log written, notification sent)
```

### Why This Matters

- **Reduces dependency on developers** for routine customization.
- **Eliminates risk** of accidental production changes from unreviewed modifications.
- **Empowers admins** to shape their software in a controlled, auditable way.
- **Creates a compliance trail** for every software change.
- **Scales across verticals** — the same MagicLamp customization layer can serve multiple SpreadVerse-powered products.

---

## Technical Boundaries

| Layer | Owned By | MagicLamp Role |
|-------|----------|----------------|
| Production Code | GitHub / developers | Advisory only — no direct writes |
| VPS / Infrastructure | UAE VPS | Advisory only — no direct shell access |
| CRM Database | SpreadVerse v2 Postgres | Read-only context; no direct writes |
| Customization Config | MagicLamp | Author and store proposals; hand off to SpreadVerse v2 |
| Agent Behaviour | MagicLamp | Full control within permission boundaries |
| Knowledge Base | MagicLamp | Full control (facts, memory, RAG) |

---

## UAE Hosting Commitment

MagicLamp is and will remain **UAE-hosted**:

- All AI inference runs locally on UAE VPS via Ollama (Hermes 3).
- No production data leaves the UAE.
- No cloud LLM APIs (OpenAI, Anthropic, Gemini) are used for production requests in MVP.
- Vector memory and agent state remain on-premises.

See [`docs/security/UAE-DATA-RESIDENCY-POLICY.md`](../security/UAE-DATA-RESIDENCY-POLICY.md) for full policy.

---

## Related Documents

- [`docs/STATUS.md`](../STATUS.md) — Active workstream tracker
- [`docs/architecture/OFFLINE-AGENT-ARCHITECTURE.md`](../architecture/OFFLINE-AGENT-ARCHITECTURE.md) — 5-phase platform evolution
- [`docs/security/AGENT-PERMISSION-MODEL.md`](../security/AGENT-PERMISSION-MODEL.md) — Action permission levels
- [`docs/security/UAE-DATA-RESIDENCY-POLICY.md`](../security/UAE-DATA-RESIDENCY-POLICY.md) — Data sovereignty policy
