"""Shared services and helpers for the Brain API sub-routers.

This module contains everything that used to be private helpers at the top of
``brain/api/v1/brain.py``: the in-process task store, the fact cache, the
LLM caller and the small DI helpers. Centralising them lets the per-feature
routers (``memory``, ``reason``, ``training``, ``changes``, ``scheduler``)
remain small and focused.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from time import time
from typing import Any, Dict, List, Optional

import httpx
from fastapi import Depends

from core.auth import CurrentUser
from core.circuit import ollama_circuit
from core.config import settings
from core.database import DatabaseClient, get_database_client
from core.logger import get_logger
from repositories import FactRepository

log = get_logger("api.brain.services")

# ── Caches & in-memory stores ─────────────────────────────────────
# NOTE: these are intentionally module-level singletons so that all sub-routers
# share state. A production deployment should swap the task store for Redis
# (see docs/adr/0001-brain-router-split.md).
_FACT_CACHE_TTL = 300  # seconds
_fact_cache: Dict[str, tuple[List[Dict[str, Any]], float]] = {}
_task_store: Dict[str, Dict[str, Any]] = {}


# ── Dependency providers ──────────────────────────────────────────
def get_fact_repository(
    db: DatabaseClient = Depends(get_database_client),
) -> FactRepository:
    """FastAPI dependency that constructs a :class:`FactRepository`."""
    return FactRepository(db)


def org_of(user: CurrentUser) -> Optional[str]:
    """Extract the tenant id from a user (currently aliased to ``org_id``)."""
    return user.org_id


# ── Task-store helpers ────────────────────────────────────────────
def create_task(task_type: str, user_id: str) -> str:
    """Register a new background task and return its id."""
    task_id = str(uuid.uuid4())
    _task_store[task_id] = {
        "task_id": task_id,
        "task_type": task_type,
        "status": "processing",
        "user_id": user_id,
        "created_at": datetime.utcnow().isoformat(),
        "result": None,
        "error": None,
    }
    return task_id


def update_task_success(task_id: str, result: Any) -> None:
    if task_id in _task_store:
        _task_store[task_id]["status"] = "completed"
        _task_store[task_id]["result"] = result
        _task_store[task_id]["completed_at"] = datetime.utcnow().isoformat()


def update_task_error(task_id: str, error: str) -> None:
    if task_id in _task_store:
        _task_store[task_id]["status"] = "failed"
        _task_store[task_id]["error"] = error
        _task_store[task_id]["completed_at"] = datetime.utcnow().isoformat()


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    return _task_store.get(task_id)


# ── Fact cache ────────────────────────────────────────────────────
def get_cached_facts(tenant_id: str, fact_repo: FactRepository) -> List[Dict[str, Any]]:
    """Return up to 20 recent facts for the tenant, with a 5-minute TTL cache."""
    cache_key = f"facts_{tenant_id}"
    now = time()
    cached = _fact_cache.get(cache_key)
    if cached is not None:
        facts, ts = cached
        if now - ts < _FACT_CACHE_TTL:
            return facts
    fact_models = fact_repo.get_recent_facts(tenant_id=tenant_id, limit=20)
    facts = [{"key": f.key, "value": f.value} for f in fact_models]
    _fact_cache[cache_key] = (facts, now)
    return facts


# ── LLM caller (Ollama via circuit breaker) ───────────────────────
async def llm(
    prompt: str,
    system: Optional[str] = None,
    json_mode: bool = False,
) -> str:
    """Single-shot call to the configured Ollama model behind a circuit breaker."""

    async def _call() -> str:
        payload: Dict[str, Any] = {
            "model": settings.OLLAMA_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": system
                    or "You are MagicLamp AI Brain — a UAE banking CRM specialist.",
                },
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {"temperature": 0.3},
        }
        if json_mode:
            payload["format"] = "json"
        async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT) as client:
            r = await client.post(f"{settings.OLLAMA_URL}/api/chat", json=payload)
            return r.json()["message"]["content"]

    try:
        return await ollama_circuit.call(_call)
    except Exception as e:  # pragma: no cover - exercised via streaming path
        # SECURITY: do not echo the exception object to the caller — it can
        # contain stack-trace fragments or upstream URLs (CodeQL py/stack-trace-exposure).
        # Log full detail server-side and return a generic message to the user.
        log.error(f"LLM call failed: {e}")
        return "AI Engine unavailable. Please try again shortly."


async def llm_stream(prompt: str, system: Optional[str] = None):
    """Async generator yielding token chunks from Ollama's streaming chat API.

    Falls back to a single ``llm()`` call on transport errors so callers can
    always rely on at least one chunk being produced.
    """
    payload: Dict[str, Any] = {
        "model": settings.OLLAMA_MODEL,
        "messages": [
            {
                "role": "system",
                "content": system
                or "You are MagicLamp AI Brain — a UAE banking CRM specialist.",
            },
            {"role": "user", "content": prompt},
        ],
        "stream": True,
        "options": {"temperature": 0.3},
    }
    try:
        async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT) as client:
            async with client.stream(
                "POST", f"{settings.OLLAMA_URL}/api/chat", json=payload
            ) as r:
                async for line in r.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        import json as _json

                        chunk = _json.loads(line)
                    except ValueError:
                        continue
                    msg = (chunk.get("message") or {}).get("content")
                    if msg:
                        yield msg
                    if chunk.get("done"):
                        return
    except Exception as e:
        log.warning(f"streaming LLM failed, falling back to non-stream: {e}")
        # Best-effort fallback so the SSE consumer still gets content.
        text = await llm(prompt, system=system)
        # Yield in small slices so the UI still feels responsive.
        for i in range(0, len(text), 64):
            yield text[i : i + 64]
            await asyncio.sleep(0)
