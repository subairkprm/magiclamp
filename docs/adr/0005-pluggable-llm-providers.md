# ADR 0005 — Pluggable LLM provider layer

- **Status:** Accepted
- **Date:** 2026-05
- **Deciders:** Lead Architect
- **Tags:** backend, llm, deploy

## Context

Until this change, every brain LLM call hardwired Ollama as the only backend.
`brain/api/v1/_brain/services.py` issued requests to `OLLAMA_URL/api/chat` with
the Ollama-specific payload shape, and `core/circuit.py` exposed a single
`ollama_circuit` breaker.

That coupling made the simple deploy story impossible:

- Every Railway / single-VPS user had to also run a local Ollama instance —
  which dominates RAM/GPU requirements and rules out small instances entirely.
- Switching to a hosted LLM (OpenAI, Anthropic, Groq, Gemini, OpenRouter) was a
  source-code change, not a configuration change.
- Per-tenant "user choice" of provider was infeasible.

## Decision

Introduce a small provider abstraction in `brain/core/llm/`:

- `LLMProvider` Protocol with `complete(prompt, system, json_mode) -> str` and
  `stream(prompt, system) -> AsyncIterator[str]`.
- One adapter per backend: `openai.py`, `anthropic.py`, `groq.py`,
  `openrouter.py`, `gemini.py`, `ollama.py`. Adapters are thin (~50 LoC each)
  and share a small `_openai_compat.py` helper for the four backends that
  speak the OpenAI chat-completions schema.
- `get_provider(name=None) -> LLMProvider` selects by an explicit argument
  (per-request override) or falls back to the `LLM_PROVIDER` env var
  (default: `openai`). A separate `CircuitBreaker` is maintained per provider
  name.
- `services.llm` and `services.llm_stream` delegate to the provider returned
  by `get_provider()` instead of speaking directly to Ollama.

API keys live in environment variables only — they are never persisted in the
database. Per-tenant *selection* (which provider + which model) is persisted
in a new `llm_settings` table and exposed through three admin endpoints
(`GET /admin/llm/providers`, `PUT /admin/llm/active`, `POST /admin/llm/test`).

## Consequences

**Positive**

- Ollama becomes one option among many. Default deployments need no local
  GPU box.
- Adding a new vendor is one new ~50-LoC file plus one entry in `_registry()`.
- Per-provider circuit breakers prevent one flapping vendor from poisoning
  calls to another.
- "User choice" of provider is feasible without code changes — operators can
  flip providers from the desktop client.

**Negative**

- One more layer of indirection between `services.llm` and the wire.
- Six adapters means six surfaces to maintain when vendors change their
  request schemas. Mitigation: four of the six share `_openai_compat.py`.

**Neutral**

- Behaviour is preserved bit-for-bit when `LLM_PROVIDER=ollama`. The existing
  Ollama integration tests pass unchanged because `OllamaProvider` mirrors
  the prior request payload.

## Alternatives considered

- **LiteLLM** — would give us most of this for free, but adds a heavyweight
  dependency (~80 MB), pulls in vendor SDKs we don't want, and constrains
  observability (its retries / circuit-breaker logic wraps everything). Not
  worth it for six adapters.
- **Direct vendor SDKs (`openai`, `anthropic`, `google-generativeai`)** —
  rejected because each SDK adds ~5–20 MB to the image and pulls transitive
  deps that conflict on Python 3.11. The HTTP surfaces are tiny and stable
  enough to call `httpx` directly.
