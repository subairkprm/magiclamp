# PR #33 Founder Merge Gate

This file defines the founder-side decision gate for the WS-01 to WS-05 hardening PR.

## Scope

PR #33 must include only:

- network exposure reduction
- container hardening
- strict CORS behavior
- production docs protection
- private/admin-only N8N access path

It must not include:

- model router
- Hermes implementation
- RAG
- search gateway
- agent registry
- database migration
- business feature work

## Required Review Order

1. Review the PR description.
2. Review changed files.
3. Complete `PR-33-REVIEW-CHECKLIST.md`.
4. Confirm CI/checks are green or explain why no CI exists.
5. Deploy only to staging/private VPS first.
6. Run `verify-hardening.sh`.
7. Review script output.
8. Merge only if the result is GREEN or if every AMBER warning has a written founder decision.

## Block Merge If

- Any internal service is publicly reachable.
- CORS allows wildcard in production.
- API docs are public in production.
- N8N is publicly reachable without an admin-controlled access path.
- Real secrets are committed.
- The PR includes unrelated WS-06+ scope.
- The change adds an external AI/cloud dependency.

## Merge Allowed If

- Checklist is all YES.
- Verification script returns GREEN.
- No unrelated scope is present.
- Rollback path is clear.

## Founder Sign-Off Template

```md
Founder review completed for PR #33.

Checklist: PASS / FAIL
Verification: GREEN / AMBER / RED
Unresolved warnings: none / listed below
Decision: merge / block

Evidence:
- PR diff reviewed
- Verification script output reviewed
- No unrelated scope found
```
