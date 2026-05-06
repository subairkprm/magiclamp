"""Reasoning routes — lead, ask (sync + streaming), decide, self-analysis, task status."""

import asyncio
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from core.auth import CurrentUser, get_current_user
from core.config import settings
from core.database import DatabaseClient, get_database_client
from core.exceptions import AuthorizationError, TaskNotFoundError
from core.limiter import limiter
from core.logger import get_logger
from core.validation import (
    ReasonAskRequest,
    ReasonDecideRequest,
    ReasonLeadRequest,
    sanitize_string,
)
from repositories import FactRepository

from .memory import memory_stats
from .services import (
    create_task,
    get_cached_facts,
    get_fact_repository,
    get_task,
    llm,
    llm_stream,
    org_of,
    update_task_error,
    update_task_success,
)

log = get_logger("api.brain.reason")
router = APIRouter(tags=["brain"])


# ── Background processors ─────────────────────────────────────────
async def _process_reason_lead(task_id: str, lead: Dict, org_id: Optional[str]) -> None:
    """Background task to score & enrich a UAE banking lead."""
    try:
        prompt = f"""Analyse this UAE banking lead and return JSON:
{{"score":0-100,"priority":"low|medium|high|urgent","eligibility":"likely_eligible|borderline|likely_rejected",
"key_risks":[],"opportunities":[],"recommended_products":[],"next_action":"","reasoning":""}}

Lead: {json.dumps(lead)}"""
        result_str = await llm(prompt, json_mode=True)
        try:
            result = json.loads(result_str)
        except Exception:
            result = {"score": 50, "priority": "medium", "reasoning": result_str[:200]}

        if org_id:
            db = get_database_client()
            db.insert(
                table="brain_training_data",
                data={
                    "input": f"Analyse lead: {json.dumps(lead)[:300]}",
                    "output": json.dumps(result)[:500],
                    "source": "lead_analysis",
                    "quality": 1.5,
                },
                tenant_id=org_id,
            )

        update_task_success(task_id, result)
    except Exception as e:
        log.error(f"Lead reasoning task {task_id} failed: {str(e)}")
        update_task_error(task_id, str(e))


def _retrieve_for_question(question: str, org_id: Optional[str]) -> tuple[List[Dict[str, Any]], str]:
    """Resolve the retrieval set for a free-form question.

    Returns ``(facts, retrieval_mode)`` where ``retrieval_mode`` is one of
    ``"rag"``, ``"recent"`` or ``"none"``. Honors ``settings.RAG_ENABLED``.
    """
    retrieved_facts: List[Dict[str, Any]] = []
    retrieval_mode = "none"
    if not org_id:
        return retrieved_facts, retrieval_mode

    db = get_database_client()
    fact_repo = FactRepository(db)

    if settings.RAG_ENABLED:
        rag_facts = fact_repo.semantic_search(
            query=question,
            tenant_id=org_id,
            k=settings.RAG_TOP_K,
            min_score=settings.RAG_MIN_SIMILARITY,
        )
        if rag_facts:
            retrieved_facts = [{"key": f.key, "value": f.value} for f in rag_facts]
            retrieval_mode = "rag"
            return retrieved_facts, retrieval_mode

    retrieved_facts = get_cached_facts(tenant_id=org_id, fact_repo=fact_repo)
    retrieval_mode = "recent" if retrieved_facts else "none"
    return retrieved_facts, retrieval_mode


def _build_ask_prompt(question: str, retrieved_facts: List[Dict[str, Any]]) -> str:
    """Assemble the cited prompt for the Ask flow."""
    if retrieved_facts:
        ctx_lines = [
            f"[#{i + 1}] {f['key']}: {str(f['value'])[:200]}"
            for i, f in enumerate(retrieved_facts)
        ]
        fact_ctx = "\n".join(ctx_lines)
        return (
            "Answer the question using your knowledge and the cited facts below. "
            "When a fact supports your answer, reference it by its bracketed id "
            "(e.g. [#1]).\n\n"
            f"Facts:\n{fact_ctx}\n\nQuestion: {question}"
        )
    return f"Answer the question using your general knowledge.\n\nQuestion: {question}"


