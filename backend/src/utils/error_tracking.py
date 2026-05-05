"""
Enhanced Error Tracking and Logging

Provides structured logging and error tracking to catch issues in production.
"""

import json
import logging
import traceback
from datetime import datetime
from functools import wraps
from typing import Any, Dict, Optional


# Configure structured logging
class StructuredLogger:
    """Logger that outputs structured JSON logs for easy parsing"""

    @staticmethod
    def setup_logging(log_level: str = "INFO"):
        """Setup structured logging configuration"""
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format="%(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler("logs/app.log", mode="a"),
            ],
        )

    @staticmethod
    def log_event(event_type: str, message: str, level: str = "INFO", **kwargs):
        """
        Log a structured event.

        Args:
            event_type: Type of event (api_call, error, database, etc.)
            message: Human-readable message
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            **kwargs: Additional context to include in log
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "level": level,
            "message": message,
            **kwargs,
        }

        logger = logging.getLogger(__name__)
        log_method = getattr(logger, level.lower(), logger.info)
        log_method(json.dumps(log_entry))

    @staticmethod
    def log_api_call(
        endpoint: str,
        method: str,
        status_code: int,
        duration_ms: float,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        **kwargs,
    ):
        """Log an API call with relevant context"""
        StructuredLogger.log_event(
            event_type="api_call",
            message=f"{method} {endpoint} -> {status_code}",
            level="INFO",
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration_ms=duration_ms,
            user_id=user_id,
            organization_id=org_id,
            **kwargs,
        )

    @staticmethod
    def log_error(
        error: Exception, context: Optional[Dict[str, Any]] = None, level: str = "ERROR"
    ):
        """
        Log an error with full context and stack trace.

        Args:
            error: The exception that occurred
            context: Additional context about the error
            level: Log level (ERROR or CRITICAL)
        """
        error_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "stack_trace": traceback.format_exc(),
        }

        if context:
            error_data["context"] = context

        StructuredLogger.log_event(
            event_type="error",
            message=f"{type(error).__name__}: {str(error)}",
            level=level,
            **error_data,
        )

    @staticmethod
    def log_database_query(
        query_type: str, table: str, duration_ms: float, success: bool = True, **kwargs
    ):
        """Log database query performance"""
        StructuredLogger.log_event(
            event_type="database_query",
            message=f"{query_type} on {table}",
            level="DEBUG",
            query_type=query_type,
            table=table,
            duration_ms=duration_ms,
            success=success,
            **kwargs,
        )


def track_errors(func):
    """
    Decorator to automatically log errors from functions.

    Usage:
        @track_errors
        def my_function():
            ...
    """

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            StructuredLogger.log_error(
                error=e,
                context={
                    "function": func.__name__,
                    "args": str(args)[:100],  # Limit arg length
                    "kwargs": str(kwargs)[:100],
                },
            )
            raise

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            StructuredLogger.log_error(
                error=e,
                context={
                    "function": func.__name__,
                    "args": str(args)[:100],
                    "kwargs": str(kwargs)[:100],
                },
            )
            raise

    # Return appropriate wrapper based on function type
    import inspect

    if inspect.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


# Error patterns to track
class ErrorPatternDetector:
    """Detects recurring error patterns"""

    error_counts = {}

    @staticmethod
    def record_error(error_type: str, endpoint: Optional[str] = None):
        """Record an error occurrence"""
        key = f"{error_type}:{endpoint}" if endpoint else error_type

        if key not in ErrorPatternDetector.error_counts:
            ErrorPatternDetector.error_counts[key] = {
                "count": 0,
                "first_seen": datetime.utcnow(),
                "last_seen": None,
            }

        ErrorPatternDetector.error_counts[key]["count"] += 1
        ErrorPatternDetector.error_counts[key]["last_seen"] = datetime.utcnow()

        # Alert if error repeats frequently
        if ErrorPatternDetector.error_counts[key]["count"] >= 10:
            StructuredLogger.log_event(
                event_type="error_pattern_detected",
                message=f"Recurring error: {key}",
                level="WARNING",
                error_key=key,
                count=ErrorPatternDetector.error_counts[key]["count"],
                first_seen=ErrorPatternDetector.error_counts[key][
                    "first_seen"
                ].isoformat(),
            )

    @staticmethod
    def get_error_report() -> Dict[str, Any]:
        """Get a report of all error patterns"""
        return {
            "total_error_types": len(ErrorPatternDetector.error_counts),
            "errors": ErrorPatternDetector.error_counts,
        }


# Middleware helper for FastAPI
class ErrorTrackingMiddleware:
    """
    FastAPI middleware to track all errors.

    Add to your FastAPI app:
        app.add_middleware(ErrorTrackingMiddleware)
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        import time

        start_time = time.time()

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code = message["status"]
                duration_ms = (time.time() - start_time) * 1000

                # Log API call
                StructuredLogger.log_api_call(
                    endpoint=scope["path"],
                    method=scope["method"],
                    status_code=status_code,
                    duration_ms=duration_ms,
                )

                # Track errors
                if status_code >= 400:
                    ErrorPatternDetector.record_error(
                        error_type=f"HTTP_{status_code}", endpoint=scope["path"]
                    )

            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            StructuredLogger.log_error(
                e,
                context={
                    "endpoint": scope["path"],
                    "method": scope["method"],
                },
            )
            ErrorPatternDetector.record_error(
                error_type=type(e).__name__, endpoint=scope["path"]
            )
            raise


# Initialize logging
import os

os.makedirs("logs", exist_ok=True)
StructuredLogger.setup_logging()
