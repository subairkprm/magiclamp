"""
MagicLamp — Audit Middleware
Every mutating API call (POST/PUT/PATCH/DELETE) is automatically logged.
"""

import json
from datetime import datetime
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from core.database import get_database_client
from core.logger import get_logger

log = get_logger("audit")

_supabase_client = None

def _get_supabase():
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _supabase_client

SKIP_PATHS = {"/health", "/docs", "/openapi.json", "/api/v1/auth/refresh"}
AUDIT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if (
            request.method in AUDIT_METHODS
            and request.url.path not in SKIP_PATHS
            and not request.url.path.startswith("/static")
        ):
            try:
                user_id = "anonymous"
                org_id = None
                # Extract from request state if auth ran
                if hasattr(request.state, "user"):
                    user_id = getattr(request.state.user, "user_id", "anonymous")
                    org_id = getattr(request.state.user, "org_id", None)

                _get_supabase().table("audit_log").insert({
                    "org_id":      org_id,
                    "user_id":     user_id,
                    "action":      f"{request.method} {request.url.path}",
                    "entity_type": request.url.path.split("/")[3] if len(request.url.path.split("/")) > 3 else "api",
                    "new_data":    {"status": response.status_code, "path": request.url.path},
                    "ip_address":  request.client.host if request.client else None,
                    "user_agent":  request.headers.get("user-agent", ""),
                }).execute()
            except Exception as e:
                log.warning(f"[Audit] Failed to log: {e}")

        return response


def log_action(
    action: str,
    entity_type: str = None,
    entity_id: str = None,
    old_data: dict = None,
    new_data: dict = None,
    user_id: str = "system",
    org_id: str = None,
):
    """Manually log an audit entry from any code path."""
    try:
        _get_supabase().table("audit_log").insert({
            "org_id":      org_id,
            "user_id":     user_id,
            "action":      action,
            "entity_type": entity_type,
            "entity_id":   str(entity_id) if entity_id else None,
            "old_data":    old_data,
            "new_data":    new_data,
        }).execute()
    except Exception as e:
        log.warning(f"[Audit] Manual log failed: {e}")
