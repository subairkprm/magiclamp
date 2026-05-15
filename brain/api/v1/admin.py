"""MagicLamp API v1 — Admin Routes (full platform control)"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from core.config import settings
from core.auth import get_current_user, require_admin, CurrentUser, hash_password, generate_api_key
from core.audit import log_action
from core.circuit import ollama_circuit, supabase_circuit, telegram_circuit, n8n_circuit
from core.registry import registry
from core.bus import bus
from core.validation import (
    CreateUserRequest,
    CreateOrgRequest,
    UpdateOrgRequest,
    CreateAPIKeyRequest,
    CreateWebhookRequest,
    AuditLogQuery,
    ResetPasswordRequest,
    sanitize_string,
)
from core.database import get_database_client, DatabaseClient
from repositories import UserRepository
from core.limiter import limiter
import httpx, secrets

router = APIRouter(prefix="/admin", tags=["admin"])

# Import limiter from main
from core.limiter import limiter

# Dependency to get UserRepository
def get_user_repository(db: DatabaseClient = Depends(get_database_client)) -> UserRepository:
    return UserRepository(db)


# ── SYSTEM HEALTH ─────────────────────────────
@router.get("/health")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def system_health(request: Request, admin: CurrentUser = Depends(require_admin)) -> Dict[str, Any]:
    health = await registry.health_check_all()
    circuits = {
        "ollama": ollama_circuit.get_status(),
        "supabase": supabase_circuit.get_status(),
        "telegram": telegram_circuit.get_status(),
        "n8n": n8n_circuit.get_status(),
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
async def list_orgs(
    request: Request, admin: CurrentUser = Depends(require_admin), db: DatabaseClient = Depends(get_database_client)
) -> List[Dict[str, Any]]:
    # Organizations don't have tenant_id (they ARE the tenant)
    result = db.select(table="organizations", columns="*")
    return result.data


@router.post("/orgs")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def create_org(
    request: Request,
    body: CreateOrgRequest,
    admin: CurrentUser = Depends(require_admin),
    db: DatabaseClient = Depends(get_database_client),
) -> Dict[str, Any]:
    result = db.insert(
        table="organizations",
        data={
            "name": body.name,
            "slug": body.slug,
            "plan": body.plan,
        },
    )
    if not result.success or not result.data:
        raise HTTPException(status_code=500, detail="Failed to create organization")

    org = result.data[0]
    log_action("org.created", "organization", org["id"], new_data=body.dict(), user_id=admin.user_id)
    return org


@router.patch("/orgs/{org_id}")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def update_org(
    request: Request,
    org_id: str,
    body: UpdateOrgRequest,
    admin: CurrentUser = Depends(require_admin),
    db: DatabaseClient = Depends(get_database_client),
) -> Dict[str, Any]:
    # Sanitize org_id to prevent injection
    org_id = sanitize_string(org_id, max_length=50)
    update_data = body.dict(exclude_unset=True)

    result = db.update(table="organizations", data=update_data, filters={"id": org_id})
    if not result.success:
        raise HTTPException(status_code=500, detail="Failed to update organization")

    log_action("org.updated", "organization", org_id, new_data=update_data, user_id=admin.user_id)
    return result.data[0] if result.data else {}


# ── USERS ─────────────────────────────────────
@router.get("/users")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def list_users(
    request: Request, admin: CurrentUser = Depends(require_admin), db: DatabaseClient = Depends(get_database_client)
) -> List[Dict[str, Any]]:
    # List all users across all tenants (admin function)
    result = db.select(table="users", columns="id,name,email,role,created_at")
    return result.data


@router.post("/users")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def create_user(
    request: Request,
    body: CreateUserRequest,
    admin: CurrentUser = Depends(require_admin),
    user_repo: UserRepository = Depends(get_user_repository),
    db: DatabaseClient = Depends(get_database_client),
) -> Dict[str, Any]:
    tenant_id = admin.org_id or "default"  # Admin must have a tenant or use default

    # Check if user already exists (cross-tenant check)
    result = db.select(table="users", columns="id", filters={"email": body.email}, limit=1)
    if result.success and result.data:
        raise HTTPException(400, "Email already exists")

    # Create user using repository
    new_user = user_repo.create_user(
        name=body.username,
        email=body.email,
        password_hash=hash_password(body.password),
        tenant_id=tenant_id,
        role=body.role,
    )

    # Add to team if specified
    if body.team_id:
        db.insert(
            table="team_members",
            data={
                "team_id": body.team_id,
                "user_id": str(new_user.id),
                "role": "agent",
            },
            tenant_id=tenant_id,
        )

    log_action(
        "user.created",
        "user",
        str(new_user.id),
        new_data={"email": body.email, "role": body.role},
        user_id=admin.user_id,
    )
    return {"id": new_user.id, "username": body.username, "email": body.email, "role": body.role}


@router.delete("/users/{user_id}")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def delete_user(
    request: Request,
    user_id: int,
    admin: CurrentUser = Depends(require_admin),
    db: DatabaseClient = Depends(get_database_client),
) -> Dict[str, bool]:
    if str(user_id) == admin.user_id:
        raise HTTPException(400, "Cannot delete yourself")

    tenant_id = admin.org_id or "default"
    # Delete user using DatabaseClient (cross-tenant admin operation)
    result = db.delete(table="users", filters={"id": user_id})
    if not result.success:
        raise HTTPException(500, "Failed to delete user")

    log_action("user.deleted", "user", str(user_id), user_id=admin.user_id)
    return {"ok": True}


@router.patch("/users/{user_id}/password")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def reset_user_password(
    request: Request,
    user_id: int,
    body: ResetPasswordRequest,
    admin: CurrentUser = Depends(require_admin),
    db: DatabaseClient = Depends(get_database_client),
) -> Dict[str, bool]:
    # Password validation now handled by Pydantic model
    result = db.update(table="users", data={"password_hash": hash_password(body.password)}, filters={"id": user_id})
    if not result.success:
        raise HTTPException(500, "Failed to reset password")

    log_action("user.password_reset", "user", str(user_id), user_id=admin.user_id)
    return {"ok": True}


# ── API KEYS ──────────────────────────────────
@router.get("/api-keys")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def list_api_keys(
    request: Request, admin: CurrentUser = Depends(require_admin), db: DatabaseClient = Depends(get_database_client)
) -> List[Dict[str, Any]]:
    if not admin.org_id:
        return []

    result = db.select(
        table="api_keys", columns="id,name,key_prefix,scopes,is_active,last_used_at,created_at", tenant_id=admin.org_id
    )
    return result.data


@router.post("/api-keys")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def create_api_key(
    request: Request, body: CreateAPIKeyRequest, admin: CurrentUser = Depends(require_admin)
) -> Dict[str, str]:
    if not admin.org_id:
        raise HTTPException(400, "No org associated with this admin")
    plain_key, _ = generate_api_key(admin.org_id, body.name, body.scopes)
    log_action("api_key.created", "api_key", None, new_data={"name": body.name}, user_id=admin.user_id)
    return {"key": plain_key, "note": "Store this key — it will not be shown again"}


@router.delete("/api-keys/{key_id}")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def revoke_api_key(
    request: Request,
    key_id: str,
    admin: CurrentUser = Depends(require_admin),
    db: DatabaseClient = Depends(get_database_client),
) -> Dict[str, bool]:
    tenant_id = admin.org_id
    if not tenant_id:
        raise HTTPException(400, "Admin has no tenant/org association")

    result = db.update(table="api_keys", data={"is_active": False}, tenant_id=tenant_id, filters={"id": key_id})
    if not result.success:
        raise HTTPException(500, "Failed to revoke API key")

    log_action("api_key.revoked", "api_key", key_id, user_id=admin.user_id)
    return {"ok": True}


# ── WEBHOOKS ──────────────────────────────────
@router.get("/webhooks")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def list_webhooks(
    request: Request, admin: CurrentUser = Depends(require_admin), db: DatabaseClient = Depends(get_database_client)
) -> List[Dict[str, Any]]:
    tenant_id = admin.org_id
    if not tenant_id:
        return []

    result = db.select(
        table="webhooks", columns="id,name,url,events,is_active,last_called,failure_count", tenant_id=tenant_id
    )
    return result.data


@router.post("/webhooks")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def create_webhook(
    request: Request,
    body: CreateWebhookRequest,
    admin: CurrentUser = Depends(require_admin),
    db: DatabaseClient = Depends(get_database_client),
) -> Dict[str, Any]:
    tenant_id = admin.org_id
    if not tenant_id:
        raise HTTPException(400, "Admin has no tenant/org association")

    result = db.insert(
        table="webhooks",
        data={
            "name": body.name,
            "url": body.url,
            "events": body.events,
        },
        tenant_id=tenant_id,
    )
    if not result.success or not result.data:
        raise HTTPException(500, "Failed to create webhook")

    webhook = result.data[0]
    log_action("webhook.created", "webhook", webhook["id"], user_id=admin.user_id)
    return webhook


@router.delete("/webhooks/{webhook_id}")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def delete_webhook(
    request: Request,
    webhook_id: str,
    admin: CurrentUser = Depends(require_admin),
    db: DatabaseClient = Depends(get_database_client),
) -> Dict[str, bool]:
    tenant_id = admin.org_id
    if not tenant_id:
        raise HTTPException(400, "Admin has no tenant/org association")

    result = db.delete(table="webhooks", tenant_id=tenant_id, filters={"id": webhook_id})
    if not result.success:
        raise HTTPException(500, "Failed to delete webhook")

    log_action("webhook.deleted", "webhook", webhook_id, user_id=admin.user_id)
    return {"ok": True}


@router.post("/webhooks/{webhook_id}/test")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def test_webhook(
    request: Request,
    webhook_id: str,
    admin: CurrentUser = Depends(require_admin),
    db: DatabaseClient = Depends(get_database_client),
) -> Dict[str, Any]:
    tenant_id = admin.org_id
    if not tenant_id:
        raise HTTPException(400, "Admin has no tenant/org association")

    result = db.select(table="webhooks", columns="*", tenant_id=tenant_id, filters={"id": webhook_id}, limit=1)
    if not result.success or not result.data:
        raise HTTPException(404, "Webhook not found")

    hook = result.data[0]
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
    admin: CurrentUser = Depends(require_admin),
    db: DatabaseClient = Depends(get_database_client),
) -> List[Dict[str, Any]]:
    tenant_id = admin.org_id
    if not tenant_id:
        return []

    # Note: 'like' filtering not directly supported by DatabaseClient
    # Fetch and filter in Python for now
    result = db.select(
        table="audit_log", columns="*", tenant_id=tenant_id, order_by="created_at.desc", limit=query.limit
    )

    data = result.data if result.success else []
    if query.action:
        # Filter by action pattern
        data = [item for item in data if query.action.lower() in item.get("action", "").lower()]

    return data


# ── INTEGRATIONS ─────────────────────────────
@router.get("/integrations")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def list_integrations(
    request: Request, admin: CurrentUser = Depends(require_admin), db: DatabaseClient = Depends(get_database_client)
) -> List[Dict[str, Any]]:
    tenant_id = admin.org_id
    if not tenant_id:
        return []

    result = db.select(table="integrations", columns="*", tenant_id=tenant_id)
    return result.data


@router.put("/integrations/{type}")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def upsert_integration(
    request: Request,
    type: str,
    body: dict,
    admin: CurrentUser = Depends(require_admin),
    db: DatabaseClient = Depends(get_database_client),
) -> Dict[str, bool]:
    # Sanitize type parameter
    type = sanitize_string(type, max_length=50)
    tenant_id = admin.org_id
    if not tenant_id:
        raise HTTPException(400, "Admin has no tenant/org association")

    # Check if exists
    existing = db.select(table="integrations", columns="id", tenant_id=tenant_id, filters={"type": type}, limit=1)

    if existing.success and existing.data:
        # Update existing
        db.update(
            table="integrations",
            data={"config": body.get("config", {}), "status": "active"},
            tenant_id=tenant_id,
            filters={"type": type},
        )
    else:
        # Insert new
        db.insert(
            table="integrations",
            data={
                "type": type,
                "name": body.get("name", type),
                "config": body.get("config", {}),
                "status": "active",
            },
            tenant_id=tenant_id,
        )

    log_action(f"integration.{type}.configured", "integration", type, user_id=admin.user_id)
    return {"ok": True}


# ── PLANS ─────────────────────────────────────
@router.get("/plans")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def list_plans(
    request: Request, admin: CurrentUser = Depends(require_admin), db: DatabaseClient = Depends(get_database_client)
) -> List[Dict[str, Any]]:
    # Plans are global, not tenant-scoped
    result = db.select(table="subscription_plans", columns="*")
    return result.data


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
