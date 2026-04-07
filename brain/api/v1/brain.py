"""MagicLamp API v1 — Brain Routes (memory, reasoning, training, scheduler)"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Any, Optional, Dict, List
from supabase import create_client
from core.config import settings
from core.auth import get_current_user, require_admin, CurrentUser
from core.circuit import ollama_circuit
from core.logger import get_logger
from core.validation import (
    RememberRequest, ObserveRequest, ReasonLeadRequest,
    ReasonAskRequest, ReasonDecideRequest, TrainingAddRequest,
    RecordChangeRequest, sanitize_string
)
import httpx, json, asyncio
from datetime import datetime
from functools import lru_cache
from time import time

log = get_logger("api.brain")
router = APIRouter(prefix="/brain", tags=["brain"])
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

# Import limiter from main
from main import limiter

# Cache for fact loading with TTL
_fact_cache: Dict[str, tuple[List[Dict], float]] = {}
_FACT_CACHE_TTL = 300  # 5 minutes

# ── HELPERS ───────────────────────────────────
async def _llm(prompt: str, system: str = None, json_mode: bool = False) -> str:
    async def _call():
        payload = {
            "model": settings.OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": system or "You are MagicLamp AI Brain — a UAE banking CRM specialist."},
                {"role": "user",   "content": prompt}
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
    except Exception as e:
        return f"AI Engine unavailable: {e}"

def _org(user: CurrentUser) -> Optional[str]:
    return user.org_id

def _get_cached_facts(cache_key: str = "global") -> List[Dict]:
    """Load facts with simple time-based cache to avoid hitting DB on every request."""
    now = time()
    if cache_key in _fact_cache:
        facts, timestamp = _fact_cache[cache_key]
        if now - timestamp < _FACT_CACHE_TTL:
            return facts
    # Cache miss or expired - fetch from DB
    facts = supabase.table("brain_facts").select("key,value").limit(20).execute().data
    _fact_cache[cache_key] = (facts, now)
    return facts

# ── MEMORY ────────────────────────────────────
@router.post("/memory/remember")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def remember(request: Request, body: RememberRequest, user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    supabase.table("brain_facts").upsert({
        "org_id":     _org(user),
        "key":        body.key,
        "value":      json.dumps(body.value) if not isinstance(body.value, str) else body.value,
        "source":     body.source,
        "confidence": body.confidence,
        "updated_at": datetime.utcnow().isoformat(),
    }, on_conflict="org_id,key").execute()
    return {"ok": True, "key": body.key}

@router.get("/memory/recall/{key}")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def recall(request: Request, key: str, user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    # Sanitize key to prevent injection
    key = sanitize_string(key, max_length=100)
    result = supabase.table("brain_facts").select("*")\
        .eq("key", key).execute()
    if result.data:
        try:
            val = json.loads(result.data[0]["value"])
        except:
            val = result.data[0]["value"]
        return {"key": key, "value": val, "found": True}
    return {"key": key, "value": None, "found": False}

@router.get("/memory/facts")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def all_facts(request: Request, user: CurrentUser = Depends(get_current_user)) -> Dict[str, str]:
    result = supabase.table("brain_facts").select("key,value,source,confidence").execute()
    return {r["key"]: r["value"] for r in result.data}

@router.post("/memory/observe")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def observe(request: Request, body: ObserveRequest, user: CurrentUser = Depends(get_current_user)) -> Dict[str, bool]:
    supabase.table("brain_events").insert({
        "org_id":     _org(user),
        "event_type": body.event_type,
        "category":   body.category,
        "data":       {"text": body.text, **(body.metadata or {})},
        "summary":    body.text[:200],
        "importance": body.importance,
    }).execute()
    return {"ok": True}

@router.get("/memory/events")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def events(request: Request, category: str = None, event_type: str = None, limit: int = 50,
                 user: CurrentUser = Depends(get_current_user)) -> List[Dict[str, Any]]:
    q = supabase.table("brain_events").select("*").order("created_at", desc=True).limit(limit)
    if category:
        q = q.eq("category", category)
    if event_type:
        q = q.eq("event_type", event_type)
    return q.execute().data

@router.get("/memory/stats")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def memory_stats(request: Request, user: CurrentUser = Depends(get_current_user)) -> Dict[str, int]:
    facts     = supabase.table("brain_facts").select("id", count="exact").execute()
    events    = supabase.table("brain_events").select("id", count="exact").execute()
    training  = supabase.table("brain_training_data").select("id", count="exact").execute()
    decisions = supabase.table("brain_decisions").select("id", count="exact").execute()
    return {
        "facts":            facts.count or 0,
        "events":           events.count or 0,
        "training_samples": training.count or 0,
        "decisions":        decisions.count or 0,
    }

# ── REASONING ─────────────────────────────────
@router.post("/reason/lead")
@limiter.limit(settings.RATE_LIMIT_AI)
async def reason_lead(request: Request, body: ReasonLeadRequest, user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    lead = body.lead
    prompt = f"""Analyse this UAE banking lead and return JSON:
{{"score":0-100,"priority":"low|medium|high|urgent","eligibility":"likely_eligible|borderline|likely_rejected",
"key_risks":[],"opportunities":[],"recommended_products":[],"next_action":"","reasoning":""}}