async def _process_reason_ask(task_id: str, question: str, org_id: Optional[str]) -> None:
    """Background task for the polled Ask flow."""
    try:
        retrieved_facts, retrieval_mode = _retrieve_for_question(question, org_id)
        log.info(
            f"reason_ask task={task_id} tenant={org_id} retrieval={retrieval_mode} "
            f"hits={len(retrieved_facts)}"
        )
        prompt = _build_ask_prompt(question, retrieved_facts)
        answer = await llm(prompt)

        if org_id:
            db = get_database_client()
            db.insert(
                table="brain_training_data",
                data={
                    "input": question,
                    "output": answer[:500],
                    "source": "api_ask",
                    "quality": 1.0,
                    "metadata": {
                        "retrieval_mode": retrieval_mode,
                        "retrieved_keys": [f["key"] for f in retrieved_facts],
                    },
                },
                tenant_id=org_id,
            )

        update_task_success(
            task_id,
            {
                "question": question,
                "answer": answer,
                "retrieval_mode": retrieval_mode,
                "citations": [
                    {"id": i + 1, "key": f["key"]}
                    for i, f in enumerate(retrieved_facts)
                ],
            },
        )
    except Exception as e:
        log.error(f"Ask reasoning task {task_id} failed: {str(e)}")
        update_task_error(task_id, str(e))


async def _process_reason_decide(
    task_id: str, situation: str, options: List[str], org_id: Optional[str]
) -> None:
    """Background task for decision reasoning."""
    try:
        opts_text = f"\nOptions: {', '.join(options)}" if options else ""
        prompt = f"""Make a decision and return JSON:
{{"decision":"","reasoning":"","confidence":0.0,"risks":[],"expected_outcome":"","follow_up_actions":[]}}
Situation: {situation}{opts_text}"""
        result_str = await llm(prompt, json_mode=True)
        try:
            result = json.loads(result_str)
        except Exception:
            result = {"decision": "manual_review", "reasoning": result_str[:200]}

        if org_id:
            db = get_database_client()
            db.insert(
                table="brain_decisions",
                data={
                    "trigger": situation[:300],
                    "reasoning": result.get("reasoning", "")[:500],
                    "action": result.get("decision", "")[:200],
                    "confidence": result.get("confidence", 0.5),
                },
                tenant_id=org_id,
            )

        update_task_success(task_id, result)
    except Exception as e:
        log.error(f"Decide reasoning task {task_id} failed: {str(e)}")
        update_task_error(task_id, str(e))


