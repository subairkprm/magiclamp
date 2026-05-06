"""
MagicLamp — Centralized Configuration
All config validated at startup. No silent failures.
"""
import os
from pydantic_settings import BaseSettings
from pydantic import Field, model_validator
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    APP_NAME:        str = "MagicLamp"
    APP_VERSION:     str = "1.0.0"
    ENVIRONMENT:     str = Field(default="production", alias="ENV")

    # ── Database backend ────────────────────────
    # "sqlite" (default — no external service, ideal for Railway/single-box deploys)
    # "supabase" (use managed Postgres — requires SUPABASE_URL + SUPABASE_SERVICE_KEY)
    DB_BACKEND:      str = Field(default="sqlite", alias="DB_BACKEND")

    SUPABASE_URL:    Optional[str] = Field(default=None, alias="SUPABASE_URL")
    SUPABASE_KEY:    Optional[str] = Field(default=None, alias="SUPABASE_SERVICE_KEY")

    # ── LLM provider (pluggable) ────────────────
    # Default provider used when no per-tenant override is configured. One of:
    # openai | anthropic | groq | openrouter | gemini | ollama
    LLM_PROVIDER:    str = Field(default="openai", alias="LLM_PROVIDER")

    # Provider-specific keys & models. All optional — only the keys for the
    # provider(s) you actually use need to be set.
    OPENAI_API_KEY:     Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    OPENAI_MODEL:       str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    OPENAI_BASE_URL:    str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")

    ANTHROPIC_API_KEY:  Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    ANTHROPIC_MODEL:    str = Field(default="claude-3-5-haiku-latest", alias="ANTHROPIC_MODEL")

    GROQ_API_KEY:       Optional[str] = Field(default=None, alias="GROQ_API_KEY")
    GROQ_MODEL:         str = Field(default="llama-3.1-8b-instant", alias="GROQ_MODEL")

    OPENROUTER_API_KEY: Optional[str] = Field(default=None, alias="OPENROUTER_API_KEY")
    OPENROUTER_MODEL:   str = Field(default="openai/gpt-4o-mini", alias="OPENROUTER_MODEL")

    GOOGLE_API_KEY:     Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")
    GEMINI_MODEL:       str = Field(default="gemini-1.5-flash", alias="GEMINI_MODEL")

    LLM_TIMEOUT:        int = Field(default=120, alias="LLM_TIMEOUT")

    # ── Ollama (optional / VPS deployment) ──────
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

    CORS_ORIGINS:        str = Field(default="*", alias="CORS_ALLOWED_ORIGINS")

    # ── RAG / Vector memory ─────────────────────
    RAG_ENABLED:         bool = Field(default=False, alias="RAG_ENABLED")
    EMBEDDING_PROVIDER:  str = Field(default="local", alias="EMBEDDING_PROVIDER")  # local | ollama
    EMBEDDING_MODEL:     str = Field(default="all-MiniLM-L6-v2", alias="EMBEDDING_MODEL")
    EMBEDDING_DIM:       int = Field(default=384, alias="EMBEDDING_DIM")
    VECTOR_STORE:        str = Field(default="chroma", alias="VECTOR_STORE")  # chroma | memory
    VECTOR_STORE_PATH:   Optional[str] = Field(default=None, alias="VECTOR_STORE_PATH")
    VECTOR_COLLECTION:   str = Field(default="brain_facts", alias="VECTOR_COLLECTION")
    RAG_TOP_K:           int = Field(default=5, alias="RAG_TOP_K")
    RAG_MIN_SIMILARITY:  float = Field(default=0.0, alias="RAG_MIN_SIMILARITY")

    @model_validator(mode="before")
    @classmethod
    def resolve_supabase_key(cls, values):
        """Only enforce Supabase credentials when the Supabase backend is active.

        When DB_BACKEND=sqlite (the default), MagicLamp does not need any
        Supabase configuration at all — making the simple Railway / single-box
        deployment path zero-config beyond the LLM key.
        """
        backend = (values.get("DB_BACKEND") or os.environ.get("DB_BACKEND") or "sqlite").lower()
        if backend != "supabase":
            return values

        if not values.get("SUPABASE_URL"):
            values["SUPABASE_URL"] = os.environ.get("SUPABASE_URL")
        if not values.get("SUPABASE_URL"):
            raise ValueError(
                "DB_BACKEND=supabase requires SUPABASE_URL to be set"
            )
        if not values.get("SUPABASE_SERVICE_KEY"):
            env_key = os.environ.get("SUPABASE_KEY", "") or os.environ.get("SUPABASE_SERVICE_KEY", "")
            if not env_key:
                raise ValueError(
                    "DB_BACKEND=supabase requires SUPABASE_SERVICE_KEY (or SUPABASE_KEY)"
                )
            values["SUPABASE_SERVICE_KEY"] = env_key
        return values

    class Config:
        env_file = ".env"
        case_sensitive = False
        populate_by_name = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
