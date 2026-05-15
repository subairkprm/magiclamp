"""
MagicLamp Brain — Master Control Server
Starts all modules, event bus, scheduler, and API server.
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from prometheus_fastapi_instrumentator import Instrumentator

from core.config import settings
from core.logger import get_logger
from core.registry import registry
from core.bus import bus
from core.audit import AuditMiddleware
from core.exceptions import MagicLampException
from core.limiter import limiter
from api.v1 import auth, admin, brain as brain_api

log = get_logger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── STARTUP ──────────────────────────────
    log.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.ENVIRONMENT}]")

    # Start event bus
    asyncio.create_task(bus.start())

    # Initialize modules
    await registry.initialize_all()

    # Start scheduler
    if settings.AUTO_MODE:
        from scheduler import auto_scheduler

        auto_scheduler.start()

    log.info("MagicLamp Brain is LIVE")
    yield

    # ── SHUTDOWN ─────────────────────────────
    log.info("MagicLamp shutting down...")
    await bus.stop()
    await registry.shutdown_all()


app = FastAPI(
    title="MagicLamp Brain API",
    description="Enterprise AI Brain — Memory, Reasoning, Training, Control",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url=None if settings.ENVIRONMENT == "production" else "/docs",
    redoc_url=None if settings.ENVIRONMENT == "production" else "/redoc",
)

# Register rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ── EXCEPTION HANDLERS ────────────────────────────
@app.exception_handler(MagicLampException)
async def magiclamp_exception_handler(request: Request, exc: MagicLampException):
    """Handle custom MagicLamp exceptions with clean JSON responses."""
    log.warning(f"MagicLamp exception: {exc.error_code} - {exc.message}", extra={"details": exc.details})
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all handler for unhandled exceptions."""
    log.error(f"Unhandled exception: {type(exc).__name__} - {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "INTERNAL_SERVER_ERROR", "message": "An unexpected error occurred", "status_code": 500},
    )


# ── PROMETHEUS METRICS ────────────────────────────
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# ── MIDDLEWARE ────────────────────────────────
# CORS: deny all cross-origin by default (CORS_ALLOWED_ORIGINS is empty).
# Set CORS_ALLOWED_ORIGINS=https://lamp.ae[,https://...] in production .env.
_raw_origins = settings.CORS_ORIGINS.strip()
if _raw_origins and _raw_origins != "*":
    # Reject any entry that is bare `*` or contains a wildcard character
    # (e.g. `https://*`) to prevent accidental open-CORS configs.
    allowed_origins = [
        o.strip()
        for o in _raw_origins.split(",")
        if o.strip() and "*" not in o
    ]
    if len(allowed_origins) < len([o for o in _raw_origins.split(",") if o.strip()]):
        log.warning("CORS: wildcard-containing origins were stripped from CORS_ALLOWED_ORIGINS — use fully-qualified URLs only")
else:
    # Empty string → no origins allowed. Wildcard `*` is blocked intentionally;
    # operators must list explicit origins.
    allowed_origins = []

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=True,
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(AuditMiddleware)

# ── ROUTES ────────────────────────────────────
app.include_router(auth.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(brain_api.router, prefix="/api/v1")


# ── HEALTH ────────────────────────────────────
@app.get("/health")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def health(request: Request):
    """Liveness + sovereign-mode posture.

    The ``deployment`` block is consumed by the admin "data-residency
    selector" UI and by PDPL audit exports (ADR 0007). It deliberately
    contains no secrets — only the *names* of the configured backend, LLM
    provider, region tag, and sovereign-mode flag.
    """
    from core.llm import get_active_provider_name

    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "app": settings.APP_NAME,
        "deployment": {
            "db_backend": settings.DB_BACKEND,
            "llm_provider": get_active_provider_name(),
            "region": settings.DEPLOYMENT_REGION,
            "sovereign_mode": settings.SOVEREIGN_MODE,
        },
    }


@app.get("/")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def root(request: Request):
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }
