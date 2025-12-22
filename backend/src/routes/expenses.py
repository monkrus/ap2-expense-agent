"""
Expense Management Routes with Role-Based Access Control

This module provides comprehensive expense management endpoints with:
- Secure multi-tenant isolation
- Role-based permissions
- Complete expense lifecycle workflows
- Approval chains
- Audit trails
"""

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

    # Validate expense amount
    if data.amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Expense amount must be positive"
        )

    # Parse expense date
    expense_date = (
        datetime.fromisoformat(data.date) if data.date else datetime.utcnow()
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
                "status": expense.status.value,
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

    return {
        "id": expense.id,
        "amount": expense.amount,
        "vendor": expense.vendor,
        "category": expense.category,
        "description": expense.description,
        "status": expense.status.value,
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

    # Apply status filter
    if status_filter:
        query = query.filter(Expense.status == status_filter)

    # Role-based filtering
    user_org_role = get_user_organization_role(current_user.id, org_id, db)

    # SECURITY FIX (HIGH-4): Only use organization roles for filtering
    # Members see only their own expenses
    if user_org_role in ["member", None]:
        query = query.filter(Expense.user_id == current_user.id)

    # All other org roles (manager, admin, owner) see all expenses

    expenses = query.all()

    return [
        {
            "id": e.id,
            "amount": e.amount,
            "vendor": e.vendor,
            "category": e.category,
            "description": e.description,
            "status": e.status.value if hasattr(e.status, 'value') else e.status,
            "date": e.date.isoformat() if e.date else None,
            "user_id": e.user_id,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in expenses
    ]


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
            in [UserRole.ADMIN, UserRole.MANAGER, UserRole.ACCOUNTANT]
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
    format: str = "csv",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Export expenses to CSV

    Permissions: Accountants, admins
    """
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
        current_user.role in [UserRole.ADMIN, UserRole.ACCOUNTANT]
    )

    if not can_export:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to export expenses"
        )

    # Get all expenses for organization
    expenses = db.query(Expense).filter(Expense.organization_id == org_id).all()

    # In a real implementation, generate actual CSV file
    # For now, return metadata

    return {
        "message": "Export ready",
        "format": format,
        "expense_count": len(expenses),
        "exported_by": current_user.username,
        "exported_at": datetime.utcnow().isoformat()
    }


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
        "status": expense.status.value if hasattr(expense.status, 'value') else expense.status,
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
        "status": expense.status.value if hasattr(expense.status, 'value') else expense.status,
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
    Delete an expense

    - Employees can delete their own PENDING expenses
    - Admins can delete any expense
    - Accountants CANNOT delete expenses (audit trail protection)
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
    logger.info(f"DELETE EXPENSE - User: {current_user.username}, Role: {current_user.role}, RoleType: {type(current_user.role)}")
    logger.info(f"DELETE EXPENSE - Checking if role == UserRole.ACCOUNTANT: {current_user.role == UserRole.ACCOUNTANT}")

    # CRITICAL: Accountants cannot delete expenses (audit trail protection)
    # Check both enum and string value to handle all cases
    user_role_value = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    if current_user.role == UserRole.ACCOUNTANT or user_role_value == "accountant":
        logger.info("DELETE EXPENSE - BLOCKING ACCOUNTANT DELETE")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accountants cannot delete expenses to maintain audit trail integrity"
        )

    # Check delete permission
    if not can_modify_expense(expense, current_user, org_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot delete this expense"
        )

    db.delete(expense)
    db.commit()

    return {"message": "Expense deleted successfully"}


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

    # Prevent self-approval
    if expense.user_id == current_user.id:
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

    if current_user.role == UserRole.ADMIN:
        effective_role = UserRole.ADMIN
    elif current_user.role == UserRole.ACCOUNTANT:
        effective_role = UserRole.ACCOUNTANT
    elif user_org_role == "owner":
        effective_role = UserRole.ADMIN
    else:
        effective_role = UserRole.MANAGER

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
            EmailService.send_expense_approved_email(
                to_email=expense_owner.email,
                expense_data=expense_data,
                approver_name=current_user.full_name or current_user.username
            )
    except Exception as e:
        # Log error but don't fail the approval
        print(f"Failed to send approval email: {str(e)}")

    return {
        "id": expense.id,
        "status": expense.status.value if hasattr(expense.status, 'value') else expense.status,
        "message": f"Expense approved by {current_user.username}",
        "approved_by": current_user.id,
        "approved_at": expense.approved_at.isoformat()
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

    # Prevent self-rejection (same logic as approval)
    if expense.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot reject your own expense"
        )

    # Check rejection permission
    user_org_role = get_user_organization_role(current_user.id, org_id, db)

    can_reject = (
        user_org_role in ["owner", "admin", "manager"] or
        current_user.role in [UserRole.ADMIN, UserRole.MANAGER]
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
            EmailService.send_expense_rejected_email(
                to_email=expense_owner.email,
                expense_data=expense_data,
                rejector_name=current_user.full_name or current_user.username,
                reason=reason
            )
    except Exception as e:
        # Log error but don't fail the rejection
        print(f"Failed to send rejection email: {str(e)}")

    return {
        "id": expense.id,
        "status": expense.status.value if hasattr(expense.status, 'value') else expense.status,
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
        current_user.role in [UserRole.ADMIN, UserRole.MANAGER, UserRole.ACCOUNTANT]
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
        current_user.role in [UserRole.ADMIN, UserRole.MANAGER]
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
