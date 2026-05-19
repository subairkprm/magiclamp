# software-supply-chain-baseline-v1

## Purpose
Establish an intended software supply chain security baseline aligned to OWASP SCVS target baseline controls for MagicLamp.

## Scope
All Python dependencies referenced by `brain/requirements.txt` and `uv.lock`.

## Control Objectives
- Prevent use of unverified or unreviewed dependency sources.
- Ensure deterministic, pinned dependency resolution.
- Monitor and remediate known CVEs in dependency graph.

## Required Controls
- All installable dependencies must be pinned and resolved via `uv.lock`.
- Dependabot must remain configured for dependency monitoring (`.github/dependabot.yml` present).
- Vulnerability scanning (e.g., `pip-audit` or `safety`) must run in CI.
- No package installation is allowed outside `uv sync` managed workflows.
- AI/LLM packages must not be introduced without explicit security review.
- OWASP SCVS Level 1 controls are treated as the target baseline.

## Validation and Evidence
Representative validation commands/evidence:
- Dependency CVE check:
  - `uv run pip-audit`
- Dependabot configuration presence:
  - `cat .github/dependabot.yml`
- Lockfile-controlled dependency posture:
  - `test -f uv.lock && echo "uv.lock present"`

This document defines intended controls and target baseline expectations; it is not a formal compliance attestation.

## Exceptions and Risk Acceptance
Any exception (including temporary package pin bypass) requires written founder/security approval with compensating controls and expiry date.

## Review Cadence
Every PR (lightweight checks) plus monthly full dependency audit.

## Owner and Approvals
Owner: Platform maintainer / Super Admin.
Approvals: Founder/security reviewer for exceptions and baseline adjustments.
