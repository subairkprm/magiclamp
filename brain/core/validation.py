"""
MagicLamp — Input Validation Models
Comprehensive Pydantic models for API input validation and security.
"""

from pydantic import BaseModel, ConfigDict, Field, EmailStr, field_validator
from typing import Optional, List, Dict, Any, Literal, Annotated
import re
import socket
import ipaddress
import urllib.parse

# ── STRICT BASE MODEL ────────────────────────────────────────


class StrictBaseModel(BaseModel):
    """Base model with strict type checking to prevent silent coercion."""

    model_config = ConfigDict(strict=True)


# ── PASSWORD VALIDATION ──────────────────────────────────────


class PasswordValidator:
    """Enhanced password validation with security best practices"""

    MIN_LENGTH = 12
    COMMON_PASSWORDS_FILE = None  # Could load from file in production

    # Expanded list of the most commonly used weak passwords
    _HARDCODED_COMMON_PASSWORDS = {
        "password", "123456", "qwerty", "admin", "letmein", "welcome",
        "password1", "password123", "123456789", "12345678", "12345",
        "1234567", "1234567890", "abc123", "iloveyou", "monkey", "dragon",
        "master", "superman", "batman", "trustno1", "sunshine", "princess",
        "shadow", "michael", "jessica", "charlie", "donald", "football",
        "baseball", "soccer", "hockey", "pokemon", "starwars", "minecraft",
        "qwerty123", "qwertyuiop", "asdfghjkl", "zxcvbnm", "passw0rd",
        "p@ssword", "p@ssw0rd", "password!", "pass123", "pass1234",
        "admin123", "admin1234", "root", "root123", "toor", "test",
        "test123", "guest", "guest123", "user", "user123", "login",
        "login123", "secret", "secret123", "changeme", "change123",
        "1q2w3e4r", "1q2w3e", "qazwsx", "zaq12wsx", "qweasd",
        "aaaaaa", "aaaaaaaaaaaa", "111111", "111111111111", "000000",
        "696969", "123123", "654321", "987654321", "121212",
        "abcdef", "abcdefgh", "abcdefghij", "abcdefghijkl",
        "whatever", "nothing", "blahblah", "hello", "hello123",
        "freedom", "love", "cheese", "butter", "cookie", "cake",
        "computer", "internet", "website", "network", "server",
        "superman1", "batman1", "spiderman", "ironman", "captain",
    }

    @classmethod
    def load_common_passwords(cls) -> set:
        """
        Load common passwords from file if available, falling back to
        the hardcoded set.
        """
        if cls.COMMON_PASSWORDS_FILE:
            try:
                with open(cls.COMMON_PASSWORDS_FILE, "r", encoding="utf-8") as f:
                    passwords = {line.strip().lower() for line in f if line.strip()}
                    if passwords:
                        return passwords
            except (OSError, IOError):
                pass
        return cls._HARDCODED_COMMON_PASSWORDS

    @staticmethod
    def validate(password: str) -> tuple[bool, Optional[str]]:
        """
        Validate password strength
        Returns: (is_valid, error_message)
        """
        if len(password) < PasswordValidator.MIN_LENGTH:
            return False, f"Password must be at least {PasswordValidator.MIN_LENGTH} characters"

        # Check for at least one uppercase
        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter"

        # Check for at least one lowercase
        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter"

        # Check for at least one digit
        if not re.search(r"\d", password):
            return False, "Password must contain at least one number"

        # Check for at least one special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least one special character"

        # Check against common passwords
        common_passwords = PasswordValidator.load_common_passwords()
        if password.lower() in common_passwords:
            return False, "Password is too common and easily guessed"

        return True, None


# ── AUTH MODELS ──────────────────────────────────────────────


class LoginRequest(StrictBaseModel):
    username: Annotated[str, Field(min_length=3, max_length=255, strip_whitespace=True)]
    password: str = Field(..., min_length=6)

    @field_validator("username")
    @classmethod
    def username_valid(cls, v):
        # Strict allowlist: alphanumeric, underscore, dash only.
        # SQL injection must be prevented at the DB layer via parameterized queries.
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Username can only contain letters, numbers, underscore, and dash")
        return v.lower().strip()


class ChangePasswordRequest(StrictBaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=12)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v):
        is_valid, error = PasswordValidator.validate(v)
        if not is_valid:
            raise ValueError(error)
        return v


