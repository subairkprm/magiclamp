# Lamp.ae 90-Day Roadmap

> Demo-able every two weeks. Source of truth for milestone tracking.
> Detailed rationale lives in
> [`docs/explanation/uae-commercial-product-plan.md`](docs/explanation/uae-commercial-product-plan.md).

## Phase 0 — Foundations (Weeks 1–2)

- [x] PRD + ADR 0007 written and merged (`docs/explanation/uae-commercial-product-plan.md`, `docs/adr/0007-uae-market-commercial-direction.md`).
- [x] Sub-agent operating model documented (`SUBAGENTS.md`).
- [x] Jais (UAE-hosted) LLM provider adapter wired into the pluggable
      registry (`brain/core/llm/jais.py`) — Sovereign Mode unblocked at the
      provider layer.
- [x] Sovereign-mode posture surfaced on `/health` (`db_backend`,
      `llm_provider`, `region`, `sovereign_mode`) — admin "data residency
      selector" can now read it without a new endpoint.
- [x] UAE locale primitives (AED currency, 5 % VAT, Arabic-Indic digits)
      with tests (`brain/core/locale.py`, `tests/test_locale.py`).
- [x] Brand design tokens added on top of ADR 0004 (Pearl White, Desert
      Sand, Saadiyat Teal, Burj Gold, Midnight Oud).
- [ ] Multi-tenant isolation audit (Backend / API + Security agents).
- [ ] Eval harness scaffolding (AI / LLM + QA agents).
- [ ] Cloud region decision recorded as ADR 0008.

## Phase 1 — Commercial Skeleton (Weeks 3–6)

- [ ] Auth + workspaces + RBAC (Owner / Admin / Manager / Agent / Viewer).
- [ ] Stripe + Telr + Tabby billing pipeline; AED-default invoices using
      `core.locale.compute_vat`.
- [ ] Customer 360 v1 (profile, timeline, fact ledger, attachments).
- [ ] Web app shell (Next.js 15) consuming the new design tokens.
- [ ] Bilingual marketing landing at `lamp.ae`.
- [ ] Closed alpha with 5 design partners (1 bank, 1 RE brokerage, 3 SMEs).

## Phase 2 — AI Differentiator (Weeks 7–10)

- [ ] Two-tier LLM routing (cheap router + frontier synthesiser).
- [ ] Arabic-tuned prompts + Gulf-dialect system messages.
- [ ] WhatsApp Business Cloud API integration.
- [ ] Document intelligence (PDF / Emirates ID / trade licence extraction).
- [ ] Daily AI briefing GA (7 a.m. GST → Telegram + email + in-app).
- [ ] Sovereign-mode toggle in the admin console (reads `/health` deployment
      block, writes through to `LLM_PROVIDER`/`DB_BACKEND`).

## Phase 3 — Launch-Ready (Weeks 11–13)

- [ ] External pen test + PDPL audit pass.
- [ ] SOC2 Type 1 readiness assessment.
- [ ] Public pricing page live; Stripe / Telr / Tabby checkout open.
- [ ] Public beta opens; target 50 paying customers.

## Success metrics (tracked weekly)

| Metric                                | Target              |
| ------------------------------------- | ------------------- |
| 24 h activation                       | ≥ 60 %              |
| Week-4 retention                      | ≥ 45 %              |
| Logo retention (annual)               | ≥ 90 %              |
| Hallucination rate (eval set)         | < 2 %               |
| Arabic vs. English CSAT delta         | < 0.3               |
| p95 chat first-token                  | < 800 ms            |
| p95 full reasoning                    | < 4 s               |
| External PDPL findings                | 0                   |
| Paying tenants @ 6 months             | 100                 |
| ARR @ 12 months                       | AED 1.5 M           |
| Sovereign enterprise deal @ 9 months  | 1 (bank or gov)     |
