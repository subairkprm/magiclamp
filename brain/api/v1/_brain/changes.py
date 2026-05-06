"""Change-log routes — record_change & change_history."""

import json
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request

from core.auth import CurrentUser, get_current_user
from core.config import settings
from core.database import DatabaseClient, get_database_client
from core.limiter import limiter
from core.validation import RecordChangeRequest
from repositories import FactRepository

from .services import get_fact_repository, org_of

router = APIRouter(tags=["brain"])


@router.post("/changes/record")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def record_change(
    request: Request,
    body: RecordChangeRequest,
    user: CurrentUser = Depends(get_current_user),
    fact_repo: FactRepository = Depends(get_fact_repository),
    db: DatabaseClient = Depends(get_database_client),
) -> Dict[str, Any]:
    tenant_id = org_of(user)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User has no tenant/org association")

    what = body.what
    text = f"CHANGE: {what} changed from '{body.from_val}' to '{body.to_val}'. Reason: {body.reason}"

    db.insert(
        table="brain_events",
        data={
            "event_type": "change_recorded",
            "category": "changes",
            "data": body.dict(),
            "summary": text[:200],
            "importance": 3,
        },
        tenant_id=tenant_id,
    )

    fact_repo.save_fact(
        key=f"change.{what}.latest",
        value=json.dumps(
            {
                "from": body.from_val,
                "to": body.to_val,
                "reason": body.reason,
                "ts": datetime.utcnow().isoformat(),
            }
        ),
        tenant_id=tenant_id,
        source="change_record",
    )
    return {"ok": True, "remembered": text[:100]}


@router.get("/changes/history")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def change_history(
    request: Request,
    limit: int = 50,
    user: CurrentUser = Depends(get_current_user),
    db: DatabaseClient = Depends(get_database_client),
) -> List[Dict[str, Any]]:
    tenant_id = org_of(user)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User has no tenant/org association")

    result = db.select(
        table="brain_events",
        columns="*",
        tenant_id=tenant_id,
        filters={"category": "changes"},
        order_by="created_at.desc",
        limit=limit,
    )
    return result.data
