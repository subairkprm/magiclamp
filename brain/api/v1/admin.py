"""MagicLamp API v1 — Admin Routes (full platform control)"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from supabase import create_client
from core.config import settings
from core.auth import get_current_user, require_admin, CurrentUser, hash_password, generate_api_key
from core.audit import log_action
from core.circuit import ollama_circuit, supabase_circuit, telegram_circuit, n8n_circuit
from core.registry import registry
from core.bus import bus
from core.validation import (
    CreateUserRequest, CreateOrgRequest, UpdateOrgRequest,
    CreateAPIKeyRequest, CreateWebhookRequest, AuditLogQuery,
    ResetPasswordRequest, sanitize_string
)
import httpx, secrets

router = APIRouter(prefix="/admin", tags=["admin"])
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

# Import limiter from main
from main import limiter

# ── SYSTEM HEALTH ─────────────────────────────
@router.get("/health")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def system_health(request: Request, admin: CurrentUser = Depends(require_admin)) -> Dict[str, Any]:
    health = await registry.health_check_all()
    circuits = {
        "ollama":   ollama_circuit.get_status(),
        "supabase": supabase_circuit.get_status(),
        "telegram": telegram_circuit.get_status(),
        "n8n":      n8n_circuit.get_status(),
    }
    modules = registry.list_modules()
    healthy_count = sum(1 for m in modules if m.get("health"))
    return {
        "status": "healthy" if healthy_count == len(modules) else "degraded",
        "modules": modules,
        "circuits": circuits,
        "bus": bus.stats(),
        "version": settings.APP_VERSION,
    }

# ── ORGANIZATIONS ─────────────────────────────
@router.get("/orgs")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def list_orgs(request: Request, admin: CurrentUser = Depends(require_admin)) -> List[Dict[str, Any]]:
    return supabase.table("organizations").select("*").execute().data

@router.post("/orgs")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def create_org(request: Request, body: CreateOrgRequest, admin: CurrentUser = Depends(require_admin)) -> Dict[str, Any]:
    result = supabase.table("organizations").insert({
        "name": body.name,
        "slug": body.slug,
        "plan": body.plan,
    }).execute()
    log_action("org.created", "organization", result.data[0]["id"], new_data=body.dict(), user_id=admin.user_id)
    return result.data[0]

@router.patch("/orgs/{org_id}")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def update_org(request: Request, org_id: str, body: UpdateOrgRequest, admin: CurrentUser = Depends(require_admin)) -> Dict[str, Any]:
    # Sanitize org_id to prevent injection
    org_id = sanitize_string(org_id, max_length=50)
    update_data = body.dict(exclude_unset=True)
    result = supabase.table("organizations").update(update_data).eq("id", org_id).execute()
    log_action("org.updated", "organization", org_id, new_data=update_data, user_id=admin.user_id)
    return result.data[0] if result.data else {}

# ── USERS ─────────────────────────────────────
@router.get("/users")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def list_users(request: Request, admin: CurrentUser = Depends(require_admin)) -> List[Dict[str, Any]]:
    return supabase.table("users").select("id,name,email,role,created_at").execute().data

@router.post("/users")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def create_user(request: Request, body: CreateUserRequest, admin: CurrentUser = Depends(require_admin)) -> Dict[str, Any]:
    existing = supabase.table("users").select("id").eq("email", body.email).execute()
    if existing.data:
        raise HTTPException(400, "Email already exists")
    result = supabase.table("users").insert({
        "name":          body.username,
        "email":         body.email,
        "password_hash": hash_password(body.password),
        "role":          body.role,
    }).execute()
    new_user = result.data[0]
    if body.team_id:
        supabase.table("team_members").insert({
            "team_id": body.team_id,
            "user_id": str(new_user["id"]),
            "role":    "agent",
        }).execute()
    log_action("user.created", "user", str(new_user["id"]), new_data={"email": body.email, "role": body.role}, user_id=admin.user_id)
    return {"id": new_user["id"], "username": body.username, "email": body.email, "role": body.role}

@router.delete("/users/{user_id}")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def delete_user(request: Request, user_id: int, admin: CurrentUser = Depends(require_admin)) -> Dict[str, bool]:
    if str(user_id) == admin.user_id:
        raise HTTPException(400, "Cannot delete yourself")
    supabase.table("users").delete().eq("id", user_id).execute()
    log_action("user.deleted", "user", str(user_id), user_id=admin.user_id)
    return {"ok": True}

@router.patch("/users/{user_id}/password")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def reset_user_password(request: Request, user_id: int, body: ResetPasswordRequest, admin: CurrentUser = Depends(require_admin)) -> Dict[str, bool]:
    # Password validation now handled by Pydantic model
    supabase.table("users").update({"password_hash": hash_password(body.password)}).eq("id", user_id).execute()
    log_action("user.password_reset", "user", str(user_id), user_id=admin.user_id)
    return {"ok": True}

# ── API KEYS ──────────────────────────────────
@router.get("/api-keys")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def list_api_keys(request: Request, admin: CurrentUser = Depends(require_admin)) -> List[Dict[str, Any]]:
    data = supabase.table("api_keys").select(
        "id,name,key_prefix,scopes,is_active,last_used_at,created_at"
    ).eq("org_id", admin.org_id).execute().data if admin.org_id else []
    return data

@router.post("/api-keys")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def create_api_key(request: Request, body: CreateAPIKeyRequest, admin: CurrentUser = Depends(require_admin)) -> Dict[str, str]:
    if not admin.org_id:
        raise HTTPException(400, "No org associated with this admin")
    plain_key, _ = generate_api_key(
        admin.org_id,
        body.name,
        body.scopes
    )
    log_action("api_key.created", "api_key", None, new_data={"name": body.name}, user_id=admin.user_id)
    return {"key": plain_key, "note": "Store this key — it will not be shown again"}

@router.delete("/api-keys/{key_id}")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def revoke_api_key(request: Request, key_id: str, admin: CurrentUser = Depends(require_admin)) -> Dict[str, bool]:
    supabase.table("api_keys").update({"is_active": False}).eq("id", key_id).execute()
    log_action("api_key.revoked", "api_key", key_id, user_id=admin.user_id)
    return {"ok": True}

# ── WEBHOOKS ──────────────────────────────────
@router.get("/webhooks")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def list_webhooks(request: Request, admin: CurrentUser = Depends(require_admin)) -> List[Dict[str, Any]]:
    return supabase.table("webhooks").select("id,name,url,events,is_active,last_called,failure_count").execute().data

@router.post("/webhooks")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def create_webhook(request: Request, body: CreateWebhookRequest, admin: CurrentUser = Depends(require_admin)) -> Dict[str, Any]:
    result = supabase.table("webhooks").insert({
        "org_id":  admin.org_id,
        "name":    body.name,
        "url":     body.url,
        "events":  body.events,
    }).execute()
    log_action("webhook.created", "webhook", result.data[0]["id"], user_id=admin.user_id)
    return result.data[0]

@router.delete("/webhooks/{webhook_id}")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def delete_webhook(request: Request, webhook_id: str, admin: CurrentUser = Depends(require_admin)) -> Dict[str, bool]:
    supabase.table("webhooks").delete().eq("id", webhook_id).execute()
    log_action("webhook.deleted", "webhook", webhook_id, user_id=admin.user_id)
    return {"ok": True}

@router.post("/webhooks/{webhook_id}/test")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def test_webhook(request: Request, webhook_id: str, admin: CurrentUser = Depends(require_admin)) -> Dict[str, Any]:
    wh = supabase.table("webhooks").select("*").eq("id", webhook_id).execute()
    if not wh.data:
        raise HTTPException(404, "Webhook not found")
    hook = wh.data[0]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(hook["url"], json={"event": "test", "from": "MagicLamp"})
        return {"status": r.status_code, "ok": r.status_code < 300}
    except Exception as e:
        return {"status": 0, "ok": False, "error": str(e)}

# ── AUDIT LOG ─────────────────────────────────
@router.get("/audit-log")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def get_audit_log(
    request: Request,
    query: AuditLogQuery = Depends(),
    admin: CurrentUser = Depends(require_admin)
) -> List[Dict[str, Any]]:
    q = supabase.table("audit_log").select("*").order("created_at", desc=True).limit(query.limit)
    if query.action:
        # Use parameterized query, sanitized by Pydantic model
        q = q.like("action", f"%{query.action}%")
    return q.execute().data

# ── INTEGRATIONS ─────────────────────────────
@router.get("/integrations")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def list_integrations(request: Request, admin: CurrentUser = Depends(require_admin)) -> List[Dict[str, Any]]:
    return supabase.table("integrations").select("*").execute().data

@router.put("/integrations/{type}")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def upsert_integration(request: Request, type: str, body: dict, admin: CurrentUser = Depends(require_admin)) -> Dict[str, bool]:
    # Sanitize type parameter
    type = sanitize_string(type, max_length=50)
    existing = supabase.table("integrations").select("id").eq("type", type).execute()
    if existing.data:
        supabase.table("integrations").update({"config": body.get("config", {}), "status": "active"})\
            .eq("type", type).execute()
    else:
        supabase.table("integrations").insert({
            "org_id": admin.org_id,
            "type":   type,
            "name":   body.get("name", type),
            "config": body.get("config", {}),
            "status": "active",
        }).execute()
    log_action(f"integration.{type}.configured", "integration", type, user_id=admin.user_id)
    return {"ok": True}

# ── PLANS ─────────────────────────────────────
@router.get("/plans")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def list_plans(request: Request, admin: CurrentUser = Depends(require_admin)) -> List[Dict[str, Any]]:
    return supabase.table("subscription_plans").select("*").execute().data

# ── MODULE CONTROL ────────────────────────────
@router.get("/modules")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def list_modules(request: Request, admin: CurrentUser = Depends(require_admin)) -> List[Dict[str, Any]]:
    return registry.list_modules()

@router.post("/modules/health-check")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def run_health_check(request: Request, admin: CurrentUser = Depends(require_admin)) -> Dict[str, Dict[str, Any]]:
    results = await registry.health_check_all()
    return {k: {"healthy": v.healthy, "message": v.message} for k, v in results.items()}
