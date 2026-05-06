"""Google Gemini provider adapter (uses the v1beta REST API)."""

from __future__ import annotations

import json
from typing import AsyncIterator, Optional

import httpx

from core.config import settings
from core.logger import get_logger

from .openai import DEFAULT_SYSTEM

log = get_logger("llm.gemini")


class GeminiProvider:
    name = "gemini"
    base_url = "https://generativelanguage.googleapis.com/v1beta"

    def is_configured(self) -> bool:
        return bool(settings.GOOGLE_API_KEY)

    def model_name(self) -> str:
        return settings.GEMINI_MODEL

    def _payload(self, prompt: str, system: Optional[str]) -> dict:
        return {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "systemInstruction": {"parts": [{"text": system or DEFAULT_SYSTEM}]},
            "generationConfig": {"temperature": 0.3},
        }

    async def complete(
        self, prompt: str, system: Optional[str] = None, json_mode: bool = False
    ) -> str:
        payload = self._payload(prompt, system)
        if json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"
        url = (
            f"{self.base_url}/models/{self.model_name()}:generateContent"
            f"?key={settings.GOOGLE_API_KEY or ''}"
        )
        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            body = r.json()
        try:
            parts = body["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts)
        except (KeyError, IndexError, TypeError) as e:
            log.warning(f"Unexpected Gemini response shape: {e}")
            return ""

    async def stream(
        self, prompt: str, system: Optional[str] = None
    ) -> AsyncIterator[str]:
        payload = self._payload(prompt, system)
        url = (
            f"{self.base_url}/models/{self.model_name()}:streamGenerateContent"
            f"?alt=sse&key={settings.GOOGLE_API_KEY or ''}"
        )
        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
            async with client.stream("POST", url, json=payload) as r:
                async for line in r.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:") :].strip()
                    if not data:
                        continue
                    try:
                        chunk = json.loads(data)
                    except ValueError:
                        continue
                    try:
                        parts = chunk["candidates"][0]["content"]["parts"]
                        text = "".join(p.get("text", "") for p in parts)
                    except (KeyError, IndexError, TypeError):
                        text = ""
                    if text:
                        yield text
