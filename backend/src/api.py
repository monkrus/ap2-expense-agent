from typing import Optional

from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from pydantic import BaseModel, validator
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session

from .auth import get_current_active_user
from .config import settings
from .database import get_db, init_db
from .error_handlers import register_exception_handlers
from .logging_config import RequestLogger, setup_logging
from .marketplace_enforcement import MarketplaceEnforcementMiddleware
from .models import User
from .permissions import (
    Permission,
    can_approve_expense,
    check_permission,
    has_any_permission,
)
from .rate_limit import limiter, rate_limit_handler
from .routes import admin_router, auth_router, oauth_router, users_router
from .routes.ap2 import router as ap2_router
from .routes.billing_org import router as billing_org_router
from .routes.dlq_admin import router as dlq_admin_router
from .routes.gcp_webhooks import router as gcp_webhooks_router
from .routes.notifications import router as notifications_router
from .routes.organizations import router as organizations_router
from .routes.expenses import router as expenses_router
from .routes.receipts import router as receipts_router
from .routes.webhooks import router as webhooks_router
from .routes.approval_policies import router as approval_policies_router
from .routes.budgets import router as budgets_router
from .routes.analytics import router as analytics_router
from .routes.recurring_expenses import router as recurring_expenses_router
from .routes.onboarding import router as onboarding_router
from .security_middleware import RequestIDMiddleware, SecurityHeadersMiddleware
from .startup_checks import validate_settings
from .tenant_context import tenant_middleware
from .utils.error_tracking import ErrorTrackingMiddleware

# Try to import database-integrated agent, fallback to in-memory agent
try:
    from .agent_db import ExpenseManagementAgent as DBAgent  # noqa: F401

    AGENT_DB_AVAILABLE = True
except ImportError:
    AGENT_DB_AVAILABLE = False
    print("Warning: Database agent not available. Using in-memory agent.")

# Fallback to in-memory agent if DB agent not available
if not AGENT_DB_AVAILABLE:
    try:
        from .agent import ExpenseManagementAgent  # noqa: F401

        AGENT_AVAILABLE = True
    except ImportError:
        AGENT_AVAILABLE = False
        print(
            "Warning: Google AI dependencies not installed. Agent features will be disabled."
        )
else:
    AGENT_AVAILABLE = True

# Fail fast on insecure production settings
validate_settings()

app = FastAPI(
    title="AP2 Expense Management Agent",
    description="AI-powered expense management with AP2 protocol",
    version="1.0.0",
)
# Initialize structured logging early
try:
    setup_logging(level=("DEBUG" if settings.debug else "INFO"))
except Exception:
    pass
# Force reload - auth routes should be available

# Register global error handlers
register_exception_handlers(app)

# Add rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# Add security middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)

# Add error tracking middleware for pattern detection
app.add_middleware(ErrorTrackingMiddleware)

# HTTPS redirect (enable in production/staging)
if settings.environment in ("production", "staging"):
    app.add_middleware(HTTPSRedirectMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Organization-Id",
    ],  # Added X-Organization-Id for multi-tenancy
)

# Add tenant middleware for multi-tenancy support
app.middleware("http")(tenant_middleware)
# Enforce Marketplace entitlement state/limits
app.add_middleware(MarketplaceEnforcementMiddleware)


# Basic request metrics middleware
try:
    from prometheus_client import Counter, Histogram

    HTTP_REQUESTS = Counter(
        "http_requests_total", "Total HTTP requests", ["method", "path", "status"]
    )
    HTTP_LATENCY = Histogram(
        "http_request_duration_seconds", "HTTP request latency (s)", ["method", "path"]
    )

    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        path = request.url.path
        method = request.method
        with HTTP_LATENCY.labels(method=method, path=path).time():
            response = await call_next(request)
        HTTP_REQUESTS.labels(
            method=method, path=path, status=str(response.status_code)
        ).inc()
        return response

except Exception:
    pass


# Access logging with Cloud Trace correlation
import time as _time


@app.middleware("http")
async def access_log_middleware(request: Request, call_next):
    trace_header = request.headers.get("X-Cloud-Trace-Context")
    gcp_trace = None
    gcp_span = None
    if trace_header:
        # Format: TRACE_ID/SPAN_ID;o=TRACE_TRUE
        parts = trace_header.split("/", 1)
        trace_id = parts[0]
        if len(parts) > 1 and ";" in parts[1]:
            span_part = parts[1].split(";", 1)[0]
            gcp_span = span_part
        project_id = settings.google_cloud_project or settings.gcp_project_id
        if project_id and trace_id:
            gcp_trace = f"projects/{project_id}/traces/{trace_id}"

    start = _time.perf_counter()
    req_size = None
    try:
        req_size = int(request.headers.get("content-length", "0"))
    except Exception:
        req_size = None
    response = await call_next(request)
    duration_ms = (_time.perf_counter() - start) * 1000.0

    req_id = response.headers.get("X-Request-ID") or request.headers.get("X-Request-ID")
    resp_size = None
    try:
        resp_size = int(response.headers.get("content-length", "0"))
    except Exception:
        resp_size = None
    org_id = request.headers.get("X-Organization-Id")
    try:
        RequestLogger.log_request(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
            response_time=duration_ms,
            organization_id=org_id,
            request_id=req_id,
            gcp_trace=gcp_trace,
            gcp_span=gcp_span,
            request_size=req_size,
            response_size=resp_size,
        )
    except Exception:
        pass

    return response


