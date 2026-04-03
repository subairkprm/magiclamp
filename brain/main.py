"""
MagicLamp Brain — Master Control Server
Starts all modules, event bus, scheduler, and API server.
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from core.config import settings
from core.logger import get_logger
from core.registry import registry
from core.bus import bus
from core.audit import AuditMiddleware
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
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── MIDDLEWARE ────────────────────────────────
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(AuditMiddleware)

# ── ROUTES ────────────────────────────────────
app.include_router(auth.router,       prefix="/api/v1")
app.include_router(admin.router,      prefix="/api/v1")
app.include_router(brain_api.router,  prefix="/api/v1")

# ── HEALTH ────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.APP_VERSION, "app": settings.APP_NAME}

@app.get("/")
async def root():
    return {
        "app":     settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs":    "/docs",
        "health":  "/health",
    }
