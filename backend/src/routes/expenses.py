"""
Expense Management Routes with Role-Based Access Control

This module provides comprehensive expense management endpoints with:
- Secure multi-tenant isolation
- Role-based permissions
- Complete expense lifecycle workflows
- Approval chains
- Audit trails
"""

import json
import logging
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, or_

from ..auth import get_current_active_user
from ..database import get_db
from ..models import (
    Expense,
    ExpenseComment,
    ExpenseStatus,
    Notification,
    NotificationType,
    Organization,
    OrganizationMember,
    PaymentMandate,
    RuleRequest,
    RuleRequestStatus,
    User,
    UserRole,
    OrganizationRole,
)
from ..schemas import ExpenseSubmission, ExpenseUpdate
from ..tenant_context import (
    TenantContext,
    verify_organization_access,
    get_user_organization_role,
)
from ..permissions import can_approve_expense
from ..email_service import EmailService

router = APIRouter(prefix="/api/v1/expenses", tags=["expenses"])
logger = logging.getLogger(__name__)


# ============================================================================
# SECURITY HELPER FUNCTIONS
# ============================================================================

def ensure_org_access(user_id: str, org_id: str, db: Session):
    """Verify user has access to organization, raise 403 if not"""
    if not verify_organization_access(user_id, org_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this organization"
        )


def ensure_expense_access(expense_id: str, user: User, org_id: str, db: Session) -> Expense:
    """
    Verify user can access specific expense
    Returns expense if authorized, raises 403/404 otherwise
    """
    # First verify organization access
    ensure_org_access(user.id, org_id, db)

    # Get expense
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.organization_id == org_id
    ).first()

    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )

    # Check role-based access
    user_org_role = get_user_organization_role(user.id, org_id, db)

    # SECURITY FIX (HIGH-4): Only check organization roles, not global roles
    # Owners and admins can see all expenses in their organization
    if user_org_role in ["owner", "admin"]:
        return expense

    # Managers can see department expenses
    if user_org_role == "manager":
        if user.department_id:
            expense_owner = db.query(User).filter(User.id == expense.user_id).first()
            if expense_owner and expense_owner.department_id == user.department_id:
                return expense
            # Fall through to own-expense check below
        else:
            # No department set — fall through to own-expense check
            pass

    # Employees (and managers outside their dept) can only see their own expenses
    if expense.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own expenses"
        )

    return expense


def can_modify_expense(expense: Expense, user: User, org_id: str, db: Session, action: str = "edit") -> bool:
    """Check if user can modify expense.

    action='edit' enforces strict locking on approved/rejected expenses.
    action='withdraw' allows admins/owners to withdraw any non-withdrawn expense.
    """
    user_org_role = get_user_organization_role(user.id, org_id, db)
    is_admin = user_org_role in ["owner", "admin"] or user.role == UserRole.ADMIN

    # For withdraw: admins can withdraw any expense that isn't already withdrawn
    if action == "withdraw":
        if expense.status == ExpenseStatus.WITHDRAWN:
            return False
        if is_admin:
            return True
        # Regular users can only withdraw their own pending expenses
        return expense.user_id == user.id and expense.status == ExpenseStatus.PENDING

    # For edit: approved or rejected expenses are locked — no one can edit them
    if expense.status in [ExpenseStatus.APPROVED, ExpenseStatus.REJECTED]:
        return False

    if is_admin:
        return True

    # Users can only modify their own pending expenses
    if expense.user_id == user.id and expense.status == ExpenseStatus.PENDING:
        return True

    return False


