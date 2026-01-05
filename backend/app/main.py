from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import logging
import time

from app.config import settings
from app.database import engine
from app.models import Base
from app.api.v1.router import api_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Florida Docketing Assistant API",
    description="Legal docketing and case management with AI-powered analysis",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        "service": "Florida Docketing Assistant API"
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Florida Docketing Assistant API",
        "docs": "/api/docs",
        "health": "/health"
    }

# Include API router
app.include_router(api_router, prefix="/api/v1")

# Create database tables on startup
@app.on_event("startup")
async def startup():
    logger.info("Starting Florida Docketing Assistant API...")
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Application startup complete")

@app.on_event("shutdown")
async def shutdown():
    logger.info("Application shutdown")
