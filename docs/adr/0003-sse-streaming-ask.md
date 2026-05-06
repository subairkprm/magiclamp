# ADR 0003 — Server-Sent Events for the streaming Ask flow

- **Status:** Accepted
- **Date:** 2026-05
- **Tags:** backend, streaming, chat, ux

## Context

The original Ask flow (`POST /brain/reason/ask`) returns a `task_id` and the
desktop client polls `GET /brain/tasks/{task_id}` until completion. This was
fine for an internal MVP but is well below the bar set by Perplexity, Claude
and ChatGPT — users expect tokens to render incrementally, with retrieval
citations visible as soon as they are known.

## Decision

Add a *parallel* streaming endpoint, `POST /brain/reason/ask/stream`, that
emits Server-Sent Events with three event types:

| Event   | Payload (JSON)                                            | When |
|---------|-----------------------------------------------------------|------|
| `meta`  | `{ "retrieval_mode": "rag", "citations": [{id,key},...] }` | Once, before the first token |
| `token` | `"chunk of text"`                                          | Repeatedly, as tokens stream from Ollama |
| `done`  | `{}`                                                       | Once, terminal marker |

The endpoint **reuses the same retrieval and prompt assembly path** as
`/brain/reason/ask` (factored into `_brain.reason._retrieve_for_question`
and `_build_ask_prompt`), so behaviour matches and there is no second
codepath to maintain.

The polled endpoint is kept for two reasons:

1. **Fallback.** The client falls back to the polled flow if the gateway
   buffers SSE or strips it.
2. **Backwards compatibility.** Existing automation scripts continue to work.

### Why SSE (not WebSockets)?

- One-way (server → client) is exactly what we need for token streaming.
- Native browser support, no extra runtime, trivially proxied through nginx
  with `proxy_buffering off`.
- The endpoint is HTTP — auth, rate-limiting, audit middleware all keep
  working unchanged.

## Consequences

### Positive
- TTFT in the desktop UI is bound by the model's first-token latency, not by
  the polling interval (was 1 s).
- The streaming hook (`desktop/src/api/useAskStream.js`) auto-degrades to the
  polled task when streaming fails — no user-visible regression.
- Citations render immediately (via the `meta` event) so users can see *what*
  the answer is grounded in even before the words arrive.

### Negative
- Reverse proxies must disable response buffering for this route. The
  endpoint sets `X-Accel-Buffering: no` and `Cache-Control: no-cache` to nudge
  nginx, but configuration is environment-specific.
- The streaming path persists training data after the answer completes; if
  the client disconnects mid-stream, that persistence is skipped (not a
  regression — same behaviour as polled errors).
