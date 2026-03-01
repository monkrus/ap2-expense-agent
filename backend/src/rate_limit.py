"""
Rate limiting configuration and utilities
"""

import os

from fastapi import Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .config import settings

# Initialize rate limiter
TESTING = os.getenv("TESTING", "false").lower() == "true"
limiter = Limiter(
    key_func=get_remote_address,
    enabled=(not TESTING) and settings.rate_limit_enabled,
)


# Endpoints where rate limit hits indicate potential malicious behaviour
_SENSITIVE_PATHS = {"/auth/login", "/auth/register", "/auth/password", "/invitations"}


# Rate limit error handler
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded errors and alert on sensitive endpoints."""
    ip = request.client.host if request.client else "unknown"
    path = request.url.path

    # Fire alert for sensitive endpoints
    if any(s in path for s in _SENSITIVE_PATHS):
        try:
            from .monitoring import AlertManager

            AlertManager.alert_suspicious_activity(
                activity_type="rate_limit_exceeded",
                ip_address=ip,
                endpoint=path,
            )
        except Exception:
            pass  # Never let alerting break the response

    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "rate_limit_exceeded",
            "detail": "Too many requests. Please try again later.",
            "retry_after": exc.retry_after if hasattr(exc, "retry_after") else 60,
        },
    )


# Common rate limit decorators
class RateLimits:
    """Common rate limit configurations"""

    # Authentication endpoints
    LOGIN = "5/minute"  # 5 login attempts per minute
    REGISTER = "3/hour"  # 3 registrations per hour
    PASSWORD_RESET = "3/hour"  # 3 password reset requests per hour
    REFRESH_TOKEN = "10/minute"  # 10 token refreshes per minute

    # General API endpoints
    API_READ = "100/minute"  # 100 read operations per minute
    API_WRITE = "50/minute"  # 50 write operations per minute

    # Admin endpoints
    ADMIN = "30/minute"  # 30 admin operations per minute

    # Payment endpoints (strict limits to prevent duplicate charges)
    CHECKOUT = "3/hour"  # Maximum 3 checkout attempts per hour per user
    SUBSCRIPTION = "5/hour"  # 5 subscription operations per hour

    # Heavy operations
    HEAVY = "10/minute"  # 10 heavy operations per minute (e.g., reports, exports)

    # Invitation endpoint — prevents email spam via SendGrid
    INVITE = "20/hour"  # 20 invitations per hour per IP
