"""
API endpoints for managing approval policies
Owner/Admin can configure automated expense approval rules
"""

import uuid
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import (
    ApprovalPolicy,
    OrganizationMember,
    OrganizationRole,
    User,
    UserRole,
)
from ..services.approval_policy_service import ApprovalPolicyService

router = APIRouter(prefix="/api/v1/approval-policies", tags=["approval-policies"])


# ============================================================================
# Pydantic Models
# ============================================================================


class ApprovalPolicyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    priority: int = Field(default=0, ge=0, le=1000)
    auto_approve: bool = Field(default=True)
    require_receipt: bool = Field(default=True)
    notify_on_auto_approve: bool = Field(default=True)

    # Conditions (flexible JSON)
    conditions: Optional[Dict] = Field(default_factory=dict)

    # Limits
    max_amount_per_expense: Optional[float] = Field(None, gt=0)
    daily_limit_per_user: Optional[float] = Field(None, gt=0)
    monthly_limit_per_user: Optional[float] = Field(None, gt=0)
    yearly_limit_per_user: Optional[float] = Field(None, gt=0)


class ApprovalPolicyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    priority: Optional[int] = Field(None, ge=0, le=1000)
    is_active: Optional[bool] = None
    auto_approve: Optional[bool] = None
    require_receipt: Optional[bool] = None
    notify_on_auto_approve: Optional[bool] = None
    conditions: Optional[Dict] = None
    max_amount_per_expense: Optional[float] = Field(None, gt=0)
    daily_limit_per_user: Optional[float] = Field(None, gt=0)
    monthly_limit_per_user: Optional[float] = Field(None, gt=0)
    yearly_limit_per_user: Optional[float] = Field(None, gt=0)


class ApprovalPolicyResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    description: Optional[str]
    priority: int
    is_active: bool
    auto_approve: bool
    require_receipt: bool
    notify_on_auto_approve: bool
    conditions: Dict
    limits: Dict
    created_at: str
    updated_at: str
    created_by: Optional[str]
    updated_by: Optional[str]

    class Config:
        from_attributes = True


class PolicyTestRequest(BaseModel):
    """Test if an expense would match a policy"""

    amount: float = Field(..., gt=0)
    category: Optional[str] = None  # Empty = test against all categories
    vendor: str = ""
    has_receipt: bool = True
    # Test which limit type to check: "daily", "monthly", "yearly", or None for per-expense only
    test_limit_type: Optional[str] = None


class PolicyTestResponse(BaseModel):
    would_auto_approve: bool
    matching_policy: Optional[Dict]
    reason: str
    remaining_limits: Optional[Dict]


# ============================================================================
# Helper Functions
# ============================================================================


def get_user_organization(db: Session, user_id: str) -> Optional[str]:
    """Get organization ID for user"""
    member = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.user_id == user_id,
            OrganizationMember.is_active == True,
        )
        .first()
    )
    return member.organization_id if member else None


def check_admin_or_owner(user: User, organization_id: str, db: Session) -> bool:
    """Check if user is admin or organization owner"""
    # System admin
    if user.role == UserRole.ADMIN:
        return True

    # Organization owner/admin
    member = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.user_id == user.id,
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.is_active == True,
        )
        .first()
    )

    if member and member.role in [OrganizationRole.OWNER, OrganizationRole.ADMIN]:
        return True

    return False


# ============================================================================
# CRUD Endpoints
# ============================================================================


