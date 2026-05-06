# Deploy MagicLamp on a VPS with Ollama (advanced)

> **Status:** Optional / advanced. Most users should use the
> [5-minute Railway deploy](deploy-railway.md) instead — it has zero external
> service dependencies beyond the LLM provider you choose.
>
> This guide is for users who want **fully self-hosted, GPU-accelerated local
> inference** with Ollama, plus the n8n automation layer and reverse-proxy
> SSL termination.

The full multi-service stack lives in the existing
[`docker-compose.yml`](../../docker-compose.yml) at the repository root. It
brings up:

| Service | Purpose |
|---|---|
| `ollama` | Local LLM runtime (default model: `qwen2.5:7b`). |
| `brain` | The MagicLamp Brain API — this is the **only** service the Railway-mode deploy uses. |
| `agent` | CRM AI Agent. |
| `n8n` | Workflow automation. |
| `ui` | Frontend served by nginx. |
| `nginx` | Reverse proxy + TLS termination. |
| `certbot` | Let's Encrypt auto-renewal. |

## Prerequisites

- A Linux VPS (Ubuntu 22.04 LTS or similar) with at least:
  - 8 GB RAM (16 GB recommended for `qwen2.5:7b`).
  - 50 GB disk.
  - GPU strongly recommended for usable Ollama latency.
- A domain pointed at the VPS IP.
- Docker 20.10+ and Docker Compose 2.0+.

## Configuration

1. Copy the env template:

   ```bash
   cp .env.example .env
   ```

2. Fill in the required values (`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`,
   `JWT_SECRET`, `BRAIN_SECRET`, `N8N_PASSWORD`, `SERVER_HOST`, …).
3. Tell the brain to use the local Ollama instance and Supabase backend:

   ```bash
   echo "DB_BACKEND=supabase"   >> .env
   echo "LLM_PROVIDER=ollama"   >> .env
   echo "OLLAMA_URL=http://ollama:11434" >> .env
   ```

## Bring it up

```bash
docker compose up -d
docker compose logs -f brain
```

The brain becomes available at `https://<your-domain>` once nginx + certbot
have negotiated TLS.

## Why this is no longer the default path

When MagicLamp first shipped, this stack *was* the default. As of the
"Railway-ready single-service deploy" change:

- The brain service no longer requires Ollama, Supabase, Redis, or n8n at
  startup. Each of those is now **optional** and only contacted when the
  matching feature is configured.
- The default `LLM_PROVIDER` is `openai` and the default `DB_BACKEND` is
  `sqlite`. With those defaults, a single container ships everything you need.
- The compose file is preserved unchanged for users who genuinely want the
  full stack — typically because they need GPU-local inference, the n8n
  automation surface, or want to host Postgres themselves.

See [explanation/deployment-modes.md](../explanation/deployment-modes.md) for
the full decision matrix.
