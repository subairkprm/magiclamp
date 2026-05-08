"""Tests for the Jais (UAE-hosted) LLM provider adapter."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "brain"))

os.environ.setdefault("DB_BACKEND", "sqlite")
os.environ.setdefault("JWT_SECRET", "test_secret_key_min_32_chars_long_xx")


def test_jais_is_registered_in_provider_registry():
    from core.llm import list_providers

    names = {row["name"] for row in list_providers()}
    assert "jais" in names, "Jais provider must be registered alongside the others"


def test_jais_get_provider_returns_jais_adapter():
    from core.llm import get_provider

    p = get_provider("jais")
    assert p.name == "jais"


def test_jais_is_configured_requires_key_and_base_url(monkeypatch):
    from core.config import settings
    from core.llm.jais import JaisProvider

    p = JaisProvider()

    monkeypatch.setattr(settings, "JAIS_API_KEY", None)
    monkeypatch.setattr(settings, "JAIS_BASE_URL", "https://api.jais.ai/v1")
    assert p.is_configured() is False

    monkeypatch.setattr(settings, "JAIS_API_KEY", "secret")
    monkeypatch.setattr(settings, "JAIS_BASE_URL", "")
    assert p.is_configured() is False

    monkeypatch.setattr(settings, "JAIS_API_KEY", "secret")
    monkeypatch.setattr(settings, "JAIS_BASE_URL", "https://api.jais.ai/v1")
    assert p.is_configured() is True


def test_jais_model_name_uses_settings(monkeypatch):
    from core.config import settings
    from core.llm.jais import JaisProvider

    monkeypatch.setattr(settings, "JAIS_MODEL", "jais-13b-chat")
    assert JaisProvider().model_name() == "jais-13b-chat"


@pytest.mark.asyncio
async def test_jais_complete_delegates_to_openai_compat(monkeypatch):
    """The Jais adapter should reuse the shared OpenAI-compatible helpers,
    forwarding the configured base URL, key, and model."""
    from core.config import settings
    from core.llm import jais as jais_mod

    captured: dict = {}

    async def _fake_chat_complete(**kwargs):
        captured.update(kwargs)
        return "marhaba"

    monkeypatch.setattr(settings, "JAIS_API_KEY", "test-key")
    monkeypatch.setattr(settings, "JAIS_BASE_URL", "https://api.jais.ai/v1")
    monkeypatch.setattr(settings, "JAIS_MODEL", "jais-30b-chat")
    monkeypatch.setattr(jais_mod.oc, "chat_complete", _fake_chat_complete)

    out = await jais_mod.JaisProvider().complete("hello")
    assert out == "marhaba"
    assert captured["base_url"] == "https://api.jais.ai/v1"
    assert captured["api_key"] == "test-key"
    assert captured["model"] == "jais-30b-chat"
    # The shared helper builds the messages list — check the user prompt is in it.
    msgs = captured["messages"]
    assert any(m["role"] == "user" and m["content"] == "hello" for m in msgs)


@pytest.mark.asyncio
async def test_jais_stream_delegates_to_openai_compat(monkeypatch):
    from core.config import settings
    from core.llm import jais as jais_mod

    async def _fake_chat_stream(**kwargs):
        for ch in ("a", "b", "c"):
            yield ch

    monkeypatch.setattr(settings, "JAIS_API_KEY", "test-key")
    monkeypatch.setattr(settings, "JAIS_BASE_URL", "https://api.jais.ai/v1")
    monkeypatch.setattr(jais_mod.oc, "chat_stream", _fake_chat_stream)

    chunks = []
    async for c in jais_mod.JaisProvider().stream("hi"):
        chunks.append(c)
    assert chunks == ["a", "b", "c"]
