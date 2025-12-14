"""
Regression tests for role permissions, tier limits, and approval flows.
"""

from types import SimpleNamespace
from uuid import uuid4

from src.billing.tier_limits import get_tier_limits
from src.models import ExpenseCategory, SubscriptionTier, UserRole
from src.models_approval import ApprovalPolicy
from src.permissions import Permission, has_permission
from src.services.approval_policy_service import ApprovalPolicyService


def test_role_permissions_matrix():
    """Verify each role has the expected approval/view capabilities."""
    # Employees cannot approve or view all expenses
    assert not has_permission(UserRole.EMPLOYEE, Permission.EXPENSE_APPROVE_ALL)
    assert not has_permission(UserRole.EMPLOYEE, Permission.EXPENSE_VIEW_ALL)

    # Managers can approve/deny within their department but not globally
    assert has_permission(UserRole.MANAGER, Permission.EXPENSE_APPROVE_DEPARTMENT)
    assert not has_permission(UserRole.MANAGER, Permission.EXPENSE_APPROVE_ALL)

    # Accountants get read-only full visibility
    assert has_permission(UserRole.ACCOUNTANT, Permission.EXPENSE_VIEW_ALL)
    assert not has_permission(UserRole.ACCOUNTANT, Permission.EXPENSE_APPROVE_ALL)

    # Admins are superusers
    assert has_permission(UserRole.ADMIN, Permission.EXPENSE_APPROVE_ALL)
    assert has_permission(UserRole.ADMIN, Permission.BILLING_MANAGE)


def test_tier_limits():
    """Validate per-tier limits that gate feature access."""
    free = get_tier_limits(SubscriptionTier.FREE)
    starter = get_tier_limits(SubscriptionTier.STARTER)
    pro = get_tier_limits(SubscriptionTier.PROFESSIONAL)
    enterprise = get_tier_limits(SubscriptionTier.ENTERPRISE)

    assert free.max_users == 1 and free.max_expenses_per_month == 20
    assert starter.max_users == 5 and starter.max_expenses_per_month == 50
    assert pro.max_users == 25 and pro.max_expenses_per_month is None
    assert enterprise.max_users == 100 and enterprise.max_expenses_per_month is None


def test_auto_approval_policy_allows_small_expense(db_session):
    """Auto-approval policies approve in-policy expenses and leave others pending."""
    org_id = str(uuid4())

    policy = ApprovalPolicy(
        id=str(uuid4()),
        organization_id=org_id,
        name="Auto-approve under $100",
        priority=10,
        is_active=True,
        auto_approve=True,
        require_receipt=False,
        notify_on_auto_approve=True,
        conditions={},
        max_amount_per_expense=100.00,
    )
    db_session.add(policy)
    db_session.commit()

    service = ApprovalPolicyService(db_session)
    user = SimpleNamespace(id=str(uuid4()), role=UserRole.EMPLOYEE)

    # Within limit -> auto-approve
    expense_ok = SimpleNamespace(
        id=str(uuid4()),
        organization_id=org_id,
        amount=50.0,
        category=ExpenseCategory.OFFICE_SUPPLIES,
        vendor="Staples",
        receipts=[],
        user_id=user.id,
    )
    should_auto, matched_policy, reason = service.evaluate_expense(expense_ok, user)
    assert should_auto is True
    assert matched_policy.id == policy.id
    assert "Auto-approve" in reason or "policy" in reason

    # Above limit -> manual review
    expense_manual = SimpleNamespace(
        id=str(uuid4()),
        organization_id=org_id,
        amount=150.0,
        category=ExpenseCategory.OFFICE_SUPPLIES,
        vendor="Staples",
        receipts=[],
        user_id=user.id,
    )
    should_auto, matched_policy, reason = service.evaluate_expense(
        expense_manual, user
    )
    assert should_auto is False
    assert matched_policy is None
    assert "No matching auto-approval policy" in reason
