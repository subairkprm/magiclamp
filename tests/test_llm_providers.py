"""Tests for the pluggable LLM provider layer (core.llm)."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "brain"))

os.environ.setdefault("DB_BACKEND", "sqlite")
os.environ.setdefault("JWT_SECRET", "test_secret_key_min_32_chars_long_xx")


def test_default_provider_is_openai(monkeypatch):
    from core.config import settings
    from core.llm import get_active_provider_name, set_active_provider

    monkeypatch.setattr(settings, "LLM_PROVIDER", "openai")
    set_active_provider(None)  # clear any override from earlier tests
    assert get_active_provider_name() == "openai"


def test_set_active_provider_overrides_env(monkeypatch):
    from core.config import settings
    from core.llm import get_active_provider_name, set_active_provider

    monkeypatch.setattr(settings, "LLM_PROVIDER", "openai")
    set_active_provider("groq")
    try:
        assert get_active_provider_name() == "groq"
    finally:
        set_active_provider(None)


def test_set_active_provider_rejects_unknown():
    from core.llm import set_active_provider

    with pytest.raises(ValueError):
        set_active_provider("not-a-real-provider")


def test_list_providers_reports_configuration_state(monkeypatch):
    from core.config import settings
    from core.llm import list_providers, set_active_provider

    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", None)
    set_active_provider(None)

    rows = {p["name"]: p for p in list_providers()}
    # Every adapter should be registered.
    for n in ("openai", "anthropic", "groq", "openrouter", "gemini", "ollama"):
        assert n in rows
    assert rows["openai"]["configured"] is True
    assert rows["anthropic"]["configured"] is False


def test_get_provider_falls_back_on_unknown_name():
    from core.llm import get_provider

    p = get_provider("does-not-exist")
    assert p.name == "openai"


@pytest.mark.asyncio
async def test_llm_caller_uses_active_provider(monkeypatch):
    """services.llm should delegate to the provider returned by get_provider."""
    from api.v1._brain import services
    from core.llm import set_active_provider

    class _StubProvider:
        name = "stub"
        model = "stub-model"

        def is_configured(self):
            return True

        def model_name(self):
            return self.model

        async def complete(self, prompt, system=None, json_mode=False):
            return f"echo:{prompt}"

        async def stream(self, prompt, system=None):
            for ch in ("a", "b", "c"):
                yield ch

    stub = _StubProvider()
    monkeypatch.setattr(services, "get_provider", lambda name=None: stub)

    out = await services.llm("hello")
    assert out == "echo:hello"

    # Streaming should yield the same chunks the provider produces.
    chunks = []
    async for c in services.llm_stream("hi"):
        chunks.append(c)
    assert chunks == ["a", "b", "c"]
    set_active_provider(None)


@pytest.mark.asyncio
async def test_llm_caller_returns_safe_message_on_failure(monkeypatch):
    """When the provider raises, services.llm must return a generic message
    instead of leaking the underlying exception."""
    from api.v1._brain import services
    from core.llm import get_circuit, set_active_provider

    class _BoomProvider:
        name = "boom"

        def model_name(self):
            return "x"

        def is_configured(self):
            return True

        async def complete(self, *a, **kw):
            raise RuntimeError("upstream blew up: secret-token-abc")

        async def stream(self, *a, **kw):
            raise RuntimeError("nope")
            yield  # pragma: no cover

    monkeypatch.setattr(services, "get_provider", lambda name=None: _BoomProvider())
    # Reset the circuit so prior tests don't leave it OPEN.
    cb = get_circuit("boom")
    cb._failure_count = 0
    cb._state = type(cb._state)("closed")

    text = await services.llm("anything")
    assert "AI Engine unavailable" in text
    assert "secret-token-abc" not in text  # exception message must not leak
    set_active_provider(None)
