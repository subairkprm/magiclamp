"""
MagicLamp — Centralized Configuration
All config validated at startup. No silent failures.
"""
import os
from pydantic_settings import BaseSettings
from pydantic import AliasChoices, Field, field_validator
from functools import lru_cache
from typing import Optional
from urllib.parse import urlparse


class Settings(BaseSettings):
    APP_NAME:        str = "MagicLamp"
    APP_VERSION:     str = "1.0.0"
    ENVIRONMENT:     str = Field(default="production", alias="ENV")

    SUPABASE_URL:    str = Field(..., alias="SUPABASE_URL")
    SUPABASE_KEY:    Optional[str] = Field(default=None, alias="SUPABASE_SERVICE_KEY")

    OLLAMA_URL:      str = Field(default="http://localhost:11434")
    OLLAMA_MODEL:    str = Field(default="qwen2.5:7b")
    OLLAMA_TIMEOUT:  int = Field(default=120)

    JWT_SECRET:      str = Field(..., alias="JWT_SECRET")
    JWT_ALGORITHM:   str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    BRAIN_API_KEY: str = Field(default="", alias="BRAIN_SECRET")

    TELEGRAM_TOKEN:  Optional[str] = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    TELEGRAM_ADMIN:  Optional[str] = Field(default=None, alias="TELEGRAM_ADMIN_CHAT_ID")

    N8N_URL:         str = Field(default="http://n8n:5678")
    N8N_API_KEY:     Optional[str] = Field(default=None, alias="N8N_API_KEY")

    DATA_DIR:        str = Field(default="./data/brain", alias="BRAIN_DATA_DIR")
    AUTO_MODE:       bool = Field(default=False, alias="BRAIN_AUTO_MODE")

    RATE_LIMIT_DEFAULT:  str = "100/minute"
    RATE_LIMIT_AI:       str = "20/minute"
    RATE_LIMIT_AUTH:     str = "5/minute"

    # Canonical env var: CORS_ALLOWED_ORIGINS
    # Backward compatibility: CORS_ORIGINS is also accepted
    CORS_ORIGINS:        str = Field(default="*", validation_alias=AliasChoices("CORS_ALLOWED_ORIGINS", "CORS_ORIGINS"))

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
                "Set explicit origins using CORS_ALLOWED_ORIGINS (canonical): https://app.example.com,https://ops.example.com"
            )

        # Reject empty or whitespace-only
        if not v or not v.strip():
            raise ValueError(
                "CORS_ORIGINS cannot be empty in production. "
                "Set explicit origins using CORS_ALLOWED_ORIGINS (canonical): https://app.example.com"
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
            # Normalize trailing slash before parsing so https://app.example.com/ is treated as https://app.example.com
            origin_normalized = origin.rstrip("/")
            parsed = urlparse(origin_normalized)
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
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
