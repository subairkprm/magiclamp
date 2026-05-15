# MagicLamp — Workstream Status

> **Source of truth** for what is actually done vs what is claimed.
> Updated with every merged PR. Overclaiming = false confidence at audit time.

Last updated: 2026-05-15

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Done — merged, tested, verifiable |
| 🔄 | In progress — PR open, not yet merged |
| 🔴 | Not started — or started but not production-safe |
| ⚠️  | Partial — done in one layer but not complete |

---

## Phase 0 — Foundations

| Item | Status | Notes |
|------|--------|-------|
| PRD + ADR 0007 (UAE commercial direction) | ✅ | `docs/explanation/uae-commercial-product-plan.md` |
| Sub-agent operating model (`SUBAGENTS.md`) | ✅ | |
| Jais (UAE-hosted) LLM provider adapter | ✅ | `brain/core/llm/jais.py` |
| Sovereign-mode surfaced on `/health` | ✅ | `db_backend`, `llm_provider`, `region`, `sovereign_mode` |
| UAE locale primitives (AED, 5% VAT, Arabic-Indic) | ✅ | `brain/core/locale.py` |
| Brand design tokens | ✅ | ADR 0004 — Pearl White, Desert Sand, Saadiyat Teal, Burj Gold, Midnight Oud |

---

## Phase 1 — Commercial Skeleton

| Item | Status | Notes |
|------|--------|-------|
| Workspace RBAC matrix | ✅ | `brain/core/rbac.py` — deny-by-default, 5 roles, tested |
| AED billing scaffold (Stripe / Telr / Tabby) | ✅ | `brain/core/billing.py` — 5% VAT, fils precision, tested |
| Customer 360 backend domain | ✅ | `brain/core/customer.py` — CustomerProfile, Attachment, timeline |
| UAE identity helpers | ✅ | `brain/core/uae_id.py` — Luhn EID, mobile normalisation |
| LLM eval harness | ✅ | `brain/eval/` — 5 rules, CLI gate, smoke cases |
| Repository + HTTP wiring for Customer 360 | 🔴 | Domain module done; no REST endpoints yet |
| Bilingual marketing landing (lamp.ae) | 🔴 | |
| Closed alpha with 5 design partners | 🔴 | |

---

## Phase 2 — AI Differentiator

| Item | Status | Notes |
|------|--------|-------|
| Two-tier LLM router domain module (WS-08) | 🔄 | `brain/core/llm_router.py` — PR #35 open, no HTTP wiring yet |
| Arabic-tuned prompts + Gulf-dialect system messages | 🔴 | |
| WhatsApp Business Cloud API integration | 🔴 | |
| Document intelligence (PDF / EID / trade licence) | 🔴 | |
| Daily AI briefing GA | 🔴 | |
| Sovereign-mode toggle in admin console | 🔴 | |

---

## Security & Platform Hardening (WS series)

> ⚠️  **These are deployment safety gates. Do not expose MagicLamp to VPS until
> WS-01 through WS-05 are all ✅.**

| Workstream | Status | Exposure if skipped |
|------------|--------|---------------------|
| **WS-01** — Bind internal ports to 127.0.0.1 | ✅ | `docker-compose.yml` — ollama/brain/agent/n8n bound to loopback |
| **WS-02** — Container / image hardening | 🔴 | Images run as root; no read-only filesystem |
| **WS-03** — CORS strict allowlist | ✅ | Default changed from `*` to `""`; middleware rejects wildcard |
| **WS-04** — Disable `/docs` in production | ✅ | `brain/main.py` + nginx 403 block |
| **WS-05** — N8N admin-gated at nginx | ⚠️ | Port bound to loopback (WS-01 covers port leak); nginx proxy still open — IP-allow-list pending |

### WS-01 — fix applied

All four internal service ports are now bound to `127.0.0.1` in
`docker-compose.yml`. Only nginx (80/443) remains publicly reachable.

### WS-03 — fix applied

`brain/core/config.py`: default changed from `"*"` to `""`.
`brain/main.py`: wildcard is now rejected; operators must set
`CORS_ALLOWED_ORIGINS=https://lamp.ae` explicitly in production `.env`.

### WS-04 — fix applied

`brain/main.py` disables `/docs` and `/redoc` when `ENV=production`.
`nginx/conf.d/magiclamp.conf` returns 403 for `/docs`, `/redoc`,
`/openapi.json` as defence-in-depth.

---

## Infrastructure

| Item | Status | Notes |
|------|--------|-------|
| Docker Compose stack | ✅ | All 7 services defined |
| Nginx reverse proxy + rate limits | ✅ | conf.d with JSON logging, req zones |
| SQLite backend | ✅ | Default; schema in `brain/migrations/schema.sql` |
| Supabase backend (lazy import) | ✅ | `DB_BACKEND=supabase` switches impl |
| RAG pipeline (embedder + vector store) | ✅ | Gated by `RAG_ENABLED` |
| Circuit breaker per LLM provider | ✅ | `brain/core/circuit.py` |
| SSL / Let's Encrypt | ⚠️ | Certbot service exists; HTTPS block commented out until domain live |
| Firewall / UFW rules | 🔴 | No ufw config in repo; relies on port binding (WS-01) |
