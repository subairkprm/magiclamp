# Hermes & Ollama Usage

> **Local LLM inference on UAE VPS using Ollama. No cloud API calls for production.**

---

## Why Hermes 3?

MagicLamp uses **Hermes 3** (by Nous Research) as its primary reasoning model, served via **Ollama** on the UAE VPS.

Hermes 3 is chosen because:

- Strong instruction-following for complex, multi-step tasks
- Good Arabic and multilingual support
- Excellent function-calling and JSON-mode output
- Suitable for UAE banking and business domain reasoning
- Available in 8B parameter size — fits comfortably on a standard VPS with 16GB RAM
- Fully local — no data leaves the server

---

## Ollama Service

Ollama runs as a Docker service on port `11434` (internal).

| Setting | Value |
|---------|-------|
| Service name | `ollama` |
| Internal port | `11434` |
| Default model | `hermes3:8b` (frontier) |
| Fast model | `qwen2.5:3b` (or configurable) |
| Exposed externally | ❌ No — internal only |
| GPU required | Recommended but not mandatory |

---

## Model Configuration

Models are selected via the `OLLAMA_MODEL` environment variable:

```bash
# In .env
OLLAMA_MODEL=hermes3:8b       # Primary reasoning model
OLLAMA_FAST_MODEL=qwen2.5:3b  # Optional fast tier
OLLAMA_URL=http://ollama:11434 # Internal Docker network URL
```

---

## Pulling Models

```bash
# Pull Hermes 3 8B (primary)
docker exec ollama ollama pull hermes3:8b

# Pull qwen2.5 3B (fast tier)
docker exec ollama ollama pull qwen2.5:3b

# Or via Makefile
make pull-model MODEL=hermes3:8b
make pull-model MODEL=qwen2.5:3b

# List installed models
make list-models
```

---

## Provider Registration

Ollama is registered as an LLM provider in `brain/core/llm/__init__.py`:

```python
# Registered providers include:
# openai, anthropic, groq, openrouter, gemini, ollama, jais

provider = get_provider("ollama", model="hermes3:8b")
response = await provider.complete(messages=[...])
```

The Ollama adapter follows the same `LLMProvider` protocol as all other providers — it is interchangeable in any code that uses the protocol.

---

## Circuit Breaker

Each LLM provider, including Ollama, has a circuit breaker via `get_circuit()`:

```python
circuit = get_circuit("ollama")
if circuit.state == "open":
    # Ollama is unavailable — return 503
    raise ServiceUnavailableError("Ollama inference unavailable")
```

If Ollama becomes unavailable:
- The circuit opens after a configurable number of failures.
- The Brain API returns HTTP 503 with a structured error response.
- **No fallback to a cloud LLM** — the offline-first guarantee is preserved.
- An alert is sent via Telegram if configured.

---

## Supported Model Families

The following model families are tested and supported:

| Model | Size | Use Case |
|-------|------|----------|
| `hermes3:8b` | ~5GB | Primary reasoning, complex tasks |
| `qwen2.5:7b` | ~4GB | General purpose, good Arabic support |
| `qwen2.5:3b` | ~2GB | Fast tier, simple Q&A |
| `qwen2.5:14b` | ~8GB | Higher quality, requires more RAM |

Other Ollama-compatible models can be used but are not officially supported.

---

## Adding New LLM Providers

To add a new LLM provider (for non-production or experimental use):

1. Create an adapter in `brain/core/llm/` mirroring the structure of `groq.py` or `openrouter.py`.
2. Register it in the `_registry()` function in `brain/core/llm/__init__.py`.
3. Set `LLM_PROVIDER` environment variable or call `set_active_provider()`.

⚠️ **New providers that call cloud APIs must not be used for production inference** until the data residency policy is reviewed and the founder provides explicit approval.

---

## Performance Guidance

| RAM Available | Recommended Config |
|--------------|-------------------|
| 8GB | `qwen2.5:3b` only — single model |
| 16GB | `hermes3:8b` or `qwen2.5:7b` + `qwen2.5:3b` fast tier |
| 32GB+ | `qwen2.5:14b` frontier + `qwen2.5:3b` fast tier |

GPU acceleration significantly improves inference speed. Configure Ollama with CUDA or Metal as appropriate for the VPS hardware.

---

## Related Documents

- [`docs/architecture/MODEL-ROUTER.md`](MODEL-ROUTER.md)
- [`docs/architecture/OFFLINE-AGENT-ARCHITECTURE.md`](OFFLINE-AGENT-ARCHITECTURE.md)
- [`docs/security/UAE-DATA-RESIDENCY-POLICY.md`](../security/UAE-DATA-RESIDENCY-POLICY.md)
