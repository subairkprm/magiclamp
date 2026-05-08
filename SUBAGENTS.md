# Sub-Agent Operating Model — Lamp.ae

> Companion to [`docs/explanation/uae-commercial-product-plan.md`](docs/explanation/uae-commercial-product-plan.md)
> and [ADR 0007](docs/adr/0007-uae-market-commercial-direction.md).
> This file is the **runnable** version of §6 of the plan: it is the contract
> the supervising lead and the 13 specialist sub-agents work to.

## Decision rights

| Owned by the lead (never delegated)             | Delegated to sub-agents |
| ----------------------------------------------- | ----------------------- |
| Brand                                            | All implementation     |
| Pricing                                          | Tooling choices         |
| Schema                                           | Component APIs          |
| Security posture                                 | Test strategies         |
| Release decisions                                | Day-to-day sequencing   |

Anything cross-cutting (schema, auth, pricing, brand) is a lead decision and
is recorded as an ADR in `docs/adr/`. Sub-agents may propose ADRs; only the
lead may merge one.

## Sub-agents

| #  | Agent                       | Owns                                                            | DoD                                                  |
| -- | --------------------------- | --------------------------------------------------------------- | ---------------------------------------------------- |
| 1  | Market & Product Research   | UAE buyer interviews, competitor teardowns, pricing tests       | Monthly insights memo + updated PRD                  |
| 2  | UX Research & Design        | Personas, journey maps, Figma, RTL spec, accessibility          | Storybook published, AA audit pass                   |
| 3  | Frontend Engineering        | Next.js web, Electron polish, mobile (later)                    | Lighthouse ≥ 95, bundle < 200 KB, RTL parity         |
| 4  | Backend / API               | FastAPI brain extensions, multi-tenant isolation, rate limits   | OpenAPI diff clean, p95 < 250 ms, 0 tenant leaks     |
| 5  | AI / LLM                    | Provider routing, prompts, eval harness, RAG quality, fine-tune | Eval suite green, hallucination rate tracked         |
| 6  | Data & RAG                  | Schema evolution, pgvector ops, embeddings, migrations          | Migration zero-downtime, recall@5 > 0.85             |
| 7  | Integrations                | WhatsApp Cloud, M365, Google, n8n, Telr/Tabby/Stripe            | Per connector: webhook tests + retry + UI            |
| 8  | Security & Compliance       | PDPL mapping, DSAR flow, audit log, secrets, pen-test fixes     | Risk register updated; CodeQL high = 0               |
| 9  | DevOps / SRE                | Terraform, CI/CD, environments, SLOs, incident runbooks         | 99.9 % SLO infra, deploy < 10 min, rollback < 2 min  |
| 10 | QA & Eval                   | Playwright E2E, k6 load, Arabic linguistic QA, LLM eval         | < 1 % flake; release blocked if eval regression > 3% |
| 11 | Localization                | Arabic MSA + Gulf dialect, Hijri, currency, number formats      | Native reviewer sign-off per release                 |
| 12 | Growth / GTM                | Marketing site, SEO/ASO, content, partnerships                  | CAC tracked; one new content asset / week            |
| 13 | Customer Success            | In-app onboarding, help center, support macros, NPS             | TTV < 10 min; CSAT > 4.5                             |

## Cadence

- **Daily** — 15-minute async stand-up (each agent posts: did / doing /
  blocked / asks for supervisor).
- **Weekly (Friday)** — demo + retro; lead signs off the next week's plan.
- **Bi-weekly** — customer council with 3 paying design partners
  (1 bank, 1 RE brokerage, 1 SME).
- **Monthly** — strategy review with the Market & Product Research agent.
- **Quarterly** — OKRs; lead writes them, agents commit to deliverables.

## Quality gates (block release)

1. CodeQL high-severity findings = **0**.
2. LLM eval regression vs. previous release ≤ **3 %**.
3. Test flake rate ≤ **1 %** over the last 100 CI runs.
4. p95 chat first-token ≤ **800 ms** in the staging Arabic suite.
5. PDPL DSAR workflow E2E test passes (export + erasure round-trip).

## Repo guard-rails (sub-agents follow or write an ADR to deviate)

- Pluggable LLM provider Protocol (`brain/core/llm/__init__.py`) — never
  hard-code a vendor SDK in business code; go through `get_provider()`.
- `DB_BACKEND=sqlite` is the default for tests and zero-config deploys.
  Supabase imports must stay lazy (`brain/core/database.py`,
  `brain/core/auth.py`, `brain/scheduler.py`).
- Single rate-limiter singleton in `brain/core/limiter.py`.
- Design tokens in `desktop/src/index.css` are the only place colors live.
  New brand tokens must be additive (see the "Quiet Luxury" block).
- ADRs (`docs/adr/`) are required for every irreversible decision.
