"""
MagicLamp — Auth System
JWT access + refresh tokens. API key support. Full RBAC.
"""
import hashlib
import secrets
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from jose import JWTError, jwt
from supabase import create_client, Client
from core.config import settings
from core.logger import get_logger

log = get_logger("auth")

_supabase_client: Optional[Client] = None

def _get_supabase() -> Client:
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _supabase_client

bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
brain_key_header = APIKeyHeader(name="X-Brain-Key", auto_error=False)

# ── TOKEN CREATION ────────────────────────────
def create_access_token(user_id: str, role: str, org_id: str = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "role": role,
        "org_id": org_id,
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire,
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

# ── PASSWORD ──────────────────────────────────
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

# ── API KEY ───────────────────────────────────
def generate_api_key(org_id: str, name: str, scopes: list[str]) -> tuple[str, str]:
    """Returns (plain_key, key_hash). Store only the hash."""
    plain = "ml_" + secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(plain.encode()).hexdigest()
    prefix = plain[:10]
    _get_supabase().table("api_keys").insert({
        "org_id": org_id,
        "name": name,
        "key_hash": key_hash,
        "key_prefix": prefix,
        "scopes": scopes,
        "created_by": "admin",
    }).execute()
    return plain, key_hash

def verify_api_key(plain_key: str) -> Optional[dict]:
    key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
    result = _get_supabase().table("api_keys").select("*")\
        .eq("key_hash", key_hash).eq("is_active", True).execute()
    if result.data:
        key = result.data[0]
        _get_supabase().table("api_keys").update({"last_used_at": datetime.utcnow().isoformat()})\
            .eq("id", key["id"]).execute()
        return key
    return None

# ── DEPENDENCY: Current User ──────────────────
class CurrentUser:
    def __init__(self, user_id: str, role: str, org_id: str = None, via: str = "jwt"):
        self.user_id = user_id
        self.role    = role
        self.org_id  = org_id
        self.via     = via  # "jwt" | "api_key" | "brain_key"

    @property
    def is_admin(self) -> bool:
        return self.role in ("admin", "super_admin")

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    api_key: Optional[str] = Security(api_key_header),
    brain_key: Optional[str] = Security(brain_key_header),
) -> CurrentUser:
    # Brain key auth (internal services)
    if brain_key and brain_key == settings.BRAIN_API_KEY:
        return CurrentUser(user_id="brain", role="super_admin", via="brain_key")

    # API key auth
    if api_key:
        key_data = verify_api_key(api_key)
        if key_data:
            return CurrentUser(
                user_id="api_key:" + key_data["key_prefix"],
                role="api",
                org_id=key_data.get("org_id"),
                via="api_key"
            )
        raise HTTPException(status_code=401, detail="Invalid API key")

    # JWT auth
    if credentials:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        return CurrentUser(
            user_id=payload["sub"],
            role=payload.get("role", "user"),
            org_id=payload.get("org_id"),
            via="jwt"
        )

    raise HTTPException(status_code=401, detail="Authentication required")

async def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

async def require_brain_key(brain_key: str = Security(brain_key_header)) -> bool:
    if brain_key != settings.BRAIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid brain key")
    return True