# Include authentication routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(oauth_router)
app.include_router(admin_router)

# Include organization router (multi-tenancy)
app.include_router(organizations_router)

# Include billing router (organization-based only)
app.include_router(billing_org_router)
app.include_router(ap2_router)
app.include_router(webhooks_router)

# Include expense router (with improved security and RBAC)
app.include_router(expenses_router)

app.include_router(receipts_router)
app.include_router(approval_policies_router)
app.include_router(budgets_router)
app.include_router(notifications_router)
app.include_router(analytics_router)
app.include_router(recurring_expenses_router)
app.include_router(onboarding_router)

# Include GCP Marketplace webhooks
app.include_router(gcp_webhooks_router)

# Include DLQ Admin endpoints
app.include_router(dlq_admin_router)


# Prometheus metrics endpoint (for GKE scraping)
try:
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    @app.get("/metrics")
    async def metrics():
        data = generate_latest()
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)

except Exception:
    pass


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()

    # CRITICAL: Verify tier limits before starting application
    # This ensures tier limits haven't been tampered with
    # Skip in test mode — test DB won't have billing tiers seeded
    import os as _os
    if not _os.environ.get("TESTING"):
        try:
            from .billing.tier_limit_guardian import verify_tier_limits_on_startup
            verify_tier_limits_on_startup()
        except Exception as e:
            print(f"[CRITICAL] Tier limit verification failed: {e}")
            print("[CRITICAL] Application startup blocked for security")
            raise

    # Note: Default test users seeding removed.
    # Run `python -m src.seed_data` manually if needed for testing.

    # Start recurring expense scheduler
    try:
        from .scheduler import RecurringExpenseScheduler
        scheduler = RecurringExpenseScheduler(check_interval=60)
        await scheduler.start()
    except Exception as e:
        print(f"[WARNING] Failed to start recurring expense scheduler: {e}")

    print("[STARTUP] Registered routes:")
    for route in app.routes:
        if hasattr(route, "path"):
            print(
                f"  {route.methods if hasattr(route, 'methods') else 'N/A'} {route.path}"
            )


# Agent will be initialized per-request with database session
# This is more appropriate for database-backed operations
agent = None


class ExpenseSubmission(BaseModel):
    amount: float
    vendor: str
    category: str  # Will be validated against ExpenseCategory enum values
    description: str
    date: Optional[str] = (
        None  # ISO format date string (YYYY-MM-DD), defaults to today if not provided
    )
    # Note: user_id is derived from the authenticated user (current_user), not from the request

    @validator("amount")
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        # Security: Prevent unreasonably large amounts (max $1,000,000 per expense)
        if v > 1000000:
            raise ValueError("Amount cannot exceed $1,000,000 per expense")
        return v

    @validator("description")
    def sanitize_description(cls, v):
        """Sanitize description to prevent XSS attacks"""
        import html

        # HTML escape any dangerous characters
        sanitized = html.escape(v)
        # Also limit length
        if len(sanitized) > 1000:
            raise ValueError("Description cannot exceed 1000 characters")
        return sanitized

    @validator("vendor")
    def sanitize_vendor(cls, v):
        """Sanitize vendor name to prevent XSS attacks"""
        import html

        sanitized = html.escape(v)
        if len(sanitized) > 200:
            raise ValueError("Vendor name cannot exceed 200 characters")
        return sanitized

    @validator("category")
    def validate_category(cls, v):
        from .models import ExpenseCategory

        # Check if the value matches any of the enum values
        valid_categories = [e.value for e in ExpenseCategory]
        if v not in valid_categories:
            raise ValueError(f'Category must be one of: {", ".join(valid_categories)}')
        return v

    @validator("date")
    def validate_date(cls, v):
        if v is None:
            return None
        # Validate date format
        from datetime import datetime

        try:
            datetime.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")


class ExpenseApproval(BaseModel):
    expense_id: str
    approver_id: str
    rejection_reason: Optional[str] = None


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "AP2 Expense Management Agent"}


# ============================================================================
# NOTE: EXPENSE ENDPOINTS NOW IN routes/expenses.py
# ============================================================================
# All expense endpoints have been moved to backend/src/routes/expenses.py
# The new router provides improved security, RBAC, and multi-tenant isolation.
# ============================================================================
