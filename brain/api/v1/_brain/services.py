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

from fastapi import Depends

from core.auth import CurrentUser
from core.config import settings
from core.database import DatabaseClient, get_database_client
from core.llm import get_circuit, get_provider
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


# ── LLM caller (pluggable provider via core.llm) ──────────────────
async def llm(
    prompt: str,
    system: Optional[str] = None,
    json_mode: bool = False,
    provider: Optional[str] = None,
) -> str:
    """Single-shot call to the active LLM provider behind a circuit breaker.

    The provider is selected by ``core.llm.get_provider`` — typically the one
    the user has chosen in Settings (or ``LLM_PROVIDER`` env). Pass
    ``provider=`` to force a specific adapter for one call.
    """

    p = get_provider(provider)
    circuit = get_circuit(p.name)

    async def _call() -> str:
        return await p.complete(prompt=prompt, system=system, json_mode=json_mode)

    try:
        return await circuit.call(_call)
    except Exception as e:  # pragma: no cover - exercised via streaming path
        # SECURITY: do not echo the exception object to the caller — it can
        # contain stack-trace fragments or upstream URLs (CodeQL py/stack-trace-exposure).
        # Log full detail server-side and return a generic message to the user.
        log.error(f"LLM call failed: {e}")
        return "AI Engine unavailable. Please try again shortly."


async def llm_stream(
    prompt: str,
    system: Optional[str] = None,
    provider: Optional[str] = None,
):
    """Async generator yielding token chunks from the active LLM provider.

    Falls back to a single ``llm()`` call on transport errors so callers can
    always rely on at least one chunk being produced.
    """
    p = get_provider(provider)
    try:
        async for chunk in p.stream(prompt=prompt, system=system):
            if chunk:
                yield chunk
        return
    except Exception as e:
        log.warning(f"streaming LLM failed, falling back to non-stream: {e}")
        # Best-effort fallback so the SSE consumer still gets content.
        text = await llm(prompt, system=system, provider=provider)
        # Yield in small slices so the UI still feels responsive.
        for i in range(0, len(text), 64):
            yield text[i : i + 64]
            await asyncio.sleep(0)