# ============================================================================
# EXPENSE CRUD ENDPOINTS
# ============================================================================

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_expense(
    data: ExpenseSubmission,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a new expense

    Accessible by: All authenticated users
    """
    # Get organization context
    org_id = request.headers.get("X-Organization-Id")

    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required (X-Organization-Id header missing)"
        )

    # Verify organization access (CRITICAL SECURITY CHECK)
    ensure_org_access(current_user.id, org_id, db)

    # Check tier limits (BILLING ENFORCEMENT)
    from ..billing.limit_enforcer import LimitEnforcer, LimitExceededError
    try:
        limit_enforcer = LimitEnforcer(db)
        limit_enforcer.check_expense_limit(org_id, raise_error=True)
    except LimitExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e)
        )

    # =====================================================================
    # COMPREHENSIVE INPUT VALIDATION
    # =====================================================================

    # Validate expense amount
    if data.amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Expense amount must be positive"
        )

    # Maximum amount validation (prevent unrealistic expenses)
    MAX_EXPENSE_AMOUNT = 100000.00  # $100,000
    if data.amount > MAX_EXPENSE_AMOUNT:
        raise HTTPException(
            status_code=400,
            detail=f"Expense amount cannot exceed ${MAX_EXPENSE_AMOUNT:,.2f}. Please contact admin for special approval."
        )

    # Decimal precision validation (currency should have max 2 decimal places)
    if round(data.amount, 2) != data.amount:
        raise HTTPException(
            status_code=400,
            detail="Expense amount must have at most 2 decimal places"
        )

    # Parse and validate expense date
    expense_date = (
        datetime.fromisoformat(data.date) if data.date else datetime.utcnow()
    )

    # Date validation: cannot be in the future
    if expense_date > datetime.utcnow():
        raise HTTPException(
            status_code=400,
            detail="Expense date cannot be in the future"
        )

    # Date validation: cannot be too old (more than 1 year)
    one_year_ago = datetime.utcnow().replace(year=datetime.utcnow().year - 1)
    if expense_date < one_year_ago:
        raise HTTPException(
            status_code=400,
            detail="Expense date cannot be older than 1 year. Please contact admin if you need to submit an older expense."
        )

    # Vendor validation
    if data.vendor and len(data.vendor) > 200:
        raise HTTPException(
            status_code=400,
            detail="Vendor name cannot exceed 200 characters"
        )

    # Description validation
    if data.description and len(data.description) > 1000:
        raise HTTPException(
            status_code=400,
            detail="Description cannot exceed 1000 characters"
        )

    # =====================================================================
    # DUPLICATE SUBMISSION DETECTION (SAFEGUARD)
    # =====================================================================
    # Check if an identical expense was submitted in the last 10 seconds
    # This prevents accidental duplicate submissions from button double-clicks
    from datetime import timedelta
    duplicate_window = datetime.utcnow() - timedelta(seconds=10)

    recent_duplicate = db.query(Expense).filter(
        and_(
            Expense.user_id == current_user.id,
            Expense.organization_id == org_id,
            Expense.amount == data.amount,
            Expense.vendor == data.vendor,
            Expense.category == data.category,
            Expense.description == data.description,
            Expense.created_at >= duplicate_window
        )
    ).first()

    if recent_duplicate:
        logger.warning(
            f"Duplicate expense submission detected for user {current_user.id}. "
            f"Identical expense {recent_duplicate.id} was created {(datetime.utcnow() - recent_duplicate.created_at).total_seconds():.1f}s ago. "
            f"Rejecting duplicate to prevent accidental double-submission."
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Duplicate submission detected. An identical expense was just submitted {int((datetime.utcnow() - recent_duplicate.created_at).total_seconds())} seconds ago. Please wait before submitting again."
        )

    # =====================================================================
    # BUDGET GUARDIAN EVALUATION (proactive budget enforcement)
    # =====================================================================
    budget_warnings = []
    try:
        from ..services.budget_guardian_service import BudgetGuardianService

        guardian = BudgetGuardianService(db)
        category_value = data.category.value if hasattr(data.category, 'value') else str(data.category)
        guardian_result = guardian.evaluate_expense(
            expense_amount=data.amount,
            organization_id=org_id,
            category=category_value,
            user_id=current_user.id,
            hard_block=False,  # Soft enforcement: warn but don't block
        )
        budget_warnings = guardian_result.warnings

        if not guardian_result.allowed:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": "Expense blocked by budget guardian",
                    "blocks": guardian_result.blocks,
                    "budget_impacts": [
                        {
                            "budget_name": i.budget_name,
                            "budget_amount": i.budget_amount,
                            "current_spending": i.current_spending,
                            "proposed_total": i.proposed_total,
                            "percentage_after": i.percentage_after,
                        }
                        for i in guardian_result.budget_impacts
                    ],
                }
            )
    except HTTPException:
        raise
    except ImportError:
        logger.debug("Budget guardian service not available")
    except Exception as e:
        logger.error(f"Budget guardian evaluation failed (non-blocking): {e}")

    # Create expense with PENDING status initially
    expense = Expense(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        user_id=current_user.id,
        amount=data.amount,
        vendor=data.vendor,
        category=data.category,
        description=data.description,
        status=ExpenseStatus.PENDING,
        date=expense_date,
        ai_analysis="Manual submission",
        risk_level="LOW",
        compliance_check=True,
        auto_approved=False,  # Default to False
    )

    db.add(expense)
    db.flush()  # Flush to get ID but don't commit yet

    # =====================================================================
    # AUTO-APPROVAL EVALUATION (TWO-TIER HIERARCHY)
    # Uses shared service: Tier 1 AP2 Intent Mandates, Tier 2 Approval Policies
    # =====================================================================
    from ..services.auto_approval_service import evaluate_auto_approval, notify_admins_new_expense

    approval_result = await evaluate_auto_approval(db, expense, current_user, org_id)

    # Track expense submission for billing
    try:
        from ..billing.usage_tracker import UsageTracker
        tracker = UsageTracker(db)
        metadata = {"expense_id": expense.id, "amount": float(expense.amount)}
        if approval_result.approved:
            metadata["auto_approved"] = True
            metadata["auto_approved_via"] = approval_result.via
        tracker.track_usage(
            user_id=current_user.id,
            usage_type="expense",
            quantity=1,
            organization_id=org_id,
            metadata=metadata,
        )
        logger.info(f"Tracked expense submission for billing: {expense.id}")
    except Exception as e:
        logger.error(f"Failed to track expense usage: {str(e)}")

    if approval_result.approved:
        db.commit()
        db.refresh(expense)

        return {
            "id": expense.id,
            "amount": expense.amount,
            "vendor": expense.vendor,
            "category": expense.category,
            "description": expense.description,
            "status": expense.status.value.lower(),
            "date": expense.date.isoformat() if expense.date else None,
            "created_at": expense.created_at.isoformat() if expense.created_at else None,
            "auto_approved": True,
            "auto_approved_via": approval_result.via,
            "message": approval_result.message,
        }

    # MANUAL APPROVAL REQUIRED
    db.commit()
    db.refresh(expense)

    # Notify admins about new pending expense
    notify_admins_new_expense(db, expense, current_user, org_id)
    db.commit()

    response = {
        "id": expense.id,
        "amount": expense.amount,
        "vendor": expense.vendor,
        "category": expense.category,
        "description": expense.description,
        "status": expense.status.value.lower(),
        "date": expense.date.isoformat() if expense.date else None,
        "created_at": expense.created_at.isoformat() if expense.created_at else None,
        "auto_approved": False,
        "message": "Expense submitted for manual approval"
    }
    if budget_warnings:
        response["budget_warnings"] = budget_warnings
    return response


@router.get("")
async def list_expenses(
    request: Request,
    status: Optional[str] = None,
    status_filter: Optional[str] = None,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List expenses based on user role

    - Employees: See only their own expenses
    - Managers: See all team expenses
    - Accountants: See all expenses (for audit)
    - Admins/Owners: See all expenses
    """
    org_id = request.headers.get("X-Organization-Id")

    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required"
        )

    # Verify organization access (CRITICAL SECURITY CHECK)
    ensure_org_access(current_user.id, org_id, db)

    # Base query — exclude archived expenses (they have their own admin endpoint)
    query = db.query(Expense).filter(Expense.organization_id == org_id, Expense.is_archived == False)

    # Apply status filter — accept both ?status= and ?status_filter= param names
    effective_status = status or status_filter
    if effective_status:
        try:
            status_enum = ExpenseStatus[effective_status.upper()]
            query = query.filter(Expense.status == status_enum)
        except KeyError:
            pass  # Invalid status value — ignore

    # Apply category filter
    if category:
        from ..models import ExpenseCategory
        try:
            category_enum = ExpenseCategory[category.upper()]
            query = query.filter(Expense.category == category_enum)
        except KeyError:
            pass  # Invalid category — ignore

    # Role-based filtering
    user_org_role = get_user_organization_role(current_user.id, org_id, db)

    # SECURITY FIX (HIGH-4): Only use organization roles for filtering
    # Members see only their own expenses
    if user_org_role in ["employee", None]:
        query = query.filter(Expense.user_id == current_user.id)
    elif user_org_role == "manager":
        # Managers see their own + department expenses
        if current_user.department_id:
            dept_user_ids = [u.id for u in db.query(User.id).filter(
                User.department_id == current_user.department_id
            ).all()]
            query = query.filter(Expense.user_id.in_(dept_user_ids))
        else:
            # No department set — see only own expenses
            query = query.filter(Expense.user_id == current_user.id)
    # owner/admin see all (no filter)

    expenses = query.all()

    # Fetch user details and approval metadata for each expense
    expense_list = []
    for e in expenses:
        # Get expense owner details
        expense_owner = db.query(User).filter(User.id == e.user_id).first()

        # Get approver details if expense was approved/rejected
        approver = None
        if e.approved_by:
            approver = db.query(User).filter(User.id == e.approved_by).first()

        # Resolve display name: prefer full_name, fall back to username, then email
        if expense_owner:
            display_name = expense_owner.full_name or expense_owner.username or expense_owner.email
        else:
            display_name = "Unknown User"

        expense_list.append({
            "id": e.id,
            "amount": e.amount,
            "vendor": e.vendor,
            "category": e.category,
            "description": e.description,
            "status": (e.status.value.lower() if hasattr(e.status, 'value') else str(e.status).lower()),
            "date": e.date.isoformat() if e.date else None,
            "user_id": e.user_id,
            "user_name": display_name,
            "user_email": expense_owner.email if expense_owner else "unknown@example.com",
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "updated_at": e.updated_at.isoformat() if e.updated_at else None,
            "approved_by": e.approved_by,
            "approved_by_name": approver.full_name if approver else None,
            "approved_at": e.approved_at.isoformat() if e.approved_at else None,
            "transaction_id": e.transaction_id,
            "rejection_reason": e.rejection_reason,
            "auto_approved": e.auto_approved,
            "auto_approved_via": e.auto_approved_via,
        })

    # Return expenses as direct list (API contract)
    return expense_list


