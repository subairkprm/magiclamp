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
        if not values.get("SUPABASE_SERVICE_KEY"):
            env_key = os.environ.get("SUPABASE_KEY", "")
            if not env_key:
                raise ValueError(
                    "Supabase key is required: set SUPABASE_SERVICE_KEY or SUPABASE_KEY"
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
