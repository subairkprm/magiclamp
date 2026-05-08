# ADR 0007 — UAE-market commercial direction ("Lamp.ae")

- **Status:** Accepted
- **Date:** 2026-05
- **Deciders:** Supervising Lead
- **Tags:** product, strategy, market, compliance, ui-ux

## Context

MagicLamp today is a developer-grade open-source AI brain: FastAPI service,
pluggable LLM providers ([ADR 0005](0005-pluggable-llm-providers.md)),
SQLite-default storage with Supabase as the alternate backend
([ADR 0006](0006-sqlite-default-backend.md)), a CSS-token + RTL-aware design
system ([ADR 0004](0004-design-tokens-and-rtl.md)), an SSE streaming
reasoning endpoint ([ADR 0003](0003-sse-streaming-ask.md)), an Electron
desktop client ([ADR 0002](0002-desktop-consolidation.md)), and a per-feature
brain router layout ([ADR 0001](0001-brain-router-split.md)).

The product opportunity in front of us — UAE Banking, Real Estate, SME, and
semi-Government — requires more than a dev tool. It demands a commercial,
PDPL-compliant, Arabic-first, sovereign-deployable AI CRM with billing,
integrations (WhatsApp Cloud, M365, Stripe / Telr / Tabby), high-end UI/UX,
and a credible enterprise security posture.

This ADR records the strategic decision to take that direction and to do so
under a **sub-agent–led delivery model with a single supervising lead**,
without abandoning the architectural guard-rails the previous ADRs put in
place.

## Decision

We adopt the **"Lamp.ae" UAE-market commercial product plan** documented in
[`docs/explanation/uae-commercial-product-plan.md`](../explanation/uae-commercial-product-plan.md).

Key irreversible commitments locked in by this ADR:

1. **Positioning.** "The Sovereign Arabic-first AI CRM Brain — runs in UAE,
   speaks your dialect, 1/5 the cost of Salesforce." All scope, naming, and
   marketing decisions must be consistent with this positioning.
2. **Bilingual / Arabic-first.** Every user-facing surface must ship with
   hand-tuned RTL, IBM Plex Sans Arabic typography, and a Hijri-date toggle.
   Auto-mirrored RTL is not acceptable.
3. **PDPL compliance is a launch blocker, not a v2 wish.** Data residency
   selector, right-to-erasure (DSAR), consent ledger, audit log, and
   retention policies must exist by GA.
4. **Sovereign Mode is a first-class deployment.** The two-backend split
   established in ADR 0006 (SQLite + Supabase) and the provider Protocol
   established in ADR 0005 are kept and extended — Sovereign Mode pins
   `DB_BACKEND` to a UAE-region store and `LLM_PROVIDER` to a UAE-hosted
   model (Jais, Falcon 3, or local Ollama). No new abstractions are
   introduced where these already suffice.
5. **Sub-agent delivery model.** Thirteen specialist sub-agents (Market,
   UX, Frontend, Backend, AI/LLM, Data/RAG, Integrations, Security,
   DevOps, QA/Eval, Localization, Growth, Customer Success) execute under
   the supervising lead. Sub-agents own *how*; the lead owns *what*, *when*,
   and the cross-cutting concerns (schema, auth, pricing, brand, security
   posture, release decisions). Every irreversible technical call gets its
   own ADR.
6. **Phased 90-day roadmap.** Foundations → Commercial Skeleton → AI
   Differentiator → Launch-Ready, with demo-able milestones every two weeks
   and a closed alpha of 5 design partners by the end of Phase 1.
7. **Pricing in AED.** Starter AED 99, Professional AED 349, Enterprise
   AED 1,500 / user / month + setup. Stripe + Telr + Tabby; VAT-compliant
   invoicing.

## Consequences

**Positive**

- Gives every contributor and sub-agent a single shared source of truth for
  market, scope, sequencing, and quality bars — replacing ad-hoc decisions
  with a reviewable artefact.
- Anchors future technical ADRs (e.g. WhatsApp connector, billing service,
  Sovereign Mode toggle, two-tier LLM router) to a concrete commercial
  rationale, so reviewers can judge changes against a stable strategy.
- Preserves the existing architecture's strengths: the pluggable provider
  Protocol, the SQLite-default backend, the lazy Supabase imports, the
  in-memory rate limiter, the design-token + RTL system, and the per-feature
  router split all become load-bearing for the commercial product instead of
  being thrown away.

**Negative**

- Locks the project into a regional (UAE-first) GTM. Pivoting to a different
  primary market later would require a follow-up ADR superseding this one.
- Raises the bar for every user-facing change: contributors must consider
  bilingual / RTL / Hijri / PDPL implications even on small features.
- Requires sustained sub-agent coordination overhead (daily stand-up, weekly
  demo, bi-weekly customer council). The lead is responsible for keeping
  this lightweight.

**Neutral**

- Does not by itself ship any code. It authorises subsequent PRs — each
  scoped to one sub-agent — and gives reviewers a yard-stick to accept or
  reject them against the plan.

## Alternatives considered

- **Stay horizontal / global open-source tool.** Rejected. The competitive
  field for generic AI CRMs is crowded (Salesforce, HubSpot, Zoho, Attio,
  Twenty). The UAE-resident, Arabic-first, PDPL-compliant niche is large,
  underserved, and aligns with concrete enterprise budgets.
- **Build a thin SaaS wrapper without sovereign deployment.** Rejected.
  Banking and government buyers explicitly require on-prem / UAE-region;
  ignoring them caps the realistic ARR ceiling and forfeits the most
  differentiated tier of the pricing model.
- **Single-team delivery (no sub-agent split).** Rejected. The required
  surface area (web + desktop + mobile + billing + integrations + LLM eval
  + compliance + Arabic localisation + GTM) cannot be sequenced sanely
  without explicit ownership boundaries and a supervising lead with final
  cut on cross-cutting concerns.
- **Rewrite in another stack.** Rejected. The existing FastAPI + pluggable
  LLM + SQLite/Supabase + Electron foundation already addresses most of the
  hard technical risks. Productisation, localisation, compliance, and design
  polish — not a rewrite — are the work.

## References

- Plan: [`docs/explanation/uae-commercial-product-plan.md`](../explanation/uae-commercial-product-plan.md)
- Related ADRs: [0001](0001-brain-router-split.md),
  [0002](0002-desktop-consolidation.md), [0003](0003-sse-streaming-ask.md),
  [0004](0004-design-tokens-and-rtl.md),
  [0005](0005-pluggable-llm-providers.md),
  [0006](0006-sqlite-default-backend.md).
