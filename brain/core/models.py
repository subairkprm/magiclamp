"""
MagicLamp Domain Models
Pydantic models for core entities with multi-tenant support.
Every model includes tenant_id for data isolation.
"""
from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
import re


# ── BASE MODEL ────────────────────────────────────
class TenantModel(BaseModel):
    """Base model for all tenant-scoped entities."""
    tenant_id: str = Field(..., description="Tenant identifier for data isolation")

    class Config:
        # Allow ORM mode for Supabase responses
        from_attributes = True
        # Use alias for org_id -> tenant_id mapping if needed
        populate_by_name = True


# ── USER MODELS ───────────────────────────────────
class User(TenantModel):
    """User entity with authentication and authorization."""
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password_hash: str
    role: Literal["user", "admin", "agent", "super_admin"] = "user"
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    @validator('name')
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()


class Team(TenantModel):
    """Team/Group within a tenant."""
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TeamMember(TenantModel):
    """Association between users and teams."""
    id: Optional[str] = None
    team_id: str
    user_id: str
    role: Literal["member", "agent", "lead"] = "member"
    created_at: Optional[datetime] = None


# ── BRAIN MODELS ──────────────────────────────────
class Fact(TenantModel):
    """Knowledge fact stored in the brain."""
    id: Optional[str] = None
    key: str = Field(..., min_length=1, max_length=255)
    value: Any
    source: str = Field(default="api", max_length=100)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @validator('key')
    def key_valid(cls, v):
        if not re.match(r'^[a-z0-9._-]+$', v):
            raise ValueError("Key must contain only lowercase letters, numbers, dots, underscores, and dashes")
        return v


class Event(TenantModel):
    """Observable event in the system."""
    id: Optional[str] = None
    event_type: str = Field(..., max_length=100)
    category: str = Field(default="general", max_length=100)
    data: Dict[str, Any] = Field(default_factory=dict)
    summary: str = Field(default="", max_length=500)
    importance: int = Field(default=1, ge=1, le=5)
    created_at: Optional[datetime] = None

    @validator('event_type', 'category')
    def type_valid(cls, v):
        if not re.match(r'^[a-z0-9_-]+$', v):
            raise ValueError("Type must contain only lowercase letters, numbers, underscores, and dashes")
        return v


class TrainingData(TenantModel):
    """Training data for AI model fine-tuning."""
    id: Optional[str] = None
    input: str = Field(..., min_length=1, max_length=10000)
    output: str = Field(..., min_length=1, max_length=10000)
    source: str = Field(default="manual", max_length=100)
    quality: float = Field(default=1.0, ge=0.0, le=2.0)
    verified: bool = False
    context: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


class Decision(TenantModel):
    """AI-made decision record."""
    id: Optional[str] = None
    trigger: str = Field(..., max_length=1000)
    reasoning: str = Field(..., max_length=2000)
    action: str = Field(..., max_length=500)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    outcome: Optional[str] = None
    created_at: Optional[datetime] = None


class Analysis(TenantModel):
    """Brain self-analysis record."""
    id: Optional[str] = None
    subject: str = Field(..., max_length=200)
    analysis: str = Field(..., min_length=1)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None


# ── TASK MODELS ───────────────────────────────────
class Task(TenantModel):
    """Background task tracking."""
    task_id: str = Field(..., description="Unique task identifier")
    task_type: Literal["reason_lead", "reason_ask", "reason_decide", "custom"] = "custom"
    status: Literal["processing", "completed", "failed"] = "processing"
    user_id: str
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        populate_by_name = True


# ── ORGANIZATION MODELS ───────────────────────────
class Organization(BaseModel):
    """Organization/Tenant entity. Note: No tenant_id since this IS the tenant."""
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100)
    plan: Literal["free", "starter", "professional", "enterprise"] = "free"
    is_active: bool = True
    settings: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @validator('slug')
    def slug_valid(cls, v):
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError("Slug must contain only lowercase letters, numbers, and dashes")
        return v.lower()

    class Config:
        from_attributes = True
        populate_by_name = True


# ── API KEY MODELS ────────────────────────────────
class APIKey(TenantModel):
    """API key for programmatic access."""
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=100)
    key_hash: str
    key_prefix: str = Field(..., max_length=20)
    scopes: List[str] = Field(default_factory=list)
    is_active: bool = True
    created_by: str
    last_used_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


# ── WEBHOOK MODELS ────────────────────────────────
class Webhook(TenantModel):
    """Webhook configuration for event notifications."""
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=100)
    url: str = Field(..., min_length=1, max_length=500)
    events: List[str] = Field(default_factory=list)
    is_active: bool = True
    secret: Optional[str] = None
    last_called: Optional[datetime] = None
    failure_count: int = 0
    created_at: Optional[datetime] = None

    @validator('url')
    def url_valid(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError("Webhook URL must start with http:// or https://")
        return v


# ── INTEGRATION MODELS ────────────────────────────
class Integration(TenantModel):
    """External service integration."""
    id: Optional[str] = None
    type: str = Field(..., max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    config: Dict[str, Any] = Field(default_factory=dict)
    status: Literal["active", "inactive", "error"] = "inactive"
    last_sync: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ── AUDIT LOG MODELS ──────────────────────────────
class AuditLog(TenantModel):
    """Audit trail for all tenant actions."""
    id: Optional[str] = None
    action: str = Field(..., max_length=100)
    resource_type: str = Field(..., max_length=50)
    resource_id: Optional[str] = None
    user_id: Optional[str] = None
    old_data: Optional[Dict[str, Any]] = None
    new_data: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: Optional[datetime] = None

    @validator('action')
    def action_valid(cls, v):
        if not re.match(r'^[a-z0-9._-]+$', v):
            raise ValueError("Action must contain only lowercase letters, numbers, dots, underscores, and dashes")
        return v


# ── SUBSCRIPTION MODELS ───────────────────────────
class SubscriptionPlan(BaseModel):
    """Subscription plan definition. Global, not tenant-scoped."""
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=50)
    price_monthly: float = Field(default=0.0, ge=0.0)
    price_yearly: float = Field(default=0.0, ge=0.0)
    features: Dict[str, Any] = Field(default_factory=dict)
    limits: Dict[str, int] = Field(default_factory=dict)
    is_active: bool = True
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        populate_by_name = True
