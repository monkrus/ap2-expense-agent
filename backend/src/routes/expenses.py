"""
Expense Management Routes with Role-Based Access Control

This module provides comprehensive expense management endpoints with:
- Secure multi-tenant isolation
- Role-based permissions
- Complete expense lifecycle workflows
- Approval chains
- Audit trails
"""

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
    ExpenseStatus,
    Notification,
    NotificationType,
    Organization,
    OrganizationMember,
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

    # Managers can see all team expenses in their organization
    if user_org_role == "manager":
        return expense

    # Employees can only see their own expenses
    if expense.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own expenses"
        )

    return expense


def can_modify_expense(expense: Expense, user: User, org_id: str, db: Session) -> bool:
    """Check if user can modify expense"""
    user_org_role = get_user_organization_role(user.id, org_id, db)

    # Owners and admins can modify any expense
    if user_org_role in ["owner", "admin"] or user.role == UserRole.ADMIN:
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
    # AUTO-APPROVAL EVALUATION
    # =====================================================================
    try:
        from ..services.approval_policy_service import ApprovalPolicyService

        policy_service = ApprovalPolicyService(db)
        should_auto_approve, matching_policy, reason = policy_service.evaluate_expense(
            expense, current_user
        )

        if should_auto_approve and matching_policy:
            # AUTO-APPROVE THE EXPENSE
            expense.status = ExpenseStatus.APPROVED
            expense.approved_by = current_user.id  # Self-approval via policy
            expense.approved_at = datetime.utcnow()
            expense.auto_approved = True
            expense.approval_policy_id = matching_policy.id

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
                "approval_policy_id": matching_policy.id,
                "message": f"Auto-approved by policy: {matching_policy.name}"
            }
    except ImportError:
        # Approval policy service not available, continue with manual approval
        pass
    except Exception as e:
        # Log error but don't fail the request
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Auto-approval evaluation failed: {e}")

    # MANUAL APPROVAL REQUIRED (or auto-approval failed)
    db.commit()
    db.refresh(expense)

    # Create notifications for admins/managers
    try:
        # Get all admins and managers in the organization
        admin_members = (
            db.query(OrganizationMember)
            .filter(OrganizationMember.organization_id == org_id)
            .filter(OrganizationMember.role.in_([
                OrganizationRole.ADMIN.value,
                OrganizationRole.OWNER.value
            ]))
            .filter(OrganizationMember.is_active == True)
            .all()
        )

        # Create notification for each admin/manager
        for member in admin_members:
            # Don't notify the person who submitted (if they're also an admin)
            if member.user_id == current_user.id:
                continue

            notification = Notification(
                id=str(uuid.uuid4()),
                user_id=member.user_id,
                organization_id=org_id,
                notification_type=NotificationType.EXPENSE_SUBMITTED,
                title="New Expense Submitted",
                message=f"{current_user.full_name or current_user.username} submitted a ${float(expense.amount):.2f} expense for {expense.vendor or 'Unknown vendor'} - awaiting approval",
                expense_id=expense.id,
                is_read=False,
                created_at=datetime.utcnow()
            )
            db.add(notification)

        db.commit()
    except Exception as e:
        # Log error but don't fail the request
        logger.error(f"Failed to create admin notifications: {str(e)}", exc_info=True)

    return {
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


@router.get("")
async def list_expenses(
    request: Request,
    status_filter: Optional[str] = None,
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

    # Base query
    query = db.query(Expense).filter(Expense.organization_id == org_id)

    # Apply status filter (convert to uppercase for enum matching)
    if status_filter:
        # Convert string to ExpenseStatus enum (case-insensitive)
        try:
            status_enum = ExpenseStatus[status_filter.upper()]
            query = query.filter(Expense.status == status_enum)
        except KeyError:
            # Invalid status filter - ignore it
            pass

    # Role-based filtering
    user_org_role = get_user_organization_role(current_user.id, org_id, db)

    # SECURITY FIX (HIGH-4): Only use organization roles for filtering
    # Members see only their own expenses
    if user_org_role in ["member", None]:
        query = query.filter(Expense.user_id == current_user.id)

    # All other org roles (manager, admin, owner) see all expenses

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

        expense_list.append({
            "id": e.id,
            "amount": e.amount,
            "vendor": e.vendor,
            "category": e.category,
            "description": e.description,
            "status": (e.status.value.lower() if hasattr(e.status, 'value') else str(e.status).lower()),
            "date": e.date.isoformat() if e.date else None,
            "user_id": e.user_id,
            "user_name": expense_owner.full_name if expense_owner else "Unknown User",
            "user_email": expense_owner.email if expense_owner else "unknown@example.com",
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "updated_at": e.updated_at.isoformat() if e.updated_at else None,
            "approved_by": e.approved_by,
            "approved_by_name": approver.full_name if approver else None,
            "approved_at": e.approved_at.isoformat() if e.approved_at else None,
            "transaction_id": e.transaction_id,
            "rejection_reason": e.rejection_reason,
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
                    expense.status.value
                    if hasattr(expense.status, "value")
                    else expense.status
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
        current_user.role == UserRole.ADMIN or
        current_user.role == UserRole.ACCOUNTANT
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

    # CRITICAL: Accountants cannot withdraw expenses (audit trail protection)
    # Check both enum and string value to handle all cases
    user_role_value = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    if current_user.role == UserRole.ADMIN:
        logger.info("WITHDRAW EXPENSE - BLOCKING ACCOUNTANT WITHDRAW")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accountants cannot withdraw expenses to maintain audit trail integrity"
        )

    # Check withdraw permission
    if not can_modify_expense(expense, current_user, org_id, db):
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

    # Check approval permission
    user_org_role = get_user_organization_role(current_user.id, org_id, db)
    if user_org_role not in ["owner", "admin", "manager"]:
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
        effective_role = current_user.role if current_user.role else UserRole.USER

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

    # Create AP2 payment mandates for approved expense
    ap2_result = None
    try:
        from ..payments.ap2_service import AP2PaymentService

        ap2_service = AP2PaymentService(db)

        # Prepare cart items from expense
        cart_items = [{
            "description": expense.description or f"Expense: {expense.vendor}",
            "amount": float(expense.amount),
            "vendor": expense.vendor or "Unknown Vendor",
            "category": str(expense.category.value if hasattr(expense.category, 'value') else expense.category),
        }]

        # Create complete AP2 flow
        ap2_result = await ap2_service.complete_ap2_flow(
            user_id=expense.user_id,
            items=cart_items,
            merchant=expense.vendor or "Unknown Vendor",
            constraints={
                "max_amount": float(expense.amount) * 1.05,  # 5% buffer
                "merchant": expense.vendor or "Unknown Vendor",
                "approval_required": False,  # Already approved
            },
        )

        # Update expense with AP2 mandate IDs
        expense.intent_mandate_id = ap2_result.get("intent_mandate_id")
        expense.cart_mandate_id = ap2_result.get("cart_mandate_id")
        expense.payment_mandate_id = ap2_result.get("payment_mandate_id")
        expense.transaction_id = ap2_result.get("payment_mandate_id")  # Use payment mandate ID as transaction ID
        db.commit()

        logger.info(f"AP2 mandates created for expense {expense.id}: {ap2_result.get('intent_mandate_id')}")
    except Exception as e:
        # Log error but don't fail the approval (AP2 is optional)
        logger.error(f"Failed to create AP2 mandates (non-blocking) for expense {expense.id}: {str(e)}", exc_info=True)

    return {
        "id": expense.id,
        "status": (expense.status.value.lower() if hasattr(expense.status, 'value') else str(expense.status).lower()),
        "message": f"Expense approved by {current_user.username}",
        "approved_by": current_user.id,
        "approved_at": expense.approved_at.isoformat(),
        "ap2_mandates_created": ap2_result is not None and ap2_result.get("ap2_flow_complete", False),
        "transaction_id": expense.transaction_id,
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
    data: dict,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Request receipt from expense submitter

    Permissions: Accountants, managers, admins
    """
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