class CreateUserRequest(StrictBaseModel):
    username: Annotated[str, Field(min_length=3, max_length=50, strip_whitespace=True)]
    email: EmailStr
    password: str = Field(..., min_length=12)
    role: Literal["user", "admin", "agent"] = "user"
    team_id: Optional[int] = None

    @field_validator("username")
    @classmethod
    def username_valid(cls, v):
        # Only allow alphanumeric, underscore, dash
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Username can only contain letters, numbers, underscore, and dash")
        return v.lower()

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        is_valid, error = PasswordValidator.validate(v)
        if not is_valid:
            raise ValueError(error)
        return v


# ── BRAIN API MODELS ─────────────────────────────────────────


class RememberRequest(StrictBaseModel):
    key: Annotated[str, Field(pattern=r"^[a-z0-9._-]+$", min_length=1, max_length=100)]
    value: Any
    source: Optional[str] = Field(default="api", max_length=50)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    @field_validator("key")
    @classmethod
    def key_no_injection(cls, v):
        # Prevent key injection attacks
        forbidden = ["__", "admin", "system", "root", "config"]
        if any(f in v.lower() for f in forbidden):
            raise ValueError("Key contains forbidden pattern")
        return v


class ObserveRequest(StrictBaseModel):
    text: Annotated[str, Field(min_length=1, max_length=5000, strip_whitespace=True)]
    event_type: Optional[str] = Field(default="observation", max_length=50)
    category: Optional[str] = Field(default="general", max_length=50)
    metadata: Optional[Dict[str, Any]] = None
    importance: int = Field(default=1, ge=1, le=5)

    @field_validator("event_type", "category")
    @classmethod
    def no_special_chars(cls, v):
        if v and not re.match(r"^[a-z0-9_-]+$", v):
            raise ValueError("Only lowercase letters, numbers, underscore, and dash allowed")
        return v


class ReasonLeadRequest(StrictBaseModel):
    lead: Dict[str, Any] = Field(..., description="Lead data for analysis")

    @field_validator("lead")
    @classmethod
    def validate_lead(cls, v):
        # Pydantic already enforces Dict[str, Any]; just guard against huge payloads.
        if len(str(v)) > 10000:  # Prevent DoS via huge payloads
            raise ValueError("Lead data too large")
        return v


class ReasonAskRequest(StrictBaseModel):
    question: Annotated[str, Field(min_length=5, max_length=1000, strip_whitespace=True)]

    @field_validator("question")
    @classmethod
    def sanitize_question(cls, v):
        # Remove potential XSS/injection attempts.
        # NOTE: For production use a proper sanitization library such as nh3 or bleach.
        forbidden = [
            "<script", "javascript:", "onerror=", "onclick=", "onload=",
            "onmouseover=", "onfocus=", "<svg", "<object", "<embed",
            "<form", "data:text/html", "<base", "<link", "vbscript:",
            "expression(", "<iframe",
        ]
        if any(pattern in v.lower() for pattern in forbidden):
            raise ValueError("Question contains forbidden content")
        return v


class ReasonDecideRequest(StrictBaseModel):
    situation: Annotated[str, Field(min_length=5, max_length=2000, strip_whitespace=True)]
    options: Optional[List[str]] = Field(default=None, max_length=20)

    @field_validator("options")
    @classmethod
    def validate_options(cls, v):
        if v:
            for option in v:
                if len(option) > 200:
                    raise ValueError("Option text too long")
        return v


class TrainingAddRequest(StrictBaseModel):
    input_text: Annotated[str, Field(min_length=1, max_length=5000)]
    output_text: Annotated[str, Field(min_length=1, max_length=5000)]
    source: Optional[str] = Field(default="manual", max_length=50)
    quality: float = Field(default=1.0, ge=0.0, le=1.0)


class RecordChangeRequest(StrictBaseModel):
    what: Annotated[str, Field(min_length=1, max_length=100, strip_whitespace=True)]
    from_val: Optional[str] = Field(default="", max_length=500)
    to_val: Optional[str] = Field(default="", max_length=500)
    reason: Optional[str] = Field(default="", max_length=500)


# ── ADMIN API MODELS ─────────────────────────────────────────


class CreateOrgRequest(StrictBaseModel):
    name: Annotated[str, Field(min_length=2, max_length=100, strip_whitespace=True)]
    slug: Annotated[str, Field(pattern=r"^[a-z0-9-]+$", min_length=2, max_length=50)]
    plan: Literal["free", "starter", "pro", "enterprise"] = "free"

    @field_validator("slug")
    @classmethod
    def slug_valid(cls, v):
        if v.startswith("-") or v.endswith("-"):
            raise ValueError("Slug cannot start or end with dash")
        return v


class UpdateOrgRequest(StrictBaseModel):
    name: Optional[Annotated[str, Field(min_length=2, max_length=100)]] = None
    plan: Optional[Literal["free", "starter", "pro", "enterprise"]] = None
    status: Optional[Literal["active", "suspended", "deleted"]] = None