@router.post(
    "", response_model=ApprovalPolicyResponse, status_code=status.HTTP_201_CREATED
)
def create_approval_policy(
    data: ApprovalPolicyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new approval policy (Owner/Admin only)

    Example policy configurations:

    1. Auto-approve small expenses:
    {
      "name": "Small expenses auto-approval",
      "max_amount_per_expense": 50.00,
      "daily_limit_per_user": 200.00,
      "monthly_limit_per_user": 1000.00,
      "require_receipt": true,
      "auto_approve": true
    }

    2. Category-specific approval:
    {
      "name": "Office supplies auto-approval",
      "max_amount_per_expense": 200.00,
      "conditions": {
        "categories": ["Office Supplies"],
        "vendors": ["Staples", "Office Depot"]
      },
      "auto_approve": true
    }

    3. Trusted employee approval:
    {
      "name": "Senior staff meals",
      "max_amount_per_expense": 100.00,
      "conditions": {
        "categories": ["Meals"],
        "user_ids": ["user_123", "user_456"]
      },
      "daily_limit_per_user": 100.00,
      "auto_approve": true
    }
    """
    org_id = get_user_organization(db, current_user.id)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a member of any organization",
        )

    # Check permissions
    if not check_admin_or_owner(current_user, org_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners and admins can create approval policies",
        )

    # Validate conditions
    if data.conditions:
        # Validate category list
        if "categories" in data.conditions:
            from ..models import ExpenseCategory

            valid_categories = [cat.value for cat in ExpenseCategory]
            for cat in data.conditions["categories"]:
                if cat not in valid_categories:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid category: {cat}. Must be one of: {valid_categories}",
                    )

    # Create policy
    policy = ApprovalPolicy(
        id=f"policy_{uuid.uuid4().hex[:16]}",
        organization_id=org_id,
        name=data.name,
        description=data.description,
        priority=data.priority,
        auto_approve=data.auto_approve,
        require_receipt=data.require_receipt,
        notify_on_auto_approve=data.notify_on_auto_approve,
        conditions=data.conditions,
        max_amount_per_expense=data.max_amount_per_expense,
        daily_limit_per_user=data.daily_limit_per_user,
        monthly_limit_per_user=data.monthly_limit_per_user,
        yearly_limit_per_user=data.yearly_limit_per_user,
        created_by=current_user.id,
    )

    db.add(policy)
    db.commit()
    db.refresh(policy)

    return ApprovalPolicyResponse(**policy.to_dict())


@router.get("", response_model=List[ApprovalPolicyResponse])
def list_approval_policies(
    active_only: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all approval policies for organization"""
    org_id = get_user_organization(db, current_user.id)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a member of any organization",
        )

    query = db.query(ApprovalPolicy).filter(ApprovalPolicy.organization_id == org_id)

    if active_only:
        query = query.filter(ApprovalPolicy.is_active == True)

    query = query.order_by(
        ApprovalPolicy.priority.desc(), ApprovalPolicy.created_at.desc()
    )

    policies = query.all()

    return [ApprovalPolicyResponse(**p.to_dict()) for p in policies]


