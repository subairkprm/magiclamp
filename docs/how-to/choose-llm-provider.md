# Choose an LLM provider

MagicLamp talks to one LLM provider at a time, selected via the
`LLM_PROVIDER` environment variable (or live at runtime via **Admin → AI
Provider** in the desktop client). All providers share the same internal
contract, so switching is a one-variable change with no code modifications.

## Supported providers

| `LLM_PROVIDER` | Where to get a key | Default model | Best for |
|---|---|---|---|
| `openai` | <https://platform.openai.com/api-keys> | `gpt-4o-mini` | Best quality / latency, broad capability. |
| `anthropic` | <https://console.anthropic.com/settings/keys> | `claude-3-5-haiku-latest` | Long-context tasks, careful reasoning. |
| `groq` | <https://console.groq.com/keys> | `llama-3.1-8b-instant` | Cheapest + fastest hosted inference. |
| `openrouter` | <https://openrouter.ai/keys> | `openai/gpt-4o-mini` | Single account, hundreds of models — pick any model from any vendor. |
| `gemini` | <https://aistudio.google.com/app/apikey> | `gemini-1.5-flash` | Google ecosystem, generous free tier. |
| `ollama` | n/a (local install) | `qwen2.5:7b` | Fully self-hosted; requires a VPS or workstation. |

## Recommended cheap defaults

For a brand-new project on a starter budget:

- **Cheapest hosted:** `groq` with `llama-3.1-8b-instant` — sub-second responses,
  free tier covers thousands of calls per day.
- **Best quality / cost ratio:** `openai` with `gpt-4o-mini`.
- **Most flexibility:** `openrouter` — set `OPENROUTER_MODEL` to anything in
  their catalogue (e.g. `anthropic/claude-3-haiku`, `meta-llama/llama-3.3-70b`).

## Configuration

Set two variables per provider — the key, and (optionally) the model name:

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
# Optional: override the default
# OPENAI_MODEL=gpt-4o
```

Provider keys are read directly from the environment and **never written to
the database**. The active selection (provider name + model) is persisted per
tenant in the `llm_settings` table so it survives restarts.

## Switching at runtime

In the desktop client:

1. Open **Admin → AI Provider**.
2. Pick a provider from the dropdown.
3. Optionally override the model name.
4. Click **Save**, then **Test connection** to verify.

The change takes effect immediately — every subsequent brain call routes
through the new provider.

You can also script it:

```bash
# List providers + which are configured
curl -H "Authorization: Bearer $JWT" \
  https://<host>/api/v1/admin/llm/providers

# Switch to Groq
curl -X PUT \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"provider":"groq"}' \
  https://<host>/api/v1/admin/llm/active
```

## Circuit breakers

Each provider gets its own [circuit breaker](../adr/0005-pluggable-llm-providers.md)
so a flapping vendor can't take the rest of MagicLamp down with it. After 3
consecutive failures the breaker opens for 20 seconds; calls during that
window short-circuit to a generic "AI Engine unavailable" message instead of
hanging.
