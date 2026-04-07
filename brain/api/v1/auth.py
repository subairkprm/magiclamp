"""MagicLamp API v1 — Auth Routes"""
from fastapi import APIRouter, HTTPException, Depends, Response, Request
from pydantic import BaseModel
from supabase import create_client
from core.config import settings
from core.auth import (hash_password, verify_password, create_access_token,
                       create_refresh_token, decode_token, get_current_user, CurrentUser)
from core.audit import log_action
from core.logger import get_logger
from core.validation import LoginRequest, ChangePasswordRequest

log = get_logger("api.auth")
router = APIRouter(prefix="/auth", tags=["auth"])
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/login")
async def login(body: LoginRequest, response: Response):
    # Timing-attack resistant user lookup
    # Always check password even if user not found to prevent user enumeration
    DUMMY_HASH = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU7fVKgL.E2K"

    result = supabase.table("users").select("*").eq("email", body.username).execute()
    if not result.data:
        result = supabase.table("users").select("*").eq("name", body.username).execute()

    user = result.data[0] if result.data else None
    password_hash = user.get("password_hash", DUMMY_HASH) if user else DUMMY_HASH

    # Always verify password to prevent timing attacks
    password_valid = verify_password(body.password, password_hash)

    if not user or not password_valid:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Get team to find org
    team_result = supabase.table("team_members").select("team_id").eq("user_id", str(user["id"])).execute()
    org_id = None
    if team_result.data:
        team = supabase.table("teams").select("org_id").eq("id", team_result.data[0]["team_id"]).execute()
        if team.data:
            org_id = str(team.data[0].get("org_id", ""))

    access_token  = create_access_token(str(user["id"]), user.get("role", "user"), org_id)
    refresh_token = create_refresh_token(str(user["id"]))

    log_action("user.login", "user", str(user["id"]), user_id=str(user["id"]), org_id=org_id)

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
            "org_id":   org_id,
        }
    }

@router.post("/refresh")
async def refresh(body: RefreshRequest):
    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user_id = payload["sub"]
    result = supabase.table("users").select("*").eq("id", int(user_id)).execute()
    if not result.data:
        raise HTTPException(status_code=401, detail="User not found")
    user = result.data[0]
    access_token = create_access_token(user_id, user.get("role", "user"))
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
async def me(user: CurrentUser = Depends(get_current_user)):
    return {"user_id": user.user_id, "role": user.role, "org_id": user.org_id, "via": user.via}

@router.post("/logout")
async def logout(user: CurrentUser = Depends(get_current_user)):
    log_action("user.logout", "user", user.user_id, user_id=user.user_id)
    return {"ok": True}

@router.patch("/password")
async def change_password(body: ChangePasswordRequest, user: CurrentUser = Depends(get_current_user)):
    # Password validation now handled by Pydantic model
    result = supabase.table("users").select("password_hash").eq("id", int(user.user_id)).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    if not verify_password(body.current_password, result.data[0]["password_hash"]):
        raise HTTPException(status_code=401, detail="Wrong current password")
    new_hash = hash_password(body.new_password)
    supabase.table("users").update({"password_hash": new_hash}).eq("id", int(user.user_id)).execute()
    log_action("user.password_changed", "user", user.user_id, user_id=user.user_id)
    return {"ok": True}
