"""
Global Error Handlers and Custom Exceptions
Provides consistent error handling across the application
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import ValidationError
import logging
import traceback
from typing import Union
import sys

from .logging_config import get_logger, RequestLogger

logger = get_logger(__name__)


# ============================================================================
# Custom Exceptions
# ============================================================================

class APIException(Exception):
    """Base exception for all API errors"""
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: dict = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(APIException):
    """Authentication failed"""
    def __init__(self, message: str = "Authentication failed", details: dict = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTH_FAILED",
            details=details
        )


class AuthorizationError(APIException):
    """User not authorized for this action"""
    def __init__(self, message: str = "Not authorized", details: dict = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN",
            details=details
        )


class ResourceNotFoundError(APIException):
    """Resource not found"""
    def __init__(self, resource: str, resource_id: str = None):
        message = f"{resource} not found"
        if resource_id:
            message += f": {resource_id}"

        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            details={"resource": resource, "resource_id": resource_id}
        )


class ValidationError(APIException):
    """Data validation error"""
    def __init__(self, message: str, field: str = None, details: dict = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="VALIDATION_ERROR",
            details={"field": field, **(details or {})}
        )


class ConflictError(APIException):
    """Resource conflict (e.g., duplicate)"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT",
            details=details
        )


class RateLimitError(APIException):
    """Rate limit exceeded"""
    def __init__(self, retry_after: int = 60):
        super().__init__(
            message="Too many requests. Please try again later.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED",
            details={"retry_after": retry_after}
        )


class ServiceUnavailableError(APIException):
    """External service unavailable"""
    def __init__(self, service: str, details: dict = None):
        super().__init__(
            message=f"Service temporarily unavailable: {service}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="SERVICE_UNAVAILABLE",
            details={"service": service, **(details or {})}
        )


class DatabaseError(APIException):
    """Database operation error"""
    def __init__(self, message: str = "Database operation failed", details: dict = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DATABASE_ERROR",
            details=details
        )


# ============================================================================
# Error Response Builder
# ============================================================================

def build_error_response(
    status_code: int,
    message: str,
    error_code: str = None,
    details: dict = None,
    request_id: str = None
) -> JSONResponse:
    """Build consistent error response"""
    error_response = {
        "error": {
            "message": message,
            "code": error_code or "UNKNOWN_ERROR",
            "status": status_code
        }
    }

    if details:
        error_response["error"]["details"] = details

    if request_id:
        error_response["request_id"] = request_id

    return JSONResponse(
        status_code=status_code,
        content=error_response
    )


# ============================================================================
# Exception Handlers
# ============================================================================

async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """Handle custom API exceptions"""
    request_id = request.headers.get("X-Request-ID")

    logger.warning(
        f"API Exception: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "endpoint": str(request.url),
            "method": request.method,
            "request_id": request_id
        }
    )

    return build_error_response(
        status_code=exc.status_code,
        message=exc.message,
        error_code=exc.error_code,
        details=exc.details,
        request_id=request_id
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions"""
    request_id = request.headers.get("X-Request-ID")

    logger.warning(
        f"HTTP Exception: {exc.status_code} - {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "endpoint": str(request.url),
            "method": request.method,
            "request_id": request_id
        }
    )

    # Return standard FastAPI format with "detail" for compatibility
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc.detail)}
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors"""
    request_id = request.headers.get("X-Request-ID")

    # Extract validation errors
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })

    logger.warning(
        f"Validation Error: {len(errors)} field(s) failed validation",
        extra={
            "errors": errors,
            "endpoint": str(request.url),
            "method": request.method,
            "request_id": request_id
        }
    )

    return build_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Request validation failed",
        error_code="VALIDATION_ERROR",
        details={"errors": errors},
        request_id=request_id
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle SQLAlchemy database errors"""
    request_id = request.headers.get("X-Request-ID")

    # Log full error with traceback
    logger.error(
        f"Database Error: {str(exc)}",
        exc_info=exc,
        extra={
            "endpoint": str(request.url),
            "method": request.method,
            "request_id": request_id
        }
    )

    # Check for specific error types
    if isinstance(exc, IntegrityError):
        message = "Data integrity constraint violated"
        error_code = "INTEGRITY_ERROR"
    else:
        message = "Database operation failed"
        error_code = "DATABASE_ERROR"

    return build_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message=message,
        error_code=error_code,
        request_id=request_id
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all uncaught exceptions"""
    request_id = request.headers.get("X-Request-ID")

    # Log full error with traceback
    logger.error(
        f"Unhandled Exception: {type(exc).__name__}: {str(exc)}",
        exc_info=exc,
        extra={
            "exception_type": type(exc).__name__,
            "endpoint": str(request.url),
            "method": request.method,
            "request_id": request_id,
            "traceback": traceback.format_exc()
        }
    )

    # Send to error tracking service (e.g., Sentry)
    try:
        import sentry_sdk
        sentry_sdk.capture_exception(exc)
    except:
        pass

    # Don't expose internal errors in production
    import os
    if os.getenv("ENVIRONMENT") == "production":
        message = "An internal error occurred. Please try again later."
    else:
        message = f"{type(exc).__name__}: {str(exc)}"

    return build_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message=message,
        error_code="INTERNAL_ERROR",
        request_id=request_id
    )


# ============================================================================
# Register Exception Handlers
# ============================================================================

def register_exception_handlers(app):
    """Register all exception handlers with FastAPI app"""

    # Custom exceptions
    app.add_exception_handler(APIException, api_exception_handler)

    # HTTP exceptions
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    # Validation errors
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # Database errors
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)

    # Catch-all for unexpected errors
    app.add_exception_handler(Exception, general_exception_handler)

    logger.info("Exception handlers registered")


# ============================================================================
# Error Tracking Integration (Sentry)
# ============================================================================

def init_error_tracking():
    """Initialize error tracking service (Sentry)"""
    import os

    sentry_dsn = os.getenv("SENTRY_DSN")

    if sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

            sentry_sdk.init(
                dsn=sentry_dsn,
                environment=os.getenv("ENVIRONMENT", "development"),
                traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
                integrations=[
                    FastApiIntegration(),
                    SqlalchemyIntegration(),
                ],
                send_default_pii=False,  # Don't send personally identifiable information
                before_send=before_send_sentry
            )

            logger.info("Sentry error tracking initialized")
        except ImportError:
            logger.warning("Sentry SDK not installed. Error tracking disabled.")
        except Exception as e:
            logger.error(f"Failed to initialize Sentry: {e}")
    else:
        logger.info("Sentry DSN not configured. Error tracking disabled.")


def before_send_sentry(event, hint):
    """Filter sensitive data before sending to Sentry"""
    # Remove sensitive headers
    if "request" in event and "headers" in event["request"]:
        headers = event["request"]["headers"]
        for sensitive_header in ["Authorization", "Cookie", "X-API-Key"]:
            if sensitive_header in headers:
                headers[sensitive_header] = "[REDACTED]"

    # Remove sensitive query parameters
    if "request" in event and "query_string" in event["request"]:
        query = event["request"]["query_string"]
        for sensitive_param in ["password", "token", "api_key"]:
            if sensitive_param in query:
                event["request"]["query_string"] = "[REDACTED]"

    return event
