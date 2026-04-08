"""
MagicLamp — Input Validation Models
Comprehensive Pydantic models for API input validation and security.
"""
from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, List, Dict, Any, Literal, Annotated
import re


# ── PASSWORD VALIDATION ──────────────────────────────────────

class PasswordValidator:
    """Enhanced password validation with security best practices"""

    MIN_LENGTH = 12
    COMMON_PASSWORDS_FILE = None  # Could load from file in production

    @staticmethod
    def validate(password: str) -> tuple[bool, Optional[str]]:
        """
        Validate password strength
        Returns: (is_valid, error_message)
        """
        if len(password) < PasswordValidator.MIN_LENGTH:
            return False, f"Password must be at least {PasswordValidator.MIN_LENGTH} characters"

        # Check for at least one uppercase
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"

        # Check for at least one lowercase
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"

        # Check for at least one digit
        if not re.search(r'\d', password):
            return False, "Password must contain at least one number"

        # Check for at least one special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least one special character"

        # Check against common passwords (simple check)
        common_weak = ['password', '123456', 'qwerty', 'admin', 'letmein', 'welcome']
        if password.lower() in common_weak:
            return False, "Password is too common and easily guessed"

        return True, None


# ── AUTH MODELS ──────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: Annotated[str, Field(min_length=3, max_length=255, strip_whitespace=True)]
    password: str = Field(..., min_length=6)

    @field_validator('username')
    @classmethod
    def username_valid(cls, v):
        # Prevent SQL injection attempts
        if any(char in v for char in ["'", '"', ';', '--', '/*', '*/']):
            raise ValueError("Invalid characters in username")
        return v.lower().strip()


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=12)

    @field_validator('new_password')
    @classmethod
    def password_strength(cls, v):
        is_valid, error = PasswordValidator.validate(v)
        if not is_valid:
            raise ValueError(error)
        return v


class CreateUserRequest(BaseModel):
    username: Annotated[str, Field(min_length=3, max_length=50, strip_whitespace=True)]
    email: EmailStr
    password: str = Field(..., min_length=12)
    role: Literal["user", "admin", "agent"] = "user"
    team_id: Optional[int] = None

    @field_validator('username')
    @classmethod
    def username_valid(cls, v):
        # Only allow alphanumeric, underscore, dash
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Username can only contain letters, numbers, underscore, and dash")
        return v.lower()

    @field_validator('password')
    @classmethod
    def password_strength(cls, v):
        is_valid, error = PasswordValidator.validate(v)
        if not is_valid:
            raise ValueError(error)
        return v


# ── BRAIN API MODELS ─────────────────────────────────────────

class RememberRequest(BaseModel):
    key: Annotated[str, Field(pattern=r'^[a-z0-9._-]+$', min_length=1, max_length=100)]
    value: Any
    source: Optional[str] = Field(default="api", max_length=50)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    @field_validator('key')
    @classmethod
    def key_no_injection(cls, v):
        # Prevent key injection attacks
        forbidden = ['__', 'admin', 'system', 'root', 'config']
        if any(f in v.lower() for f in forbidden):
            raise ValueError("Key contains forbidden pattern")
        return v


class ObserveRequest(BaseModel):
    text: Annotated[str, Field(min_length=1, max_length=5000, strip_whitespace=True)]
    event_type: Optional[str] = Field(default="observation", max_length=50)
    category: Optional[str] = Field(default="general", max_length=50)
    metadata: Optional[Dict[str, Any]] = None
    importance: int = Field(default=1, ge=1, le=5)

    @field_validator('event_type', 'category')
    @classmethod
    def no_special_chars(cls, v):
        if v and not re.match(r'^[a-z0-9_-]+$', v):
            raise ValueError("Only lowercase letters, numbers, underscore, and dash allowed")
        return v


class ReasonLeadRequest(BaseModel):
    lead: Dict[str, Any] = Field(..., description="Lead data for analysis")

    @field_validator('lead')
    @classmethod
    def validate_lead(cls, v):
        if not isinstance(v, dict):
            raise ValueError("Lead must be a dictionary")
        if len(str(v)) > 10000:  # Prevent DoS via huge payloads
            raise ValueError("Lead data too large")
        return v


class ReasonAskRequest(BaseModel):
    question: Annotated[str, Field(min_length=5, max_length=1000, strip_whitespace=True)]

    @field_validator('question')
    @classmethod
    def sanitize_question(cls, v):
        # Remove potential injection attempts
        if any(pattern in v.lower() for pattern in ['<script', 'javascript:', 'onerror=']):
            raise ValueError("Question contains forbidden content")
        return v


class ReasonDecideRequest(BaseModel):
    situation: Annotated[str, Field(min_length=5, max_length=2000, strip_whitespace=True)]
    options: Optional[List[str]] = Field(default=None, max_length=20)

    @field_validator('options')
    @classmethod
    def validate_options(cls, v):
        if v:
            for option in v:
                if len(option) > 200:
                    raise ValueError("Option text too long")
        return v


