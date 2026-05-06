# Quickstart — Run MagicLamp locally in 10 minutes

This walkthrough gets the Brain API and the desktop client running on a
single workstation. Estimated time: **10 minutes** with the prerequisites
already installed.

## Prerequisites

- Python ≥ 3.11
- Node.js ≥ 18 + npm
- A local [Ollama](https://ollama.ai) install with the configured model
  pulled (default: `qwen2.5:7b`)
- A Supabase project (URL + service-role key)

## 1. Configure environment

Copy the example env file and fill in the required values:

```bash
cp .env.example .env  # if missing, create one with the keys below
```

Required keys (see `brain/core/config.py` for the full list):

```ini
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SERVICE_KEY=<service-role-key, ≥32 chars>
JWT_SECRET=<random-secret, ≥32 chars>
BRAIN_SECRET=<random-secret, ≥32 chars>
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
ENVIRONMENT=development
BRAIN_AUTO_MODE=false
```

## 2. Start the Brain API

```bash
pip install -r brain/requirements.txt
cd brain && uvicorn main:app --reload --port 9000
```

Browse to <http://localhost:9000/docs> to confirm the OpenAPI page renders.
You should see the routes registered by the split router (memory, reason
including `reason/ask/stream`, training, changes, scheduler).

## 3. Start the desktop client

```bash
cd desktop
npm install
npm run dev          # starts Vite + Electron
# or, web-only:
npm run dev:vite
```

## 4. Sign in & ask the Brain

1. Use the **Login** screen to authenticate (admin user provisioned via your
   Supabase users table).
2. Open the **Brain** tab → **Ask**.
3. Enter a question. You should see tokens stream in, citation chips render
   as `[#1]`, `[#2]`, and a **Sources** panel below the answer.

If the gateway strips SSE you'll see the *Streaming unavailable — answered
via polled task fallback* note; the answer still renders.

## Next steps

- **[Streaming Ask reference](../reference/streaming-ask.md)** — wire your
  own client to the SSE endpoint.
- **[ADR 0004 — Design tokens & RTL](../adr/0004-design-tokens-and-rtl.md)** —
  switch the UI to light theme or Arabic right-to-left from the sidebar.
- **[`docs/rag.md`](../rag.md)** — enable & tune the RAG retrieval path.
