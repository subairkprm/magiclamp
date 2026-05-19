# magic-lamp-security-boundaries-v1

## Purpose
Define the operational security boundaries for what MagicLamp is allowed and prohibited to do as an internal control-plane system.

## Scope
MagicLamp control-plane services, interfaces, and agent-driven operations across planning, routing, and reporting workflows.

## Control Objectives
- Enforce least privilege for control-plane actions.
- Prevent unauthorized production-impacting operations.
- Ensure high-risk actions require explicit human approval.

## Required Controls
Allowed actions:
- Translate instructions.
- Read CI status.
- Read PR metadata.
- Suggest fixes.
- Generate task plans.
- Produce evidence reports.

Prohibited actions:
- Merge PRs.
- Deploy to production.
- Deploy to staging.
- Run database migrations.
- Change VPS firewall rules.
- Edit secrets.
- Perform direct database writes outside approved metadata tables.

Approval gate table (architecture contract):

| Action Domain | Gate Level | Human Approval Requirement |
|---|---|---|
| VPS/deployment changes | HARD GATE | Mandatory founder/security review before merge or execution |
| Auth/security changes | HARD GATE | Mandatory founder/security review |
| Database/schema changes | HARD GATE | Mandatory founder/security review |
| Agent permission changes | HARD GATE | Mandatory founder/security review |
| GitHub write access changes | HARD GATE | Mandatory founder/security review |
| Production customization application | HARD GATE | Mandatory founder/security review |
| External/cloud LLM usage | HARD GATE | Mandatory founder/security review |
| Data leaving UAE residency boundaries | HARD GATE | Mandatory founder/security review |

Access model:
- Super Admin-only operation.
- Internal backend call path only.
- No public endpoint exposure.

Enforcement mechanisms:
- FastAPI route guards for privileged control-plane operations.
- `MAGIC_LAMP_ENABLED` feature flag gating execution.
- Docker internal network isolation.
- nginx configuration does not proxy control-plane routes publicly.

## Validation and Evidence
Representative validation checks:
- Route/permission guard tests and code review records for privileged endpoints.
- Environment configuration review for `MAGIC_LAMP_ENABLED`.
- Docker network inspection (`docker network inspect <network>`).
- nginx active config review to confirm control-plane routes are not public (`nginx -T`).

This boundary definition is an intended control baseline and does not represent formal certification.

## Exceptions and Risk Acceptance
Exceptions to prohibited actions are not allowed without explicit written founder/security approval and documented temporary controls.

## Review Cadence
Quarterly and upon architecture contract changes.

## Owner and Approvals
Owner: Platform maintainer / Super Admin.
Approvals: Founder/security reviewer for boundary exceptions and policy changes.
