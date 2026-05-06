# Streaming Ask — `POST /api/v1/brain/reason/ask/stream`

The streaming endpoint produces a Server-Sent Events stream for the Ask flow.
Use it from the desktop chat surface or any HTTP client that can read SSE.

## Request

```http
POST /api/v1/brain/reason/ask/stream HTTP/1.1
Authorization: Bearer <jwt>
Content-Type: application/json
Accept: text/event-stream

{ "question": "What is the best product for a salaried client at AED 15k?" }
```

Rate-limited via `RATE_LIMIT_AI`. Same auth model as `/brain/reason/ask`.

## Response

`Content-Type: text/event-stream`. Three event types are emitted in this order:

```
event: meta
data: {"retrieval_mode":"rag","citations":[{"id":1,"key":"product.salary_15k.recommendations"}]}

event: token
data: "The best product for"

event: token
data: " a salaried client at AED 15k"

event: token
data: " is the Premium account [#1]."

event: done
data: {}
```

* `meta` is sent **once**, before the first token, so the UI can render
  citation chips as soon as it knows where the answer is grounded.
* `token` payloads are JSON strings — that means they are safe to embed
  newlines (`\n`) and quotes; always run them through `JSON.parse` before
  appending to the buffer.
* `done` is the terminal marker. After it the server closes the connection.

## Behaviour notes

| Concern         | Behaviour |
|-----------------|-----------|
| Retrieval       | Identical to `POST /brain/reason/ask` (same RAG + recent-facts fallback) |
| Training data   | Persisted with `source: "api_ask_stream"` after the answer completes |
| Auth failures   | Returned as a normal HTTP 401 *before* the stream starts |
| Ollama failure  | Falls back to a single non-streaming call internally; the client still sees `token` events |
| Reverse proxies | Headers `Cache-Control: no-cache` and `X-Accel-Buffering: no` are set so nginx will not buffer; configure your proxy accordingly |

## Client example

The desktop client uses a small fetch-based hook,
[`desktop/src/api/useAskStream.js`](../../desktop/src/api/useAskStream.js),
because `EventSource` cannot send a request body or a Bearer header.
