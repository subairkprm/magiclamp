"""Ollama provider adapter.

Preserves the exact request shape used by the previous
``brain.api.v1._brain.services.llm`` / ``llm_stream`` helpers so that VPS
deployments (and the existing test suite) keep working bit-for-bit when
``LLM_PROVIDER=ollama``.
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Dict, Optional

import httpx

from core.config import settings
from core.logger import get_logger

from .openai import DEFAULT_SYSTEM

log = get_logger("llm.ollama")


def _payload(prompt: str, system: Optional[str], stream: bool, json_mode: bool) -> Dict[str, Any]:
    p: Dict[str, Any] = {
        "model": settings.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system or DEFAULT_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "stream": stream,
        "options": {"temperature": 0.3},
    }
    if json_mode:
        p["format"] = "json"
    return p


class OllamaProvider:
    name = "ollama"

    def is_configured(self) -> bool:
        # Ollama is reachable iff a URL is configured; we don't probe at
        # boot time because that would couple every deploy to the network.
        return bool(settings.OLLAMA_URL)

    def model_name(self) -> str:
        return settings.OLLAMA_MODEL

    async def complete(
        self, prompt: str, system: Optional[str] = None, json_mode: bool = False
    ) -> str:
        payload = _payload(prompt, system, stream=False, json_mode=json_mode)
        async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT) as client:
            r = await client.post(f"{settings.OLLAMA_URL}/api/chat", json=payload)
            return r.json()["message"]["content"]

    async def stream(
        self, prompt: str, system: Optional[str] = None
    ) -> AsyncIterator[str]:
        payload = _payload(prompt, system, stream=True, json_mode=False)
        async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT) as client:
            async with client.stream(
                "POST", f"{settings.OLLAMA_URL}/api/chat", json=payload
            ) as r:
                async for line in r.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                    except ValueError:
                        continue
                    msg = (chunk.get("message") or {}).get("content")
                    if msg:
                        yield msg
                    if chunk.get("done"):
                        return
