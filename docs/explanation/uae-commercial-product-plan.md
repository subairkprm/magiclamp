# UAE-Market Commercial Product Plan ("Lamp.ae")

> Status: **Adopted** (see [ADR 0007](../adr/0007-uae-market-commercial-direction.md))
> Audience: supervising lead, sub-agents, design partners
> Type: explanation / product strategy (Diátaxis)

This document captures the full product plan to take MagicLamp from a
developer-grade open-source brain (FastAPI + pluggable LLM + SQLite/Supabase +
Electron desktop) to a **commercial-grade, UAE-market-ready AI CRM Brain** with
high-end UI/UX, a complete feature surface, and a sub-agent–led delivery model
under a single supervising lead.

It is intentionally a strategy artefact — not an implementation. Concrete work
lands as follow-up PRs, each scoped to one sub-agent and gated by the cadence
described in section 6.

---

## 1. Market Research Summary (UAE)

**Demand drivers we are designing against**

- **Banking & Wealth Management** — ENBD, FAB, ADCB, Mashreq, ADIB run active
  "AI for relationship managers" programmes. Pain: manual KYC notes, scattered
  customer history, slow lead triage, Arabic/English context switching.
- **Real Estate (Dubai / Abu Dhabi)** — DAMAC, Emaar, Sobha brokers spend
  40–60 % of their day on lead qualification, follow-up reminders, WhatsApp
  threads. They want one brain that remembers every client preference.
- **SME / free-zone businesses** (DMCC, IFZA, ADGM) — ~750 k SMEs need CRM
  without enterprise pricing. Price-sensitive, want zero-setup SaaS.
- **Government / Semi-Gov** (TDRA, DED, MOHRE) — UAE PDPL (Federal Decree-Law
  45/2021) data-residency mandate. On-prem / UAE-cloud is non-negotiable.

**Regulatory must-haves**

- **UAE PDPL** — data residency, right-to-erasure, consent ledger.
- **CBUAE** consumer protection rules for any banking deployment.
- **VAT 5 %** invoicing built into billing.
- **Arabic-first UX** — RTL polished (not just mirrored), Hijri calendar option.

**Competitive landscape**

- Salesforce Einstein, MS Dynamics Copilot — too expensive, US-data-resident,
  weak Arabic.
- Zoho, HubSpot — cheap, no UAE residency, generic AI.
- Local players (Bayzat, Sarwa, Yadawy) — vertical, not a horizontal AI brain.

**Positioning**

> "The Sovereign Arabic-first AI CRM Brain — runs in UAE, speaks your dialect,
> 1/5 the cost of Salesforce."

**Pricing model** (validated against local benchmarks)

| Tier | Audience | Price |
|---|---|---|
| Starter | SME | AED 99 / user / month |
| Professional | Banking / RE teams | AED 349 / user / month |
| Enterprise (Sovereign on-prem) | Bank / Gov | AED 1,500 / user / month + setup |

Free 14-day trial, no card. Payment rails: Stripe + Telr (local) + Tabby
(BNPL for SMEs).

---

## 2. Product Vision

**"Lamp" — your business's AI brain that never forgets a customer.**

A bilingual (Arabic / English) AI-native CRM that:

1. **Remembers** every customer interaction (calls, WhatsApp, email, meeting
   notes) with confidence-scored facts.
2. **Reasons** over that memory to surface next-best-action, churn risk,
   upsell signals.
3. **Acts** through workflows (n8n) and integrations (WhatsApp Business,
   Microsoft 365, Telegram, Zoho/SAP connectors).
4. **Complies** with UAE PDPL by default, with a one-click sovereign
   deployment option.

---

## 3. Feature Surface

### v1.0 "Launch" (must-have)

- **Onboarding** — 60-second signup, OTP via UAE telco numbers, optional
  Emirates ID verification.
- **Workspace** with role-based access (Owner / Admin / Manager / Agent /
  Viewer).
- **Customer 360** — profile, timeline, fact ledger, semantic recall,
  attachments.
- **AI Reasoning** — streaming chat (the existing
  `/brain/reason/ask/stream`) with inline citations, "explain this" trace,
  Arabic/English toggle per message.