@router.get("/report")
async def get_expense_report(
    request: Request,
    user_id: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Expense report summary with optional user filter.

    Returns aggregated counts and expense list scoped to the organization.
    """
    org_id = request.headers.get("X-Organization-Id")

    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required",
        )

    ensure_org_access(current_user.id, org_id, db)

    if user_id and user_id != current_user.id:
        user_org_role = get_user_organization_role(current_user.id, org_id, db)
        can_view_others = (
            user_org_role in ["owner", "admin", "manager"]
            or current_user.role
            == UserRole.ADMIN
        )
        if not can_view_others:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view other users' expenses",
            )

        member = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.user_id == user_id,
                OrganizationMember.organization_id == org_id,
                OrganizationMember.is_active == True,
            )
            .first()
        )
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in this organization",
            )

    target_user_id = user_id or current_user.id

    query = (
        db.query(Expense)
        .options(selectinload(Expense.receipts))
        .filter(Expense.organization_id == org_id)
    )
    if target_user_id:
        query = query.filter(Expense.user_id == target_user_id)

    expenses = query.order_by(Expense.created_at.desc()).all()

    total_amount = sum(float(expense.amount) for expense in expenses)
    pending_count = sum(
        1
        for expense in expenses
        if (expense.status.value if hasattr(expense.status, "value") else expense.status)
        == ExpenseStatus.PENDING.value
    )
    approved_count = sum(
        1
        for expense in expenses
        if (expense.status.value if hasattr(expense.status, "value") else expense.status)
        == ExpenseStatus.APPROVED.value
    )
    rejected_count = sum(
        1
        for expense in expenses
        if (expense.status.value if hasattr(expense.status, "value") else expense.status)
        == ExpenseStatus.REJECTED.value
    )

    return {
        "total_expenses": len(expenses),
        "total_amount": total_amount,
        "pending_count": pending_count,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "expenses": [
            {
                "id": expense.id,
                "user_id": expense.user_id,
                "amount": float(expense.amount),
                "vendor": expense.vendor,
                "category": (
                    expense.category.value
                    if hasattr(expense.category, "value")
                    else expense.category
                ),
                "description": expense.description,
                "status": (
                    expense.status.value.lower()
                    if hasattr(expense.status, "value")
                    else str(expense.status).lower()
                ),
                "date": expense.date.isoformat() if expense.date else None,
                "transaction_id": expense.transaction_id,
                "rejection_reason": expense.rejection_reason,
                "created_at": (
                    expense.created_at.isoformat() if expense.created_at else None
                ),
                "approved_at": (
                    expense.approved_at.isoformat() if expense.approved_at else None
                ),
                "receipt_count": len(expense.receipts or []),
                "receipts": [
                    {
                        "id": receipt.id,
                        "filename": receipt.original_filename,
                        "file_size": receipt.file_size,
                        "content_type": receipt.content_type,
                        "uploaded_at": (
                            receipt.uploaded_at.isoformat()
                            if receipt.uploaded_at
                            else None
                        ),
                    }
                    for receipt in (expense.receipts or [])
                ],
            }
            for expense in expenses
        ],
    }


@router.post("/{expense_id}/archive")
async def archive_expense(
    expense_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Archive an expense (employee can archive own completed expenses)"""
    org_id = request.headers.get("X-Organization-Id")
    if not org_id:
        raise HTTPException(status_code=400, detail="Organization context required")

    ensure_org_access(current_user.id, org_id, db)

    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.organization_id == org_id,
        Expense.user_id == current_user.id,
    ).first()

    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    if expense.status == ExpenseStatus.PENDING:
        raise HTTPException(status_code=400, detail="Cannot archive pending expenses")

    if expense.is_archived:
        raise HTTPException(status_code=400, detail="Expense is already archived")

    expense.is_archived = True
    expense.archived_at = datetime.utcnow()
    expense.archived_by = current_user.id
    db.commit()

    return {"success": True, "message": "Expense archived successfully"}