class CreateAPIKeyRequest(StrictBaseModel):
    name: Annotated[str, Field(min_length=3, max_length=100, strip_whitespace=True)]
    scopes: List[str] = Field(default=["read"], max_length=20)

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, v):
        allowed_scopes = {"read", "write", "admin", "leads", "memory", "training"}
        for scope in v:
            if scope not in allowed_scopes:
                raise ValueError(f"Invalid scope: {scope}")
        return v


class CreateWebhookRequest(StrictBaseModel):
    name: Annotated[str, Field(min_length=3, max_length=100)]
    url: Annotated[str, Field(pattern=r"^https?://.+", max_length=500)]
    events: List[str] = Field(default=[], max_length=50)

    @field_validator("url")
    @classmethod
    def url_secure(cls, v):
        # Enforce HTTPS in production
        if not v.startswith("https://"):
            # Warning: allowing http for development
            pass
        # Prevent SSRF: resolve the hostname to an IP and reject private/reserved ranges.
        # Simple substring matching is trivially bypassed (e.g. nip.io redirects, IPv6, hex IPs).
        parsed = urllib.parse.urlparse(v)
        hostname = parsed.hostname
        if not hostname:
            raise ValueError("Webhook URL must have a valid hostname")
        try:
            # getaddrinfo returns resolved IP(s); use the first result
            addr_infos = socket.getaddrinfo(hostname, None)
            for addr_info in addr_infos:
                ip_str = addr_info[4][0]
                ip = ipaddress.ip_address(ip_str)
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                    raise ValueError("Webhook URL cannot point to internal network")
                # Also block IPv6 loopback explicitly
                if ip_str == "::1":
                    raise ValueError("Webhook URL cannot point to internal network")
        except (socket.gaierror, ValueError) as exc:
            if "Webhook URL" in str(exc):
                raise
            raise ValueError(f"Webhook URL hostname could not be resolved: {hostname}") from exc
        return v

    @field_validator("events")
    @classmethod
    def validate_events(cls, v):
        allowed_events = {
            "lead.created",
            "lead.updated",
            "user.login",
            "decision.made",
            "memory.updated",
            "training.completed",
        }
        for event in v:
            if event not in allowed_events:
                raise ValueError(f"Invalid event: {event}")
        return v


class AuditLogQuery(StrictBaseModel):
    limit: int = Field(default=50, ge=1, le=1000)
    action: Optional[Annotated[str, Field(max_length=100)]] = None

    @field_validator("action")
    @classmethod
    def sanitize_action(cls, v):
        if v:
            # Strict allowlist: only alphanumeric, underscore, dot, dash.
            # SQL injection must be prevented at the DB layer via parameterized queries.
            if not re.match(r"^[a-zA-Z0-9_.\-]+$", v):
                raise ValueError("Action contains invalid characters")
        return v


class ResetPasswordRequest(StrictBaseModel):
    password: str = Field(..., min_length=12)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        is_valid, error = PasswordValidator.validate(v)
        if not is_valid:
            raise ValueError(error)
        return v


# ── RATE LIMITING HELPERS ────────────────────────────────────


def get_client_ip(request) -> str:
    """Extract client IP for rate limiting.

    WARNING: X-Forwarded-For is client-controlled and must only be trusted
    when the application is deployed behind a known, trusted reverse proxy.
    The rightmost IP is used because it is appended by the closest trusted
    proxy, making it harder to spoof than the leftmost value.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """Sanitize string input to prevent injection attacks.

    NOTE: For production use a proper sanitization library such as nh3 or
    bleach rather than this blocklist, which may miss novel attack vectors.
    """
    if not value:
        return ""

    # Remove null bytes
    value = value.replace("\x00", "")

    # Limit length
    value = value[:max_length]

    # Remove suspicious patterns
    suspicious = [
        "<script",
        "</script",
        "javascript:",
        "onerror=",
        "onclick=",
        "onload=",
        "onmouseover=",
        "onfocus=",
        "<svg",
        "<object",
        "<embed",
        "<form",
        "data:text/html",
        "<base",
        "<link",
        "vbscript:",
        "expression(",
        "<iframe",
        "eval(",
        "DROP TABLE",
        "DELETE FROM",
        "INSERT INTO",
        "--",
        "/*",
        "*/",
        "UNION SELECT",
    ]

    for pattern in suspicious:
        if pattern.lower() in value.lower():
            # Rather than just removing, reject the input
            raise ValueError(f"Input contains forbidden pattern: {pattern}")

    return value.strip()
