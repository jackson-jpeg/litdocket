"""Security middleware exports"""
from app.middleware.security import (
    limiter,
    RATE_LIMITS,
    SecurityHeadersMiddleware,
    rate_limit_exceeded_handler,
    validate_pdf_magic_number,
    validate_file_signature,
    TRUSTED_HOSTS,
    get_real_client_ip,
)

__all__ = [
    "limiter",
    "RATE_LIMITS",
    "SecurityHeadersMiddleware",
    "rate_limit_exceeded_handler",
    "validate_pdf_magic_number",
    "validate_file_signature",
    "TRUSTED_HOSTS",
    "get_real_client_ip",
]
