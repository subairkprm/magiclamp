"""Groq provider adapter — OpenAI-compatible endpoint."""

from __future__ import annotations

from typing import AsyncIterator, Optional

from core.config import settings

from . import _openai_compat as oc
from .openai import DEFAULT_SYSTEM


class GroqProvider:
    name = "groq"
    base_url = "https://api.groq.com/openai/v1"

    def is_configured(self) -> bool:
        return bool(settings.GROQ_API_KEY)

    def model_name(self) -> str:
        return settings.GROQ_MODEL

    async def complete(
        self, prompt: str, system: Optional[str] = None, json_mode: bool = False
    ) -> str:
        return await oc.chat_complete(
            base_url=self.base_url,
            api_key=settings.GROQ_API_KEY or "",
            model=self.model_name(),
            messages=oc.build_messages(prompt, system, DEFAULT_SYSTEM),
            json_mode=json_mode,
        )

    async def stream(
        self, prompt: str, system: Optional[str] = None
    ) -> AsyncIterator[str]:
        async for chunk in oc.chat_stream(
            base_url=self.base_url,
            api_key=settings.GROQ_API_KEY or "",
            model=self.model_name(),
            messages=oc.build_messages(prompt, system, DEFAULT_SYSTEM),
        ):
            yield chunk