- **Lead Scoring & Pipeline** — visual Kanban + AI auto-score with confidence.
- **WhatsApp Business Cloud API** — most-requested UAE channel.
- **Email** (M365 / Gmail OAuth) two-way sync.
- **Daily AI Briefing** (already in scheduler) — 07:00 GST, push to Telegram +
  email + in-app.
- **Document intelligence** — drop a PDF / Emirates ID / trade licence →
  extracted, linked to customer.
- **Billing** — Stripe + Telr + Tabby; VAT-compliant invoices; AED default.
- **Admin console** — usage, audit log, data residency selector, user
  management, SSO (Azure AD / Google).
- **Mobile-responsive web** + the existing Electron desktop, polished.
- **Arabic-first** — RTL, native Naskh fonts (IBM Plex Sans Arabic), Hijri
  date toggle, Gulf-dialect aware system prompts.

### v1.1 "Moat" (differentiators)

- **Sovereign Mode** — one-click "Run inside UAE": LLM provider pinned to a
  UAE-hosted model (Falcon 3 / Jais on G42 Cloud or local Ollama), DB to UAE
  region, local vector store.
- **Compliance Pack** — pre-built PDPL DSAR workflow, consent ledger,
  retention policies, audit export.
- **Per-tenant fine-tune** — nightly LoRA on the tenant's own reasoning
  traces.
- **WhatsApp AI co-pilot** — agent types in Arabic, AI suggests reply with
  cultural context.
- **Voice** — Arabic speech-to-text (ElevenLabs / Whisper-large-v3) for
  meeting notes auto-logged into the brain.
- **Marketplace** — connectors for Tally, Zoho Books, SAP B1, Property
  Finder, Bayut, Dubizzle.

### v2.0 "Scale"

- Industry verticals: Banking pack, Real-Estate pack, Healthcare pack
  (DHA-aligned).
- White-label for SI partners (Tech Mahindra, Injazat).
- Native iOS / Android apps via React Native + Expo.

---

## 4. UI / UX — High-End Design Direction

**Design language: "Quiet Luxury × Gulf Modern"**

- Inspired by Linear, Arc, Superhuman — with a Gulf identity.
- **Palette**: Pearl White, Desert Sand, Saadiyat Teal `#0E6B66`, Burj Gold
  accent `#C9A96E`, Midnight Oud (dark mode).
- **Typography**: Inter (Latin) + IBM Plex Sans Arabic (no font-mixing
  artefacts).
- **Motion**: Framer-Motion micro-interactions, 200 ms easing, no gratuitous
  animation.
- **Density**: Linear-style command palette (⌘K), keyboard-first, three-pane
  workspace.
- **RTL**: not auto-flipped — hand-tuned mirror with proper number formatting
  (Arabic-Indic optional), correct icon flips, calendar shows both Gregorian
  and Hijri.
- **Accessibility**: WCAG 2.2 AA, full Arabic screen-reader pass.
- **Design tokens**: extend the existing token system from
  [ADR 0004](../adr/0004-design-tokens-and-rtl.md) with semantic tokens
  (`--surface-1`, `--accent-prestige`, …).
- **Component kit**: shadcn/ui + Radix primitives, Tailwind, Storybook with
  both LTR and RTL stories.
- **Marketing site**: separate Next.js site at `lamp.ae` with bilingual
  landing and a "AED you'd save vs Salesforce" calculator.

---

## 5. Architecture Targets

Building on what already exists (FastAPI brain, pluggable LLM, SQLite /
Supabase, RAG, scheduler, Electron desktop):

- **Frontend** — Next.js 15 (App Router) for web, React Native (Expo) for
  mobile (later), keep Electron for desktop.
- **Backend** — keep the FastAPI brain; extract billing, notifications, and
  integrations as separate workers.
- **DB** — Supabase (UAE region — eu-central or new G42 partnership) for
  SaaS; SQLite for sovereign single-tenant
  (see [ADR 0006](../adr/0006-sqlite-default-backend.md)).
