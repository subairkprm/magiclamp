"""Scheduler routes — list & manually trigger background jobs."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request

from core.auth import CurrentUser, get_current_user, require_admin
from core.config import settings
from core.limiter import limiter

router = APIRouter(tags=["brain"])


@router.get("/scheduler/jobs")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def scheduler_jobs(
    request: Request, user: CurrentUser = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    from scheduler import auto_scheduler  # local import keeps cold-start fast

    return auto_scheduler.get_jobs()


@router.post("/scheduler/run/{job_id}")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def run_job(
    request: Request, job_id: str, admin: CurrentUser = Depends(require_admin)
) -> Dict[str, Any]:
    from scheduler import auto_scheduler

    job_map = {
        "crm_snapshot": auto_scheduler.job_crm_snapshot,
        "score_leads": auto_scheduler.job_score_new_leads,
        "pattern_analysis": auto_scheduler.job_pattern_analysis,
        "self_analysis": auto_scheduler.job_self_analysis,
        "daily_briefing": auto_scheduler.job_daily_briefing,
        "memory_consolidation": auto_scheduler.job_memory_consolidation,
    }
    fn = job_map.get(job_id)
    if not fn:
        raise HTTPException(404, f"Job {job_id} not found")
    await fn()
    return {"ok": True, "job": job_id}
