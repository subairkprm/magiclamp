"""Jais provider adapter — UAE-hosted Arabic-first LLM, OpenAI-compatible.

Jais (Inception / G42, served on G42 Cloud or any compatible inference
gateway) is a strong choice for the "Sovereign Mode" deployment described in
ADR 0007: traffic stays inside a UAE region, and the model is tuned for
Arabic + Gulf-dialect synthesis.

The vendor exposes an OpenAI-compatible ``/chat/completions`` surface, so the
adapter just delegates to the shared :mod:`_openai_compat` helpers — keeping
this file consistent with the Groq / OpenRouter adapters.

Configuration (all via environment variables):

* ``JAIS_API_KEY``  — bearer token for the inference gateway.
* ``JAIS_BASE_URL`` — full base URL, e.g. ``https://api.jais.ai/v1``.
* ``JAIS_MODEL``    — model identifier, defaults to ``jais-30b-chat``.
"""

from __future__ import annotations

from typing import AsyncIterator, Optional

from core.config import settings

from . import _openai_compat as oc
from .openai import DEFAULT_SYSTEM


class JaisProvider:
    name = "jais"

    def is_configured(self) -> bool:
        return bool(settings.JAIS_API_KEY and settings.JAIS_BASE_URL)

    def model_name(self) -> str:
        return settings.JAIS_MODEL

    async def complete(
        self, prompt: str, system: Optional[str] = None, json_mode: bool = False
    ) -> str:
        return await oc.chat_complete(
            base_url=settings.JAIS_BASE_URL,
            api_key=settings.JAIS_API_KEY or "",
            model=self.model_name(),
            messages=oc.build_messages(prompt, system, DEFAULT_SYSTEM),
            json_mode=json_mode,
        )

    async def stream(
        self, prompt: str, system: Optional[str] = None
    ) -> AsyncIterator[str]:
        async for chunk in oc.chat_stream(
            base_url=settings.JAIS_BASE_URL,
            api_key=settings.JAIS_API_KEY or "",
            model=self.model_name(),
            messages=oc.build_messages(prompt, system, DEFAULT_SYSTEM),
        ):
            yield chunk
