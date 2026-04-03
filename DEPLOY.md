# MagicLamp — VPS Deployment Guide

## What Gets Installed

```
VPS (Contabo 12GB)
│
├── Coolify :8000          ← Web panel — manage everything from browser
│   └── Watches GitHub → auto-deploys on git push
│
└── MagicLamp Stack (Docker Compose)
    ├── Nginx :80/:443     ← All public traffic enters here
    │   ├── /              → MagicLamp UI
    │   ├── /api/          → Brain API
    │   ├── /agent/        → CRM Agent
    │   ├── /n8n/          → Workflow Studio
    │   └── /docs          → API Documentation
    ├── Brain :9000        ← Master Control (internal)
    ├── Agent :8000        ← CRM AI Agent (internal)
    ├── Ollama :11434      ← Local LLM (internal)
    └── N8N :5678          ← Automation (internal)
```

---

## First-Time VPS Setup

### Requirements
- Ubuntu 22.04 LTS
- 12 GB RAM (Contabo Cloud VPS 20 — $7.95/mo)
- Root access

### Deploy

```bash
# 1. SSH into your VPS
ssh root@YOUR_VPS_IP

# 2. Clone the repo
git clone https://github.com/subairkprm/magiclamp /opt/magiclamp
cd /opt/magiclamp

# 3. Run the one-command installer
bash start.sh
```

The installer will:
- Install Docker + Docker Compose
- Configure firewall (ports 22, 80, 443, 8000)
- Install Coolify web panel
- Auto-generate JWT_SECRET, BRAIN_SECRET, N8N_ENCRYPTION_KEY
- Build and start all 6 containers
- Pull Qwen2.5 7B AI model in background
- Register Telegram webhook

---

## Coolify Setup (Web Panel)

After `start.sh` completes:

**1. Open Coolify**
```
http://YOUR_VPS_IP:8000
```

**2. Create admin account** (first visit only)

**3. Connect GitHub**
- Settings → Sources → Add Source → GitHub
- Authorize: `github.com/subairkprm/magiclamp`

**4. Create Project**
- Projects → New Project → "MagicLamp"
- Add Application → Docker Compose
- Repository: `subairkprm/magiclamp`
- Branch: `main`
- Compose file: `docker-compose.yml`

**5. Add Environment Variables**
Copy from your `.env` file into Coolify's Environment Variables panel.

**6. Enable Auto Deploy**
- Settings → Enable "Auto Deploy on Push"
- Now every `git push` to `main` → Coolify rebuilds and restarts automatically

---

## After Setup — Access Points

| Service | URL |
|---|---|
| MagicLamp Platform | `http://YOUR_VPS_IP/` |
| Coolify Web Panel | `http://YOUR_VPS_IP:8000` |
| Brain API Docs | `http://YOUR_VPS_IP/docs` |
| N8N Workflows | `http://YOUR_VPS_IP/n8n/` |
| Agent Health | `http://YOUR_VPS_IP/agent/health` |

---

## Day-to-Day Operations

All from your laptop — no SSH needed after initial setup:

```bash
# Deploy code update
git push origin main
# → Coolify auto-detects → rebuilds brain/agent → restarts

# View logs (in Coolify UI or terminal)
make logs

# Check health
make status

# Pull a new AI model
make pull-model MODEL=mistral:7b

# Backup everything
make backup

# Trigger daily briefing manually
make trigger-briefing
```

---

## SSL (HTTPS) Setup

If you have a domain pointing to your VPS IP:

```bash
make ssl DOMAIN=yourdomain.com EMAIL=your@email.com
```

Then update `nginx/conf.d/magiclamp.conf` to enable the HTTPS server block.

---

## RAM Usage on 12GB VPS

| Service | RAM | Status |
|---|---|---|
| Ubuntu OS | 400 MB | Always |
| Ollama + Qwen2.5 7B | 5,000 MB | Always |
| Brain (Python) | 400 MB | Always |
| Agent (Python) | 150 MB | Always |
| N8N | 450 MB | Always |
| Nginx | 64 MB | Always |
| Coolify | 300 MB | Always |
| **Total used** | **~6.8 GB** | |
| **Free headroom** | **~5.2 GB** | |