@router.get("/{policy_id}", response_model=ApprovalPolicyResponse)
def get_approval_policy(
    policy_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific approval policy"""
    org_id = get_user_organization(db, current_user.id)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a member of any organization",
        )

    policy = (
        db.query(ApprovalPolicy)
        .filter(
            ApprovalPolicy.id == policy_id,
            ApprovalPolicy.organization_id == org_id,
        )
        .first()
    )

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval policy not found",
        )

    return ApprovalPolicyResponse(**policy.to_dict())


@router.patch("/{policy_id}", response_model=ApprovalPolicyResponse)
def update_approval_policy(
    policy_id: str,
    data: ApprovalPolicyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an approval policy (Owner/Admin only)"""
    org_id = get_user_organization(db, current_user.id)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a member of any organization",
        )

    # Check permissions
    if not check_admin_or_owner(current_user, org_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners and admins can update approval policies",
        )

    policy = (
        db.query(ApprovalPolicy)
        .filter(
            ApprovalPolicy.id == policy_id,
            ApprovalPolicy.organization_id == org_id,
        )
        .first()
    )

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval policy not found",
        )

    # Update fields
    if data.name is not None:
        policy.name = data.name
    if data.description is not None:
        policy.description = data.description
    if data.priority is not None:
        policy.priority = data.priority
    if data.is_active is not None:
        policy.is_active = data.is_active
    if data.auto_approve is not None:
        policy.auto_approve = data.auto_approve
    if data.require_receipt is not None:
        policy.require_receipt = data.require_receipt
    if data.notify_on_auto_approve is not None:
        policy.notify_on_auto_approve = data.notify_on_auto_approve
    if data.conditions is not None:
        policy.conditions = data.conditions
    if data.max_amount_per_expense is not None:
        policy.max_amount_per_expense = data.max_amount_per_expense
    if data.daily_limit_per_user is not None:
        policy.daily_limit_per_user = data.daily_limit_per_user
    if data.monthly_limit_per_user is not None:
        policy.monthly_limit_per_user = data.monthly_limit_per_user
    if data.yearly_limit_per_user is not None:
        policy.yearly_limit_per_user = data.yearly_limit_per_user

    policy.updated_by = current_user.id

    db.commit()
    db.refresh(policy)

    return ApprovalPolicyResponse(**policy.to_dict())


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_approval_policy(
    policy_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an approval policy (Owner/Admin only)"""
    org_id = get_user_organization(db, current_user.id)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a member of any organization",
        )

    # Check permissions
    if not check_admin_or_owner(current_user, org_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners and admins can delete approval policies",
        )

    policy = (
        db.query(ApprovalPolicy)
        .filter(
            ApprovalPolicy.id == policy_id,
            ApprovalPolicy.organization_id == org_id,
        )
        .first()
    )

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval policy not found",
        )

    db.delete(policy)
    db.commit()


# ============================================================================
# Testing & Analytics Endpoints
# ============================================================================


@router.post("/test", response_model=PolicyTestResponse)
def test_all_policies(
    test_data: PolicyTestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Test if a hypothetical expense would be auto-approved by ANY policy

    Tests against all active policies in priority order (highest first)
    """
    import logging

    logger = logging.getLogger(__name__)
    logger.info(
        f"[TEST] Request: amount={test_data.amount}, test_limit_type='{test_data.test_limit_type}'"
    )

    org_id = get_user_organization(db, current_user.id)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a member of any organization",
        )

    # Get all active policies for this organization, ordered by priority
    policies = (
        db.query(ApprovalPolicy)
        .filter(
            ApprovalPolicy.organization_id == org_id,
            ApprovalPolicy.is_active == True,
        )
        .order_by(ApprovalPolicy.priority.desc())
        .all()
    )

    if not policies:
        return PolicyTestResponse(
            would_auto_approve=False,
            matching_policy=None,
            reason="No active approval rules configured",
            remaining_limits=None,
        )

    # Create mock expense for testing
    from decimal import Decimal

    from ..models import Expense, ExpenseCategory

    # Use a default category if none specified (for "All Categories" test)
    # The category value doesn't matter when testing against policies with no category restrictions
    test_category = (
        test_data.category.strip()
        if test_data.category and test_data.category.strip()
        else "MEALS"
    )

    mock_expense = Expense(
        id="test_expense",
        organization_id=org_id,
        user_id=current_user.id,
        vendor=test_data.vendor,
        amount=Decimal(str(test_data.amount)),
        category=ExpenseCategory(test_category),
        status="pending",
    )
    # Set receipts as an attribute (for testing purposes without DB persistence)
    mock_expense._has_receipt = test_data.has_receipt

    # Test against all policies in priority order
    policy_service = ApprovalPolicyService(db)
    best_partial_match = None  # Track policies that match except for amount

    for policy in policies:
        matches, reason = policy_service._matches_policy(
            mock_expense, current_user, policy
        )
        test_amount = Decimal(str(test_data.amount))

        # When a specific limit type is selected, test that specific limit
        logger.info(
            f"[TEST] test_limit_type='{test_data.test_limit_type}', type={type(test_data.test_limit_type)}"
        )
        if test_data.test_limit_type and test_data.test_limit_type not in [
            "",
            "None",
            None,
        ]:
            logger.info(
                f"[TEST] Entering limit type check for '{test_data.test_limit_type}'"
            )
            # Check if the requested limit is configured on this policy
            limit_not_configured = None
            limit_value = None
            limit_label = test_data.test_limit_type

            if test_data.test_limit_type == "daily":
                limit_value = policy.daily_limit_per_user
                if not limit_value:
                    limit_not_configured = "daily"
            elif test_data.test_limit_type == "monthly":
                limit_value = policy.monthly_limit_per_user
                if not limit_value:
                    limit_not_configured = "monthly"
            elif test_data.test_limit_type == "yearly":
                limit_value = policy.yearly_limit_per_user
                if not limit_value:
                    limit_not_configured = "yearly"

            # If this policy doesn't have the requested limit, try next policy
            if limit_not_configured:
                logger.info(
                    f"[TEST] Policy '{policy.name}' has no {limit_not_configured} limit, trying next policy"
                )
                continue

            # Note: We skip the per-expense max check here because user is specifically testing
            # a spending limit (daily/monthly/yearly), not the per-expense limit

            # Check if this single expense would exceed the selected limit
            # (Assumes no prior spending - tests if expense fits within the limit)
            limit_decimal = Decimal(str(limit_value))
            logger.info(
                f"[TEST] Comparing: test_amount={test_amount} vs limit={limit_decimal}, max_per_expense={policy.max_amount_per_expense}"
            )
            if test_amount > limit_decimal:
                return PolicyTestResponse(
                    would_auto_approve=False,
                    matching_policy=policy.to_dict(),
                    reason=f"You exceeded your {limit_label} spending limit (${limit_value})",
                    remaining_limits=None,
                )
            else:
                # Amount is within the limit - would auto-approve
                return PolicyTestResponse(
                    would_auto_approve=True,
                    matching_policy=policy.to_dict(),
                    reason=f"Matched rule: {policy.name} (within {limit_label} limit of ${limit_value})",
                    remaining_limits=None,
                )

        # Standard test (no specific limit type selected - "Per-expense only")
        if matches:
            logger.info(f"[TEST] Matched policy: {policy.name}")
            logger.info(
                f"[TEST] Policy limits: daily={policy.daily_limit_per_user}, monthly={policy.monthly_limit_per_user}, yearly={policy.yearly_limit_per_user}"
            )

            within_limits, limit_reason = policy_service._check_limits(
                mock_expense,
                current_user,
                policy,
                simulated_daily_spent=None,
                simulated_monthly_spent=None,
                simulated_yearly_spent=None,
            )

            if within_limits:
                # Found a matching policy that approves
                remaining_limits = policy_service.get_user_remaining_limits(
                    current_user.id, org_id, policy.id
                )

                # Convert Decimal to float for JSON serialization
                remaining_limits_json = (
                    {
                        k: float(v) if isinstance(v, Decimal) else v
                        for k, v in remaining_limits.items()
                    }
                    if remaining_limits
                    else None
                )

                return PolicyTestResponse(
                    would_auto_approve=True,
                    matching_policy=policy.to_dict(),
                    reason=f"Matched rule: {policy.name}",
                    remaining_limits=remaining_limits_json,
                )
            else:
                # Matched conditions but exceeded limits - still show which rule matched
                return PolicyTestResponse(
                    would_auto_approve=False,
                    matching_policy=policy.to_dict(),
                    reason=limit_reason,  # Already formatted as "You exceeded..."
                    remaining_limits=None,
                )
        elif "exceeded the maximum" in reason.lower() and not best_partial_match:
            # This policy matched category/vendor/etc but amount was too high
            best_partial_match = (policy, reason)

    # If we found a partial match (matched everything except amount), report it
    if best_partial_match:
        policy, reason = best_partial_match
        return PolicyTestResponse(
            would_auto_approve=False,
            matching_policy=policy.to_dict(),
            reason=reason,  # Already formatted as "You exceeded..."
            remaining_limits=None,
        )

    # If a specific limit type was requested but no policy had it configured
    if test_data.test_limit_type and test_data.test_limit_type not in [
        "",
        "None",
        None,
    ]:
        limit_label = test_data.test_limit_type
        return PolicyTestResponse(
            would_auto_approve=False,
            matching_policy=None,
            reason=f"No rules have a {limit_label} limit configured. Add a {limit_label} limit to one of your rules to test this.",
            remaining_limits=None,
        )

    # No policies matched at all
    return PolicyTestResponse(
        would_auto_approve=False,
        matching_policy=None,
        reason="No rules match this expense (amount, category, or other conditions)",
        remaining_limits=None,
    )


