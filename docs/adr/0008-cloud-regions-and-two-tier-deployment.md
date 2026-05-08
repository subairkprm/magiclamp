# ADR 0008 — Cloud regions and the two-tier deployment model

- **Status:** Accepted
- **Date:** 2026-05
- **Tags:** infra, deployment, residency, pdpl, sovereign

## Context

ADR 0007 commits Lamp.ae to a UAE-first product with a "Sovereign Mode" for
buyers (banks, government, regulated enterprises) that need a strong data
residency story. Two questions then need a single, repo-level answer that
sub-agents and Terraform code can both read:

1. **Where do the *Standard tier* tenants run?** Most SMEs and brokerages
   pay AED-monthly and want a fast, low-overhead managed deployment. They
   are happy with a major cloud region as long as it is geographically in
   the Middle East.
2. **Where do the *Sovereign tier* tenants run?** Banks, government, and any
   buyer with a written PDPL or sectoral residency requirement must be able
   to point at a UAE-licensed cloud (G42 / Khazna) or an on-prem appliance.

We also need a baked-in answer for "where does the marketing site / SaaS
control plane live?" so DNS, certs, and the CI/CD pipeline have one home.

## Decision

We adopt a **two-tier deployment model** with a single source of truth in
configuration (the `DEPLOYMENT_REGION` and `SOVEREIGN_MODE` env vars added
in this branch and exposed via `/health.deployment`):

### Standard tier — `aws-me-central-1` (Bahrain) *or* `aws-me-central-2` (UAE)

- **Primary**: AWS `me-central-1` (Bahrain) — mature, lowest p95 latency
  to Dubai (< 15 ms), best supporting-services catalogue today.
- **Preferred when GA**: AWS `me-central-2` (UAE, Abu Dhabi) for tenants
  that want their data physically inside UAE without paying the Sovereign
  premium. Migration is a config flip; no code change.
- Identifier in `DEPLOYMENT_REGION`: `me-central-1` or `me-central-2`.
- `SOVEREIGN_MODE=false`.

### Sovereign tier — UAE-licensed cloud or appliance

- **Default cloud**: G42 Cloud / Core42 (formerly Khazna) — UAE-licensed,
  TDRA-aligned, and the natural home for the Jais LLM provider added in
  this branch.
- **On-prem option**: a single-binary Docker Compose appliance using the
  SQLite default backend (ADR 0006) and Ollama or Jais self-hosted for
  inference. No outbound traffic to non-UAE endpoints.
- Identifier in `DEPLOYMENT_REGION`: `uae-g42` or `on-prem`.
- `SOVEREIGN_MODE=true`. The admin UI must refuse to enable any non-UAE
  LLM provider while this flag is true (enforcement lands with the admin
  console UI in Phase 2).

### Control plane (marketing site, billing, status page, CI artefacts)

- Hosted on the **Standard tier** in `me-central-1`. Sovereign tenants
  never call into the control plane at runtime; their appliance only
  fetches signed update bundles over HTTPS.

## Consequences

### Positive

- One env-var (`DEPLOYMENT_REGION`) drives Terraform, the `/health` posture
  block, the admin "data residency selector", and PDPL audit exports.
- The Standard → Sovereign upgrade is a deployment-time decision, not a
  code change. The pluggable LLM provider layer (ADR 0005) and the SQLite
  default backend (ADR 0006) already make this seamless.
- We avoid coupling the product to a single cloud vendor. The Terraform
  modules will be split per provider so a future region (e.g. KSA or
  Egypt) is additive.

### Negative

- We will maintain at least two parallel deployment pipelines (AWS +
  G42). The DevOps/SRE agent owns this complexity; the trade is acceptable
  because Sovereign deals are a primary GTM lever (ADR 0007).
- AWS `me-central-2` is newer; some auxiliary services may lag Bahrain by
  a few quarters. We mitigate by keeping the Standard tier on `me-central-1`
  until parity is reached.
- On-prem appliance support widens the test matrix. We keep the appliance
  variant minimal: SQLite + Ollama/Jais + the Brain API; no Supabase, no
  managed vector DB.

## Validation

The choices in this ADR are observable at runtime through the existing
`/health.deployment` block — operators (and the upcoming admin UI) can
read `region` + `sovereign_mode` to confirm the deployment matches what
the contract or compliance auditor expects.
