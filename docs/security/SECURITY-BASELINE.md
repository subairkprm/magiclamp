# Security Baseline

> **Minimum security requirements for all MagicLamp deployments.**

---

## Overview

This document defines the security baseline for MagicLamp MVP. All deployments must satisfy these controls before being considered operational.

**Status:** This is a documentation-only baseline. It defines requirements; it does not certify any deployment as compliant. Each deployment must be independently verified.

---

## 1. Authentication & Access Control

| Control | Requirement |
|---------|-------------|
| JWT Authentication | All API endpoints require a valid JWT token except `/health` |
| JWT Secret Strength | Minimum 32 characters, randomly generated (`openssl rand -hex 32`) |
| JWT Expiry | Access tokens expire within 60 minutes; refresh tokens within 7 days |
| API Keys | Service-to-service calls use separate API keys, not user JWTs |
| Brain Key | Internal brain service uses a separate `BRAIN_SECRET` (min 32 chars) |
| RBAC | All workspace operations are governed by `brain/core/rbac.py`; deny-by-default |
| Password Policy | Minimum 12 chars; must include uppercase, lowercase, digit, special char |
| Common Password Check | Passwords must not appear in the common password list |

---

## 2. Network Security

| Control | Requirement |
|---------|-------------|
| HTTPS | All external endpoints must use TLS 1.2+ |
| NGINX | NGINX must be the only public-facing entry point |
| Ollama Port | Port 11434 must NOT be exposed to the public internet |
| Supabase Port | Database port must NOT be exposed to the public internet |
| CORS | Production deployments must specify explicit allowed origins (not `*`) |
| Firewall | Only ports 80, 443 (and SSH 22 from trusted IPs) should be open |

---

## 3. Secrets Management

| Control | Requirement |
|---------|-------------|
| No hardcoded secrets | All secrets in `.env` — never committed to Git |
| `.env` in `.gitignore` | Confirmed present (see `.gitignore`) |
| Secret rotation | Rotate JWT_SECRET, BRAIN_SECRET, N8N keys on any suspected compromise |
| No secrets in logs | Log formatters must not emit secret values |
| Secrets not exposed in API | No endpoint may return raw secret values |

---

## 4. Audit Logging

| Control | Requirement |
|---------|-------------|
| Mutating operations logged | All POST/PUT/PATCH/DELETE operations produce an audit entry |
| Audit entry fields | Must include: user_id, org_id, action, timestamp, IP address, request summary |
| Audit log immutability | Audit logs must not be deletable via user-facing API |
| Failed auth attempts logged | Every failed login or token validation is logged |
| Agent RED action attempts logged | Every blocked RED action produces an audit entry |

---

## 5. Input Validation

| Control | Requirement |
|---------|-------------|
| Pydantic validation | All API inputs validated with Pydantic models |
| SQL injection prevention | No raw SQL string interpolation; use parameterised queries |
| XSS prevention | All user-supplied strings HTML-escaped before rendering |
| SSRF prevention | URL inputs validated against an allowlist before any outbound HTTP call |
| File upload restrictions | File uploads (if any) restricted by type and size |

---

## 6. Data Protection

| Control | Requirement |
|---------|-------------|
| PII at rest | Customer PII must be stored in Supabase Postgres on UAE VPS |
| PII in transit | Customer PII must only travel over TLS |
| No cloud LLM with PII | Customer PII must never be sent to a cloud LLM API |
| Emirates ID validation | All EID inputs validated with `brain/core/uae_id.is_valid_emirates_id()` |
| Mobile number normalisation | All UAE mobile inputs normalised with `brain/core/uae_id.normalize_uae_mobile()` |

---

## 7. Container & Infrastructure Security

| Control | Requirement |
|---------|-------------|
| No root containers | All services should run as non-root users where possible |
| Image scanning | Docker images should be scanned for known CVEs before production deployment |
| Dependency pinning | Python dependencies pinned in `requirements.txt` / `uv.lock` |
| No debug mode in production | `BRAIN_DEBUG=false` in production `.env` |
| Resource limits | Docker Compose services should have memory/CPU limits set |

---

## 8. Backup & Recovery

| Control | Requirement |
|---------|-------------|
| Daily backups | Supabase data and `.env` backed up daily |
| Backup encryption | Backups containing secrets must be encrypted |
| Recovery tested | Restore procedure must be tested at least once per quarter |
| Rollback capability | Every deployment must have a documented rollback path |

See [`docs/operations/BACKUP-ROLLBACK.md`](../operations/BACKUP-ROLLBACK.md) for procedures.

---

## 9. Incident Response

| Control | Requirement |
|---------|-------------|
| Telegram alerting | Critical failures trigger Telegram alert to admin chat |
| Circuit breakers | All external service calls protected by circuit breakers |
| On-call contact | Founder/lead engineer must have access to VPS SSH and Telegram alerts |

---

## 10. What Is Not Required in MVP

The following controls are noted as future requirements but are **not required** for MVP:

- SOC 2 certification
- Penetration testing (recommended but not gating)
- WAF (Web Application Firewall) — NGINX rate limiting is the MVP control
- SIEM (Security Information and Event Management)
- HSM (Hardware Security Module) for key storage

---

## Security Acceptance Gate

Before any deployment is considered production-ready (not MVP):

- [ ] All secrets generated with `openssl rand -hex 32` or equivalent
- [ ] CORS restricted to known origins
- [ ] HTTPS enabled with valid certificate
- [ ] Ollama and database ports firewalled from public internet
- [ ] Audit log confirmed writing entries
- [ ] Telegram alerts confirmed firing
- [ ] Backup restore tested

---

## Related Documents

- [`docs/security/UAE-DATA-RESIDENCY-POLICY.md`](UAE-DATA-RESIDENCY-POLICY.md)
- [`docs/security/AGENT-PERMISSION-MODEL.md`](AGENT-PERMISSION-MODEL.md)
- [`docs/security/WEB-SEARCH-SAFETY.md`](WEB-SEARCH-SAFETY.md)
- [`docs/operations/VPS-PRIVATE-DEPLOYMENT.md`](../operations/VPS-PRIVATE-DEPLOYMENT.md)
- [`docs/operations/BACKUP-ROLLBACK.md`](../operations/BACKUP-ROLLBACK.md)