@router.post("/{policy_id}/test", response_model=PolicyTestResponse)
def test_policy(
    policy_id: str,
    test_data: PolicyTestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Test if a hypothetical expense would match this specific policy

    Useful for policy configuration and debugging
    """
    org_id = get_user_organization(db, current_user.id)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a member of any organization",
        )

    policy = (
        db.query(ApprovalPolicy)
        .filter(
            ApprovalPolicy.id == policy_id,
            ApprovalPolicy.organization_id == org_id,
        )
        .first()
    )

    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval policy not found",
        )

    # Create mock expense for testing
    from decimal import Decimal

    from ..models import Expense, ExpenseCategory

    # Use a default category if none specified (for "All Categories" test)
    # The category value doesn't matter when testing against policies with no category restrictions
    test_category = (
        test_data.category.strip()
        if test_data.category and test_data.category.strip()
        else "MEALS"
    )

    mock_expense = Expense(
        id="test_expense",
        organization_id=org_id,
        user_id=current_user.id,
        vendor=test_data.vendor,
        amount=Decimal(str(test_data.amount)),
        category=ExpenseCategory(test_category),
        status="pending",
    )
    # Set receipts as an attribute (for testing purposes without DB persistence)
    mock_expense._has_receipt = test_data.has_receipt

    # Evaluate
    policy_service = ApprovalPolicyService(db)
    matches, reason = policy_service._matches_policy(mock_expense, current_user, policy)

    if matches:
        within_limits, limit_reason = policy_service._check_limits(
            mock_expense, current_user, policy
        )
        would_approve = within_limits
        final_reason = limit_reason if not within_limits else "Would auto-approve"
    else:
        would_approve = False
        final_reason = reason

    # Get remaining limits
    remaining_limits = policy_service.get_user_remaining_limits(
        current_user.id, org_id, policy_id
    )

    # Convert Decimal to float for JSON serialization
    remaining_limits_json = {
        k: float(v) if isinstance(v, Decimal) else v
        for k, v in remaining_limits.items()
    }

    return PolicyTestResponse(
        would_auto_approve=would_approve,
        matching_policy=policy.to_dict() if would_approve else None,
        reason=final_reason,
        remaining_limits=remaining_limits_json if remaining_limits else None,
    )


@router.get("/analytics/statistics")
def get_policy_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get analytics on auto-approval usage

    Returns statistics on how many expenses are being auto-approved,
    which policies are most used, etc.
    """
    org_id = get_user_organization(db, current_user.id)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a member of any organization",
        )

    # Check permissions
    if not check_admin_or_owner(current_user, org_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners and admins can view analytics",
        )

    from datetime import datetime, timedelta

    from sqlalchemy import func

    from ..models import Expense

    # Last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    # Total expenses in last 30 days
    total_expenses = (
        db.query(func.count(Expense.id))
        .filter(
            Expense.organization_id == org_id,
            Expense.created_at >= thirty_days_ago,
        )
        .scalar()
        or 0
    )

    # Auto-approved expenses
    auto_approved = (
        db.query(func.count(Expense.id))
        .filter(
            Expense.organization_id == org_id,
            Expense.auto_approved == True,
            Expense.approved_at >= thirty_days_ago,
        )
        .scalar()
        or 0
    )

    # Manual approved
    manual_approved = (
        db.query(func.count(Expense.id))
        .filter(
            Expense.organization_id == org_id,
            Expense.auto_approved == False,
            Expense.status == "approved",
            Expense.approved_at >= thirty_days_ago,
        )
        .scalar()
        or 0
    )

    # Auto-approval rate
    approval_rate = (auto_approved / total_expenses * 100) if total_expenses > 0 else 0

    # Total amount auto-approved
    auto_approved_amount = (
        db.query(func.sum(Expense.amount))
        .filter(
            Expense.organization_id == org_id,
            Expense.auto_approved == True,
            Expense.approved_at >= thirty_days_ago,
        )
        .scalar()
        or 0
    )

    # By policy statistics
    policy_stats = (
        db.query(
            Expense.approval_policy_id,
            func.count(Expense.id).label("count"),
            func.sum(Expense.amount).label("total_amount"),
        )
        .filter(
            Expense.organization_id == org_id,
            Expense.auto_approved == True,
            Expense.approved_at >= thirty_days_ago,
        )
        .group_by(Expense.approval_policy_id)
        .all()
    )

    policy_breakdown = []
    for policy_id, count, total_amount in policy_stats:
        if policy_id:
            policy = (
                db.query(ApprovalPolicy).filter(ApprovalPolicy.id == policy_id).first()
            )
            policy_breakdown.append(
                {
                    "policy_id": policy_id,
                    "policy_name": policy.name if policy else "Unknown",
                    "expense_count": count,
                    "total_amount": float(total_amount) if total_amount else 0,
                }
            )

    return {
        "period": "last_30_days",
        "total_expenses": total_expenses,
        "auto_approved_count": auto_approved,
        "manual_approved_count": manual_approved,
        "auto_approval_rate_percent": round(approval_rate, 2),
        "auto_approved_total_amount": float(auto_approved_amount),
        "policy_breakdown": policy_breakdown,
        "time_saved_estimate_hours": auto_approved * 0.05,  # Assume 3 min/expense saved
    }
