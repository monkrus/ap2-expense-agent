from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
import os

from .config import settings
from .routes import auth_router, users_router, oauth_router, admin_router
from .routes.billing import router as billing_router
from .routes.ap2 import router as ap2_router
from .routes.webhooks import router as webhooks_router
from .routes.organizations import router as organizations_router
from .database import init_db, get_db
from .auth import get_current_active_user
from .models import User
from .rate_limit import limiter, rate_limit_handler
from slowapi.errors import RateLimitExceeded
from .security_middleware import SecurityHeadersMiddleware, RequestIDMiddleware, HTTPSRedirectMiddleware
from .tenant_context import tenant_middleware

# Try to import database-integrated agent, fallback to in-memory agent
try:
    from .agent_db import ExpenseManagementAgent as DBAgent
    AGENT_DB_AVAILABLE = True
except ImportError:
    AGENT_DB_AVAILABLE = False
    print("Warning: Database agent not available. Using in-memory agent.")

# Fallback to in-memory agent if DB agent not available
if not AGENT_DB_AVAILABLE:
    try:
        from .agent import ExpenseManagementAgent
        AGENT_AVAILABLE = True
    except ImportError:
        AGENT_AVAILABLE = False
        print("Warning: Google AI dependencies not installed. Agent features will be disabled.")
else:
    AGENT_AVAILABLE = True

app = FastAPI(
    title="AP2 Expense Management Agent",
    description="AI-powered expense management with AP2 protocol",
    version="1.0.0"
)

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
    allow_headers=["Authorization", "Content-Type", "X-Organization-Id"],  # Added X-Organization-Id for multi-tenancy
)

# Add tenant middleware for multi-tenancy support
app.middleware("http")(tenant_middleware)

# Include authentication routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(oauth_router)
app.include_router(admin_router)

# Include organization router (multi-tenancy)
app.include_router(organizations_router)

# Include billing and payment routers
app.include_router(billing_router)
app.include_router(ap2_router)
app.include_router(webhooks_router)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()

# Agent will be initialized per-request with database session
# This is more appropriate for database-backed operations
agent = None

class ExpenseSubmission(BaseModel):
    user_id: str
    amount: float
    vendor: str
    category: str
    description: str

class ExpenseApproval(BaseModel):
    expense_id: str
    approver_id: str

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "AP2 Expense Management Agent"}

@app.post("/api/v1/expenses")
async def submit_expense(
    data: ExpenseSubmission,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    request: Request = None
):
    try:
        # Get organization context for multi-tenancy
        from .tenant_context import TenantContext
        organization_id = TenantContext.get_organization()

        # Initialize database-integrated agent with organization context
        if AGENT_DB_AVAILABLE:
            agent = DBAgent(
                db=db,
                api_key=settings.google_api_key or os.getenv("GOOGLE_API_KEY", ""),
                project_id=settings.google_cloud_project or os.getenv("GOOGLE_CLOUD_PROJECT", ""),
                organization_id=organization_id  # Multi-tenancy
            )
        else:
            raise HTTPException(status_code=503, detail="Agent service unavailable")

        # Use authenticated user's ID
        expense = agent.submit_expense(
            user_id=current_user.id,
            amount=data.amount,
            vendor=data.vendor,
            category=data.category,
            description=data.description
        )
        return {"success": True, "expense": expense}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/expenses/approve")
async def approve_expense(
    data: ExpenseApproval,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        # Get organization context for multi-tenancy
        from .tenant_context import TenantContext
        organization_id = TenantContext.get_organization()

        # Initialize database-integrated agent with organization context
        if AGENT_DB_AVAILABLE:
            agent = DBAgent(
                db=db,
                api_key=settings.google_api_key or os.getenv("GOOGLE_API_KEY", ""),
                project_id=settings.google_cloud_project or os.getenv("GOOGLE_CLOUD_PROJECT", ""),
                organization_id=organization_id  # Multi-tenancy
            )
        else:
            raise HTTPException(status_code=503, detail="Agent service unavailable")

        # Use authenticated user's ID as approver
        result = agent.approve_and_process_expense(
            expense_id=data.expense_id,
            approver_id=current_user.id
        )
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/expenses/report")
async def get_report(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    user_id: Optional[str] = None
):
    # Regular users can only see their own reports
    # Managers and admins can see all reports
    from .models import UserRole
    if user_id and user_id != current_user.id:
        if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.ACCOUNTANT]:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to view other users' reports"
            )

    # Get organization context for multi-tenancy
    from .tenant_context import TenantContext
    organization_id = TenantContext.get_organization()

    # Initialize database-integrated agent with organization context
    if AGENT_DB_AVAILABLE:
        agent = DBAgent(
            db=db,
            api_key=settings.google_api_key or os.getenv("GOOGLE_API_KEY", ""),
            project_id=settings.google_cloud_project or os.getenv("GOOGLE_CLOUD_PROJECT", ""),
            organization_id=organization_id  # Multi-tenancy
        )
    else:
        raise HTTPException(status_code=503, detail="Agent service unavailable")

    report = agent.get_expense_report(user_id or current_user.id)
    return report

@app.get("/api/v1/audit/{transaction_id}")
async def get_audit(
    transaction_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        # Initialize database-integrated agent
        if AGENT_DB_AVAILABLE:
            agent = DBAgent(
                db=db,
                api_key=settings.google_api_key or os.getenv("GOOGLE_API_KEY", ""),
                project_id=settings.google_cloud_project or os.getenv("GOOGLE_CLOUD_PROJECT", "")
            )
        else:
            raise HTTPException(status_code=503, detail="Agent service unavailable")

        audit = agent.get_audit_trail(transaction_id)
        return audit
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))