"""
MagicLamp — Auto Scheduler
Background job scheduler for autonomous brain operations.
Runs periodic tasks: CRM snapshots, lead scoring, pattern analysis, briefings.
"""

import asyncio
from typing import Callable, Dict, List, Optional
from datetime import datetime, time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.job import Job
import httpx

from core.config import settings
from core.logger import get_logger
from core.bus import bus
from core.circuit import ollama_circuit
from supabase import create_client, Client

log = get_logger("scheduler")

_supabase_client = None

def _get_supabase():
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _supabase_client


class AutoScheduler:
    """
    Autonomous scheduler for brain operations.
    Integrates with FastAPI event loop without blocking.
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone="Asia/Dubai")
        self._running = False
        self._jobs: Dict[str, Job] = {}

    def start(self):
        """Start the scheduler and register all jobs"""
        if self._running:
            log.warning("[Scheduler] Already running")
            return

        log.info("[Scheduler] Starting autonomous scheduler...")

        # Register periodic jobs
        self._register_jobs()

        # Start the scheduler
        self.scheduler.start()
        self._running = True

        log.info(f"[Scheduler] Started with {len(self._jobs)} jobs")

    def stop(self):
        """Stop the scheduler gracefully"""
        if not self._running:
            return

        log.info("[Scheduler] Stopping scheduler...")
        self.scheduler.shutdown(wait=True)
        self._running = False
        log.info("[Scheduler] Scheduler stopped")

    def _register_jobs(self):
        """Register all autonomous jobs"""

        # Every 6 hours: Take CRM snapshot
        self._add_job(
            "crm_snapshot", self.job_crm_snapshot, CronTrigger(hour="*/6", minute=0), "Take CRM snapshot every 6 hours"
        )

        # Every 2 hours: Score new leads
        self._add_job(
            "score_leads", self.job_score_new_leads, IntervalTrigger(hours=2), "Score new leads every 2 hours"
        )

        # Daily at 3 AM: Pattern analysis
        self._add_job(
            "pattern_analysis",
            self.job_pattern_analysis,
            CronTrigger(hour=3, minute=0),
            "Analyze patterns daily at 3 AM",
        )

        # Daily at 4 AM: Self analysis
        self._add_job(
            "self_analysis", self.job_self_analysis, CronTrigger(hour=4, minute=0), "Self-analysis daily at 4 AM"
        )

        # Daily at 8 AM: Daily briefing
        self._add_job(
            "daily_briefing", self.job_daily_briefing, CronTrigger(hour=8, minute=0), "Send daily briefing at 8 AM"
        )

        # Every 12 hours: Memory consolidation
        self._add_job(
            "memory_consolidation",
            self.job_memory_consolidation,
            IntervalTrigger(hours=12),
            "Consolidate memories every 12 hours",
        )

    def _add_job(self, job_id: str, func: Callable, trigger, description: str):
        """Add a job to the scheduler"""
        try:
            job = self.scheduler.add_job(
                func,
                trigger=trigger,
                id=job_id,
                name=description,
                replace_existing=True,
                max_instances=1,  # Prevent overlapping executions
                misfire_grace_time=300,  # 5 minutes grace for missed jobs
            )
            self._jobs[job_id] = job
            log.info(f"[Scheduler] Registered: {job_id} — {description}")
        except Exception as e:
            log.error(f"[Scheduler] Failed to register {job_id}: {e}")

    def get_jobs(self) -> List[Dict]:
        """Get list of all registered jobs with status"""
        jobs_list = []
        for job_id, job in self._jobs.items():
            jobs_list.append(
                {
                    "id": job_id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger),
                }
            )
        return jobs_list

    # ── JOB IMPLEMENTATIONS ──────────────────────────────────────

    async def job_crm_snapshot(self):
        """Take snapshot of CRM state for training data"""
        try:
            log.info("[Job:CRM Snapshot] Starting...")

            # Get Supabase client (lazy initialization)
            supabase = _get_supabase_client()

            # Get lead counts by status
            leads = _get_supabase().table("leads").select("id,status,score", count="exact").execute()

            # Get team performance metrics
            teams = _get_supabase().table("teams").select("id,name", count="exact").execute()

            snapshot = {
                "timestamp": datetime.utcnow().isoformat(),
                "total_leads": leads.count or 0,
                "teams_count": teams.count or 0,
                "snapshot_type": "crm_overview",
            }

            # Store as brain event
            _get_supabase().table("brain_events").insert({
                "event_type": "crm_snapshot",
                "category": "automation",
                "data": snapshot,
                "summary": f"CRM snapshot: {snapshot['total_leads']} leads",
                "importance": 2,
            }).execute()

            await bus.emit("scheduler.crm_snapshot.completed", snapshot)
            log.info(f"[Job:CRM Snapshot] Complete — {snapshot['total_leads']} leads")

        except Exception as e:
            log.error(f"[Job:CRM Snapshot] Failed: {e}")
            await bus.emit("scheduler.job.failed", {"job": "crm_snapshot", "error": str(e)})

    async def job_score_new_leads(self):
        """Score leads that haven't been scored yet"""
        try:
            log.info("[Job:Score Leads] Starting...")

            # Get Supabase client (lazy initialization)
            supabase = _get_supabase_client()

            # Get leads without scores or old scores
            result = _get_supabase().table("leads").select("*").is_("score", "null").limit(50).execute()

            if not result.data:
                log.info("[Job:Score Leads] No new leads to score")
                return

            scored_count = 0
            for lead in result.data:
                try:
                    # Simple scoring logic (can be enhanced with AI)
                    score = await self._calculate_lead_score(lead)

                    # Update lead
                    _get_supabase().table("leads").update({"score": score}).eq("id", lead["id"]).execute()
                    scored_count += 1

                except Exception as lead_error:
                    log.warning(f"[Job:Score Leads] Failed to score lead {lead['id']}: {lead_error}")
                    continue

            await bus.emit("scheduler.leads_scored", {"count": scored_count})
            log.info(f"[Job:Score Leads] Scored {scored_count} leads")

        except Exception as e:
            log.error(f"[Job:Score Leads] Failed: {e}")

    async def job_pattern_analysis(self):
        """Analyze patterns in CRM data"""
        try:
            log.info("[Job:Pattern Analysis] Starting...")

            # Get Supabase client (lazy initialization)
            supabase = _get_supabase_client()

            # Get recent events
            events = _get_supabase().table("brain_events").select("*")\
                .order("created_at", desc=True).limit(100).execute()

            if not events.data:
                log.info("[Job:Pattern Analysis] No events to analyze")
                return

            # Analyze event frequency
            event_types = {}
            for event in events.data:
                event_type = event.get("event_type", "unknown")
                event_types[event_type] = event_types.get(event_type, 0) + 1

            analysis = {
                "timestamp": datetime.utcnow().isoformat(),
                "events_analyzed": len(events.data),
                "event_type_distribution": event_types,
                "most_common_event": max(event_types.items(), key=lambda x: x[1])[0] if event_types else None,
            }

            # Store analysis
            _get_supabase().table("brain_analyses").insert({
                "subject": "pattern_analysis",
                "analysis": str(analysis),
                "metrics": analysis,
            }).execute()

            await bus.emit("scheduler.pattern_analysis.completed", analysis)
            log.info(f"[Job:Pattern Analysis] Complete — {len(events.data)} events analyzed")

        except Exception as e:
            log.error(f"[Job:Pattern Analysis] Failed: {e}")

    async def job_self_analysis(self):
        """Perform self-analysis of brain health"""
        try:
            log.info("[Job:Self Analysis] Starting...")

            # Get Supabase client (lazy initialization)
            supabase = _get_supabase_client()

            # Get system metrics
            facts_count = _get_supabase().table("brain_facts").select("id", count="exact").execute().count or 0
            events_count = _get_supabase().table("brain_events").select("id", count="exact").execute().count or 0
            decisions_count = _get_supabase().table("brain_decisions").select("id", count="exact").execute().count or 0

            # Calculate health score (simple heuristic)
            health_score = min(100, (facts_count * 0.3 + events_count * 0.01 + decisions_count * 0.5))

            analysis = {
                "timestamp": datetime.utcnow().isoformat(),
                "health_score": int(health_score),
                "facts_count": facts_count,
                "events_count": events_count,
                "decisions_count": decisions_count,
                "status": "healthy" if health_score > 50 else "degraded",
            }

            # Store self-analysis
            _get_supabase().table("brain_analyses").insert({
                "subject": "self_analysis",
                "analysis": str(analysis),
                "metrics": analysis,
            }).execute()

            await bus.emit("scheduler.self_analysis.completed", analysis)
            log.info(f"[Job:Self Analysis] Complete — Health score: {health_score}")

        except Exception as e:
            log.error(f"[Job:Self Analysis] Failed: {e}")

    async def job_daily_briefing(self):
        """Generate and send daily briefing"""
        try:
            log.info("[Job:Daily Briefing] Starting...")

            # Get Supabase client (lazy initialization)
            supabase = _get_supabase_client()

            # Get yesterday's activity
            from datetime import timedelta

            yesterday = datetime.utcnow() - timedelta(days=1)

            events = _get_supabase().table("brain_events")\
                .select("*", count="exact")\
                .gte("created_at", yesterday.isoformat())\
                .execute()
            )

            decisions = _get_supabase().table("brain_decisions")\
                .select("*", count="exact")\
                .gte("created_at", yesterday.isoformat())\
                .execute()
            )

            briefing = {
                "date": datetime.utcnow().date().isoformat(),
                "events_yesterday": events.count or 0,
                "decisions_made": decisions.count or 0,
                "summary": f"Yesterday: {events.count or 0} events, {decisions.count or 0} decisions",
            }

            # Store briefing
            _get_supabase().table("brain_events").insert({
                "event_type": "daily_briefing",
                "category": "automation",
                "data": briefing,
                "summary": briefing["summary"],
                "importance": 3,
            }).execute()

            await bus.emit("scheduler.daily_briefing.completed", briefing)
            log.info(f"[Job:Daily Briefing] Complete — {briefing['summary']}")

            # Send to Telegram if configured
            if settings.TELEGRAM_TOKEN and settings.TELEGRAM_ADMIN:
                await self._send_telegram_briefing(briefing)

        except Exception as e:
            log.error(f"[Job:Daily Briefing] Failed: {e}")

    async def job_memory_consolidation(self):
        """Consolidate and optimize memory storage"""
        try:
            log.info("[Job:Memory Consolidation] Starting...")

            # Get Supabase client (lazy initialization)
            supabase = _get_supabase_client()

            # Get low-confidence facts
            low_confidence = _get_supabase().table("brain_facts")\
                .select("*")\
                .lt("confidence", 0.3)\
                .execute()

            if low_confidence.data:
                # Archive low-confidence facts
                archived_count = 0
                for fact in low_confidence.data:
                    # Move to archive or delete
                    # For now, just mark them
                    _get_supabase().table("brain_facts")\
                        .update({"source": "archived_low_confidence"})\
                        .eq("id", fact["id"])\
                        .execute()
                    archived_count += 1

                log.info(f"[Job:Memory Consolidation] Archived {archived_count} low-confidence facts")

            # Get duplicate events
            # Simple deduplication logic
            consolidation = {
                "timestamp": datetime.utcnow().isoformat(),
                "archived_facts": len(low_confidence.data) if low_confidence.data else 0,
            }

            await bus.emit("scheduler.memory_consolidation.completed", consolidation)
            log.info("[Job:Memory Consolidation] Complete")

        except Exception as e:
            log.error(f"[Job:Memory Consolidation] Failed: {e}")

    # ── HELPER METHODS ───────────────────────────────────────────

    async def _calculate_lead_score(self, lead: dict) -> int:
        """Calculate lead score based on available data"""
        score = 50  # Base score

        # Adjust based on status
        status = lead.get("status", "")
        if status == "qualified":
            score += 20
        elif status == "contacted":
            score += 10
        elif status == "cold":
            score -= 20

        # Adjust based on data completeness
        if lead.get("phone"):
            score += 5
        if lead.get("email"):
            score += 5
        if lead.get("company"):
            score += 10

        return max(0, min(100, score))

    async def _send_telegram_briefing(self, briefing: dict):
        """Send briefing to Telegram"""
        try:
            message = f"📊 Daily MagicLamp Briefing\n\n{briefing['summary']}"

            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"https://api.telegram.org/bot{settings.TELEGRAM_TOKEN}/sendMessage",
                    json={"chat_id": settings.TELEGRAM_ADMIN, "text": message, "parse_mode": "HTML"},
                )
            log.info("[Scheduler] Telegram briefing sent")
        except Exception as e:
            log.warning(f"[Scheduler] Failed to send Telegram briefing: {e}")


# Global scheduler instance
auto_scheduler = AutoScheduler()
