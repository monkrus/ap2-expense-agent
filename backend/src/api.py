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
# Force reload - auth routes should be available

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
        from .models import Expense, ExpenseStatus, ExpenseCategory
        from datetime import datetime
        import uuid

        organization_id = TenantContext.get_organization()

        # Create expense directly in database (simplified version without AI agent)
        expense = Expense(
            id=str(uuid.uuid4()),
            organization_id=organization_id or str(uuid.uuid4()),  # Create temp org if none
            user_id=current_user.id,
            amount=data.amount,
            vendor=data.vendor,
            category=data.category,
            description=data.description,
            status=ExpenseStatus.PENDING,
            date=datetime.utcnow(),
            ai_analysis="Manual submission - AI analysis not available",
            risk_level="LOW",
            compliance_check=True
        )

        db.add(expense)
        db.commit()
        db.refresh(expense)

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
                "user_id": expense.user_id
            }
        }
    except Exception as e:
        db.rollback()
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
        from .models import Expense, ExpenseStatus
        from datetime import datetime
        import uuid

        organization_id = TenantContext.get_organization()

        # Get the expense from database
        expense = db.query(Expense).filter(Expense.id == data.expense_id).first()
        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")

        if expense.status != ExpenseStatus.PENDING:
            raise HTTPException(status_code=400, detail=f"Expense is already {expense.status.value}")

        # Generate AP2 mandate IDs for tracking
        intent_id = f"intent_{uuid.uuid4().hex[:16]}"
        cart_id = f"cart_{uuid.uuid4().hex[:16]}"
        payment_id = f"payment_{uuid.uuid4().hex[:16]}"

        # Update expense status and link to AP2 mandates
        expense.status = ExpenseStatus.APPROVED
        expense.approved_by = current_user.id
        expense.approved_at = datetime.utcnow()
        expense.intent_mandate_id = intent_id
        expense.cart_mandate_id = cart_id
        expense.payment_mandate_id = payment_id
        expense.transaction_id = payment_id  # Use payment mandate as transaction ID

        db.commit()
        db.refresh(expense)

        return {
            "success": True,
            "result": {
                "expense_id": expense.id,
                "status": expense.status.value,
                "transaction_id": payment_id,
                "mandates": {
                    "intent": {"id": intent_id},
                    "cart": {"id": cart_id},
                    "payment": {"id": payment_id}
                }
            }
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
    user_id: Optional[str] = None
):
    # Regular users can only see their own reports
    # Managers and admins can see all reports
    from .models import UserRole, Expense, ExpenseStatus
    from sqlalchemy import func

    if user_id and user_id != current_user.id:
        if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.ACCOUNTANT]:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to view other users' reports"
            )

    # Query expenses directly from database
    target_user_id = user_id or current_user.id
    expenses = db.query(Expense).filter(Expense.user_id == target_user_id).all()

    # Calculate stats
    total_expenses = len(expenses)
    total_amount = sum(float(e.amount) for e in expenses)
    pending = sum(1 for e in expenses if e.status == ExpenseStatus.PENDING)
    approved = sum(1 for e in expenses if e.status == ExpenseStatus.APPROVED)
    rejected = sum(1 for e in expenses if e.status == ExpenseStatus.REJECTED)

    return {
        "user_id": target_user_id,
        "total_expenses": total_expenses,
        "total_amount": total_amount,
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "expenses": [
            {
                "id": e.id,
                "amount": float(e.amount),
                "vendor": e.vendor,
                "category": e.category,
                "description": e.description,
                "status": e.status.value,
                "date": e.date.isoformat() if e.date else None,
                "created_at": e.created_at.isoformat() if e.created_at else None
            }
            for e in expenses
        ]
    }

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