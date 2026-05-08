"""
Pluggable LLM provider layer.

This package decouples the rest of MagicLamp from any specific LLM vendor.
Callers go through :func:`get_provider` and receive an object that satisfies
the :class:`LLMProvider` protocol — they no longer know (or care) whether the
backend is OpenAI, Anthropic, Groq, OpenRouter, Gemini, or a local Ollama
instance.

The active provider is selected — in order of priority — by:

1. an explicit ``name`` argument passed to :func:`get_provider`
   (used by per-request override / "user choice");
2. the ``LLM_PROVIDER`` environment variable (default: ``"openai"``).

A separate :class:`CircuitBreaker` is maintained per provider so that a
flapping vendor can't take the rest down with it.
"""

from __future__ import annotations

from typing import AsyncIterator, Dict, List, Optional, Protocol, runtime_checkable

from core.circuit import CircuitBreaker
from core.config import settings
from core.logger import get_logger

log = get_logger("llm")


@runtime_checkable
class LLMProvider(Protocol):
    """Minimal contract every provider adapter must satisfy."""

    name: str

    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        json_mode: bool = False,
    ) -> str:
        """Return a single, full completion for ``prompt``."""

    async def stream(
        self,
        prompt: str,
        system: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Yield completion text in chunks (for SSE token streaming)."""

    def is_configured(self) -> bool:
        """Return True iff the provider has all the credentials it needs."""

    def model_name(self) -> str:
        """Return the model identifier currently in use."""


# ── Built-in registry ───────────────────────────────────────────────
def _registry() -> Dict[str, "LLMProvider"]:
    """Lazily build the registry so adapter modules import only when needed."""
    from .openai import OpenAIProvider
    from .anthropic import AnthropicProvider
    from .groq import GroqProvider
    from .openrouter import OpenRouterProvider
    from .gemini import GeminiProvider
    from .ollama import OllamaProvider
    from .jais import JaisProvider

    return {
        "openai": OpenAIProvider(),
        "anthropic": AnthropicProvider(),
        "groq": GroqProvider(),
        "openrouter": OpenRouterProvider(),
        "gemini": GeminiProvider(),
        "ollama": OllamaProvider(),
        "jais": JaisProvider(),
    }


# Cached registry — providers are cheap (no I/O at construction time).
_PROVIDERS: Optional[Dict[str, "LLMProvider"]] = None
_CIRCUITS: Dict[str, CircuitBreaker] = {}


def _all_providers() -> Dict[str, "LLMProvider"]:
    global _PROVIDERS
    if _PROVIDERS is None:
        _PROVIDERS = _registry()
    return _PROVIDERS


def list_providers() -> List[Dict[str, object]]:
    """Return a UI-friendly description of every known provider."""
    out: List[Dict[str, object]] = []
    for name, p in _all_providers().items():
        out.append(
            {
                "name": name,
                "configured": p.is_configured(),
                "model": p.model_name(),
                "active": name == get_active_provider_name(),
            }
        )
    return out


def get_circuit(name: str) -> CircuitBreaker:
    """Return (creating on first use) a circuit breaker for ``name``."""
    cb = _CIRCUITS.get(name)
    if cb is None:
        cb = CircuitBreaker(f"llm:{name}", failure_threshold=3, recovery_timeout=20)
        _CIRCUITS[name] = cb
    return cb


# ── Active-provider selection ───────────────────────────────────────
# A simple in-process override that admin endpoints can mutate at runtime.
_active_override: Optional[str] = None


def set_active_provider(name: Optional[str]) -> None:
    """Override the default provider for the lifetime of the process.

    Pass ``None`` to clear the override and fall back to ``LLM_PROVIDER``.
    """
    global _active_override
    if name is not None:
        name = name.lower()
        if name not in _all_providers():
            raise ValueError(f"Unknown LLM provider: {name!r}")
    _active_override = name


def get_active_provider_name() -> str:
    """Return the name of the currently selected provider."""
    return (_active_override or settings.LLM_PROVIDER or "openai").lower()


def get_provider(name: Optional[str] = None) -> "LLMProvider":
    """Return the provider adapter for ``name`` (or the active default)."""
    selected = (name or get_active_provider_name()).lower()
    providers = _all_providers()
    if selected not in providers:
        log.warning(
            f"Unknown LLM provider {selected!r}; falling back to openai"
        )
        selected = "openai"
    return providers[selected]


__all__ = [
    "LLMProvider",
    "get_provider",
    "list_providers",
    "set_active_provider",
    "get_active_provider_name",
    "get_circuit",
]
