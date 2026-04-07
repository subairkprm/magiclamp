"""MagicLamp API v1 — Auth Routes"""
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Response, Request
from pydantic import BaseModel
from core.config import settings
from core.auth import (hash_password, verify_password, create_access_token,
                       create_refresh_token, decode_token, get_current_user, CurrentUser)
from core.audit import log_action
from core.logger import get_logger
from core.validation import LoginRequest, ChangePasswordRequest
from core.database import get_database_client, DatabaseClient
from repositories import UserRepository
from core.exceptions import RecordNotFoundError

log = get_logger("api.auth")
router = APIRouter(prefix="/auth", tags=["auth"])

# Import limiter from main
from main import limiter

class RefreshRequest(BaseModel):
    refresh_token: str

# Dependency to get UserRepository
def get_user_repository(db: DatabaseClient = Depends(get_database_client)) -> UserRepository:
    return UserRepository(db)

@router.post("/login")
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    user_repo: UserRepository = Depends(get_user_repository),
    db: DatabaseClient = Depends(get_database_client)
) -> Dict[str, Any]:
    # Timing-attack resistant user lookup
    # Always check password even if user not found to prevent user enumeration
    DUMMY_HASH = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU7fVKgL.E2K"

    # Try to find user by email first, then by name
    # Note: This crosses tenants for login - user provides credentials, we find their tenant
    user = None
    # Search across all tenants for login (tenant_id=None means no tenant filter)
    result = db.select(table="users", columns="*", filters={"email": body.username}, limit=1)
    if result.success and result.data:
        user = result.data[0]
    else:
        result = db.select(table="users", columns="*", filters={"name": body.username}, limit=1)
        if result.success and result.data:
            user = result.data[0]

    password_hash = user.get("password_hash", DUMMY_HASH) if user else DUMMY_HASH

    # Always verify password to prevent timing attacks
    password_valid = verify_password(body.password, password_hash)

    if not user or not password_valid:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Get tenant_id from user or fetch from team
    tenant_id = user.get("tenant_id") or user.get("org_id")
    if not tenant_id:
        # Legacy: Get team to find org
        team_result = db.select(table="team_members", columns="team_id", filters={"user_id": str(user["id"])}, limit=1)
        if team_result.success and team_result.data:
            team = db.select(table="teams", columns="org_id,tenant_id", filters={"id": team_result.data[0]["team_id"]}, limit=1)
            if team.success and team.data:
                tenant_id = team.data[0].get("tenant_id") or team.data[0].get("org_id")

    access_token  = create_access_token(str(user["id"]), user.get("role", "user"), tenant_id)
    refresh_token = create_refresh_token(str(user["id"]))

    log_action("user.login", "user", str(user["id"]), user_id=str(user["id"]), org_id=tenant_id)

    return {
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "token_type":    "bearer",
        "expires_in":    settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id":       user["id"],
            "username": user.get("name") or user.get("email"),
            "email":    user.get("email"),
            "role":     user.get("role", "user"),
            "org_id":   tenant_id,
        }
    }

@router.post("/refresh")
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def refresh(
    request: Request,
    body: RefreshRequest,
    db: DatabaseClient = Depends(get_database_client)
) -> Dict[str, str]:
    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user_id = payload["sub"]

    # Lookup user without tenant filter (cross-tenant lookup for refresh)
    result = db.select(table="users", columns="*", filters={"id": int(user_id)}, limit=1)
    if not result.success or not result.data:
        raise HTTPException(status_code=401, detail="User not found")

    user = result.data[0]
    tenant_id = user.get("tenant_id") or user.get("org_id")
    access_token = create_access_token(user_id, user.get("role", "user"), tenant_id)
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def me(request: Request, user: CurrentUser = Depends(get_current_user)) -> Dict[str, Any]:
    return {"user_id": user.user_id, "role": user.role, "org_id": user.org_id, "via": user.via}

@router.post("/logout")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def logout(request: Request, user: CurrentUser = Depends(get_current_user)) -> Dict[str, bool]:
    log_action("user.logout", "user", user.user_id, user_id=user.user_id)
    return {"ok": True}

@router.patch("/password")
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    user: CurrentUser = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository)
) -> Dict[str, bool]:
    # Password validation now handled by Pydantic model
    if not user.org_id:
        raise HTTPException(status_code=400, detail="User has no tenant/org association")

    try:
        # Get user to verify current password
        user_record = user_repo.get_by_id(user_id=user.user_id, tenant_id=user.org_id)

        if not verify_password(body.current_password, user_record.password_hash):
            raise HTTPException(status_code=401, detail="Wrong current password")

        # Update password via database client directly (repository doesn't have update_password method yet)
        # TODO: Add update_password method to UserRepository
        db = get_database_client()
        new_hash = hash_password(body.new_password)
        result = db.update(
            table="users",
            data={"password_hash": new_hash},
            tenant_id=user.org_id,
            filters={"id": int(user.user_id)}
        )

        if not result.success:
            raise HTTPException(status_code=500, detail="Failed to update password")

        log_action("user.password_changed", "user", user.user_id, user_id=user.user_id)
        return {"ok": True}
    except RecordNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
