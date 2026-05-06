"""Anthropic Claude provider adapter."""

from __future__ import annotations

import json
from typing import AsyncIterator, Optional

import httpx

from core.config import settings
from core.logger import get_logger

from .openai import DEFAULT_SYSTEM

log = get_logger("llm.anthropic")


class AnthropicProvider:
    name = "anthropic"
    base_url = "https://api.anthropic.com/v1"
    api_version = "2023-06-01"

    def is_configured(self) -> bool:
        return bool(settings.ANTHROPIC_API_KEY)

    def model_name(self) -> str:
        return settings.ANTHROPIC_MODEL

    def _headers(self) -> dict:
        return {
            "x-api-key": settings.ANTHROPIC_API_KEY or "",
            "anthropic-version": self.api_version,
            "content-type": "application/json",
        }

    async def complete(
        self, prompt: str, system: Optional[str] = None, json_mode: bool = False
    ) -> str:
        payload = {
            "model": self.model_name(),
            "max_tokens": 1024,
            "system": system or DEFAULT_SYSTEM,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
        }
        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
            r = await client.post(
                f"{self.base_url}/messages", headers=self._headers(), json=payload
            )
            r.raise_for_status()
            body = r.json()
        try:
            return "".join(
                block.get("text", "")
                for block in body.get("content", [])
                if block.get("type") == "text"
            )
        except (AttributeError, TypeError) as e:
            log.warning(f"Unexpected Anthropic response shape: {e}")
            return ""

    async def stream(
        self, prompt: str, system: Optional[str] = None
    ) -> AsyncIterator[str]:
        payload = {
            "model": self.model_name(),
            "max_tokens": 1024,
            "system": system or DEFAULT_SYSTEM,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/messages",
                headers=self._headers(),
                json=payload,
            ) as r:
                async for line in r.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:") :].strip()
                    if not data:
                        continue
                    try:
                        evt = json.loads(data)
                    except ValueError:
                        continue
                    if evt.get("type") == "content_block_delta":
                        delta = (evt.get("delta") or {}).get("text")
                        if delta:
                            yield delta
                    elif evt.get("type") == "message_stop":
                        return