@router.post("/{expense_id}/unarchive")
async def unarchive_expense(
    expense_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Unarchive an expense (employee can unarchive own expenses)"""
    org_id = request.headers.get("X-Organization-Id")
    if not org_id:
        raise HTTPException(status_code=400, detail="Organization context required")

    ensure_org_access(current_user.id, org_id, db)

    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.organization_id == org_id,
        Expense.user_id == current_user.id,
    ).first()

    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    if not expense.is_archived:
        raise HTTPException(status_code=400, detail="Expense is not archived")

    expense.is_archived = False
    expense.archived_at = None
    expense.archived_by = None
    db.commit()

    return {"success": True, "message": "Expense unarchived successfully"}


@router.get("/archived")
async def get_archived_expenses(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get archived expenses for the current user"""
    org_id = request.headers.get("X-Organization-Id")
    if not org_id:
        raise HTTPException(status_code=400, detail="Organization context required")

    ensure_org_access(current_user.id, org_id, db)

    from sqlalchemy.orm import selectinload

    expenses = (
        db.query(Expense)
        .options(selectinload(Expense.receipts))
        .filter(
            Expense.organization_id == org_id,
            Expense.user_id == current_user.id,
            Expense.is_archived == True,
        )
        .order_by(Expense.archived_at.desc())
        .all()
    )

    return {
        "expenses": [
            {
                "id": e.id,
                "user_id": e.user_id,
                "amount": float(e.amount),
                "vendor": e.vendor,
                "category": e.category.value if hasattr(e.category, "value") else e.category,
                "description": e.description,
                "status": e.status.value.lower() if hasattr(e.status, "value") else str(e.status).lower(),
                "date": e.date.isoformat() if e.date else None,
                "transaction_id": e.transaction_id,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "archived_at": e.archived_at.isoformat() if e.archived_at else None,
                "receipt_count": len(e.receipts or []),
            }
            for e in expenses
        ]
    }


@router.get("/my-approval-stats")
async def get_my_approval_stats(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get approval breakdown stats for the current employee"""
    org_id = request.headers.get("X-Organization-Id")
    if not org_id:
        raise HTTPException(status_code=400, detail="Organization context required")

    ensure_org_access(current_user.id, org_id, db)

    from sqlalchemy import func

    # Total expenses
    total = (
        db.query(func.count(Expense.id))
        .filter(Expense.organization_id == org_id, Expense.user_id == current_user.id)
        .scalar() or 0
    )

    # Auto-approved
    auto_approved = (
        db.query(func.count(Expense.id))
        .filter(
            Expense.organization_id == org_id,
            Expense.user_id == current_user.id,
            Expense.auto_approved == True,
        )
        .scalar() or 0
    )

    # Auto-approved by method
    by_mandate = (
        db.query(func.count(Expense.id))
        .filter(
            Expense.organization_id == org_id,
            Expense.user_id == current_user.id,
            Expense.auto_approved == True,
            Expense.auto_approved_via == "intent_mandate",
        )
        .scalar() or 0
    )

    by_policy = (
        db.query(func.count(Expense.id))
        .filter(
            Expense.organization_id == org_id,
            Expense.user_id == current_user.id,
            Expense.auto_approved == True,
            Expense.auto_approved_via == "approval_policy",
        )
        .scalar() or 0
    )

    # Manually reviewed (approved but not auto)
    manually_approved = (
        db.query(func.count(Expense.id))
        .filter(
            Expense.organization_id == org_id,
            Expense.user_id == current_user.id,
            Expense.status == "approved",
            or_(Expense.auto_approved == False, Expense.auto_approved == None),
        )
        .scalar() or 0
    )

    # Pending
    pending = (
        db.query(func.count(Expense.id))
        .filter(
            Expense.organization_id == org_id,
            Expense.user_id == current_user.id,
            Expense.status == "pending",
        )
        .scalar() or 0
    )

    # Total amount auto-approved
    auto_amount = (
        db.query(func.sum(Expense.amount))
        .filter(
            Expense.organization_id == org_id,
            Expense.user_id == current_user.id,
            Expense.auto_approved == True,
        )
        .scalar() or 0
    )

    # Time saved estimate (3 min per auto-approved expense)
    time_saved_minutes = auto_approved * 3

    return {
        "total_expenses": total,
        "auto_approved": auto_approved,
        "auto_approved_via_mandate": by_mandate,
        "auto_approved_via_policy": by_policy,
        "manually_approved": manually_approved,
        "pending": pending,
        "auto_approved_amount": float(auto_amount),
        "time_saved_minutes": time_saved_minutes,
        "auto_rate_percent": round((auto_approved / total * 100), 1) if total > 0 else 0,
    }


@router.post("/request-approval-rule")
async def request_approval_rule(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Employee requests admin to create an auto-approval rule"""
    org_id = request.headers.get("X-Organization-Id")
    if not org_id:
        raise HTTPException(status_code=400, detail="Organization context required")

    ensure_org_access(current_user.id, org_id, db)

    body = await request.json()
    category = body.get("category", "")
    vendor = body.get("vendor", "")
    max_amount = body.get("max_amount", "")
    reason = body.get("reason", "")

    if not reason:
        raise HTTPException(status_code=400, detail="Please provide a reason for your request")

    # Create RuleRequest record
    rule_request = RuleRequest(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        requester_id=current_user.id,
        category=category or None,
        vendor=vendor or None,
        max_amount=str(max_amount) if max_amount else None,
        reason=reason,
        status=RuleRequestStatus.PENDING,
    )
    db.add(rule_request)

    # Find org admins to notify
    admins = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.is_active == True,
            OrganizationMember.role.in_([OrganizationRole.OWNER, OrganizationRole.ADMIN]),
        )
        .all()
    )

    # Build notification message
    details = []
    if category:
        details.append(f"Category: {category}")
    if vendor:
        details.append(f"Vendor: {vendor}")
    if max_amount:
        details.append(f"Max amount: ${max_amount}")
    details_str = ", ".join(details) if details else "General"

    display_name = current_user.full_name or current_user.username or current_user.email
    message = f"{display_name} requests an auto-approval rule.\n{details_str}\nReason: {reason}"

    for admin in admins:
        notification = Notification(
            id=str(uuid.uuid4()),
            user_id=admin.user_id,
            organization_id=org_id,
            notification_type=NotificationType.RULE_REQUEST,
            title="Auto-Approval Rule Request",
            message=message,
        )
        db.add(notification)

    db.commit()

    return {"status": "ok", "message": "Request sent to your admin(s)", "request_id": rule_request.id}