- **Vector** — pgvector on Supabase for SaaS; local Chroma for sovereign.
- **LLM routing** — keep the `get_provider()` Protocol from
  [ADR 0005](../adr/0005-pluggable-llm-providers.md); add Jais
  (Inception/G42), Falcon, and a UAE-hosted endpoint adapter. Two-tier:
  cheap Hermes / Qwen for tool routing, frontier model for synthesis.
- **Integrations bus** — keep n8n for automations; expose WhatsApp Business
  Cloud, M365 Graph, Google Workspace.
- **Infra** — Terraform-managed; primary on G42 / Khazna or AWS me-central-1
  (Bahrain) → UAE region when GA; CDN via Cloudflare with UAE PoPs.
- **Observability** — OpenTelemetry → Grafana Cloud; Sentry for FE;
  PostHog (self-hosted) for product analytics (PDPL-friendly).
- **Security** — SOC 2 Type 1 path within 12 months, ISO 27001 within 18,
  UAE IA Level 3 alignment.

---

## 6. Sub-Agent Delivery Model

The supervising lead owns scope, sequencing, quality gates, and weekly demos.
Each sub-agent is a specialist that **researches → advises lead → lead
approves → agent implements → lead reviews**. No sub-agent ships to `main`
without lead sign-off; no two work on the same module concurrently without an
explicit interface contract from the lead.

| # | Sub-agent (role) | Owns | Advises supervisor on | Definition of done |
|---|---|---|---|---|
| 1 | **Market & Product Research** | UAE buyer interviews, competitor teardowns, pricing tests, regulatory delta tracking | Feature priority, pricing, GTM segments | Monthly insights memo + updated PRD |
| 2 | **UX Research & Design** | Personas, journey maps, Figma system, RTL spec, accessibility | Design tokens, component API, motion spec | Figma file + Storybook published, AA audit pass |
| 3 | **Frontend Engineering** | Next.js web, Electron polish, mobile (later) | FE perf budgets, bundle size, FE state lib | Lighthouse ≥ 95, bundle &lt; 200 KB initial, RTL parity |
| 4 | **Backend / API** | FastAPI brain extensions, multi-tenant isolation, rate limits | API contracts, breaking-change policy | OpenAPI diff clean, p95 &lt; 250 ms, 0 multi-tenant leaks |
| 5 | **AI / LLM** | Provider routing, prompts, eval harness, RAG quality, fine-tuning pipeline | Model choice per task, eval scores, cost / token | Eval suite green, hallucination rate tracked, cost per task budgeted |
| 6 | **Data & RAG** | Schema evolution, pgvector ops, embeddings, migrations | Index strategy, retention, PII handling | Migration zero-downtime, recall@5 &gt; 0.85 on eval set |
| 7 | **Integrations** | WhatsApp Cloud API, M365, Google, n8n nodes, Telr / Tabby / Stripe | Which connector next, failure modes | Each connector: webhook tests + retry + UI |
| 8 | **Security & Compliance** | PDPL mapping, DSAR flow, audit log, secrets, pen-test fixes | Threat model per release, vendor DPA review | Risk register updated; CodeQL high = 0 |
| 9 | **DevOps / SRE** | Terraform, CI/CD, environments, SLOs, incident runbooks | Region choice, scaling thresholds | 99.9 % SLO infra, deploy &lt; 10 min, rollback &lt; 2 min |
| 10 | **QA & Eval** | E2E (Playwright), load (k6), Arabic linguistic QA, LLM eval (Ragas, deepeval) | Quality gates, flake budget | &lt; 1 % flake; release blocked if eval regression &gt; 3 % |
| 11 | **Localization** | Arabic MSA + Gulf dialect, Hijri, currency, number formats, native review | Tone of voice, glossary, dialect coverage | Native reviewer sign-off per release |
| 12 | **Growth / GTM** | Marketing site, SEO / ASO (Arabic + English), content, partnerships | Channel ROI, partner shortlist | CAC tracked; one new content asset / week |
| 13 | **Customer Success** | In-app onboarding, help center (bilingual), support macros, NPS | Where users drop off, top tickets | TTV &lt; 10 min; CSAT &gt; 4.5 |

**Operating rhythm**

- **Daily** — 15-min async stand-up (each agent posts: did / doing / blocked
  / asks for supervisor).
