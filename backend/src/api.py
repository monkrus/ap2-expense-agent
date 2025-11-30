from typing import Optional

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session

from .auth import get_current_active_user
from .config import settings
from .database import get_db, init_db
from .error_handlers import register_exception_handlers
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
from .routes.billing import router as billing_router
from .routes.billing_org import router as billing_org_router
from .routes.gcp_webhooks import router as gcp_webhooks_router
from .routes.notifications import router as notifications_router
from .routes.organizations import router as organizations_router
from .routes.payment import router as payment_router  # Payment endpoints - reload trigger
from .routes.receipts import router as receipts_router
from .routes.webhooks import router as webhooks_router
from .security_middleware import RequestIDMiddleware, SecurityHeadersMiddleware
from .logging_config import setup_logging, RequestLogger
from .tenant_context import tenant_middleware

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
# HTTPS redirect (enable in production)
# app.add_middleware(HTTPSRedirectMiddleware, enabled=(settings.environment == "production"))

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
        HTTP_REQUESTS.labels(method=method, path=path, status=str(response.status_code)).inc()
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

# Include billing and payment routers
app.include_router(billing_router)
app.include_router(billing_org_router)  # Organization-based billing
app.include_router(payment_router)
app.include_router(ap2_router)
app.include_router(webhooks_router)
app.include_router(receipts_router)
app.include_router(notifications_router)

# Include GCP Marketplace webhooks
app.include_router(gcp_webhooks_router)


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

    # Seed default users
    from .seed_data import ensure_default_users_exist

    db = next(get_db())
    try:
        ensure_default_users_exist(db)
    finally:
        db.close()

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


def get_organization_context(current_user: User, db: Session) -> str:
    """Get organization from context or user's default organization"""
    from .tenant_context import TenantContext, get_user_organizations

    # Try to get organization from context (X-Organization-Id header)
    org_id = TenantContext.get_organization()
    if org_id:
        return org_id

    # Fallback: Get user's first organization
    user_orgs = get_user_organizations(current_user.id, db)
    if user_orgs:
        org_id = user_orgs[0]["id"]
        TenantContext.set_organization(org_id)  # Set context for this request
        return org_id

    # No organization found - this should rarely happen
    # Could auto-create a default org here if needed
    raise HTTPException(
        status_code=400,
        detail="No organization context available. Please join an organization first.",
    )