@router.get("/rule-requests")
async def list_rule_requests(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List rule requests. Admins see all org requests, employees see their own."""
    org_id = request.headers.get("X-Organization-Id")
    if not org_id:
        raise HTTPException(status_code=400, detail="Organization context required")

    ensure_org_access(current_user.id, org_id, db)

    user_org_role = get_user_organization_role(current_user.id, org_id, db)
    is_admin = current_user.role == UserRole.ADMIN or user_org_role in ["owner", "admin"]

    query = db.query(RuleRequest).filter(RuleRequest.organization_id == org_id)

    if not is_admin:
        query = query.filter(RuleRequest.requester_id == current_user.id)

    requests_list = query.order_by(RuleRequest.created_at.desc()).limit(50).all()

    return {"requests": [r.to_dict() for r in requests_list]}


@router.post("/rule-requests/{request_id}/approve")
async def approve_rule_request(
    request_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Admin approves a rule request and notifies the employee"""
    org_id = request.headers.get("X-Organization-Id")
    if not org_id:
        raise HTTPException(status_code=400, detail="Organization context required")

    ensure_org_access(current_user.id, org_id, db)

    # Check admin permission
    user_org_role = get_user_organization_role(current_user.id, org_id, db)
    is_admin = current_user.role == UserRole.ADMIN or user_org_role in ["owner", "admin"]
    if not is_admin:
        raise HTTPException(status_code=403, detail="Only admins can approve rule requests")

    rule_req = db.query(RuleRequest).filter(
        RuleRequest.id == request_id,
        RuleRequest.organization_id == org_id,
    ).first()

    if not rule_req:
        raise HTTPException(status_code=404, detail="Rule request not found")

    if rule_req.status != RuleRequestStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Request already {rule_req.status}")

    rule_req.status = RuleRequestStatus.APPROVED
    rule_req.reviewed_by = current_user.id
    rule_req.reviewed_at = datetime.utcnow()

    # Notify employee
    notification = Notification(
        id=str(uuid.uuid4()),
        user_id=rule_req.requester_id,
        organization_id=org_id,
        notification_type=NotificationType.RULE_REQUEST_APPROVED,
        title="Rule Request Approved",
        message=f"Your request for an auto-approval rule has been approved by {current_user.full_name or current_user.email}.",
    )
    db.add(notification)
    db.commit()

    return {
        "status": "ok",
        "message": "Request approved",
        "rule_request": rule_req.to_dict(),
    }


@router.post("/rule-requests/{request_id}/deny")
async def deny_rule_request(
    request_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Admin denies a rule request with a note"""
    org_id = request.headers.get("X-Organization-Id")
    if not org_id:
        raise HTTPException(status_code=400, detail="Organization context required")

    ensure_org_access(current_user.id, org_id, db)

    # Check admin permission
    user_org_role = get_user_organization_role(current_user.id, org_id, db)
    is_admin = current_user.role == UserRole.ADMIN or user_org_role in ["owner", "admin"]
    if not is_admin:
        raise HTTPException(status_code=403, detail="Only admins can deny rule requests")

    rule_req = db.query(RuleRequest).filter(
        RuleRequest.id == request_id,
        RuleRequest.organization_id == org_id,
    ).first()

    if not rule_req:
        raise HTTPException(status_code=404, detail="Rule request not found")

    if rule_req.status != RuleRequestStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Request already {rule_req.status}")

    body = await request.json()
    admin_note = body.get("note", "")

    rule_req.status = RuleRequestStatus.DENIED
    rule_req.reviewed_by = current_user.id
    rule_req.reviewed_at = datetime.utcnow()
    rule_req.admin_note = admin_note or None

    # Notify employee
    deny_msg = f"Your request for an auto-approval rule was denied by {current_user.full_name or current_user.email}."
    if admin_note:
        deny_msg += f"\nReason: {admin_note}"

    notification = Notification(
        id=str(uuid.uuid4()),
        user_id=rule_req.requester_id,
        organization_id=org_id,
        notification_type=NotificationType.RULE_REQUEST_DENIED,
        title="Rule Request Denied",
        message=deny_msg,
    )
    db.add(notification)
    db.commit()

    return {
        "status": "ok",
        "message": "Request denied",
        "rule_request": rule_req.to_dict(),
    }


@router.get("/export")
async def export_expenses(
    request: Request,
    format: str = "pdf",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Export expenses to PDF or CSV

    Permissions: Accountants, admins

    Args:
        format: Export format - 'pdf' or 'csv' (default: pdf)
    """
    from fastapi.responses import StreamingResponse
    from ..services.pdf_generator import PDFExpenseReportGenerator
    import io

    org_id = request.headers.get("X-Organization-Id")

    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required"
        )

    # Verify organization access
    ensure_org_access(current_user.id, org_id, db)

    # Check permission (accountants and admins can export)
    user_org_role = get_user_organization_role(current_user.id, org_id, db)

    can_export = (
        user_org_role in ["owner", "admin"] or
        current_user.role == UserRole.ADMIN
    )

    if not can_export:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to export expenses"
        )

    # Get organization details
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    # Get all expenses for organization
    expenses = db.query(Expense).filter(Expense.organization_id == org_id).all()

    # Generate export file
    generator = PDFExpenseReportGenerator()
    file_bytes = generator.generate_expense_report(
        expenses=expenses,
        organization=organization,
        generated_by=current_user,
        format_type=format.lower()
    )

    # Transition payment mandates to completed for exported approved expenses
    for exp in expenses:
        if exp.payment_mandate_id and exp.status == ExpenseStatus.APPROVED:
            pm = db.query(PaymentMandate).filter(PaymentMandate.id == exp.payment_mandate_id).first()
            if pm and pm.status == "pending":
                pm.status = "completed"
                pm.completed_at = datetime.utcnow()
                db.add(pm)
    db.commit()

    # Determine content type and filename
    if format.lower() == "csv":
        content_type = "text/csv"
        filename = f"expenses_{organization.slug}_{datetime.utcnow().strftime('%Y%m%d')}.csv"
    else:
        content_type = "application/pdf"
        filename = f"expenses_{organization.slug}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"

    # Return file as streaming response
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=content_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/stats")
async def get_expense_stats(
    request: Request,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Aggregate expense statistics for the organization.

    Permissions: All authenticated org members (employees see own stats, managers+ see all)
    """
    from sqlalchemy import func as sqlfunc

    org_id = request.headers.get("X-Organization-Id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required",
        )

    ensure_org_access(current_user.id, org_id, db)

    query = db.query(Expense).filter(Expense.organization_id == org_id)

    user_org_role = get_user_organization_role(current_user.id, org_id, db)
    if user_org_role in ["employee", None]:
        query = query.filter(Expense.user_id == current_user.id)

    if start_date:
        parsed_start = datetime.strptime(start_date, "%Y-%m-%d").date()
        query = query.filter(Expense.date >= parsed_start)
    if end_date:
        parsed_end = datetime.strptime(end_date, "%Y-%m-%d").date()
        query = query.filter(Expense.date <= parsed_end)

    expenses = query.all()

    stats: dict = {"total": len(expenses), "count": len(expenses), "by_status": {}, "total_amount": 0.0, "by_status_amount": {}, "by_category": {}, "by_category_amount": {}}
    for exp in expenses:
        s = exp.status.value.lower() if exp.status else "unknown"
        stats["by_status"][s] = stats["by_status"].get(s, 0) + 1
        amount = float(exp.amount or 0)
        stats["total_amount"] += amount
        stats["by_status_amount"][s] = stats["by_status_amount"].get(s, 0.0) + amount
        cat = exp.category if exp.category else "uncategorized"
        stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1
        stats["by_category_amount"][cat] = stats["by_category_amount"].get(cat, 0.0) + amount

    stats["total_amount"] = round(stats["total_amount"], 2)
    stats["by_status_amount"] = {k: round(v, 2) for k, v in stats["by_status_amount"].items()}
    stats["by_category_amount"] = {k: round(v, 2) for k, v in stats["by_category_amount"].items()}
    return stats


@router.post("/bulk-approve", status_code=status.HTTP_200_OK)
async def bulk_approve_expenses(
    data: dict,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Approve multiple expenses at once.

    Permissions: Managers, admins, owners
    Body: {"expense_ids": ["id1", "id2", ...]}
    Returns 207 Multi-Status with per-expense results.
    """
    from fastapi.responses import JSONResponse as _JSONResponse

    org_id = request.headers.get("X-Organization-Id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required",
        )

    ensure_org_access(current_user.id, org_id, db)

    user_org_role = get_user_organization_role(current_user.id, org_id, db)
    if user_org_role not in ["owner", "admin", "manager"] and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to bulk approve expenses",
        )

    expense_ids = data.get("expense_ids", [])
    if not expense_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="expense_ids must be a non-empty list",
        )

    results = []
    any_failure = False

    for expense_id in expense_ids:
        expense = (
            db.query(Expense)
            .filter(Expense.id == expense_id, Expense.organization_id == org_id)
            .first()
        )
        if not expense:
            results.append({"id": expense_id, "status": "error", "detail": "Not found"})
            any_failure = True
            continue

        if expense.status != ExpenseStatus.PENDING:
            results.append({"id": expense_id, "status": "skipped", "detail": f"Already {expense.status.value.lower()}"})
            continue

        if expense.user_id == current_user.id and current_user.role != UserRole.ADMIN:
            results.append({"id": expense_id, "status": "error", "detail": "Cannot approve own expense"})
            any_failure = True
            continue

        # Enforce manager approval limit
        if current_user.role == UserRole.MANAGER and expense.amount > 5000.00:
            results.append({"id": expense_id, "status": "error", "detail": "Expenses over $5000 require admin approval"})
            any_failure = True
            continue

        # Department check for managers
        if user_org_role == "manager" and current_user.department_id:
            expense_owner = db.query(User).filter(User.id == expense.user_id).first()
            if expense_owner and expense_owner.department_id != current_user.department_id:
                results.append({"id": expense_id, "status": "error", "detail": "Cannot approve expenses outside your department"})
                any_failure = True
                continue

        expense.status = ExpenseStatus.APPROVED
        expense.approved_by = current_user.id
        expense.approved_at = datetime.utcnow()
        results.append({"id": expense_id, "status": "approved"})

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to commit bulk approval: {str(e)}")

    response_status = 207 if any_failure else 200
    return _JSONResponse(
        status_code=response_status,
        content={"results": results, "approved": sum(1 for r in results if r["status"] == "approved")},
    )


