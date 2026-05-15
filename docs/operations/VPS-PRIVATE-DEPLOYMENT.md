# VPS Private Deployment

> **How MagicLamp is deployed on a private UAE VPS — no cloud provider lock-in.**

---

## Deployment Philosophy

MagicLamp is deployed on a **private, UAE-hosted VPS** — not on managed cloud platforms (AWS, GCP, Azure, DigitalOcean App Platform, etc.).

This is intentional:
- UAE data residency requirement: all data remains on UAE soil.
- Control: the founder has full infrastructure ownership.
- Privacy: no cloud provider can access inference traffic or stored data.
- Cost: predictable monthly VPS cost, no per-token cloud charges.

---

## Supported Deployment Method

The primary deployment method is **Docker Compose** with NGINX as the reverse proxy.

```
Internet → NGINX (443/80) → Brain API (9000)
                          → N8N (5678, internal)
                          → Ollama (11434, internal)
                          → Supabase/Postgres (5432, internal)
```

All internal services communicate over Docker's internal network. Only NGINX is exposed to the internet.

---

## Minimum VPS Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 8 GB | 16 GB |
| Disk | 40 GB SSD | 80 GB SSD |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |
| Docker | 20.10+ | Latest stable |
| Docker Compose | 2.0+ | Latest stable |
| Network | 100 Mbps | 1 Gbps |

A GPU is recommended for Ollama inference performance but is not required for MVP.

---

## Initial Setup (High-Level — No VPS Commands Executed Here)

> **This document describes what to do. It does not execute any commands on a live server.**

### Step 1: Provision VPS

- Order a VPS from a UAE-based provider (e.g. Etisalat Cloud, du Cloud, AWS Bahrain region as fallback).
- Configure SSH key authentication — disable password SSH login.
- Open only ports 22 (SSH from trusted IPs), 80 (HTTP redirect), 443 (HTTPS).

### Step 2: Install Dependencies

```bash
# Install Docker and Docker Compose
curl -fsSL https://get.docker.com | sh
docker --version
docker compose version
```

### Step 3: Clone Repository

```bash
git clone https://github.com/subairkprm/MagicLamp.git
cd MagicLamp
```

### Step 4: Configure Environment

```bash
cp .env.example .env
# Edit .env — fill in secrets, URLs, model names
# See .env.example for all required variables
```

Required values in `.env`:

| Variable | Source |
|----------|--------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Supabase service role key |
| `JWT_SECRET` | `openssl rand -hex 32` |
| `BRAIN_SECRET` | `openssl rand -hex 32` |
| `SERVER_HOST` | VPS IP or domain name |
| `OLLAMA_MODEL` | e.g. `hermes3:8b` |
| `N8N_USER` | Admin username |
| `N8N_PASSWORD` | Strong password |
| `N8N_ENCRYPTION_KEY` | `openssl rand -hex 32` |

### Step 5: Start the Stack

```bash
docker compose up -d
make status
```

### Step 6: Pull AI Models

```bash
make pull-model MODEL=hermes3:8b
make pull-model MODEL=qwen2.5:3b
```

### Step 7: Configure SSL

```bash
make ssl DOMAIN=yourdomain.com
```

---

## Service Port Map

| Service | Internal Port | External | Notes |
|---------|-------------|----------|-------|
| Brain API | 9000 | Via NGINX only | FastAPI |
| NGINX | 80, 443 | ✅ Public | Reverse proxy + SSL |
| Ollama | 11434 | ❌ Internal only | Docker network |
| N8N | 5678 | Via NGINX only | Workflow automation |
| Supabase/Postgres | 5432 | ❌ Internal only | Database |

---

## Makefile Reference

| Command | Description |
|---------|-------------|
| `make start` | Start all services |
| `make stop` | Stop all services |
| `make restart` | Restart all services |
| `make build` | Rebuild brain + agent containers |
| `make deploy` | Full deploy with health checks |
| `make status` | Container health + API status |
| `make logs` | All service logs |
| `make brain-logs` | Brain service logs |
| `make backup` | Backup all data + .env |
| `make ssl DOMAIN=x` | Configure Let's Encrypt SSL |
| `make pull-model MODEL=x` | Pull Ollama model |
| `make list-models` | List installed Ollama models |

---

## Health Checks

```bash
# Brain API health (no auth required)
curl http://localhost:9000/health

# Full system health (requires auth)
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:9000/api/v1/admin/health
```

---

## Updating MagicLamp

```bash
git pull origin main
make build
make deploy
```

Always review the changelog before updating. Do not auto-update production without review.

---

## Security Checklist for Deployment

- [ ] All secrets generated with `openssl rand -hex 32` — not default values
- [ ] `.env` not committed to Git
- [ ] CORS set to specific domain — not `*`
- [ ] HTTPS enabled with valid certificate
- [ ] SSH password login disabled
- [ ] Ollama port 11434 firewalled from public
- [ ] Database port 5432 firewalled from public
- [ ] Telegram alerts configured and tested
- [ ] First backup taken and restore tested

---

## Related Documents

- [`docs/security/SECURITY-BASELINE.md`](../security/SECURITY-BASELINE.md)
- [`docs/security/UAE-DATA-RESIDENCY-POLICY.md`](../security/UAE-DATA-RESIDENCY-POLICY.md)
- [`docs/operations/BACKUP-ROLLBACK.md`](BACKUP-ROLLBACK.md)
