# MagicLamp Brain API

## Overview
Enterprise AI Brain system for UAE banking CRM operations. Provides autonomous memory management, intelligent reasoning, pattern analysis, and decision-making capabilities.

## Tech Stack
- **Backend**: Python 3.12 + FastAPI
- **Database**: Supabase (PostgreSQL)
- **Auth**: JWT tokens + API key + Brain key authentication
- **Rate Limiting**: SlowAPI
- **Monitoring**: Prometheus metrics
- **Logging**: structlog (structured JSON)

## Project Structure
```
brain/                  # Main application code
  main.py              # FastAPI app entry point
  scheduler.py         # Background job scheduler
  api/v1/              # API routes
    auth.py            # Authentication endpoints
    admin.py           # Admin endpoints
    brain.py           # Brain/AI endpoints
  core/                # Core modules
    config.py          # Centralized configuration (pydantic-settings)
    auth.py            # Auth utilities (JWT, password hashing, RBAC)
    audit.py           # Audit middleware
    bus.py             # Event bus
    circuit.py         # Circuit breaker for Ollama
    database.py        # Supabase database abstraction layer
    exceptions.py      # Custom exceptions
    limiter.py         # Rate limiter singleton
    logger.py          # Structured logging
    models.py          # Domain models
    registry.py        # Module registry
    validation.py      # Input validation models
  repositories/        # Data access layer
```

## Running the App
The app runs on port 5000 via:
```
cd brain && python3 -m uvicorn main:app --host 0.0.0.0 --port 5000 --reload
```

## Key Endpoints
- `GET /` - App info
- `GET /health` - Health check
- `GET /docs` - Swagger API documentation
- `GET /metrics` - Prometheus metrics
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/brain/*` - Brain API endpoints

## Environment Variables
- `SUPABASE_URL` - Supabase project URL (required)
- `SUPABASE_KEY` or `SUPABASE_SERVICE_KEY` - Supabase service role key (required)
- `JWT_SECRET` - JWT signing secret (required)
- `BRAIN_SECRET` - Brain API key (required)
- `OLLAMA_URL` - Ollama LLM URL (default: http://localhost:11434)
- `BRAIN_AUTO_MODE` - Enable auto scheduler (default: false)

## Notes
- Supabase client is lazy-initialized to handle startup gracefully
- Auto-scheduler is disabled by default for Replit environment
- `sentence-transformers` is not installed due to disk constraints (large ML package with PyTorch)
- CORS is set to allow all origins for development
- Pydantic v2 syntax used (pattern instead of regex, extra="ignore")