@app.post("/api/v1/expenses", status_code=201)
async def submit_expense(
    data: ExpenseSubmission,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    try:
        # Get organization context for multi-tenancy
        import uuid
        from datetime import datetime

        from .models import Expense, ExpenseStatus
        from .tenant_context import TenantContext
        from .billing.limit_enforcer import LimitEnforcer, LimitExceededError

        organization_id = get_organization_context(current_user, db)

        # Check expense limits (hard block for Free tier)
        try:
            limit_enforcer = LimitEnforcer(db)
            # Check monthly expense limit
            limit_enforcer.check_expense_limit(organization_id, raise_error=True)
            # Check daily rate limit (anti-abuse for Free tier)
            limit_enforcer.check_daily_rate_limit(
                organization_id, "expense", raise_error=True
            )
        except LimitExceededError as e:
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "limit_exceeded",
                    "feature": e.feature,
                    "limit": e.limit,
                    "current": e.current,
                    "message": str(e),
                    "upgrade_message": e.upgrade_message,
                },
            )

        # Parse expense date or use current date
        if data.date:
            expense_date = datetime.fromisoformat(data.date)
        else:
            expense_date = datetime.utcnow()

        # Create expense directly in database (simplified version without AI agent)
        expense = Expense(
            id=str(uuid.uuid4()),
            organization_id=organization_id
            or str(uuid.uuid4()),  # Create temp org if none
            user_id=current_user.id,
            amount=data.amount,
            vendor=data.vendor,
            category=data.category,
            description=data.description,
            status=ExpenseStatus.PENDING,
            date=expense_date,
            ai_analysis="Manual submission - AI analysis not available",
            risk_level="LOW",
            compliance_check=True,
        )

        db.add(expense)
        db.commit()
        db.refresh(expense)

        # Send email notifications
        try:
            from .models import User as UserModel
            from .models import UserRole
            from .services.notification_service import notification_service

            # Notify employee that expense was submitted
            notification_service.notify_expense_submitted(
                expense_id=expense.id,
                employee_name=current_user.full_name or current_user.username,
                employee_email=current_user.email,
                amount=float(expense.amount),
                category=expense.category,
                description=expense.description,
            )

            # Notify managers/admins of new expense awaiting approval
            managers = (
                db.query(UserModel)
                .filter(UserModel.role.in_([UserRole.ADMIN, UserRole.MANAGER]))
                .all()
            )

            for manager in managers:
                if manager.id != current_user.id:  # Don't notify the submitter
                    notification_service.notify_manager_new_expense(
                        expense_id=expense.id,
                        employee_name=current_user.full_name or current_user.username,
                        employee_email=current_user.email,
                        manager_email=manager.email,
                        amount=float(expense.amount),
                        category=expense.category,
                        description=expense.description,
                    )
        except Exception as e:
            # Log notification error but don't fail the request
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send email notification: {str(e)}")

        return {
            "success": True,
            "expense": {
                "id": expense.id,
                "amount": float(expense.amount),
                "vendor": expense.vendor,
                "category": expense.category,
                "description": expense.description,
                "status": expense.status.value,
                "date": expense.date.isoformat(),
                "user_id": expense.user_id,
            },
            "message": "Expense submitted successfully",
        }
    except HTTPException:
        # Re-raise HTTP exceptions (including 402 for limit exceeded)
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/expenses")
async def list_expenses(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List all expenses for user's organization"""
    from .models import Expense

    # Get organization context for multi-tenancy
    organization_id = get_organization_context(current_user, db)

    # Query expenses with organization filter for tenant isolation
    expenses = (
        db.query(Expense).filter(Expense.organization_id == organization_id).all()
    )

    return [
        {
            "id": expense.id,
            "amount": float(expense.amount),
            "vendor": expense.vendor,
            "category": expense.category,
            "description": expense.description,
            "status": expense.status.value,
            "date": expense.date.isoformat(),
            "user_id": expense.user_id,
        }
        for expense in expenses
    ]


@app.get("/api/v1/expenses/export")
async def export_expenses(
    format: str = "csv",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Export expenses to CSV/PDF format"""
    import io

    from fastapi.responses import StreamingResponse

    from .models import Expense, OrganizationMember

    membership = (
        db.query(OrganizationMember)
        .filter(OrganizationMember.user_id == current_user.id)
        .first()
    )

    if not membership:
        # Return empty CSV if no membership
        output = io.StringIO()
        output.write("id,amount,description,category,status,date,vendor\n")
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=expenses.csv"},
        )

    expenses = (
        db.query(Expense)
        .filter(Expense.organization_id == membership.organization_id)
        .all()
    )

    # Generate CSV
    output = io.StringIO()
    output.write("id,amount,description,category,status,date,vendor\n")
    for expense in expenses:
        output.write(
            f"{expense.id},{expense.amount},{expense.description},"
            f"{expense.category},{expense.status},{expense.date},{expense.vendor}\n"
        )

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=expenses.csv"},
    )


@app.get("/api/v1/expenses/stats")
async def get_expense_statistics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get expense statistics for current user's organization"""
    from sqlalchemy import func

    from .models import Expense, OrganizationMember

    membership = (
        db.query(OrganizationMember)
        .filter(OrganizationMember.user_id == current_user.id)
        .first()
    )

    if not membership:
        return {"total": 0, "count": 0}

    total = (
        db.query(func.sum(Expense.amount))
        .filter(Expense.organization_id == membership.organization_id)
        .scalar()
        or 0
    )

    count = (
        db.query(func.count(Expense.id))
        .filter(Expense.organization_id == membership.organization_id)
        .scalar()
        or 0
    )

    return {
        "total": float(total),
        "count": int(count),
        "organization_id": membership.organization_id,
    }


@app.get("/api/v1/expenses/all-pending")
async def get_all_pending_expenses(
    current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
):
    """Get all pending expenses from all users (admin/manager only)"""
    from .models import Expense, ExpenseStatus
    from .models import User as UserModel

    # Check permission to view all expenses
    check_permission(
        current_user.role, Permission.EXPENSE_VIEW_ALL, raise_exception=True
    )

    # Get all pending expenses with user information
    expenses = db.query(Expense).filter(Expense.status == ExpenseStatus.PENDING).all()

    # Get user details for each expense
    result = []
    for e in expenses:
        user = db.query(UserModel).filter(UserModel.id == e.user_id).first()
        result.append(
            {
                "id": e.id,
                "amount": float(e.amount),
                "vendor": e.vendor,
                "category": e.category,
                "description": e.description,
                "status": e.status.value,
                "date": e.date.isoformat() if e.date else None,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "user_id": e.user_id,
                "user_email": user.email if user else "Unknown",
                "user_name": user.full_name if user else "Unknown",
            }
        )

    return {
        "pending_count": len(result),
        "total_amount": sum(e["amount"] for e in result),
        "expenses": result,
    }


@app.get("/api/v1/expenses/all")
async def get_all_expenses(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    status: Optional[str] = None,
):
    """Get all expenses from all users with optional status filter (admin/manager only)"""
    import logging

    from .models import Expense, ExpenseStatus
    from .models import User as UserModel

    logger = logging.getLogger(__name__)
    logger.info(f"[get_all_expenses] Called with status filter: {status}")

    # Check permission to view all expenses
    check_permission(
        current_user.role, Permission.EXPENSE_VIEW_ALL, raise_exception=True
    )

    # Build query - exclude withdrawn by default
    query = db.query(Expense).filter(Expense.status != ExpenseStatus.WITHDRAWN)

    # Apply status filter if provided
    if status and status != "all":
        try:
            status_enum = ExpenseStatus(status.lower())
            logger.info(f"[get_all_expenses] Filtering by status enum: {status_enum}")
            query = query.filter(Expense.status == status_enum)
        except ValueError:
            logger.warning(f"[get_all_expenses] Invalid status value: {status}")
            pass  # Invalid status, ignore filter

    # Get all expenses ordered by creation date (newest first)
    expenses = query.order_by(Expense.created_at.desc()).all()
    logger.info(f"[get_all_expenses] Found {len(expenses)} expenses")

    # Get user details for each expense and include approver info
    result = []
    for e in expenses:
        user = db.query(UserModel).filter(UserModel.id == e.user_id).first()
        approver = None
        if e.approved_by:
            approver = db.query(UserModel).filter(UserModel.id == e.approved_by).first()

        result.append(
            {
                "id": e.id,
                "amount": float(e.amount),
                "vendor": e.vendor,
                "category": e.category,
                "description": e.description,
                "status": e.status.value,
                "date": e.date.isoformat() if e.date else None,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "approved_at": e.approved_at.isoformat() if e.approved_at else None,
                "transaction_id": e.transaction_id,
                "rejection_reason": e.rejection_reason,
                "user_id": e.user_id,
                "user_email": user.email if user else "Unknown",
                "user_name": user.full_name if user else "Unknown",
                "approved_by_name": approver.full_name if approver else None,
                "approved_by_email": approver.email if approver else None,
            }
        )

    # Calculate stats
    total_amount = sum(e["amount"] for e in result)
    pending_count = sum(1 for e in result if e["status"] == "pending")
    approved_count = sum(1 for e in result if e["status"] == "approved")
    rejected_count = sum(1 for e in result if e["status"] == "rejected")

    return {
        "total_count": len(result),
        "total_amount": total_amount,
        "pending_count": pending_count,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "expenses": result,
    }


@app.get("/api/v1/expenses/{expense_id}")
async def get_expense(
    expense_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get a single expense by ID with tenant isolation"""
    from .models import Expense

    # Get organization context for multi-tenancy
    organization_id = get_organization_context(current_user, db)

    # Query expense with organization filter for tenant isolation
    expense = (
        db.query(Expense)
        .filter(Expense.id == expense_id, Expense.organization_id == organization_id)
        .first()
    )

    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    return {
        "id": expense.id,
        "amount": float(expense.amount),
        "vendor": expense.vendor,
        "category": expense.category,
        "description": expense.description,
        "status": expense.status.value,
        "date": expense.date.isoformat(),
        "user_id": expense.user_id,
    }


@app.patch("/api/v1/expenses/{expense_id}")
async def update_expense(
    expense_id: str,
    data: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update an expense with tenant isolation"""
    from .models import Expense

    # Get organization context for multi-tenancy
    organization_id = get_organization_context(current_user, db)

    # Query expense with organization filter for tenant isolation
    expense = (
        db.query(Expense)
        .filter(Expense.id == expense_id, Expense.organization_id == organization_id)
        .first()
    )

    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    # Update fields if provided
    if "amount" in data:
        expense.amount = data["amount"]
    if "vendor" in data:
        expense.vendor = data["vendor"]
    if "category" in data:
        expense.category = data["category"]
    if "description" in data:
        expense.description = data["description"]
    if "date" in data:
        from datetime import datetime

        expense.date = (
            datetime.fromisoformat(data["date"])
            if isinstance(data["date"], str)
            else data["date"]
        )

    db.commit()
    db.refresh(expense)

    return {
        "id": expense.id,
        "amount": float(expense.amount),
        "vendor": expense.vendor,
        "category": expense.category,
        "description": expense.description,
        "status": expense.status.value,
        "date": expense.date.isoformat(),
        "user_id": expense.user_id,
    }


@app.delete("/api/v1/expenses/{expense_id}")
async def delete_expense(
    expense_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete an expense with tenant isolation"""
    from .models import Expense

    # Get organization context for multi-tenancy
    organization_id = get_organization_context(current_user, db)

    # Query expense with organization filter for tenant isolation
    expense = (
        db.query(Expense)
        .filter(Expense.id == expense_id, Expense.organization_id == organization_id)
        .first()
    )

    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    db.delete(expense)
    db.commit()

    return {"success": True, "message": "Expense deleted"}


@app.post("/api/v1/expenses/approve")
async def approve_expense(
    data: ExpenseApproval,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        # Get organization context for multi-tenancy
        from datetime import datetime

        from .models import Expense, ExpenseStatus, UserRole
        from .services.audit_service import AuditService
        from .tenant_context import TenantContext

        organization_id = TenantContext.get_organization()  # noqa: F841

        # Get the expense from database first
        expense = db.query(Expense).filter(Expense.id == data.expense_id).first()
        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")

        if expense.status != ExpenseStatus.PENDING:
            raise HTTPException(
                status_code=400, detail=f"Expense is already {expense.status.value}"
            )

        # Use new permission system with approval logic
        if not can_approve_expense(
            user_role=current_user.role,
            expense_amount=float(expense.amount),
            expense_user_id=expense.user_id,
            user_id=current_user.id,
        ):
            raise HTTPException(
                status_code=403, detail="Not authorized to approve this expense"
            )

        # Update expense status
        expense.status = ExpenseStatus.APPROVED
        expense.approved_by = current_user.id
        expense.approved_at = datetime.utcnow()

        # Create complete AP2 audit trail with all mandates
        audit_service = AuditService(db)
        audit_trail = audit_service.create_complete_audit_trail(
            expense=expense, approver=current_user, action="approve"
        )

        # Send approval notification to employee
        try:
            from .models import User as UserModel
            from .services.notification_service import notification_service

            # Get employee details
            employee = (
                db.query(UserModel).filter(UserModel.id == expense.user_id).first()
            )
            if employee:
                notification_service.notify_expense_approved(
                    expense_id=expense.id,
                    employee_name=employee.full_name or employee.username,
                    employee_email=employee.email,
                    amount=float(expense.amount),
                    approved_by=current_user.full_name or current_user.username,
                    transaction_id=audit_trail["transaction_id"],
                )
        except Exception as e:
            # Log notification error but don't fail the request
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send approval email notification: {str(e)}")

        return {
            "success": True,
            "result": {
                "expense_id": expense.id,
                "status": expense.status.value,
                "transaction_id": audit_trail["transaction_id"],
                "mandates": {
                    "intent": audit_trail["intent_mandate"],
                    "cart": audit_trail["cart_mandate"],
                    "payment": audit_trail["payment_mandate"],
                },
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/expenses/reject")
async def reject_expense(
    data: ExpenseApproval,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        # Get organization context for multi-tenancy
        import json
        import uuid
        from datetime import datetime

        from .models import AuditLog, Expense, ExpenseStatus, UserRole
        from .tenant_context import TenantContext

        organization_id = TenantContext.get_organization()  # noqa: F841

        # Get the expense from database first
        expense = db.query(Expense).filter(Expense.id == data.expense_id).first()
        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")

        if expense.status != ExpenseStatus.PENDING:
            raise HTTPException(
                status_code=400, detail=f"Expense is already {expense.status.value}"
            )

        # Use new permission system - same approval logic applies to rejection
        if not can_approve_expense(
            user_role=current_user.role,
            expense_amount=float(expense.amount),
            expense_user_id=expense.user_id,
            user_id=current_user.id,
        ):
            raise HTTPException(
                status_code=403, detail="Not authorized to reject this expense"
            )

        # Update expense status to rejected
        expense.status = ExpenseStatus.REJECTED
        expense.approved_by = current_user.id  # Track who rejected it
        expense.approved_at = datetime.utcnow()  # Track when rejected
        expense.rejection_reason = data.rejection_reason  # Save rejection reason

        # Create audit log entry for rejection
        audit_log = AuditLog(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            action="expense_reject",
            resource_type="expense",
            resource_id=expense.id,
            details=json.dumps(
                {
                    "amount": float(expense.amount),
                    "vendor": expense.vendor,
                    "category": expense.category.value,
                    "rejection_reason": data.rejection_reason,
                    "status_change": "PENDING -> REJECTED",
                }
            ),
        )
        db.add(audit_log)

        db.commit()
        db.refresh(expense)

        # Send rejection notification to employee
        try:
            from .models import User as UserModel
            from .services.notification_service import notification_service

            # Get employee details
            employee = (
                db.query(UserModel).filter(UserModel.id == expense.user_id).first()
            )
            if employee:
                notification_service.notify_expense_rejected(
                    expense_id=expense.id,
                    employee_name=employee.full_name or employee.username,
                    employee_email=employee.email,
                    amount=float(expense.amount),
                    rejected_by=current_user.full_name or current_user.username,
                    rejection_reason=data.rejection_reason,
                )
        except Exception as e:
            # Log notification error but don't fail the request
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send rejection email notification: {str(e)}")

        return {
            "success": True,
            "result": {
                "expense_id": expense.id,
                "status": expense.status.value,
                "rejected_by": current_user.id,
                "rejected_at": expense.approved_at.isoformat(),
                "rejection_reason": expense.rejection_reason,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/v1/expenses/{expense_id}/withdraw")
async def withdraw_expense(
    expense_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Withdraw a pending expense (employee only, must own the expense)"""
    try:
        from datetime import datetime

        from .models import Expense, ExpenseStatus

        # Get the expense from database
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")

        # Check ownership - only the expense owner can withdraw
        if expense.user_id != current_user.id:
            raise HTTPException(
                status_code=403, detail="You can only withdraw your own expenses"
            )

        # Can only withdraw pending expenses
        if expense.status != ExpenseStatus.PENDING:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Cannot withdraw expense with status: {expense.status.value}. "
                    "Only pending expenses can be withdrawn."
                ),
            )

        # Mark as withdrawn (soft delete)
        expense.status = ExpenseStatus.WITHDRAWN
        expense.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(expense)

        return {
            "success": True,
            "message": "Expense withdrawn successfully",
            "expense_id": expense.id,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/expenses/report")
async def get_report(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    user_id: Optional[str] = None,
):
    # Regular users can only see their own reports
    # Managers and admins can see all reports
    from .models import Expense, ExpenseStatus, UserRole

    if user_id and user_id != current_user.id:
        # Check if user has permission to view other users' reports
        if not has_any_permission(
            current_user.role,
            [Permission.REPORT_VIEW_DEPARTMENT, Permission.REPORT_VIEW_ALL],
        ):
            raise HTTPException(
                status_code=403, detail="Not authorized to view other users' reports"
            )

    # Query expenses directly from database (exclude withdrawn expenses)
    target_user_id = user_id or current_user.id
    expenses = (
        db.query(Expense)
        .filter(
            Expense.user_id == target_user_id, Expense.status != ExpenseStatus.WITHDRAWN
        )
        .all()
    )

    # Calculate stats
    total_expenses = len(expenses)
    total_amount = sum(float(e.amount) for e in expenses)
    pending = sum(1 for e in expenses if e.status == ExpenseStatus.PENDING)
    approved = sum(1 for e in expenses if e.status == ExpenseStatus.APPROVED)
    rejected = sum(1 for e in expenses if e.status == ExpenseStatus.REJECTED)

    # Get receipt details for each expense
    from .models import Receipt

    expense_list = []
    for e in expenses:
        # Fetch all receipts for this expense
        receipts = db.query(Receipt).filter(Receipt.expense_id == e.id).all()
        receipt_list = [
            {
                "id": r.id,
                "filename": r.original_filename,
                "file_size": r.file_size,
                "content_type": r.content_type,
                "uploaded_at": r.uploaded_at.isoformat() if r.uploaded_at else None,
            }
            for r in receipts
        ]

        expense_list.append(
            {
                "id": e.id,
                "amount": float(e.amount),
                "vendor": e.vendor,
                "category": e.category,
                "description": e.description,
                "status": e.status.value,
                "date": e.date.isoformat() if e.date else None,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "transaction_id": e.transaction_id,
                "rejection_reason": e.rejection_reason,
                "receipt_count": len(receipt_list),
                "receipts": receipt_list,
            }
        )

    return {
        "user_id": target_user_id,
        "total_expenses": total_expenses,
        "total_amount": total_amount,
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "expenses": expense_list,
    }


@app.put("/api/v1/expenses/{expense_id}")
async def update_expense(
    expense_id: str,
    data: ExpenseSubmission,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update a pending expense (employee only, must own the expense)"""
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"[UPDATE_EXPENSE] Route called for expense_id: {expense_id}")
    logger.info(
        f"[UPDATE_EXPENSE] Data received: user={current_user.username}, "
        f"amount={data.amount}, vendor={data.vendor}, category={data.category}, "
        f"description={data.description}"
    )

    try:
        from datetime import datetime

        from .models import Expense, ExpenseCategory, ExpenseStatus

        # Get the expense from database
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")

        # Check ownership - only the expense owner can edit
        if expense.user_id != current_user.id:
            raise HTTPException(
                status_code=403, detail="You can only edit your own expenses"
            )

        # Can only edit pending expenses
        if expense.status != ExpenseStatus.PENDING:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Cannot edit expense with status: {expense.status.value}. "
                    "Only pending expenses can be edited."
                ),
            )

        # Convert category string to enum if needed
        try:
            category_enum = ExpenseCategory(data.category)
        except ValueError:
            logger.error(f"[UPDATE_EXPENSE] Invalid category: {data.category}")
            valid_cats = ", ".join([e.value for e in ExpenseCategory])
            raise HTTPException(
                status_code=422,
                detail=f"Invalid category '{data.category}'. Must be one of: {valid_cats}",
            )

        # Update expense fields
        expense.amount = data.amount
        expense.vendor = data.vendor
        expense.category = category_enum
        expense.description = data.description
        expense.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(expense)

        return {
            "success": True,
            "message": "Expense updated successfully",
            "expense": {
                "id": expense.id,
                "amount": float(expense.amount),
                "vendor": expense.vendor,
                "category": expense.category,
                "description": expense.description,
                "status": expense.status.value,
                "date": expense.date.isoformat(),
                "user_id": expense.user_id,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/audit/{transaction_id}")
async def get_audit(
    transaction_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get complete AP2 audit trail for a transaction"""
    try:
        from .services.audit_service import AuditService

        audit_service = AuditService(db)
        audit = audit_service.get_complete_audit_trail(transaction_id)

        if not audit:
            raise HTTPException(
                status_code=404,
                detail=f"Audit trail not found for transaction {transaction_id}",
            )

        return audit
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving audit trail: {str(e)}"
        )


class CommentSubmission(BaseModel):
    comment: str


class BulkExpenseAction(BaseModel):
    expense_ids: list[str]
    rejection_reason: Optional[str] = None  # Only used for bulk reject


@app.post("/api/v1/expenses/{expense_id}/comments")
async def add_expense_comment(
    expense_id: str,
    data: CommentSubmission,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Add a comment to an expense"""
    try:
        import uuid

        from .models import Expense, ExpenseComment
        from .models import User as UserModel

        # Get the expense
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")

        # Create comment
        comment = ExpenseComment(
            id=str(uuid.uuid4()),
            expense_id=expense_id,
            user_id=current_user.id,
            comment=data.comment,
        )

        db.add(comment)
        db.commit()
        db.refresh(comment)

        # Send notification to relevant parties
        try:
            from .services.notification_service import notification_service

            # Get expense owner
            expense_owner = (
                db.query(UserModel).filter(UserModel.id == expense.user_id).first()
            )

            # Notify expense owner if commenter is not the owner
            if expense_owner and current_user.id != expense.user_id:
                notification_service.notify_comment_added(
                    expense_id=expense_id,
                    recipient_name=expense_owner.full_name or expense_owner.username,
                    recipient_email=expense_owner.email,
                    commenter_name=current_user.full_name or current_user.username,
                    comment_text=data.comment,
                    amount=float(expense.amount),
                )

            # If commenter is the owner, notify approver (if expense has been approved/rejected)
            if current_user.id == expense.user_id and expense.approved_by:
                approver = (
                    db.query(UserModel)
                    .filter(UserModel.id == expense.approved_by)
                    .first()
                )
                if approver:
                    notification_service.notify_comment_added(
                        expense_id=expense_id,
                        recipient_name=approver.full_name or approver.username,
                        recipient_email=approver.email,
                        commenter_name=current_user.full_name or current_user.username,
                        comment_text=data.comment,
                        amount=float(expense.amount),
                    )
        except Exception as e:
            # Log notification error but don't fail the request
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send comment notification: {str(e)}")

        return {
            "success": True,
            "comment": {
                "id": comment.id,
                "expense_id": comment.expense_id,
                "user_id": comment.user_id,
                "comment": comment.comment,
                "created_at": (
                    comment.created_at.isoformat() if comment.created_at else None
                ),
                "user_name": current_user.full_name or current_user.username,
                "user_email": current_user.email,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/expenses/{expense_id}/comments")
async def get_expense_comments(
    expense_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get all comments for an expense"""
    try:
        from .models import Expense, ExpenseComment
        from .models import User as UserModel

        # Verify expense exists
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")

        # Get all comments for this expense
        comments = (
            db.query(ExpenseComment)
            .filter(ExpenseComment.expense_id == expense_id)
            .order_by(ExpenseComment.created_at.asc())
            .all()
        )

        # Build response with user details
        result = []
        for comment in comments:
            user = db.query(UserModel).filter(UserModel.id == comment.user_id).first()
            result.append(
                {
                    "id": comment.id,
                    "expense_id": comment.expense_id,
                    "user_id": comment.user_id,
                    "comment": comment.comment,
                    "created_at": (
                        comment.created_at.isoformat() if comment.created_at else None
                    ),
                    "updated_at": (
                        comment.updated_at.isoformat() if comment.updated_at else None
                    ),
                    "user_name": user.full_name if user else "Unknown",
                    "user_email": user.email if user else "Unknown",
                }
            )

        return {
            "expense_id": expense_id,
            "comment_count": len(result),
            "comments": result,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/expenses/{expense_id}/receipts", status_code=201)
async def upload_receipt(
    expense_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Upload receipt for an expense"""
    import uuid
    from datetime import datetime

    from .models import Expense, Receipt

    # Validate file type
    allowed_types = ["application/pdf", "image/jpeg", "image/png", "image/jpg"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=415,
            detail=f"File type {file.content_type} not supported. Use PDF or images.",
        )

    # Get expense and verify ownership
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    # Create receipt record
    receipt = Receipt(
        id=f"receipt_{uuid.uuid4().hex[:8]}",
        expense_id=expense_id,
        filename=file.filename,
        original_filename=file.filename,
        content_type=file.content_type,
        file_size=0,  # Would store actual file size
        file_path=f"/receipts/{expense_id}/{file.filename}",  # Placeholder
        uploaded_at=datetime.utcnow(),
    )

    db.add(receipt)
    db.commit()
    db.refresh(receipt)

    return {"success": True, "receipt_id": receipt.id, "filename": receipt.filename}


@app.get("/api/v1/expenses/{expense_id}/receipts")
async def get_expense_receipts(
    expense_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get all receipts for an expense"""
    from .models import Expense, Receipt

    # Verify expense exists
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    # Get receipts
    receipts = db.query(Receipt).filter(Receipt.expense_id == expense_id).all()

    return [
        {
            "id": r.id,
            "filename": r.filename,
            "content_type": r.content_type,
            "uploaded_at": r.uploaded_at.isoformat() if r.uploaded_at else None,
        }
        for r in receipts
    ]


@app.post("/api/v1/expenses/bulk-approve")
async def bulk_approve_expenses(
    data: BulkExpenseAction,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Approve multiple expenses at once (manager/admin only)"""
    try:
        from datetime import datetime

        from .models import Expense, ExpenseStatus
        from .models import User as UserModel
        from .models import UserRole
        from .services.audit_service import AuditService

        # Check permission for bulk approve
        check_permission(
            current_user.role, Permission.EXPENSE_BULK_APPROVE, raise_exception=True
        )

        results = []
        audit_service = AuditService(db)

        for expense_id in data.expense_ids:
            try:
                # Get the expense from database
                expense = db.query(Expense).filter(Expense.id == expense_id).first()
                if not expense:
                    results.append(
                        {
                            "expense_id": expense_id,
                            "success": False,
                            "error": "Expense not found",
                        }
                    )
                    continue

                if expense.status != ExpenseStatus.PENDING:
                    results.append(
                        {
                            "expense_id": expense_id,
                            "success": False,
                            "error": f"Expense is already {expense.status.value}",
                        }
                    )
                    continue

                # Check if user can approve this specific expense (amount limit, self-approval)
                try:
                    if not can_approve_expense(
                        user_role=current_user.role,
                        expense_amount=float(expense.amount),
                        expense_user_id=expense.user_id,
                        user_id=current_user.id,
                    ):
                        results.append(
                            {
                                "expense_id": expense_id,
                                "success": False,
                                "error": "Not authorized to approve this expense",
                            }
                        )
                        continue
                except HTTPException as e:
                    results.append(
                        {"expense_id": expense_id, "success": False, "error": e.detail}
                    )
                    continue

                # Update expense status
                expense.status = ExpenseStatus.APPROVED
                expense.approved_by = current_user.id
                expense.approved_at = datetime.utcnow()

                # Create audit trail
                audit_trail = audit_service.create_complete_audit_trail(
                    expense=expense, approver=current_user, action="approve"
                )

                # Send approval notification
                try:
                    from .services.notification_service import notification_service

                    employee = (
                        db.query(UserModel)
                        .filter(UserModel.id == expense.user_id)
                        .first()
                    )
                    if employee:
                        notification_service.notify_expense_approved(
                            expense_id=expense.id,
                            employee_name=employee.full_name or employee.username,
                            employee_email=employee.email,
                            amount=float(expense.amount),
                            approved_by=current_user.full_name or current_user.username,
                            transaction_id=audit_trail["transaction_id"],
                        )
                except Exception as e:
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to send approval notification: {str(e)}")

                results.append(
                    {
                        "expense_id": expense_id,
                        "success": True,
                        "transaction_id": audit_trail["transaction_id"],
                        "status": expense.status.value,
                    }
                )

            except Exception as e:
                results.append(
                    {"expense_id": expense_id, "success": False, "error": str(e)}
                )

        db.commit()

        success_count = sum(1 for r in results if r["success"])
        return {
            "success": True,
            "total": len(data.expense_ids),
            "approved": success_count,
            "failed": len(data.expense_ids) - success_count,
            "results": results,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/expenses/bulk-reject")
async def bulk_reject_expenses(
    data: BulkExpenseAction,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Reject multiple expenses at once (manager/admin only)"""
    try:
        import json
        import uuid
        from datetime import datetime

        from .models import AuditLog, Expense, ExpenseStatus
        from .models import User as UserModel
        from .models import UserRole

        # Check permission for bulk reject
        check_permission(
            current_user.role, Permission.EXPENSE_BULK_REJECT, raise_exception=True
        )

        results = []

        for expense_id in data.expense_ids:
            try:
                # Get the expense from database
                expense = db.query(Expense).filter(Expense.id == expense_id).first()
                if not expense:
                    results.append(
                        {
                            "expense_id": expense_id,
                            "success": False,
                            "error": "Expense not found",
                        }
                    )
                    continue

                if expense.status != ExpenseStatus.PENDING:
                    results.append(
                        {
                            "expense_id": expense_id,
                            "success": False,
                            "error": f"Expense is already {expense.status.value}",
                        }
                    )
                    continue

                # Check if user can reject this specific expense (amount limit, self-approval)
                try:
                    if not can_approve_expense(
                        user_role=current_user.role,
                        expense_amount=float(expense.amount),
                        expense_user_id=expense.user_id,
                        user_id=current_user.id,
                    ):
                        results.append(
                            {
                                "expense_id": expense_id,
                                "success": False,
                                "error": "Not authorized to reject this expense",
                            }
                        )
                        continue
                except HTTPException as e:
                    results.append(
                        {"expense_id": expense_id, "success": False, "error": e.detail}
                    )
                    continue

                # Update expense status to rejected
                expense.status = ExpenseStatus.REJECTED
                expense.approved_by = current_user.id
                expense.approved_at = datetime.utcnow()
                expense.rejection_reason = data.rejection_reason

                # Create audit log entry
                audit_log = AuditLog(
                    id=str(uuid.uuid4()),
                    user_id=current_user.id,
                    action="expense_bulk_reject",
                    resource_type="expense",
                    resource_id=expense.id,
                    details=json.dumps(
                        {
                            "amount": float(expense.amount),
                            "vendor": expense.vendor,
                            "category": expense.category.value,
                            "rejection_reason": data.rejection_reason,
                            "status_change": "PENDING -> REJECTED",
                        }
                    ),
                )
                db.add(audit_log)

                # Send rejection notification
                try:
                    from .services.notification_service import notification_service

                    employee = (
                        db.query(UserModel)
                        .filter(UserModel.id == expense.user_id)
                        .first()
                    )
                    if employee:
                        notification_service.notify_expense_rejected(
                            expense_id=expense.id,
                            employee_name=employee.full_name or employee.username,
                            employee_email=employee.email,
                            amount=float(expense.amount),
                            rejected_by=current_user.full_name or current_user.username,
                            rejection_reason=data.rejection_reason,
                        )
                except Exception as e:
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to send rejection notification: {str(e)}")

                results.append(
                    {
                        "expense_id": expense_id,
                        "success": True,
                        "status": expense.status.value,
                        "rejection_reason": expense.rejection_reason,
                    }
                )

            except Exception as e:
                results.append(
                    {"expense_id": expense_id, "success": False, "error": str(e)}
                )

        db.commit()

        success_count = sum(1 for r in results if r["success"])
        return {
            "success": True,
            "total": len(data.expense_ids),
            "rejected": success_count,
            "failed": len(data.expense_ids) - success_count,
            "results": results,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