@router.get("/{expense_id}")
async def get_expense(
    expense_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get a single expense by ID

    Access control:
    - Employees can only view their own expenses
    - Managers, accountants, admins can view all expenses
    """
    org_id = request.headers.get("X-Organization-Id")

    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required"
        )

    # This function handles all security checks
    expense = ensure_expense_access(expense_id, current_user, org_id, db)

    return {
        "id": expense.id,
        "amount": expense.amount,
        "vendor": expense.vendor,
        "category": expense.category,
        "description": expense.description,
        "status": (expense.status.value.lower() if hasattr(expense.status, 'value') else str(expense.status).lower()),
        "date": expense.date.isoformat() if expense.date else None,
        "user_id": expense.user_id,
        "organization_id": expense.organization_id,
        "created_at": expense.created_at.isoformat() if expense.created_at else None,
        "updated_at": expense.updated_at.isoformat() if expense.updated_at else None,
        "auto_approved": expense.auto_approved,
        "auto_approved_via": expense.auto_approved_via,
        "intent_mandate_id": expense.intent_mandate_id,
        "cart_mandate_id": expense.cart_mandate_id,
        "payment_mandate_id": expense.payment_mandate_id,
    }


@router.put("/{expense_id}")
@router.patch("/{expense_id}")
async def update_expense(
    expense_id: str,
    data: ExpenseUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update an expense (partial updates supported)

    - Employees can update their own PENDING expenses
    - Admins can update any expense
    """
    org_id = request.headers.get("X-Organization-Id")

    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required"
        )

    expense = ensure_expense_access(expense_id, current_user, org_id, db)

    # Check modify permission
    if not can_modify_expense(expense, current_user, org_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot modify this expense"
        )

    # Update only provided fields (partial update)
    update_data = data.dict(exclude_unset=True)

    if "amount" in update_data:
        expense.amount = update_data["amount"]
    if "description" in update_data:
        expense.description = update_data["description"]
    if "vendor" in update_data:
        expense.vendor = update_data["vendor"]
    if "category" in update_data:
        expense.category = update_data["category"]
    if "date" in update_data:
        expense.date = datetime.fromisoformat(update_data["date"])

    expense.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(expense)

    return {
        "id": expense.id,
        "amount": expense.amount,
        "vendor": expense.vendor,
        "category": expense.category,
        "description": expense.description,
        "status": (expense.status.value.lower() if hasattr(expense.status, 'value') else str(expense.status).lower()),
        "date": expense.date.isoformat() if expense.date else None,
        "user_id": expense.user_id,
        "organization_id": expense.organization_id,
        "created_at": expense.created_at.isoformat() if expense.created_at else None,
        "updated_at": expense.updated_at.isoformat() if expense.updated_at else None,
    }


