"""Training data routes — stats, add, export."""

import json
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request

from core.auth import CurrentUser, get_current_user, require_admin
from core.config import settings
from core.database import DatabaseClient, get_database_client
from core.limiter import limiter
from core.validation import TrainingAddRequest

from .services import org_of

router = APIRouter(tags=["brain"])


@router.get("/training/stats")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def training_stats(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: DatabaseClient = Depends(get_database_client),
) -> Dict[str, Any]:
    tenant_id = org_of(user)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User has no tenant/org association")
    count = db.count(table="brain_training_data", tenant_id=tenant_id)
    return {"total_training_samples": count, "ready_for_export": count >= 100}


@router.post("/training/add")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def training_add(
    request: Request,
    body: TrainingAddRequest,
    user: CurrentUser = Depends(get_current_user),
    db: DatabaseClient = Depends(get_database_client),
) -> Dict[str, Any]:
    tenant_id = org_of(user)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User has no tenant/org association")

    db.insert(
        table="brain_training_data",
        data={
            "input": body.input_text,
            "output": body.output_text,
            "source": body.source,
            "quality": body.quality,
            "verified": body.source == "manual",
        },
        tenant_id=tenant_id,
    )
    count = db.count(table="brain_training_data", tenant_id=tenant_id)
    return {"ok": True, "total": count}


@router.post("/training/export")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def training_export(
    request: Request,
    min_quality: float = 0.8,
    admin: CurrentUser = Depends(require_admin),
    db: DatabaseClient = Depends(get_database_client),
) -> Dict[str, Any]:
    tenant_id = org_of(admin)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Admin has no tenant/org association")

    # NOTE: gte (>=) filtering is not directly supported by DatabaseClient yet,
    # so we filter in Python after pulling the ranked top-N.
    result = db.select(
        table="brain_training_data",
        columns="*",
        tenant_id=tenant_id,
        order_by="quality.desc",
        limit=10000,
    )
    data = [d for d in result.data if d.get("quality", 0) >= min_quality]

    jsonl_lines = []
    for d in data:
        jsonl_lines.append(
            json.dumps(
                {
                    "instruction": d["input"],
                    "input": "",
                    "output": d["output"],
                    "metadata": {
                        "source": d.get("source"),
                        "quality": d.get("quality"),
                        "ts": d.get("created_at"),
                    },
                },
                ensure_ascii=False,
            )
        )
    return {
        "samples": len(data),
        "jsonl": "\n".join(jsonl_lines),
        "modelfile": (
            f"FROM {settings.OLLAMA_MODEL}\n"
            'SYSTEM """You are MagicLamp AI Brain — UAE banking specialist."""\n'
            "PARAMETER temperature 0.3"
        ),
    }
