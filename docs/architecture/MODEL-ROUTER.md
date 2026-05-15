# Model Router

> **Two-tier LLM routing for speed, quality, and cost control.**

---

## Purpose

MagicLamp uses a two-tier LLM router (`brain/core/llm_router.py`) to:

1. Route simple, short, low-complexity requests to a **fast model** (lower cost, faster response).
2. Escalate complex, multi-step, long, or code-heavy requests to a **frontier model** (higher quality).
3. Ensure cost and latency are controlled — the fast tier handles the majority of requests.

---

## Router Architecture

```
Incoming Request
      │
      ▼
classify_complexity()
  - message length
  - multi-step keywords (EN + AR)
  - json_mode flag
  - code block detection
  - Arabic ↔ Latin code-switching
  - long conversation history
      │
  ┌───┴────┐
  │        │
SIMPLE   COMPLEX
  │        │
  ▼        ▼
Fast    Frontier
Model   Model
```

### TwoTierRouter Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `fast` | configurable | Fast/cheap model (e.g. `qwen2.5:3b` via Ollama) |
| `frontier` | configurable | High-quality model (e.g. `hermes3:8b` via Ollama) |
| `threshold` | `3` | Complexity score at or above which frontier is used |
| `escalate_sentinel` | `"ESCALATE"` | Sentinel string the fast model can return to force frontier escalation |

---

## Complexity Classifier

`classify_complexity(message, history, **kwargs)` returns an integer complexity score based on heuristics:

| Signal | Score Contribution |
|--------|-------------------|
| Message length > 500 chars | +2 |
| Message length > 1500 chars | +1 (additional) |
| Multi-step keywords detected | +2 per keyword group |
| `json_mode=True` in kwargs | +1 |
| Code blocks present (``` fences) | +2 |
| Arabic ↔ Latin code-switching | +1 |
| Long conversation history (> 10 turns) | +1 |

If total score ≥ `threshold`, the frontier model is used.

---

## Escalation Sentinel

The fast model can signal that a request is beyond its capability by returning a response that starts with the `escalate_sentinel` string (default: `"ESCALATE"`).

- **`complete()` honours the sentinel** — if the fast model returns `ESCALATE`, the router automatically re-submits the request to the frontier model.
- **`stream()` does NOT honour the sentinel** — streaming responses cannot be unsent. Use non-streaming for flows where escalation may be needed.

---

## Usage

```python
from brain.core.llm_router import TwoTierRouter
from brain.core.llm import get_provider

fast = get_provider("ollama", model="qwen2.5:3b")
frontier = get_provider("ollama", model="hermes3:8b")

router = TwoTierRouter(fast=fast, frontier=frontier, threshold=3)

# Non-streaming (supports escalation)
response = await router.complete(messages=[...])

# Streaming (no escalation support)
async for chunk in router.stream(messages=[...]):
    ...

# Stats
stats = router.stats()
# {"fast": {"calls": 47, "tokens": 12340}, "frontier": {"calls": 8, "tokens": 9870}}
```

---

## UAE / Offline Constraint

Both the fast and frontier models in MVP **must be local Ollama models**. Cloud LLM APIs (OpenAI, Anthropic, Gemini, Groq, etc.) are **not permitted** for production inference.

See [`docs/security/UAE-DATA-RESIDENCY-POLICY.md`](../security/UAE-DATA-RESIDENCY-POLICY.md) for the full policy.

---

## Future: Hybrid Routing

In future phases, a conditional hybrid tier may be introduced where:
- Approved, non-sensitive business intelligence queries may optionally use a cloud model.
- This will require explicit founder sign-off and a separate data classification framework.
- The UAE data residency policy takes precedence. No production customer data may be sent to a cloud model.

---

## Related Documents

- [`docs/architecture/HERMES-OLLAMA-USAGE.md`](HERMES-OLLAMA-USAGE.md)
- [`docs/architecture/OFFLINE-AGENT-ARCHITECTURE.md`](OFFLINE-AGENT-ARCHITECTURE.md)
- [`docs/security/UAE-DATA-RESIDENCY-POLICY.md`](../security/UAE-DATA-RESIDENCY-POLICY.md)
