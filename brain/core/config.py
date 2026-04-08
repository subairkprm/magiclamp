"""
MagicLamp — Centralized Configuration
All config validated at startup. No silent failures.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from typing import Optional

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

    # ── Redis ────────────────────────────────
    REDIS_URL:           str = Field(default="redis://localhost:6379", alias="REDIS_URL")

    # ── OpenAI ───────────────────────────────
    OPENAI_API_KEY:      Optional[str] = Field(default=None, alias="OPENAI_API_KEY")

    class Config:
        env_file = ".env"
        case_sensitive = False
        populate_by_name = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