# ── Endpoints ────────────────────────────────────────────────────
@router.post("/reason/lead")
@limiter.limit(settings.RATE_LIMIT_AI)
async def reason_lead(
    request: Request,
    background_tasks: BackgroundTasks,
    body: ReasonLeadRequest,
    user: CurrentUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """Analyse a banking lead (async background processing)."""
    task_id = create_task("reason_lead", user.user_id)
    background_tasks.add_task(_process_reason_lead, task_id, body.lead, org_of(user))
    return {
        "task_id": task_id,
        "status": "processing",
        "message": "Lead analysis started. Use GET /brain/tasks/{task_id} to check status.",
    }


@router.post("/reason/ask")
@limiter.limit(settings.RATE_LIMIT_AI)
async def reason_ask(
    request: Request,
    background_tasks: BackgroundTasks,
    body: ReasonAskRequest,
    user: CurrentUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """Ask a question (async background processing)."""
    task_id = create_task("reason_ask", user.user_id)
    background_tasks.add_task(_process_reason_ask, task_id, body.question, org_of(user))
    return {
        "task_id": task_id,
        "status": "processing",
        "message": "Question processing started. Use GET /brain/tasks/{task_id} to check status.",
    }


@router.post("/reason/ask/stream")
@limiter.limit(settings.RATE_LIMIT_AI)
async def reason_ask_stream(
    request: Request,
    body: ReasonAskRequest,
    user: CurrentUser = Depends(get_current_user),
) -> StreamingResponse:
    """Server-Sent Events streaming variant of the Ask flow.

    Emits three event types so the chat UI can render incrementally:

    - ``meta`` — JSON with ``retrieval_mode`` and ``citations`` (sent first).
    - ``token`` — repeated text chunks; concatenated they form the full answer.
    - ``done`` — terminal marker; safe to close the stream.

    The endpoint reuses the same retrieval path as ``/reason/ask`` so behaviour
    matches; only the transport changes. Training data is recorded once the
    full answer has been streamed.
    """
    org_id = org_of(user)
    question = body.question

    async def event_stream():
        # Move retrieval and prompt assembly off the request thread.
        retrieved_facts, retrieval_mode = await asyncio.to_thread(
            _retrieve_for_question, question, org_id
        )
        meta = {
            "retrieval_mode": retrieval_mode,
            "citations": [
                {"id": i + 1, "key": f["key"]}
                for i, f in enumerate(retrieved_facts)
            ],
        }
        yield f"event: meta\ndata: {json.dumps(meta)}\n\n"

        prompt = _build_ask_prompt(question, retrieved_facts)
        chunks: List[str] = []
        async for chunk in llm_stream(prompt):
            chunks.append(chunk)
            # SSE data lines must not contain raw newlines mid-payload — JSON-encode.
            yield f"event: token\ndata: {json.dumps(chunk)}\n\n"

        full_answer = "".join(chunks)
        if org_id:
            try:
                db = get_database_client()
                db.insert(
                    table="brain_training_data",
                    data={
                        "input": question,
                        "output": full_answer[:500],
                        "source": "api_ask_stream",
                        "quality": 1.0,
                        "metadata": {
                            "retrieval_mode": retrieval_mode,
                            "retrieved_keys": [f["key"] for f in retrieved_facts],
                        },
                    },
                    tenant_id=org_id,
                )
            except Exception as e:  # pragma: no cover - best-effort persistence
                log.warning(f"stream training-data insert failed: {e}")

        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/reason/decide")
@limiter.limit(settings.RATE_LIMIT_AI)
async def reason_decide(
    request: Request,
    background_tasks: BackgroundTasks,
    body: ReasonDecideRequest,
    user: CurrentUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """Make a decision (async background processing)."""
    task_id = create_task("reason_decide", user.user_id)
    background_tasks.add_task(
        _process_reason_decide, task_id, body.situation, body.options or [], org_of(user)
    )
    return {
        "task_id": task_id,
        "status": "processing",
        "message": "Decision processing started. Use GET /brain/tasks/{task_id} to check status.",
    }


@router.get("/tasks/{task_id}")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def get_task_status(
    request: Request, task_id: str, user: CurrentUser = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get the status of a background task."""
    task_id = sanitize_string(task_id, max_length=50)
    task = get_task(task_id)
    if task is None:
        raise TaskNotFoundError(task_id)
    if task["user_id"] != user.user_id:
        raise AuthorizationError("You do not have permission to view this task")
    return task


@router.get("/reason/self-analyse")
@limiter.limit(settings.RATE_LIMIT_AI)
async def self_analyse(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    fact_repo: FactRepository = Depends(get_fact_repository),
    db: DatabaseClient = Depends(get_database_client),
) -> Dict[str, Any]:
    stats = await memory_stats(request, user, fact_repo, db)
    tenant_id = org_of(user)
    if not tenant_id:
        raise HTTPException(status_code=400, detail="User has no tenant/org association")

    decisions_result = db.select(
        table="brain_decisions",
        columns="*",
        tenant_id=tenant_id,
        order_by="created_at.desc",
        limit=5,
    )
    decisions = decisions_result.data if decisions_result.success else []

    prompt = f"""Review brain state and return JSON:
{{"knowledge_summary":"","gaps":[],"pending_actions":[],"health_score":0-100,"alerts":[]}}
Stats: {json.dumps(stats)}
Recent decisions: {json.dumps(decisions, default=str)[:500]}"""
    result_str = await llm(prompt, json_mode=True)
    try:
        result = json.loads(result_str)
    except Exception:
        result = {"health_score": 75, "knowledge_summary": "Brain operational"}

    db.insert(
        table="brain_analyses",
        data={
            "subject": "self_analysis",
            "analysis": json.dumps(result),
            "metrics": stats,
        },
        tenant_id=tenant_id,
    )
    return result
