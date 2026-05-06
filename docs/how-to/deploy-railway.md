# Deploy MagicLamp to Railway

> **Audience:** Anyone who wants the fastest possible MagicLamp deployment with
> no servers to manage. Reading time: 5 minutes.

This guide gets you from "empty Railway account" to "MagicLamp Brain running
in production" with no Supabase, no Redis, no Ollama, no domain, and no SSL
configuration. The only external service involved is the LLM provider you
choose (OpenAI, Anthropic, Groq, OpenRouter, Gemini).

If you'd rather self-host the full stack on a VPS with Ollama and n8n, see
[deploy-vps-with-ollama.md](deploy-vps-with-ollama.md) instead.

## What you'll need

- A [Railway](https://railway.app) account (free tier works for testing).
- An API key from one LLM provider — see
  [choose-llm-provider.md](choose-llm-provider.md) for a comparison.
- Two random secrets (32 bytes each). Generate them with:

  ```bash
  openssl rand -hex 32
  ```

That's it.

## Step 1 — Fork & deploy

1. Fork this repository to your GitHub account.
2. In Railway, click **New Project → Deploy from GitHub repo** and pick the
   fork. Railway will detect [`railway.json`](../../railway.json) at the root
   and build the `brain/Dockerfile` automatically.
3. Wait ~2 minutes for the first build to finish. The container starts behind
   a public Railway URL — keep it open.

## Step 2 — Set 4 environment variables

In **Project → Variables**, add:

| Variable | Value |
|---|---|
| `JWT_SECRET` | output of `openssl rand -hex 32` |
| `BRAIN_SECRET` | output of `openssl rand -hex 32` |
| `LLM_PROVIDER` | `openai` (or one of `anthropic`, `groq`, `openrouter`, `gemini`) |
| `OPENAI_API_KEY` | your OpenAI key — replace the variable name to match the provider you chose (e.g. `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, …) |

Everything else has a sane default. See
[`.env.railway.example`](../../.env.railway.example) for the full list of
optional knobs (model overrides, RAG toggle, etc.).

## Step 3 — Add a Volume for SQLite

MagicLamp stores its database in `${BRAIN_DATA_DIR}/magiclamp.db`. To make sure
that file survives container restarts:

1. **Project → New → Volume**.
2. Mount path: `/data/brain` (this matches the default `BRAIN_DATA_DIR`).
3. Attach it to the `brain` service.

`railway.json` declares the volume mount target so Railway will hook this up
automatically once you create it.

## Step 4 — Verify

Open the Railway-assigned URL. You should see:

```json
{ "app": "MagicLamp", "version": "1.0.0", "docs": "/docs", "health": "/health" }
```

Then hit `/health` — it should return `{ "status": "ok", … }`.

Open `/docs` to explore the API in Swagger UI. Log in to the desktop client
(or POST `/api/v1/auth/login`) and you can immediately start posting brain
calls — they'll route through the provider you picked.

## Verifying the LLM provider

In the desktop client, go to **Admin → AI Provider**:

- The **Active provider** dropdown shows which provider is currently selected.
- Click **Test connection** to round-trip a tiny prompt through the provider's
  API and confirm your key works.

You can also call the test endpoint directly:

```bash
curl -X POST https://<your-railway-url>/api/v1/admin/llm/test \
  -H "Authorization: Bearer <your-jwt>" \
  -H "Content-Type: application/json" \
  -d '{}'
```

## Switching provider later

Set `LLM_PROVIDER` (and the matching `*_API_KEY`) to a different value and
redeploy. Or change it at runtime via the Settings → AI Provider panel — the
in-process active provider updates immediately and the choice is persisted in
the `llm_settings` table so it survives the next restart.

## What's *not* deployed on Railway?

| Component | Status |
|---|---|
| Brain API | ✅ deployed |
| SQLite database | ✅ on the Railway Volume |
| LLM provider | 🔌 your chosen vendor (OpenAI, Anthropic, Groq, …) |
| Ollama | ❌ skipped — use a VPS deploy if you want local inference |
| n8n / nginx / certbot | ❌ skipped — Railway handles ingress + TLS |
| Supabase | ❌ skipped — switch with `DB_BACKEND=supabase` if you want it back |
| ChromaDB / RAG | ❌ off by default — flip `RAG_ENABLED=true` to enable (data goes under `BRAIN_DATA_DIR/chroma`, still no external service) |

See [explanation/deployment-modes.md](../explanation/deployment-modes.md) for
the trade-offs between Simple (Railway) and Self-hosted (VPS) modes.
