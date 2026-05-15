"""
MagicLamp — Centralized Configuration
All config validated at startup. No silent failures.
"""
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from functools import lru_cache
from typing import Optional
from urllib.parse import urlparse

class Settings(BaseSettings):
    # ── Identity ────────────────────────────
    APP_NAME:        str = "MagicLamp"
    APP_VERSION:     str = "1.0.0"
    ENVIRONMENT:     str = Field(default="production", alias="ENV")

    # ── Supabase ────────────────────────────
    SUPABASE_URL:    str = Field(..., alias="SUPABASE_URL")
    SUPABASE_KEY:    str = Field(..., alias="SUPABASE_SERVICE_KEY")

    # ── Ollama ──────────────────────────────
    OLLAMA_URL:      str = Field(default="http://ollama:11434")
    OLLAMA_MODEL:    str = Field(default="qwen2.5:7b")
    OLLAMA_TIMEOUT:  int = Field(default=120)

    # ── Auth ────────────────────────────────
    JWT_SECRET:      str = Field(..., alias="JWT_SECRET")
    JWT_ALGORITHM:   str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS:   int = 30
    BRAIN_API_KEY:   str = Field(..., alias="BRAIN_SECRET")

    # ── Telegram ────────────────────────────
    TELEGRAM_TOKEN:  Optional[str] = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    TELEGRAM_ADMIN:  Optional[str] = Field(default=None, alias="TELEGRAM_ADMIN_CHAT_ID")

    # ── N8N ─────────────────────────────────
    N8N_URL:         str = Field(default="http://n8n:5678")
    N8N_API_KEY:     Optional[str] = Field(default=None, alias="N8N_API_KEY")

    # ── Brain ───────────────────────────────
    DATA_DIR:        str = Field(default="/data/brain", alias="BRAIN_DATA_DIR")
    AUTO_MODE:       bool = Field(default=True, alias="BRAIN_AUTO_MODE")

    # ── Rate Limiting ───────────────────────
    RATE_LIMIT_DEFAULT:  str = "100/minute"
    RATE_LIMIT_AI:       str = "20/minute"
    RATE_LIMIT_AUTH:     str = "5/minute"

    # ── CORS ─────────────────────────────────
    CORS_ORIGINS:        str = Field(default="*", alias="CORS_ALLOWED_ORIGINS")

    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, v: str, info) -> str:
        """
        Validate CORS origins based on environment.
        In production, wildcard origins are not allowed.
        """
        # Get environment from the validation context
        env = info.data.get("ENVIRONMENT", "production")

        # Non-production: allow pure wildcard but reject '*' mixed with other origins
        if env != "production":
            if "*" in v and v.strip() != "*":
                raise ValueError(
                    "CORS_ALLOWED_ORIGINS cannot mix '*' with explicit origins. "
                    "Use either '*' alone or a list of explicit URLs."
                )
            return v

        # Production environment must have explicit origins
        # Reject wildcard
        if v.strip() == "*":
            raise ValueError(
                "CORS_ORIGINS='*' is not allowed in production. "
                "Set explicit origins: CORS_ALLOWED_ORIGINS=https://app.example.com,https://ops.example.com"
            )

        # Reject empty or whitespace-only
        if not v or not v.strip():
            raise ValueError(
                "CORS_ORIGINS cannot be empty in production. "
                "Set explicit origins: CORS_ALLOWED_ORIGINS=https://app.example.com"
            )

        # Check each origin for wildcards and structural validity
        origins = [origin.strip() for origin in v.split(",")]
        for origin in origins:
            if not origin:
                raise ValueError(
                    "CORS_ALLOWED_ORIGINS contains an empty entry. "
                    "Use comma-separated explicit URLs only."
                )

            if "*" in origin:
                raise ValueError(
                    f"CORS origin '{origin}' contains wildcard '*' which is not allowed in production. "
                    f"Use explicit full URLs only."
                )

            # Parse with urlparse: require scheme + netloc, reject path/query/fragment
            parsed = urlparse(origin)
            if parsed.scheme not in ("http", "https"):
                raise ValueError(
                    f"CORS origin '{origin}' must start with http:// or https://. "
                    f"Example: https://app.example.com"
                )
            if not parsed.netloc:
                raise ValueError(
                    f"CORS origin '{origin}' has no host. "
                    f"Use the format https://hostname or https://hostname:port"
                )
            if parsed.path and parsed.path != "/":
                raise ValueError(
                    f"CORS origin '{origin}' must not contain a path. "
                    f"Use scheme://host[:port] only (e.g. https://app.example.com)"
                )
            if parsed.query:
                raise ValueError(
                    f"CORS origin '{origin}' must not contain a query string. "
                    f"Use scheme://host[:port] only"
                )
            if parsed.fragment:
                raise ValueError(
                    f"CORS origin '{origin}' must not contain a fragment. "
                    f"Use scheme://host[:port] only"
                )

        return v

    class Config:
        env_file = ".env"
        case_sensitive = False
        populate_by_name = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
