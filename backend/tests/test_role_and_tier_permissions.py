import uuid
from datetime import datetime

import pytest

from src.billing.limit_enforcer import LimitEnforcer, LimitExceededError
from src.models import (
    Organization,
    OrganizationMember,
    OrganizationRole,
    Subscription,
    SubscriptionTier,
    User,
    UserRole,
)
from src.permissions import Permission, get_user_permissions, has_permission


def _create_org_with_owner(db_session, tier: SubscriptionTier) -> str:
    """Helper to create an organization with an owner subscription on a given tier."""
    owner = User(
        id=str(uuid.uuid4()),
        email=f"owner-{tier.value}@example.com",
        username=f"owner_{tier.value}",
        full_name="Owner User",
        hashed_password="irrelevant",
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
        failed_login_attempts=0,
        locked_until=None,
        last_failed_login=None,
    )
    db_session.add(owner)
    db_session.flush()

    subscription = Subscription(
        id=str(uuid.uuid4()),
        user_id=owner.id,
        tier=tier,
        status="active",
        created_at=datetime.utcnow(),
    )
    db_session.add(subscription)

    org = Organization(
        id=str(uuid.uuid4()),
        name=f"{tier.value.title()} Org",
        slug=f"{tier.value}-org-{uuid.uuid4().hex[:6]}",
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db_session.add(org)
    db_session.flush()

    membership = OrganizationMember(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        user_id=owner.id,
        role=OrganizationRole.OWNER,
        is_active=True,
        joined_at=datetime.utcnow(),
    )
    db_session.add(membership)
    db_session.commit()

    return org.id


@pytest.mark.parametrize(
    "role,allowed,denied",
    [
        (
            UserRole.EMPLOYEE,
            {
                Permission.EXPENSE_SUBMIT,
                Permission.EXPENSE_VIEW_OWN,
                Permission.REPORT_VIEW_OWN,
                Permission.AUDIT_VIEW_OWN,
            },
            {
                Permission.EXPENSE_APPROVE_DEPARTMENT,
                Permission.EXPENSE_APPROVE_ALL,
                Permission.REPORT_EXPORT,
            },
        ),
        (
            UserRole.MANAGER,
            {
                Permission.EXPENSE_VIEW_DEPARTMENT,
                Permission.EXPENSE_APPROVE_DEPARTMENT,
                Permission.EXPENSE_BULK_APPROVE,
                Permission.REPORT_VIEW_DEPARTMENT,
            },
            {
                Permission.EXPENSE_APPROVE_ALL,
                Permission.SYSTEM_CONFIGURE,
            },
        ),
        (
            UserRole.ACCOUNTANT,
            {
                Permission.EXPENSE_VIEW_ALL,
                Permission.REPORT_VIEW_ALL,
                Permission.REPORT_EXPORT,
                Permission.AUDIT_VIEW_ALL,
            },
            {
                Permission.EXPENSE_APPROVE_DEPARTMENT,
                Permission.EXPENSE_APPROVE_ALL,
                Permission.USER_CHANGE_ROLE,
            },
        ),
    ],
)
def test_role_permission_matrix(role, allowed, denied):
    """Ensure each role has expected permissions and cannot misuse restricted ones."""
    for perm in allowed:
        assert has_permission(role, perm), f"{role} should have {perm}"
    for perm in denied:
        assert not has_permission(role, perm), f"{role} must NOT have {perm}"


def test_admin_has_all_permissions():
    """Admin role should carry every defined permission."""
    admin_perms = get_user_permissions(UserRole.ADMIN)
    assert set(admin_perms) == set(Permission), "Admin must include every permission"


def test_free_tier_blocks_ai_and_ap2(db_session):
    """Free tier should hard-block AI categorizations and AP2 transactions."""
    org_id = _create_org_with_owner(db_session, SubscriptionTier.FREE)
    enforcer = LimitEnforcer(db_session)

    with pytest.raises(LimitExceededError):
        enforcer.check_ai_categorization_limit(org_id, raise_error=True)
    with pytest.raises(LimitExceededError):
        enforcer.check_ap2_transaction_limit(org_id, raise_error=True)

    ok, msg = enforcer.check_feature_access(org_id, "api_access", raise_error=False)
    assert not ok and "requires" in msg.lower()


def test_paid_tiers_allow_features(db_session):
    """Paid tiers should allow key features while enforcing tier-specific gates."""
    pro_org = _create_org_with_owner(db_session, SubscriptionTier.PROFESSIONAL)
    ent_org = _create_org_with_owner(db_session, SubscriptionTier.ENTERPRISE)
    enforcer = LimitEnforcer(db_session)

    # Professional: AI/AP2 should be available, SSO should be gated
    ok, _ = enforcer.check_ai_categorization_limit(pro_org, raise_error=True)
    assert ok
    ok, _ = enforcer.check_ap2_transaction_limit(pro_org, raise_error=True)
    assert ok
    ok, msg = enforcer.check_feature_access(pro_org, "sso_enabled", raise_error=False)
    assert not ok and "requires" in msg.lower()

    # Enterprise: advanced features should be available
    ok, _ = enforcer.check_feature_access(ent_org, "sso_enabled", raise_error=True)
    assert ok
    ok, _ = enforcer.check_feature_access(ent_org, "api_access", raise_error=True)
    assert ok
