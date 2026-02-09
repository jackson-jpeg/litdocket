"""
LitDocket API - Legal docketing and case management with AI-powered analysis
"""
import sys
import logging
import time
import traceback

# Configure logging FIRST before any imports
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# =============================================================================
# IMPORTS - Split into targeted blocks for better error handling
# =============================================================================

# Standard library and framework imports (these won't fail)
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Configuration (may fail on missing environment variables)
try:
    from app.config import settings
    logger.info("Config loaded successfully")
except Exception as e:
    logger.error(f"Configuration load failed: {e}")
    logger.error("Required environment variables: DATABASE_URL, JWT_SECRET_KEY, ANTHROPIC_API_KEY")
    sys.exit(1)

# Database connection (may fail on connection issues)
try:
    from app.database import engine
    logger.info("Database engine initialized")
except Exception as e:
    logger.error(f"Database connection failed: {e}")
    logger.error(f"Check DATABASE_URL: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'check config'}")
    sys.exit(1)

# Models and routers (may fail on import errors)
try:
    from app.models import Base
    from app.api.v1.router import api_router
    logger.info("Models and API router loaded")
except Exception as e:
    logger.error(f"Import failed: {e}")
    logger.error(traceback.format_exc())
    sys.exit(1)

from app.middleware.security import (
    limiter,
    SecurityHeadersMiddleware,
    rate_limit_exceeded_handler,
    TRUSTED_HOSTS,
)

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
    expose_headers=["*", "Content-Type", "Cache-Control", "X-Accel-Buffering"],
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

    # CORS Debug: Log origin mismatch for troubleshooting
    logger.error(f"CORS/Error: Request Origin: {origin} vs Allowed: {CORS_ORIGINS}")

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
    health_status = {
        "status": "healthy",
        "version": "1.0.0",
        "service": "LitDocket API"
    }

    # Include scheduler status if available
    try:
        from app.scheduler import get_scheduler_status
        scheduler_status = get_scheduler_status()
        health_status["scheduler"] = scheduler_status
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        health_status["scheduler"] = {"running": False, "error": str(e)}

    return health_status

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

    # Start background job scheduler for Authority Core automation
    try:
        from app.scheduler import start_scheduler
        start_scheduler()
        logger.info("✓ APScheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start APScheduler: {e}")
        # Don't fail startup if scheduler fails - app can still function
        logger.warning("Application running without scheduled jobs")

    logger.info("=" * 60)
    logger.info("Application startup complete")
    logger.info(f"API docs available at: /api/docs")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown():
    logger.info("Application shutting down...")

    # Gracefully shutdown scheduler
    try:
        from app.scheduler import shutdown_scheduler
        shutdown_scheduler()
        logger.info("✓ APScheduler shut down successfully")
    except Exception as e:
        logger.error(f"Error shutting down APScheduler: {e}")

    logger.info("Application shutdown complete")
