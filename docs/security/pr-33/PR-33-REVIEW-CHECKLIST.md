# PR #33 Review Checklist — WS-01 to WS-05

Use this checklist when reviewing the PR diff. Mark YES only when the change is physically visible in the PR.

## WS-01 Network Exposure

- [ ] YES / NO — Only the reverse proxy publishes public ports.
- [ ] YES / NO — Ollama uses internal container exposure only.
- [ ] YES / NO — Brain API uses internal container exposure only.
- [ ] YES / NO — Agent service uses internal container exposure only.
- [ ] YES / NO — N8N uses internal container exposure only.
- [ ] YES / NO — Internal services share the private Docker network.
- [ ] YES / NO — Host networking is not used.

## WS-02 Container Hardening

- [ ] YES / NO — Production images are pinned; floating latest tags are removed where practical.
- [ ] YES / NO — Brain and Agent run as non-root users where practical.
- [ ] YES / NO — Containers do not request privileged mode.
- [ ] YES / NO — Services use no-new-privileges where supported.
- [ ] YES / NO — Read-only filesystem is applied where practical, or exceptions are documented.

## WS-03 CORS

- [ ] YES / NO — CORS origins are loaded from environment/config.
- [ ] YES / NO — Production fails closed if wildcard origins are configured.
- [ ] YES / NO — Example env file shows a specific allowed origin.
- [ ] YES / NO — Credentials are not combined with wildcard origins.
- [ ] YES / NO — Methods and headers are scoped or justified.

## WS-04 API Documentation Exposure

- [ ] YES / NO — API docs are disabled or protected in production.
- [ ] YES / NO — OpenAPI is disabled or protected in production.
- [ ] YES / NO — Reverse proxy blocks public docs routes in production.

## WS-05 N8N Access

- [ ] YES / NO — N8N is removed from public reverse-proxy routing.
- [ ] YES / NO — N8N has no public hostname.
- [ ] YES / NO — N8N is reachable only through an admin-controlled access path.
- [ ] YES / NO — Admin access instructions are documented.

## PR Hygiene

- [ ] YES / NO — PR scope is WS-01 to WS-05 only.
- [ ] YES / NO — No real secrets are committed.
- [ ] YES / NO — No model router, RAG, search gateway, agent registry, or database migration scope is included.
- [ ] YES / NO — No new external AI or cloud dependency is introduced.

## Decision

All YES = continue to post-deploy verification. Any NO = block merge.
