# MagicLamp — Production VPS Deployment (Docker Compose)

Primary production path: Ubuntu VPS + Docker Compose (no Coolify required).

## Prerequisites
- Ubuntu 22.04+ with Docker and Docker Compose v2
- Public domain or IP
- `.env` filled from `.env.example` with strong secrets

## One-time setup
```bash
ssh root@YOUR_VPS
git clone https://github.com/subairkprm/magiclamp /opt/magiclamp
cd /opt/magiclamp
cp .env.example .env   # fill required values
bash start.sh          # installs deps, builds, and runs prod stack
```

## Manual deploy/update
```bash
cd /opt/magiclamp
git pull origin main
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull ollama n8n
docker compose -f docker-compose.yml -f docker-compose.prod.yml build --parallel brain agent
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Health checks
```bash
curl http://localhost:9000/health
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

## Notes
- Nginx is the only public entry (80/443). Internal services are not host-exposed.
- Coolify remains optional; if used, point it at `docker-compose.yml` + `docker-compose.prod.yml`.
- SSL: use `make ssl DOMAIN=... EMAIL=...` then enable HTTPS in `nginx/conf.d/magiclamp.conf`.