Lead: {json.dumps(lead)}"""
    result_str = await _llm(prompt, json_mode=True)
    try:
        result = json.loads(result_str)
    except:
        result = {"score": 50, "priority": "medium", "reasoning": result_str[:200]}

    # Auto-store as training data
    supabase.table("brain_training_data").insert({
        "org_id": _org(user),
        "input":  f"Analyse lead: {json.dumps(lead)[:300]}",
        "output": json.dumps(result)[:500],
        "source": "lead_analysis",
        "quality": 1.5,
    }).execute()
    return result

@router.post("/reason/ask")
@limiter.limit(settings.RATE_LIMIT_AI)
async def reason_ask(request: Request, body: ReasonAskRequest, user: CurrentUser = Depends(get_current_user)) -> Dict[str, str]:
    question = body.question
    # Load relevant facts for context with caching
    facts = _get_cached_facts()
    fact_ctx = "\n".join([f"- {f['key']}: {str(f['value'])[:80]}" for f in facts])
    prompt = f"Answer using your knowledge and these facts:\n{fact_ctx}\n\nQuestion: {question}"
    answer = await _llm(prompt)
    supabase.table("brain_training_data").insert({
        "org_id": _org(user),
        "input":  question,
        "output": answer[:500],
        "source": "api_ask",
        "quality": 1.0,
    }).execute()
    return {"question": question, "answer": answer}

@router.post("/reason/decide")
@limiter.limit(settings.RATE_LIMIT_AI)
async def reason_decide(request: Request, body: ReasonDecideRequest, user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    situation = body.situation
    options   = body.options or []
    opts_text = f"\nOptions: {', '.join(options)}" if options else ""
    prompt = f"""Make a decision and return JSON:
{{"decision":"","reasoning":"","confidence":0.0,"risks":[],"expected_outcome":"","follow_up_actions":[]}}
Situation: {situation}{opts_text}"""
    result_str = await _llm(prompt, json_mode=True)
    try:
        result = json.loads(result_str)
    except:
        result = {"decision": "manual_review", "reasoning": result_str[:200]}
    supabase.table("brain_decisions").insert({
        "org_id":    _org(user),
        "trigger":   situation[:300],
        "reasoning": result.get("reasoning", "")[:500],
        "action":    result.get("decision", "")[:200],
        "confidence": result.get("confidence", 0.5),
    }).execute()
    return result

@router.get("/reason/self-analyse")
@limiter.limit(settings.RATE_LIMIT_AI)
async def self_analyse(request: Request, user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    stats = (await memory_stats(request, user))
    decisions = supabase.table("brain_decisions").select("*").order("created_at", desc=True).limit(5).execute().data
    prompt = f"""Review brain state and return JSON:
{{"knowledge_summary":"","gaps":[],"pending_actions":[],"health_score":0-100,"alerts":[]}}
Stats: {json.dumps(stats)}
Recent decisions: {json.dumps(decisions, default=str)[:500]}"""
    result_str = await _llm(prompt, json_mode=True)
    try:
        result = json.loads(result_str)
    except:
        result = {"health_score": 75, "knowledge_summary": "Brain operational"}
    supabase.table("brain_analyses").insert({
        "org_id":  _org(user),
        "subject": "self_analysis",
        "analysis": json.dumps(result),
        "metrics": stats,
    }).execute()
    return result

# ── TRAINING ──────────────────────────────────
@router.get("/training/stats")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def training_stats(request: Request, user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    result = supabase.table("brain_training_data").select("id", count="exact").execute()
    count = result.count or 0
    return {"total_training_samples": count, "ready_for_export": count >= 100}

@router.post("/training/add")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def training_add(request: Request, body: TrainingAddRequest, user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    supabase.table("brain_training_data").insert({
        "org_id":  _org(user),
        "input":   body.input_text,
        "output":  body.output_text,
        "source":  body.source,
        "quality": body.quality,
        "verified": body.source == "manual",
    }).execute()
    count = supabase.table("brain_training_data").select("id", count="exact").execute().count or 0
    return {"ok": True, "total": count}

@router.post("/training/export")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def training_export(request: Request, min_quality: float = 0.8, admin: CurrentUser = Depends(require_admin)) -> Dict[str, Any]:
    data = supabase.table("brain_training_data").select("*")\
        .gte("quality", min_quality).order("quality", desc=True).limit(10000).execute().data
    jsonl_lines = []
    for d in data:
        ctx = d.get("context") or {}
        jsonl_lines.append(json.dumps({
            "instruction": d["input"],
            "input":       "",
            "output":      d["output"],
            "metadata":    {"source": d.get("source"), "quality": d.get("quality"), "ts": d.get("created_at")},
        }, ensure_ascii=False))
    return {
        "samples": len(data),
        "jsonl": "\n".join(jsonl_lines),
        "modelfile": f"FROM {settings.OLLAMA_MODEL}\nSYSTEM \"\"\"You are MagicLamp AI Brain — UAE banking specialist.\"\"\"\nPARAMETER temperature 0.3",
    }

# ── CHANGES ───────────────────────────────────
@router.post("/changes/record")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def record_change(request: Request, body: RecordChangeRequest, user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    what = body.what
    text = f"CHANGE: {what} changed from '{body.from_val}' to '{body.to_val}'. Reason: {body.reason}"
    supabase.table("brain_events").insert({
        "org_id":     _org(user),
        "event_type": "change_recorded",
        "category":   "changes",
        "data":       body.dict(),
        "summary":    text[:200],
        "importance": 3,
    }).execute()
    supabase.table("brain_facts").upsert({
        "org_id": _org(user),
        "key":    f"change.{what}.latest",
        "value":  json.dumps({"from": body.from_val, "to": body.to_val, "reason": body.reason, "ts": datetime.utcnow().isoformat()}),
        "source": "change_record",
    }, on_conflict="org_id,key").execute()
    return {"ok": True, "remembered": text[:100]}

@router.get("/changes/history")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def change_history(request: Request, limit: int = 50, user: CurrentUser = Depends(get_current_user)) -> List[Dict[str, Any]]:
    return supabase.table("brain_events").select("*")\
        .eq("category", "changes").order("created_at", desc=True).limit(limit).execute().data

# ── SCHEDULER ─────────────────────────────────
@router.get("/scheduler/jobs")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def scheduler_jobs(request: Request, user: CurrentUser = Depends(get_current_user)) -> List[Dict[str, Any]]:
    from scheduler import auto_scheduler
    return auto_scheduler.get_jobs()

@router.post("/scheduler/run/{job_id}")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def run_job(request: Request, job_id: str, admin: CurrentUser = Depends(require_admin)) -> Dict[str, Any]:
    from scheduler import auto_scheduler
    job_map = {
        "crm_snapshot":        auto_scheduler.job_crm_snapshot,
        "score_leads":         auto_scheduler.job_score_new_leads,
        "pattern_analysis":    auto_scheduler.job_pattern_analysis,
        "self_analysis":       auto_scheduler.job_self_analysis,
        "daily_briefing":      auto_scheduler.job_daily_briefing,
        "memory_consolidation":auto_scheduler.job_memory_consolidation,
    }
    fn = job_map.get(job_id)
    if not fn:
        raise HTTPException(404, f"Job {job_id} not found")
    await fn()
    return {"ok": True, "job": job_id}
