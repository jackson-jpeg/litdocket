"""
Security Middleware - LitDocket Security Hardening

Implements:
1. Rate Limiting (slowapi) - Prevents DDoS and brute-force attacks
2. Security Headers - Prevents XSS, clickjacking, MIME sniffing
3. Request validation
"""
from fastapi import Request, Response
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# RATE LIMITING CONFIGURATION
# =============================================================================

def get_real_client_ip(request: Request) -> str:
    """
    Get real client IP, handling proxies (Railway, Cloudflare, etc.)
    """
    # Check for forwarded headers (reverse proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # X-Forwarded-For can be comma-separated list, get the first (original) IP
        return forwarded.split(",")[0].strip()

    # Check for Cloudflare header
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip

    # Fallback to direct connection IP
    return get_remote_address(request)


# Create limiter instance with real IP detection
limiter = Limiter(key_func=get_real_client_ip)

# Rate limit configurations
RATE_LIMITS = {
    "default": "100/minute",      # Standard routes
    "auth": "5/minute",           # Login/signup - prevent brute force
    "upload": "10/minute",        # File uploads - prevent abuse
    "ai": "20/minute",            # AI endpoints - expensive operations
    "export": "10/minute",        # Export endpoints - prevent abuse
}


# =============================================================================
# SECURITY HEADERS MIDDLEWARE
# =============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to all responses.

    Headers:
    - X-Content-Type-Options: nosniff - Prevent MIME type sniffing
    - X-Frame-Options: DENY - Prevent clickjacking
    - X-XSS-Protection: 1; mode=block - XSS filter (legacy browsers)
    - Strict-Transport-Security: Force HTTPS
    - Referrer-Policy: Control referrer information
    - Permissions-Policy: Restrict browser features
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # HSTS - Force HTTPS (only in production)
        # max-age=31536000 = 1 year
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Permissions Policy - Restrict browser features
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        )

        return response


# =============================================================================
# RATE LIMIT EXCEEDED HANDLER
# =============================================================================

async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Custom handler for rate limit exceeded.
    Returns JSON response with proper CORS headers.
    """
    from fastapi.responses import JSONResponse

    logger.warning(f"Rate limit exceeded for IP {get_real_client_ip(request)} on {request.url.path}")

    response = JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded. Please slow down.",
            "error": "too_many_requests",
            "retry_after": exc.detail
        }
    )

    # Add CORS headers for rate limit responses
    origin = request.headers.get("origin", "")
    allowed_origins = [
        "http://localhost:3000",
        "https://litdocket.com",
        "https://www.litdocket.com",
    ]
    if origin in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"

    response.headers["Retry-After"] = str(60)  # Suggest retry in 60 seconds

    return response


# =============================================================================
# PDF MAGIC NUMBER VALIDATION
# =============================================================================

PDF_MAGIC_BYTES = b'%PDF'

def validate_pdf_magic_number(file_content: bytes) -> bool:
    """
    Validate that a file is actually a PDF by checking magic bytes.
    Prevents uploading malicious files disguised as PDFs.

    Args:
        file_content: First bytes of the file

    Returns:
        True if file starts with PDF magic bytes
    """
    if len(file_content) < 4:
        return False
    return file_content[:4] == PDF_MAGIC_BYTES


def validate_file_signature(file_content: bytes, expected_type: str = "pdf") -> tuple[bool, str]:
    """
    Validate file signature (magic number) matches expected type.

    Args:
        file_content: File content bytes
        expected_type: Expected file type ("pdf", "image", etc.)

    Returns:
        Tuple of (is_valid, error_message)
    """
    SIGNATURES = {
        "pdf": (b'%PDF', "File is not a valid PDF"),
        "png": (b'\x89PNG', "File is not a valid PNG"),
        "jpg": (b'\xff\xd8\xff', "File is not a valid JPEG"),
        "gif": (b'GIF8', "File is not a valid GIF"),
    }

    if expected_type not in SIGNATURES:
        return True, ""  # Unknown type, skip validation

    magic_bytes, error_msg = SIGNATURES[expected_type]

    if len(file_content) < len(magic_bytes):
        return False, f"File too small to be a valid {expected_type.upper()}"

    if not file_content.startswith(magic_bytes):
        return False, error_msg

    return True, ""


# =============================================================================
# TRUSTED HOSTS CONFIGURATION
# =============================================================================

TRUSTED_HOSTS = [
    "litdocket.com",
    "www.litdocket.com",
    "litdocket-production.up.railway.app",
    "localhost",
    "127.0.0.1",
    "testserver",  # For pytest
]