@router.delete("/{expense_id}")
async def delete_expense(
    expense_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Withdraw an expense (soft delete by setting status to WITHDRAWN)

    - Employees can withdraw their own PENDING expenses
    - Admins can withdraw any expense
    - Accountants CANNOT withdraw expenses (audit trail protection)
    """
    org_id = request.headers.get("X-Organization-Id")

    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required"
        )

    expense = ensure_expense_access(expense_id, current_user, org_id, db)

    # DEBUG: Log user role
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"WITHDRAW EXPENSE - User: {current_user.username}, Role: {current_user.role}, RoleType: {type(current_user.role)}")
    logger.info(f"WITHDRAW EXPENSE - Checking if role == UserRole.ADMIN: {current_user.role == UserRole.ADMIN}")

    # Check withdraw permission
    if not can_modify_expense(expense, current_user, org_id, db, action="withdraw"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot withdraw this expense"
        )

    # Soft delete: Set status to WITHDRAWN instead of hard deleting
    expense.status = ExpenseStatus.WITHDRAWN
    expense.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "Expense withdrawn successfully"}


# ============================================================================
# APPROVAL WORKFLOW ENDPOINTS
# ============================================================================

@router.put("/{expense_id}/approve")
async def approve_expense(
    expense_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Approve an expense

    Permissions:
    - Managers can approve team expenses
    - Admins can approve any expense
    - Users CANNOT approve their own expenses
    """
    org_id = request.headers.get("X-Organization-Id")

    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required"
        )

    expense = ensure_expense_access(expense_id, current_user, org_id, db)

    # Check if expense is in a state that can be approved
    if expense.status != ExpenseStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve expense with status {expense.status.value}. Only PENDING expenses can be approved."
        )

    # Prevent self-approval (except for system admins)
    if expense.user_id == current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot approve your own expense"
        )

    # Check approval permission — global admins bypass org-role check
    user_org_role = get_user_organization_role(current_user.id, org_id, db)
    if user_org_role not in ["owner", "admin", "manager"] and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to approve expenses",
        )

    expense_owner = db.query(User).filter(User.id == expense.user_id).first()

    # Determine effective role for approval permission checking
    # Priority: User's system role first, then organization role
    if current_user.role == UserRole.ADMIN:
        effective_role = UserRole.ADMIN
    elif user_org_role == "owner":
        effective_role = UserRole.ADMIN
    elif user_org_role == "admin" and current_user.role == UserRole.MANAGER:
        # Manager with admin org role should still respect manager limits
        effective_role = UserRole.MANAGER
    elif user_org_role == "manager":
        effective_role = UserRole.MANAGER
    else:
        effective_role = current_user.role if current_user.role else UserRole.EMPLOYEE

    can_approve = can_approve_expense(
        user_role=effective_role,
        expense_amount=float(expense.amount),
        expense_user_id=expense.user_id,
        user_id=current_user.id,
        user_department_id=current_user.department_id,
        expense_owner_department_id=(
            expense_owner.department_id if expense_owner else None
        ),
    )

    if not can_approve:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to approve expenses"
        )

    # Update expense status with approval metadata
    expense.status = ExpenseStatus.APPROVED
    expense.approved_by = current_user.id
    expense.approved_at = datetime.utcnow()
    expense.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(expense)

    # Create in-app notification for expense owner
    try:
        if expense_owner:
            notification = Notification(
                id=str(uuid.uuid4()),
                user_id=expense_owner.id,
                organization_id=org_id,
                notification_type=NotificationType.EXPENSE_APPROVED,
                title=f"Expense Approved",
                message=f"Your expense of ${float(expense.amount):.2f} for {expense.vendor or 'Unknown vendor'} has been approved by {current_user.full_name or current_user.username}.",
                expense_id=expense.id,
                is_read=False,
                created_at=datetime.utcnow()
            )
            db.add(notification)
            db.commit()
    except Exception as e:
        # Log error but don't fail the approval
        logger.error(f"Failed to create in-app notification for expense {expense.id}: {str(e)}", exc_info=True)

    # Send approval notification email to expense owner
    try:
        if expense_owner and expense_owner.email:
            expense_data = {
                "id": expense.id,
                "amount": float(expense.amount),
                "vendor": expense.vendor or "Unknown",
                "description": expense.description or "",
                "category": expense.category or "Uncategorized",
                "date": expense.date.strftime("%Y-%m-%d") if expense.date else "N/A",
                "submitted_at": expense.created_at.strftime("%Y-%m-%d %H:%M") if expense.created_at else "N/A"
            }
            await EmailService.send_expense_approved_email(
                to_email=expense_owner.email,
                expense_data=expense_data,
                approver_name=current_user.full_name or current_user.username
            )
    except Exception as e:
        # Log error but don't fail the approval
        logger.error(f"Failed to send approval email for expense {expense.id}: {str(e)}", exc_info=True)

    # NOTE: AP2 mandates are NOT created here for manual approvals.
    # Rationale:
    # - If expense matched an Intent Mandate, it was auto-approved at submission (lines 243-327)
    # - If expense matched an Approval Policy, it was auto-approved without AP2 (free feature)
    # - Manual approval means NO Intent Mandate authorized it
    # - Creating Intent Mandates retroactively defeats AP2's purpose (autonomous approval)
    #
    # AP2 is ONLY used when Intent Mandates enable autonomous agent approval.
    # Manual approvals follow traditional workflow without AP2 overhead.

    return {
        "id": expense.id,
        "status": (expense.status.value.lower() if hasattr(expense.status, 'value') else str(expense.status).lower()),
        "message": f"Expense approved by {current_user.username}",
        "approved_by": current_user.id,
        "approved_at": expense.approved_at.isoformat(),
    }


