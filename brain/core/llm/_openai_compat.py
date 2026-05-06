"""Shared helpers for OpenAI-compatible chat-completions providers."""

from __future__ import annotations

import json
from typing import AsyncIterator, Dict, List, Optional

import httpx

from core.config import settings
from core.logger import get_logger

log = get_logger("llm.openai_compat")


def build_messages(
    prompt: str, system: Optional[str], default_system: str
) -> List[Dict[str, str]]:
    return [
        {"role": "system", "content": system or default_system},
        {"role": "user", "content": prompt},
    ]


async def chat_complete(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: List[Dict[str, str]],
    json_mode: bool,
    extra_headers: Optional[Dict[str, str]] = None,
    temperature: float = 0.3,
) -> str:
    """Single-shot call to an OpenAI-compatible /chat/completions endpoint."""
    payload: Dict[str, object] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "temperature": temperature,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)
    async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
        r = await client.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json=payload,
        )
        r.raise_for_status()
        body = r.json()
    try:
        return body["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError) as e:
        log.warning(f"Unexpected /chat/completions response shape: {e}")
        return ""


async def chat_stream(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: List[Dict[str, str]],
    extra_headers: Optional[Dict[str, str]] = None,
    temperature: float = 0.3,
) -> AsyncIterator[str]:
    """Stream chunks from an OpenAI-compatible SSE chat-completion endpoint."""
    payload: Dict[str, object] = {
        "model": model,
        "messages": messages,
        "stream": True,
        "temperature": temperature,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    if extra_headers:
        headers.update(extra_headers)

    async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
        async with client.stream(
            "POST",
            f"{base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json=payload,
        ) as r:
            async for line in r.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[len("data:") :].strip()
                if not data or data == "[DONE]":
                    if data == "[DONE]":
                        return
                    continue
                try:
                    chunk = json.loads(data)
                except ValueError:
                    continue
                try:
                    delta = chunk["choices"][0].get("delta") or {}
                    content = delta.get("content")
                except (KeyError, IndexError, TypeError):
                    content = None
                if content:
                    yield content
