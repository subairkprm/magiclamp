# MagicLamp Routing and Escalation

## Purpose
This document defines how work is routed in MagicLamp while preserving safety, compliance, and traceability.

## Intake rules
- Every task must map to exactly one issue.
- Every issue must map to exactly one PR.
- If scope expands, open a **new issue + new PR** rather than mixing streams.

## Route by risk band
- **GREEN**: Documentation, non-sensitive UX copy, non-production-safe metadata updates.
- **AMBER**: Internal logic/config with no production-impacting infra/auth/db changes.
- **RED**: Any change in hard-gate domains, security-sensitive paths, production customization, or UAE residency boundaries.

Agents must never bypass RED/AMBER/GREEN controls.

## Hard-gate trigger matrix
Escalate to human owner/founder before merge when any of the below is true:
1. VPS/deployment behavior changes.
2. Auth or security control behavior changes.
3. DB schema/storage/migration behavior changes.
4. Agent permission boundary or role model changes.
5. GitHub write/admin access model changes.
6. Production customization application flow changes.
7. External/cloud LLM routing or provider usage changes.
8. Data egress path could move data outside UAE residency controls.

## Agent execution restrictions
- No merges.
- No production deploys.
- No destructive shell operations.
- No production DB mutation.
- No direct writes to SpreadVerse V2 DB.

## Required routing output in PR
PR description must include:
- Risk band (RED/AMBER/GREEN)
- Whether hard-gate is triggered
- Founder action required (Yes/No + why)
