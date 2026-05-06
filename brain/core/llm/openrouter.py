"""OpenRouter provider — single key, hundreds of models, OpenAI-compatible."""

from __future__ import annotations

from typing import AsyncIterator, Optional

from core.config import settings

from . import _openai_compat as oc
from .openai import DEFAULT_SYSTEM


class OpenRouterProvider:
    name = "openrouter"
    base_url = "https://openrouter.ai/api/v1"

    def is_configured(self) -> bool:
        return bool(settings.OPENROUTER_API_KEY)

    def model_name(self) -> str:
        return settings.OPENROUTER_MODEL

    def _headers(self) -> dict:
        # OpenRouter recommends these for traffic attribution.
        return {
            "HTTP-Referer": "https://github.com/subairkprm/MagicLamp",
            "X-Title": "MagicLamp",
        }

    async def complete(
        self, prompt: str, system: Optional[str] = None, json_mode: bool = False
    ) -> str:
        return await oc.chat_complete(
            base_url=self.base_url,
            api_key=settings.OPENROUTER_API_KEY or "",
            model=self.model_name(),
            messages=oc.build_messages(prompt, system, DEFAULT_SYSTEM),
            json_mode=json_mode,
            extra_headers=self._headers(),
        )

    async def stream(
        self, prompt: str, system: Optional[str] = None
    ) -> AsyncIterator[str]:
        async for chunk in oc.chat_stream(
            base_url=self.base_url,
            api_key=settings.OPENROUTER_API_KEY or "",
            model=self.model_name(),
            messages=oc.build_messages(prompt, system, DEFAULT_SYSTEM),
            extra_headers=self._headers(),
        ):
            yield chunk