@router.put("/{expense_id}/reject")
async def reject_expense(
    expense_id: str,
    data: dict,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Reject an expense

    Permissions: Same as approve
    Required: Rejection reason in request body
    """
    org_id = request.headers.get("X-Organization-Id")

    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required"
        )

    expense = ensure_expense_access(expense_id, current_user, org_id, db)

    # Check if expense is in a state that can be rejected
    if expense.status != ExpenseStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject expense with status {expense.status.value}. Only PENDING expenses can be rejected."
        )

    # Prevent self-rejection (except for system admins)
    if expense.user_id == current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot reject your own expense"
        )

    # Check rejection permission
    user_org_role = get_user_organization_role(current_user.id, org_id, db)

    can_reject = (
        user_org_role in ["owner", "admin", "manager"] or
        current_user.role == UserRole.ADMIN
    )

    if not can_reject:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to reject expenses"
        )

    # Get rejection reason
    reason = data.get("reason", "No reason provided")

    # Update expense status with rejection metadata
    expense.status = ExpenseStatus.REJECTED
    expense.rejection_reason = reason
    expense.approved_by = current_user.id  # Track who rejected it
    expense.approved_at = datetime.utcnow()  # Time of rejection
    expense.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(expense)

    # Create in-app notification for expense owner
    try:
        expense_owner = db.query(User).filter(User.id == expense.user_id).first()
        if expense_owner:
            notification = Notification(
                id=str(uuid.uuid4()),
                user_id=expense_owner.id,
                organization_id=org_id,
                notification_type=NotificationType.EXPENSE_REJECTED,
                title=f"Expense Rejected",
                message=f"Your expense of ${float(expense.amount):.2f} for {expense.vendor or 'Unknown vendor'} was rejected by {current_user.full_name or current_user.username}. Reason: {reason}",
                expense_id=expense.id,
                is_read=False,
                created_at=datetime.utcnow()
            )
            db.add(notification)
            db.commit()
    except Exception as e:
        # Log error but don't fail the rejection
        logger.error(f"Failed to create in-app notification for expense {expense.id}: {str(e)}", exc_info=True)

    # Send rejection notification email to expense owner
    try:
        expense_owner = db.query(User).filter(User.id == expense.user_id).first()
        if expense_owner and expense_owner.email:
            expense_data = {
                "id": expense.id,
                "amount": float(expense.amount),
                "vendor": expense.vendor or "Unknown",
                "description": expense.description or "",
                "category": expense.category or "Uncategorized",
                "date": expense.date.strftime("%Y-%m-%d") if expense.date else "N/A",
                "submitted_at": expense.created_at.strftime("%Y-%m-%d %H:%M") if expense.created_at else "N/A"
            }
            await EmailService.send_expense_rejected_email(
                to_email=expense_owner.email,
                expense_data=expense_data,
                rejector_name=current_user.full_name or current_user.username,
                reason=reason
            )
    except Exception as e:
        # Log error but don't fail the rejection
        logger.error(f"Failed to send rejection email for expense {expense.id}: {str(e)}", exc_info=True)

    return {
        "id": expense.id,
        "status": (expense.status.value.lower() if hasattr(expense.status, 'value') else str(expense.status).lower()),
        "message": f"Expense rejected by {current_user.username}",
        "reason": reason,
        "rejected_at": datetime.utcnow().isoformat()
    }


# ============================================================================
# ADDITIONAL WORKFLOW ENDPOINTS
# ============================================================================

@router.put("/{expense_id}/request-receipt")
async def request_receipt(
    expense_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Request receipt from expense submitter

    Permissions: Accountants, managers, admins
    """
    import json as _json
    org_id = request.headers.get("X-Organization-Id")

    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required"
        )

    expense = ensure_expense_access(expense_id, current_user, org_id, db)

    # Check permission (accountants and managers can request receipts)
    user_org_role = get_user_organization_role(current_user.id, org_id, db)

    can_request = (
        user_org_role in ["owner", "admin", "manager"] or
        current_user.role == UserRole.ADMIN
    )

    if not can_request:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to request receipts"
        )

    # Parse optional JSON body — body may be absent or empty
    try:
        body_bytes = await request.body()
        data = _json.loads(body_bytes) if body_bytes.strip() else {}
    except Exception:
        data = {}

    message = data.get("message", "Please upload receipt for this expense")

    # In a real implementation, you'd send a notification to the expense owner
    # For now, we'll just return success

    return {
        "id": expense.id,
        "message": "Receipt request sent to expense owner",
        "requested_by": current_user.username,
        "request_message": message
    }


@router.put("/{expense_id}/flag")
async def flag_expense(
    expense_id: str,
    data: dict,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Flag expense for admin review

    Permissions: Managers can flag expenses that exceed their approval limit
    """
    org_id = request.headers.get("X-Organization-Id")

    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required"
        )

    expense = ensure_expense_access(expense_id, current_user, org_id, db)

    # Check permission
    user_org_role = get_user_organization_role(current_user.id, org_id, db)

    can_flag = (
        user_org_role in ["owner", "admin", "manager"] or
        current_user.role == UserRole.ADMIN
    )

    if not can_flag:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to flag expenses"
        )

    note = data.get("note", "Flagged for admin review")

    # In a real implementation, you might add a "flagged" status or field
    # For now, we'll just return success

    return {
        "id": expense.id,
        "message": "Expense flagged for admin review",
        "flagged_by": current_user.username,
        "note": note
    }


# ============================================================================
# COMMENTS ENDPOINTS
# ============================================================================

@router.post("/{expense_id}/comments", status_code=status.HTTP_201_CREATED)
async def add_expense_comment(
    expense_id: str,
    data: dict,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Add a comment to an expense.

    Permissions: Any org member with access to the expense
    Body: {"comment": "text"}
    """
    org_id = request.headers.get("X-Organization-Id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required",
        )

    expense = ensure_expense_access(expense_id, current_user, org_id, db)

    comment_text = (data.get("comment") or "").strip()
    if not comment_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="comment must not be empty",
        )

    comment = ExpenseComment(
        id=str(uuid.uuid4()),
        expense_id=expense.id,
        user_id=current_user.id,
        comment=comment_text,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    return {
        "id": comment.id,
        "expense_id": comment.expense_id,
        "user_id": comment.user_id,
        "username": current_user.username,
        "comment": comment.comment,
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
    }


@router.get("/{expense_id}/comments")
async def get_expense_comments(
    expense_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List all comments on an expense.

    Permissions: Any org member with access to the expense
    """
    org_id = request.headers.get("X-Organization-Id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required",
        )

    ensure_expense_access(expense_id, current_user, org_id, db)

    comments = (
        db.query(ExpenseComment)
        .filter(ExpenseComment.expense_id == expense_id)
        .order_by(ExpenseComment.created_at.asc())
        .all()
    )

    user_ids = [c.user_id for c in comments]
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    user_map = {u.id: u for u in users}

    result = []
    for c in comments:
        author = user_map.get(c.user_id)
        result.append({
            "id": c.id,
            "expense_id": c.expense_id,
            "user_id": c.user_id,
            "username": author.username if author else None,
            "comment": c.comment,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    return {"comments": result}
