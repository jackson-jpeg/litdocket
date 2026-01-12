# Force rebuild: 2026-01-09 23:25 - STRIPPED DeadlineChain to bare minimum (id, case_id, parent_deadline_id)
print("--- SYSTEM REBOOT: LOADING COMPULAW ENGINE V2.9 (BARE MINIMUM SCHEMA) ---")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import logging
import time
import traceback

from app.config import settings
from app.database import engine
from app.models import Base
from app.api.v1.router import api_router
from app.middleware.security import (
    limiter,
    SecurityHeadersMiddleware,
    rate_limit_exceeded_handler,
    TRUSTED_HOSTS,
)
# WebSocket disabled for MVP - can re-enable for production
# from app.websocket.routes import websocket_endpoint

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="LitDocket API",
    description="Legal docketing and case management with AI-powered analysis",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# =============================================================================
# SECURITY MIDDLEWARE (ORDER MATTERS!)
# =============================================================================

# 1. Rate Limiter - Register with app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# 2. Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# 3. Trusted Host Middleware (only in production)
if not settings.DEBUG:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=TRUSTED_HOSTS)

# CORS middleware - Strict Production Configuration
# Use CORS origins from config - allows for environment-specific configuration
# including Vercel preview URLs
CORS_ORIGINS = settings.ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# Global exception handler to ensure errors return proper CORS headers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch all unhandled exceptions and return a proper JSON response with CORS headers.
    This prevents CORS errors when the server has an internal error.
    """
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}")
    logger.error(traceback.format_exc())

    # Get origin from request
    origin = request.headers.get("origin", "")

    # Build response with CORS headers
    response = JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.DEBUG else "An unexpected error occurred"
        }
    )

    # Add CORS headers manually for error responses
    if origin in CORS_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"

    return response


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.info(f"{request.method} {request.url.path} - {process_time:.2f}s")
    return response

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "LitDocket API"
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "LitDocket API",
        "docs": "/api/docs",
        "health": "/health"
    }

# Include API router
app.include_router(api_router, prefix="/api/v1")

# WebSocket routes - DISABLED FOR MVP
# Re-enable when deploying with proper WebSocket infrastructure
# @app.websocket("/ws/cases/{case_id}")
# async def websocket_case_room(websocket: WebSocket, case_id: str, token: str):
#     """
#     WebSocket endpoint for case room real-time communication.
#
#     Connect with: ws://localhost:8000/ws/cases/{case_id}?token={jwt_token}
#     """
#     await websocket_endpoint(websocket, case_id, token)

# Create database tables on startup
@app.on_event("startup")
async def startup():
    logger.info("=" * 60)
    logger.info("Starting LitDocket API...")
    logger.info("=" * 60)

    # Configuration validation
    if settings.DEBUG:
        logger.warning("⚠️  DEBUG MODE ENABLED - Disable for production!")

    # Log configuration summary (without sensitive values)
    logger.info(f"Environment: {'DEVELOPMENT' if settings.DEBUG else 'PRODUCTION'}")
    logger.info(f"CORS Origins: {len(settings.ALLOWED_ORIGINS)} configured")
    logger.info(f"Database: {'SQLite' if 'sqlite' in settings.DATABASE_URL.lower() else 'PostgreSQL'}")
    logger.info(f"Database URL: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")

    # Validate critical settings
    if not settings.SECRET_KEY or len(settings.SECRET_KEY) < 32:
        logger.error("SECRET_KEY is missing or too short!")
    if not settings.JWT_SECRET_KEY or len(settings.JWT_SECRET_KEY) < 32:
        logger.error("JWT_SECRET_KEY is missing or too short!")
    if not settings.ANTHROPIC_API_KEY or not settings.ANTHROPIC_API_KEY.startswith('sk-ant-'):
        logger.error("ANTHROPIC_API_KEY is missing or invalid!")

    # CRITICAL: Database backups moved to separate cron job (Railway kills container if startup takes >30s)
    # Move to background worker or scheduled task - DO NOT run on startup!
    # from app.utils.db_backup import auto_backup_on_startup
    # auto_backup_on_startup(settings.DATABASE_URL)

    # Create database tables - only for SQLite (local dev)
    # PostgreSQL schema is managed by Supabase migrations, not SQLAlchemy
    if "sqlite" in settings.DATABASE_URL.lower():
        logger.info("Creating database tables (SQLite)...")
        Base.metadata.create_all(bind=engine)
    else:
        logger.info("Using PostgreSQL - schema managed by Supabase migrations")

    logger.info("=" * 60)
    logger.info("Application startup complete")
    logger.info(f"API docs available at: /api/docs")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown():
    logger.info("Application shutdown")
