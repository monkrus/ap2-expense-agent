"""
Structured Logging Configuration
Provides comprehensive logging with JSON formatting and log aggregation support
"""

import json
import logging
import logging.handlers
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Add extra fields
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "organization_id"):
            log_data["organization_id"] = record.organization_id
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "endpoint"):
            log_data["endpoint"] = record.endpoint
        if hasattr(record, "method"):
            log_data["method"] = record.method
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code
        if hasattr(record, "response_time"):
            log_data["response_time_ms"] = record.response_time

        # Add environment
        log_data["environment"] = os.getenv("ENVIRONMENT", "development")

        return json.dumps(log_data)


def setup_logging(
    level: str = "INFO",
    log_file: str = "logs/app.log",
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 5,
) -> None:
    """
    Configure application logging

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup files to keep
    """
    # Create logs directory
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler (JSON for production, simple for development)
    console_handler = logging.StreamHandler(sys.stdout)
    if os.getenv("ENVIRONMENT") == "production":
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
    root_logger.addHandler(console_handler)

    # File handler with rotation (always JSON)
    # Use TimedRotatingFileHandler on Windows to avoid permission issues
    try:
        if sys.platform == "win32":
            # Use time-based rotation on Windows (daily rotation)
            file_handler = logging.handlers.TimedRotatingFileHandler(
                log_file,
                when="midnight",
                interval=1,
                backupCount=backup_count,
                encoding="utf-8",
            )
        else:
            # Use size-based rotation on Unix/Linux
            file_handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
            )
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)
    except (PermissionError, OSError) as e:
        # If file logging fails, log to console only
        logging.warning(f"Could not set up file logging: {e}. Logging to console only.")

    # Error file handler (only errors and above)
    try:
        if sys.platform == "win32":
            error_file_handler = logging.handlers.TimedRotatingFileHandler(
                log_file.replace(".log", "_error.log"),
                when="midnight",
                interval=1,
                backupCount=backup_count,
                encoding="utf-8",
            )
        else:
            error_file_handler = logging.handlers.RotatingFileHandler(
                log_file.replace(".log", "_error.log"),
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(error_file_handler)
    except (PermissionError, OSError) as e:
        # If error file logging fails, continue without it
        logging.warning(f"Could not set up error file logging: {e}")

    # Set levels for specific loggers to reduce noise
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)

    # Suppress verbose SQLAlchemy logs (only show warnings and errors)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.orm").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)

    logging.getLogger("fastapi").setLevel(logging.INFO)

    logging.info(f"Logging configured: level={level}, file={log_file}")


class LoggerAdapter(logging.LoggerAdapter):
    """Custom logger adapter with context"""

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Add context to log record"""
        extra = kwargs.get("extra", {})

        # Add context from adapter
        if self.extra:
            extra.update(self.extra)

        kwargs["extra"] = extra
        return msg, kwargs


def get_logger(name: str, **context) -> LoggerAdapter:
    """
    Get logger with context

    Usage:
        logger = get_logger(__name__, user_id="123", organization_id="org_456")
        logger.info("User action performed")
    """
    logger = logging.getLogger(name)
    return LoggerAdapter(logger, context)


class RequestLogger:
    """HTTP request logging"""

    @staticmethod
    def log_request(
        method: str,
        endpoint: str,
        status_code: int,
        response_time: float,
        user_id: str = None,
        organization_id: str = None,
        request_id: str = None,
    ):
        """Log HTTP request"""
        logger = logging.getLogger("http.access")
        logger.info(
            f"{method} {endpoint} - {status_code}",
            extra={
                "method": method,
                "endpoint": endpoint,
                "status_code": status_code,
                "response_time": response_time,
                "user_id": user_id,
                "organization_id": organization_id,
                "request_id": request_id,
            },
        )

    @staticmethod
    def log_error(
        method: str,
        endpoint: str,
        error: Exception,
        user_id: str = None,
        organization_id: str = None,
        request_id: str = None,
    ):
        """Log HTTP error"""
        logger = logging.getLogger("http.error")
        logger.error(
            f"{method} {endpoint} - Error: {str(error)}",
            exc_info=error,
            extra={
                "method": method,
                "endpoint": endpoint,
                "user_id": user_id,
                "organization_id": organization_id,
                "request_id": request_id,
            },
        )


class AuditLogger:
    """Security and audit event logging"""

    @staticmethod
    def log_auth_success(user_id: str, method: str, ip_address: str = None):
        """Log successful authentication"""
        logger = logging.getLogger("audit.auth")
        logger.info(
            f"Authentication successful: user={user_id}, method={method}",
            extra={
                "event": "auth_success",
                "user_id": user_id,
                "auth_method": method,
                "ip_address": ip_address,
            },
        )

    @staticmethod
    def log_auth_failure(username: str, reason: str, ip_address: str = None):
        """Log failed authentication"""
        logger = logging.getLogger("audit.auth")
        logger.warning(
            f"Authentication failed: username={username}, reason={reason}",
            extra={
                "event": "auth_failure",
                "username": username,
                "reason": reason,
                "ip_address": ip_address,
            },
        )

    @staticmethod
    def log_permission_denied(user_id: str, resource: str, action: str):
        """Log permission denied"""
        logger = logging.getLogger("audit.access")
        logger.warning(
            f"Permission denied: user={user_id}, resource={resource}, action={action}",
            extra={
                "event": "permission_denied",
                "user_id": user_id,
                "resource": resource,
                "action": action,
            },
        )

    @staticmethod
    def log_data_access(
        user_id: str, resource_type: str, resource_id: str, action: str
    ):
        """Log data access"""
        logger = logging.getLogger("audit.data")
        logger.info(
            f"Data access: user={user_id}, resource={resource_type}:{resource_id}, action={action}",
            extra={
                "event": "data_access",
                "user_id": user_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "action": action,
            },
        )

    @staticmethod
    def log_sensitive_operation(
        user_id: str, operation: str, details: Dict[str, Any] = None
    ):
        """Log sensitive operation"""
        logger = logging.getLogger("audit.sensitive")
        logger.warning(
            f"Sensitive operation: user={user_id}, operation={operation}",
            extra={
                "event": "sensitive_operation",
                "user_id": user_id,
                "operation": operation,
                "details": details or {},
            },
        )


# Initialize logging on module import (skip in test environment to reduce output)
if not logging.getLogger().handlers and os.getenv("ENVIRONMENT") != "test":
    setup_logging(
        level=os.getenv("LOG_LEVEL", "INFO"),
        log_file=os.getenv("LOG_FILE", "logs/app.log"),
    )
