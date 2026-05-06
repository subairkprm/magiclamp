# Deployment modes

MagicLamp supports two distinct deployment shapes. They share the same source
tree, the same API surface, and the same desktop client — only the surrounding
infrastructure differs.

## Simple (Railway / single-service)

```
┌──────────────────────────────────────────┐
│  Railway container                       │
│  ┌────────────────────────────────────┐  │
│  │  brain (FastAPI)                   │  │
│  │  ├─ SQLite at /data/brain/*.db     │  │
│  │  └─ in-memory rate limiter         │  │
│  └────────────────────────────────────┘  │
└──────────────────┬───────────────────────┘
                   │  HTTPS
                   ▼
        ┌──────────────────────┐
        │ Hosted LLM provider  │  (OpenAI / Anthropic / Groq / …)
        └──────────────────────┘
```

- **External services:** exactly one — your chosen LLM provider.
- **Persistent state:** a single SQLite file on a Railway Volume.
- **Setup time:** ~5 minutes.
- **See:** [how-to/deploy-railway.md](../how-to/deploy-railway.md).

## Self-hosted (VPS, Ollama, n8n)

```
┌────────────────────────────────────────────────────────┐
│  Single VPS                                            │
│   nginx + certbot ──► brain ──► ollama (local LLM)     │
│                       │                                │
│                       └──► supabase (managed Postgres) │
│                       └──► n8n (workflow automation)   │
└────────────────────────────────────────────────────────┘
```

- **External services:** Supabase (managed Postgres). LLM runs locally.
- **Persistent state:** Postgres + on-disk model weights.
- **Setup time:** ~30 minutes plus model download.
- **See:** [how-to/deploy-vps-with-ollama.md](../how-to/deploy-vps-with-ollama.md).

## Decision matrix

| If you care about… | Pick |
|---|---|
| Fastest possible setup | Simple (Railway) |
| Lowest fixed cost (free tier OK) | Simple (Railway) |
| No third-party data residency | Self-hosted |
| GPU-local inference (no per-token billing) | Self-hosted |
| Workflow automation via n8n | Self-hosted |
| Multi-instance horizontal scaling | Self-hosted (with `DB_BACKEND=supabase`) |
| Team collaboration on the brain UI | Either — both expose the same API |

## Choosing components à la carte

The two modes are end-points on a spectrum, not the only options. Every
component is independently switchable:

| Component | Variable | Simple default | Self-hosted default |
|---|---|---|---|
| Database backend | `DB_BACKEND` | `sqlite` | `supabase` |
| LLM provider | `LLM_PROVIDER` | `openai` | `ollama` |
| Vector store / RAG | `RAG_ENABLED` | `false` | `true` (file-backed Chroma under `BRAIN_DATA_DIR/chroma`) |
| Background scheduler | `BRAIN_AUTO_MODE` | `false` | `true` |

You can, for example, run the simple Railway deploy but flip `RAG_ENABLED=true`
to enable semantic search backed by a local Chroma store on the same
volume — no external vector DB required.

## What stays the same regardless of mode

- All HTTP routes under `/api/v1/*`.
- JWT auth, API keys, audit logging, RBAC.
- Rate limiting (in-memory via slowapi).
- The desktop client (built from `desktop/`).
- The provider plugin layer — every adapter is available in every mode.