class TrainingAddRequest(BaseModel):
    input_text: Annotated[str, Field(min_length=1, max_length=5000)]
    output_text: Annotated[str, Field(min_length=1, max_length=5000)]
    source: Optional[str] = Field(default="manual", max_length=50)
    quality: float = Field(default=1.0, ge=0.0, le=2.0)


class RecordChangeRequest(BaseModel):
    what: Annotated[str, Field(min_length=1, max_length=100, strip_whitespace=True)]
    from_val: Optional[str] = Field(default="", max_length=500)
    to_val: Optional[str] = Field(default="", max_length=500)
    reason: Optional[str] = Field(default="", max_length=500)


# ── ADMIN API MODELS ─────────────────────────────────────────

class CreateOrgRequest(BaseModel):
    name: Annotated[str, Field(min_length=2, max_length=100, strip_whitespace=True)]
    slug: Annotated[str, Field(pattern=r'^[a-z0-9-]+$', min_length=2, max_length=50)]
    plan: Literal["free", "starter", "pro", "enterprise"] = "free"

    @field_validator('slug')
    @classmethod
    def slug_valid(cls, v):
        if v.startswith('-') or v.endswith('-'):
            raise ValueError("Slug cannot start or end with dash")
        return v


class UpdateOrgRequest(BaseModel):
    name: Optional[Annotated[str, Field(min_length=2, max_length=100)]] = None
    plan: Optional[Literal["free", "starter", "pro", "enterprise"]] = None
    status: Optional[Literal["active", "suspended", "deleted"]] = None


class CreateAPIKeyRequest(BaseModel):
    name: Annotated[str, Field(min_length=3, max_length=100, strip_whitespace=True)]
    scopes: List[str] = Field(default=["read"], max_length=20)

    @field_validator('scopes')
    @classmethod
    def validate_scopes(cls, v):
        allowed_scopes = {'read', 'write', 'admin', 'leads', 'memory', 'training'}
        for scope in v:
            if scope not in allowed_scopes:
                raise ValueError(f"Invalid scope: {scope}")
        return v


class CreateWebhookRequest(BaseModel):
    name: Annotated[str, Field(min_length=3, max_length=100)]
    url: Annotated[str, Field(pattern=r'^https?://.+', max_length=500)]
    events: List[str] = Field(default=[], max_length=50)

    @field_validator('url')
    @classmethod
    def url_secure(cls, v):
        # Enforce HTTPS in production
        if not v.startswith('https://'):
            # Warning: allowing http for development
            pass
        # Prevent SSRF to internal networks
        forbidden_hosts = ['localhost', '127.0.0.1', '0.0.0.0', '10.', '192.168.', '172.16.']
        if any(host in v.lower() for host in forbidden_hosts):
            raise ValueError("Webhook URL cannot point to internal network")
        return v

    @field_validator('events')
    @classmethod
    def validate_events(cls, v):
        allowed_events = {
            'lead.created', 'lead.updated', 'user.login', 'decision.made',
            'memory.updated', 'training.completed'
        }
        for event in v:
            if event not in allowed_events:
                raise ValueError(f"Invalid event: {event}")
        return v


class AuditLogQuery(BaseModel):
    limit: int = Field(default=50, ge=1, le=1000)
    action: Optional[Annotated[str, Field(max_length=100)]] = None

    @field_validator('action')
    @classmethod
    def sanitize_action(cls, v):
        if v:
            # Prevent SQL injection
            v = re.sub(r'[^\w\s.-]', '', v)
        return v


class ResetPasswordRequest(BaseModel):
    password: str = Field(..., min_length=12)

    @field_validator('password')
    @classmethod
    def password_strength(cls, v):
        is_valid, error = PasswordValidator.validate(v)
        if not is_valid:
            raise ValueError(error)
        return v


# ── RATE LIMITING HELPERS ────────────────────────────────────

def get_client_ip(request) -> str:
    """Extract client IP for rate limiting"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.client.host if request.client else "unknown"


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """Sanitize string input to prevent injection attacks"""
    if not value:
        return ""

    # Remove null bytes
    value = value.replace('\x00', '')

    # Limit length
    value = value[:max_length]

    # Remove suspicious patterns
    suspicious = [
        '<script', '</script', 'javascript:', 'onerror=',
        'onclick=', 'onload=', '<iframe', 'eval(',
        'DROP TABLE', 'DELETE FROM', 'INSERT INTO',
        '--', '/*', '*/', 'UNION SELECT'
    ]

    for pattern in suspicious:
        if pattern.lower() in value.lower():
            # Rather than just removing, reject the input
            raise ValueError(f"Input contains forbidden pattern: {pattern}")

    return value.strip()
