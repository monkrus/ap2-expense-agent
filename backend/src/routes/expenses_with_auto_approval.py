"""
Updated expense submission endpoint with auto-approval integration

This shows the changes needed to integrate auto-approval into the expense submission flow.
Replace the submit_expense function in api.py with this implementation.
"""

from datetime import datetime
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..auth import get_current_active_user
from ..database import get_db
from ..models import Expense, ExpenseStatus, Organization, OrganizationMember, User, UserRole
from ..schemas import ExpenseSubmission
from ..tenant_context import TenantContext
from ..services.approval_policy_service import ApprovalPolicyService
from ..services.audit_service import AuditService
from ..services.notification_service import notification_service


router = APIRouter()


@router.post("/api/v1/expenses", status_code=status.HTTP_201_CREATED)
async def submit_expense_with_auto_approval(
    data: ExpenseSubmission,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Submit an expense with automatic approval evaluation

    Flow:
    1. Create expense with PENDING status
    2. Check approval policies
    3. If matches auto-approval policy → Auto-approve + create AP2 audit trail
    4. If no match → Send to manager for manual approval
    """
    try:
        # Get organization context
        organization_id = TenantContext.get_organization()

        if not organization_id:
            # Check if user belongs to any organizations
            member_count = (
                db.query(OrganizationMember)
                .filter(OrganizationMember.user_id == current_user.id)
                .count()
            )

            if member_count > 0:
                raise HTTPException(
                    status_code=400,
                    detail="Organization context required (X-Organization-Id header missing)",
                )
            else:
                # Create/use default organization for testing
                default_org = (
                    db.query(Organization)
                    .filter(Organization.slug == "default-test-org")
                    .first()
                )

                if not default_org:
                    default_org = Organization(
                        id=str(uuid.uuid4()),
                        name="Default Test Organization",
                        slug="default-test-org",
                        description="Default organization for testing",
                        currency="USD",
                        timezone="UTC",
                        max_members=1000,
                        is_active=True,
                        created_at=datetime.utcnow(),
                    )
                    db.add(default_org)
                    db.commit()
                    db.refresh(default_org)

                organization_id = default_org.id

        # Validate expense amount
        if data.amount <= 0:
            raise HTTPException(
                status_code=400, detail="Expense amount must be positive"
            )

        # Parse expense date
        expense_date = datetime.fromisoformat(data.date) if data.date else datetime.utcnow()

        # Create expense with PENDING status initially
        expense = Expense(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            user_id=current_user.id,
            amount=data.amount,
            vendor=data.vendor,
            category=data.category,
            description=data.description,
            status=ExpenseStatus.PENDING,  # Always start as pending
            date=expense_date,
            ai_analysis="Manual submission - AI analysis not available",
            risk_level="LOW",
            compliance_check=True,
        )

        db.add(expense)
        db.flush()  # Flush to get ID but don't commit yet

        # =====================================================================
        # AUTO-APPROVAL EVALUATION
        # =====================================================================

        policy_service = ApprovalPolicyService(db)
        should_auto_approve, matching_policy, reason = policy_service.evaluate_expense(
            expense, current_user
        )

        if should_auto_approve and matching_policy:
            # AUTO-APPROVE THE EXPENSE
            expense.status = ExpenseStatus.APPROVED
            expense.approved_by_id = current_user.id  # Self-approval via policy
            expense.approved_at = datetime.utcnow()
            expense.auto_approved = True
            expense.approval_policy_id = matching_policy.id

            # Create AP2 audit trail (still required for compliance)
            audit_service = AuditService(db)
            audit_trail = audit_service.create_complete_audit_trail(
                expense=expense,
                approver=current_user,  # Self-approval
                action="auto_approve"
            )

            db.commit()
            db.refresh(expense)

            # Send notification about auto-approval
            try:
                # Notify employee
                notification_service.notify_expense_auto_approved(
                    expense=expense,
                    user=current_user,
                    policy=matching_policy,
                )

                # Optionally notify manager if configured
                if matching_policy.notify_on_auto_approve:
                    managers = (
                        db.query(User)
                        .join(OrganizationMember)
                        .filter(
                            OrganizationMember.organization_id == organization_id,
                            OrganizationMember.is_active == True,
                            User.role.in_([UserRole.MANAGER, UserRole.ADMIN]),
                        )
                        .all()
                    )

                    for manager in managers:
                        notification_service.notify_manager_auto_approval(
                            expense=expense,
                            manager=manager,
                            policy=matching_policy,
                        )

            except Exception as e:
                # Don't fail the whole request if notification fails
                print(f"Failed to send auto-approval notification: {e}")

            return {
                "success": True,
                "expense": {
                    "id": expense.id,
                    "vendor": expense.vendor,
                    "amount": float(expense.amount),
                    "category": expense.category.value,
                    "status": expense.status.value,
                    "auto_approved": True,
                    "approval_policy": {
                        "id": matching_policy.id,
                        "name": matching_policy.name,
                    },
                },
                "message": f"✅ Expense auto-approved by policy: {matching_policy.name}",
                "transaction_id": audit_trail.get("transaction_id"),
            }

        else:
            # MANUAL APPROVAL REQUIRED
            expense.status = ExpenseStatus.PENDING
            expense.auto_approved = False

            db.commit()
            db.refresh(expense)

            # Send notification to managers
            try:
                notification_service.notify_expense_submitted(
                    expense=expense, user=current_user
                )

                # Notify managers/approvers
                managers = (
                    db.query(User)
                    .join(OrganizationMember)
                    .filter(
                        OrganizationMember.organization_id == organization_id,
                        OrganizationMember.is_active == True,
                        User.role.in_([UserRole.MANAGER, UserRole.ADMIN]),
                    )
                    .all()
                )

                for manager in managers:
                    notification_service.notify_expense_pending_approval(
                        expense=expense, manager=manager
                    )

            except Exception as e:
                print(f"Failed to send notification: {e}")

            return {
                "success": True,
                "expense": {
                    "id": expense.id,
                    "vendor": expense.vendor,
                    "amount": float(expense.amount),
                    "category": expense.category.value,
                    "status": expense.status.value,
                    "auto_approved": False,
                },
                "message": f"Expense submitted for approval. Reason: {reason}",
            }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error creating expense: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create expense: {str(e)}")
