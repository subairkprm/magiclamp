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

log = get_logger("main")

# Import API routes after limiter is defined
from api.v1 import auth, admin, brain as brain_api


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
    docs_url="/docs",
    redoc_url="/redoc",
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
# Configure CORS based on environment
allowed_origins = ["*"]  # Default to allow all for development
if settings.CORS_ORIGINS and settings.CORS_ORIGINS != "*":
    # In production, use specific origins
    allowed_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]

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
    return {"status": "ok", "version": settings.APP_VERSION, "app": settings.APP_NAME}


@app.get("/")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
async def root(request: Request):
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }
