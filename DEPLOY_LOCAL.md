# MagicLamp — Local Development & Testing

## Prerequisites
- Docker and Docker Compose v2
- `.env` populated from `.env.example` (use local-friendly values)

## Quick start
```bash
cp .env.example .env          # set secrets and local values
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d
docker compose -f docker-compose.yml -f docker-compose.local.yml ps
```

## Defaults for local
- `ENV=development`
- `BRAIN_AUTO_MODE` defaults to false (can be set in `.env`)
- All services expose their ports to the host for debugging
- CORS allows `*` (local only)

## Health check
```bash
curl http://localhost:9000/health
curl http://localhost:8000/health
```

## Tear down
```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml down
```
