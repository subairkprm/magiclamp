"""Memory routes — remember, recall, observe, events, stats."""

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from core.auth import CurrentUser, get_current_user
from core.config import settings
from core.database import DatabaseClient, get_database_client
from core.limiter import limiter
from core.validation import ObserveRequest, RememberRequest, sanitize_string
from repositories import FactRepository

from .services import get_fact_repository, org_of

router = APIRouter(tags=["brain"])


@router.post("/memory/remember")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def remember(
    request: Request,
    body: RememberRequest,
    user: CurrentUser = Depends(get_current_user),
    fact_repo: FactRepository = Depends(get_fact_repository),
) -> Dict[str, Any]:
    tenant_id = org_of(user)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User has no tenant/org association")

    fact_repo.save_fact(
        key=body.key,
        value=json.dumps(body.value) if not isinstance(body.value, str) else body.value,
        tenant_id=tenant_id,
        source=body.source,
        confidence=body.confidence,
    )
    return {"ok": True, "key": body.key}


@router.get("/memory/recall/{key}")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def recall(
    request: Request,
    key: str,
    user: CurrentUser = Depends(get_current_user),
    fact_repo: FactRepository = Depends(get_fact_repository),
) -> Dict[str, Any]:
    key = sanitize_string(key, max_length=100)
    tenant_id = org_of(user)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User has no tenant/org association")

    fact = fact_repo.get_by_key(key=key, tenant_id=tenant_id)
    if fact:
        try:
            val = json.loads(fact.value) if isinstance(fact.value, str) else fact.value
        except Exception:
            val = fact.value
        return {"key": key, "value": val, "found": True}
    return {"key": key, "value": None, "found": False}


@router.get("/memory/facts")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def all_facts(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    fact_repo: FactRepository = Depends(get_fact_repository),
) -> Dict[str, str]:
    tenant_id = org_of(user)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User has no tenant/org association")
    facts = fact_repo.get_all(tenant_id=tenant_id)
    return {f.key: str(f.value) for f in facts}


@router.post("/memory/observe")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def observe(
    request: Request,
    body: ObserveRequest,
    user: CurrentUser = Depends(get_current_user),
    db: DatabaseClient = Depends(get_database_client),
) -> Dict[str, bool]:
    tenant_id = org_of(user)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User has no tenant/org association")

    db.insert(
        table="brain_events",
        data={
            "event_type": body.event_type,
            "category": body.category,
            "data": {"text": body.text, **(body.metadata or {})},
            "summary": body.text[:200],
            "importance": body.importance,
        },
        tenant_id=tenant_id,
    )
    return {"ok": True}


@router.get("/memory/events")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def events(
    request: Request,
    category: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 50,
    user: CurrentUser = Depends(get_current_user),
    db: DatabaseClient = Depends(get_database_client),
) -> List[Dict[str, Any]]:
    tenant_id = org_of(user)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User has no tenant/org association")

    filters: Dict[str, Any] = {}
    if category:
        filters["category"] = category
    if event_type:
        filters["event_type"] = event_type

    result = db.select(
        table="brain_events",
        columns="*",
        tenant_id=tenant_id,
        filters=filters if filters else None,
        order_by="created_at.desc",
        limit=limit,
    )
    return result.data


@router.get("/memory/stats")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def memory_stats(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    fact_repo: FactRepository = Depends(get_fact_repository),
    db: DatabaseClient = Depends(get_database_client),
) -> Dict[str, int]:
    tenant_id = org_of(user)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User has no tenant/org association")

    return {
        "facts": fact_repo.count(tenant_id=tenant_id),
        "events": db.count(table="brain_events", tenant_id=tenant_id),
        "training_samples": db.count(table="brain_training_data", tenant_id=tenant_id),
        "decisions": db.count(table="brain_decisions", tenant_id=tenant_id),
    }
