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
from .routes.receipts import router as receipts_router
from .database import init_db, get_db
from .auth import get_current_active_user
from .models import User
from .rate_limit import limiter, rate_limit_handler
from slowapi.errors import RateLimitExceeded
from .security_middleware import SecurityHeadersMiddleware, RequestIDMiddleware, HTTPSRedirectMiddleware
from .tenant_context import tenant_middleware
from .error_handlers import register_exception_handlers

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
app.include_router(receipts_router)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()
    print("[STARTUP] Registered routes:")
    for route in app.routes:
        if hasattr(route, 'path'):
            print(f"  {route.methods if hasattr(route, 'methods') else 'N/A'} {route.path}")

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
    rejection_reason: Optional[str] = None

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
        from .models import Expense, ExpenseStatus, UserRole
        from .services.audit_service import AuditService
        from datetime import datetime

        organization_id = TenantContext.get_organization()

        # Only admins, managers, and accountants can approve expenses
        if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.ACCOUNTANT]:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to approve expenses"
            )

        # Get the expense from database
        expense = db.query(Expense).filter(Expense.id == data.expense_id).first()
        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")

        if expense.status != ExpenseStatus.PENDING:
            raise HTTPException(status_code=400, detail=f"Expense is already {expense.status.value}")

        # Update expense status
        expense.status = ExpenseStatus.APPROVED
        expense.approved_by = current_user.id
        expense.approved_at = datetime.utcnow()

        # Create complete AP2 audit trail with all mandates
        audit_service = AuditService(db)
        audit_trail = audit_service.create_complete_audit_trail(
            expense=expense,
            approver=current_user,
            action="approve"
        )

        return {
            "success": True,
            "result": {
                "expense_id": expense.id,
                "status": expense.status.value,
                "transaction_id": audit_trail["transaction_id"],
                "mandates": {
                    "intent": audit_trail["intent_mandate"],
                    "cart": audit_trail["cart_mandate"],
                    "payment": audit_trail["payment_mandate"]
                }
            }
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
    db: Session = Depends(get_db)
):
    try:
        # Get organization context for multi-tenancy
        from .tenant_context import TenantContext
        from .models import Expense, ExpenseStatus, UserRole, AuditLog
        from datetime import datetime
        import uuid
        import json

        organization_id = TenantContext.get_organization()

        # Only admins, managers, and accountants can reject expenses
        if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.ACCOUNTANT]:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to reject expenses"
            )

        # Get the expense from database
        expense = db.query(Expense).filter(Expense.id == data.expense_id).first()
        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")

        if expense.status != ExpenseStatus.PENDING:
            raise HTTPException(status_code=400, detail=f"Expense is already {expense.status.value}")

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
            details=json.dumps({
                "amount": float(expense.amount),
                "vendor": expense.vendor,
                "category": expense.category.value,
                "rejection_reason": data.rejection_reason,
                "status_change": "PENDING -> REJECTED"
            })
        )
        db.add(audit_log)

        db.commit()
        db.refresh(expense)

        return {
            "success": True,
            "result": {
                "expense_id": expense.id,
                "status": expense.status.value,
                "rejected_by": current_user.id,
                "rejected_at": expense.approved_at.isoformat(),
                "rejection_reason": expense.rejection_reason
            }
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
    db: Session = Depends(get_db)
):
    """Withdraw a pending expense (employee only, must own the expense)"""
    try:
        from .models import Expense, ExpenseStatus
        from datetime import datetime

        # Get the expense from database
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")

        # Check ownership - only the expense owner can withdraw
        if expense.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You can only withdraw your own expenses"
            )

        # Can only withdraw pending expenses
        if expense.status != ExpenseStatus.PENDING:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot withdraw expense with status: {expense.status.value}. Only pending expenses can be withdrawn."
            )

        # Mark as withdrawn (soft delete)
        expense.status = ExpenseStatus.WITHDRAWN
        expense.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(expense)

        return {
            "success": True,
            "message": "Expense withdrawn successfully",
            "expense_id": expense.id
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/expenses/all-pending")
async def get_all_pending_expenses(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all pending expenses from all users (admin/manager only)"""
    from .models import UserRole, Expense, ExpenseStatus, User as UserModel

    # Only admins, managers, and accountants can view all expenses
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.ACCOUNTANT]:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to view all expenses"
        )

    # Get all pending expenses with user information
    expenses = db.query(Expense).filter(Expense.status == ExpenseStatus.PENDING).all()

    # Get user details for each expense
    result = []
    for e in expenses:
        user = db.query(UserModel).filter(UserModel.id == e.user_id).first()
        result.append({
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
            "user_name": user.full_name if user else "Unknown"
        })

    return {
        "pending_count": len(result),
        "total_amount": sum(e["amount"] for e in result),
        "expenses": result
    }

@app.get("/api/v1/expenses/all")
async def get_all_expenses(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    status: Optional[str] = None
):
    """Get all expenses from all users with optional status filter (admin/manager only)"""
    # Reload trigger
    from .models import UserRole, Expense, ExpenseStatus, User as UserModel
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"[get_all_expenses] Called with status filter: {status}")

    # Only admins, managers, and accountants can view all expenses
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.ACCOUNTANT]:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to view all expenses"
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

        result.append({
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
            "approved_by_email": approver.email if approver else None
        })

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
        "expenses": result
    }

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

    # Query expenses directly from database (exclude withdrawn expenses)
    target_user_id = user_id or current_user.id
    expenses = db.query(Expense).filter(
        Expense.user_id == target_user_id,
        Expense.status != ExpenseStatus.WITHDRAWN
    ).all()

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
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "transaction_id": e.transaction_id,
                "rejection_reason": e.rejection_reason
            }
            for e in expenses
        ]
    }

@app.put("/api/v1/expenses/{expense_id}")
async def update_expense(
    expense_id: str,
    data: ExpenseSubmission,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a pending expense (employee only, must own the expense)"""
    print(f"[UPDATE_EXPENSE] Route called for expense_id: {expense_id} - reload trigger")
    try:
        from .models import Expense, ExpenseStatus
        from datetime import datetime

        # Get the expense from database
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")

        # Check ownership - only the expense owner can edit
        if expense.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You can only edit your own expenses"
            )

        # Can only edit pending expenses
        if expense.status != ExpenseStatus.PENDING:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot edit expense with status: {expense.status.value}. Only pending expenses can be edited."
            )

        # Update expense fields
        expense.amount = data.amount
        expense.vendor = data.vendor
        expense.category = data.category
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
                "user_id": expense.user_id
            }
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
    db: Session = Depends(get_db)
):
    """Get complete AP2 audit trail for a transaction"""
    try:
        from .services.audit_service import AuditService

        audit_service = AuditService(db)
        audit = audit_service.get_complete_audit_trail(transaction_id)

        if not audit:
            raise HTTPException(
                status_code=404,
                detail=f"Audit trail not found for transaction {transaction_id}"
            )

        return audit
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving audit trail: {str(e)}")