- **Weekly** — Friday demo + retro; lead signs off the next week's plan.
- **Bi-weekly** — customer council (3 paying design partners — 1 bank, 1 RE
  brokerage, 1 SME).
- **Monthly** — strategy review with the Market & Product Research agent.
- **Quarterly** — OKRs; lead writes them, agents commit to deliverables.

**Decision rights**

- Sub-agents own *how*; the lead owns *what* and *when*.
- Anything cross-cutting (schema, auth, pricing, brand) → lead's decision.
- Architecture Decision Records (ADRs, already a repo convention) for every
  irreversible call.

---

## 7. 90-Day Roadmap (demo-able every 2 weeks)

**Phase 0 — Foundations (weeks 1–2)**

- Market & UX research sprint; PRD + Figma v0; cloud region decision; eval
  harness scaffolding; multi-tenant isolation audit.

**Phase 1 — Commercial Skeleton (weeks 3–6)**

- Auth + workspaces + RBAC; Stripe / Telr billing; Customer 360 v1; web app
  shell with design system; bilingual landing; closed alpha with 5 design
  partners.

**Phase 2 — AI Differentiator (weeks 7–10)**

- Two-tier LLM routing; Arabic-tuned prompts; WhatsApp integration; document
  intelligence; daily briefing GA; sovereign-mode toggle.

**Phase 3 — Launch-Ready (weeks 11–13)**

- Pen test + PDPL audit; SOC 2 readiness assessment; pricing live; public
  beta; first 50 paying customers target.

---

## 8. Success Metrics ("Outstanding")

- **Activation** — 60 % of signups create their first AI-recalled customer
  fact within 24 h.
- **Retention** — Week-4 retention ≥ 45 %; logo retention ≥ 90 % / year.
- **Quality** — hallucination rate &lt; 2 % on eval set; Arabic CSAT parity
  with English (Δ &lt; 0.3).
- **Performance** — p95 chat first-token &lt; 800 ms, full reasoning &lt; 4 s.
- **Compliance** — 0 PDPL findings in external audit.
- **Commercial** — 100 paying tenants in 6 months; AED 1.5 M ARR in 12
  months; 1 enterprise (bank or gov) sovereign deal in 9 months.

---

## 9. Risks and Mitigations

| Risk | Likelihood | Mitigation owned by lead |
|---|---|---|
| Arabic LLM quality below buyer expectation | High | Eval harness + human-in-loop tuning + Jais / Falcon fallback |
| PDPL interpretation shifts | Medium | Compliance agent retainer with UAE law firm; quarterly review |
| Cloud region (true UAE-resident) immaturity | Medium | Dual-deploy on G42 + me-central-1; sovereign on-prem path |
| LLM cost spiral | Medium | Two-tier routing + per-tenant cost caps + caching |
| Hiring local Arabic UX talent | Medium | Partner with one Dubai design studio for first 6 months |
| Distribution (cutting through Salesforce noise) | High | Vertical land-and-expand: dominate UAE real-estate brokerages first |

---

## 10. Lead's Commitments

- Will not delegate ownership of: **brand**, **pricing**, **schema**,
  **security posture**, **release decisions**.
- Will delegate execution of everything else, with clear contracts and
  reviews.
- Will keep the existing repo conventions (ADRs, pluggable provider, lazy
  Supabase imports, in-memory rate limiter, SQLite-default tests) as
  guard-rails — sub-agents follow them or justify deviating in an ADR.
- Will publish a weekly "what shipped / what didn't / why" note to keep the
  team and design partners aligned.
- Will personally sit in on every customer council until the team hits 100
  paying tenants.

---

**Bottom line:** the existing MagicLamp codebase is a strong technical
foundation (pluggable LLM, RAG, scheduler, multi-backend DB, Electron
client). The work to become a UAE-market commercial product is overwhelmingly
*productisation, localisation, compliance, and design polish* — not a rewrite.
With the 13 specialist sub-agents above operating under the cadence and
decision-rights model defined here, a credible v1.0 launch is achievable in
~13 weeks, with a defensible "Sovereign Arabic-first AI CRM Brain" position
that no global vendor can cleanly match.
