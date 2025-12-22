"""
TIER-FREE: Free Tier Hard Limit Enforcement Tests (CRITICAL)

Tests that FREE tier users are HARD BLOCKED when they exceed limits.
Revenue protection - prevents free tier abuse.

Priority: 🔴 CRITICAL
"""

import pytest
from fastapi import status

from src.models import SubscriptionTier
from tests.factories import (
    create_free_tier_user_with_org,
    create_organization_with_owner,
    create_pending_expense,
    create_tier_limit_scenario,
    create_user,
)


@pytest.mark.critical
@pytest.mark.billing
class TestFreeTierHardLimits:
    """Test FREE tier hard limit enforcement"""

    # ========================================================================
    # TIER-FREE-003: 21st expense blocked (monthly limit)
    # ========================================================================

    def test_TIER_FREE_003_21st_expense_blocked(
        self, client, db_session
    ):
        """
        Test ID: TIER-FREE-003
        Priority: 🔴 CRITICAL

        FREE tier: 21st expense blocked (limit: 20/month).

        Limit Enforcement: limit_enforcer.py:192-233
        """
        # Setup: FREE tier user with 20 expenses this month
        user, org, subscription = create_free_tier_user_with_org(
            db_session,
            expenses_count=20  # At limit
        )

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": "TestPass123!"}
        )
        token = login_response.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": org.id
        }

        # Try to create 21st expense
        expense_data = {
            "amount": 50.0,
            "description": "21st expense (should be blocked)",
            "category": "MEALS",
            "vendor": "Test Vendor",
        }

        response = client.post(
            "/api/v1/expenses",
            json=expense_data,
            headers=headers
        )

        # Should fail with 402 Payment Required
        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
        response_data = response.json()
        assert "detail" in response_data
        detail = response_data["detail"]

        # Verify error message mentions upgrade
        if isinstance(detail, dict):
            assert detail.get("error") == "limit_exceeded" or "Upgrade" in str(detail)
        else:
            assert "Upgrade" in detail or "limit" in detail.lower()

    def test_TIER_FREE_002_20th_expense_allowed(
        self, client, db_session
    ):
        """
        Test ID: TIER-FREE-002
        Priority: 🔴 CRITICAL

        FREE tier: 20th expense allowed (at limit, but not over).
        """
        # Setup: FREE tier user with 19 expenses this month
        user, org, subscription = create_free_tier_user_with_org(
            db_session,
            expenses_count=19  # One away from limit
        )

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": "TestPass123!"}
        )
        token = login_response.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": org.id
        }

        # Create 20th expense (last one allowed)
        expense_data = {
            "amount": 50.0,
            "description": "20th expense (last one allowed)",
            "category": "MEALS",
            "vendor": "Test Vendor",
        }

        response = client.post(
            "/api/v1/expenses",
            json=expense_data,
            headers=headers
        )

        # Should succeed
        assert response.status_code == status.HTTP_201_CREATED

    # ========================================================================
    # TIER-FREE-004: 2nd user blocked (user limit)
    # ========================================================================

    def test_TIER_FREE_004_2nd_user_blocked(
        self, client, db_session
    ):
        """
        Test ID: TIER-FREE-004
        Priority: 🔴 CRITICAL

        FREE tier: Cannot invite 2nd user (limit: 1 user).

        Limit Enforcement: limit_enforcer.py:155-191
        """
        # Setup: FREE tier organization with 1 user (owner)
        user, org, subscription = create_free_tier_user_with_org(db_session)

        # Login as owner
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": "TestPass123!"}
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Try to invite 2nd user
        invitation_data = {
            "email": "seconduser@test.com",
            "role": "member"
        }

        response = client.post(
            f"/api/v1/organizations/{org.id}/invitations",
            json=invitation_data,
            headers=headers
        )

        # Should fail with 402 Payment Required
        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
        response_data = response.json()
        assert "detail" in response_data
        detail = response_data["detail"]

        # Verify error message mentions user limit
        if isinstance(detail, dict):
            assert detail.get("error") == "limit_exceeded" or detail.get("feature") == "Users"
        else:
            assert "user" in detail.lower() or "limit" in detail.lower()

    # ========================================================================
    # TIER-FREE-005: 2nd organization blocked (org limit)
    # ========================================================================

    def test_TIER_FREE_005_2nd_organization_blocked(
        self, client, db_session
    ):
        """
        Test ID: TIER-FREE-005
        Priority: 🔴 CRITICAL

        FREE tier: Cannot create 2nd organization (limit: 1 org).

        Limit Enforcement: organizations.py:226-297
        """
        # Setup: FREE tier user with 1 organization already
        user, org, subscription = create_free_tier_user_with_org(db_session)

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": "TestPass123!"}
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Try to create 2nd organization
        org_data = {
            "name": "Second Organization",
            "slug": "second-org-unique-12345"
        }

        response = client.post(
            "/api/v1/organizations",
            json=org_data,
            headers=headers
        )

        # Should fail with 402 Payment Required
        assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
        response_data = response.json()
        assert "detail" in response_data
        detail = response_data["detail"]

        # Verify error message mentions organization limit
        if isinstance(detail, dict):
            assert detail.get("error") == "organization_limit_reached"
            assert detail.get("upgrade_required") == True
        else:
            assert "organization" in detail.lower() and "limit" in detail.lower()

    # ========================================================================
    # TIER-FREE-006: AI categorization blocked
    # ========================================================================

    def test_TIER_FREE_006_ai_categorization_blocked(
        self, db_session
    ):
        """
        Test ID: TIER-FREE-006
        Priority: 🔴 CRITICAL

        FREE tier: AI categorization blocked (limit: 0).

        Limit Enforcement: limit_enforcer.py:235-280
        """
        from src.billing.limit_enforcer import LimitEnforcer, LimitExceededError

        # Setup: FREE tier organization
        user, org, subscription = create_free_tier_user_with_org(db_session)

        # Try to use AI categorization
        enforcer = LimitEnforcer(db_session)

        with pytest.raises(LimitExceededError) as exc_info:
            enforcer.check_ai_categorization_limit(org.id, count=1, raise_error=True)

        # Verify error details
        error = exc_info.value
        assert error.feature == "AI Categorization"
        assert error.limit == 0
        assert "Upgrade to Starter" in error.upgrade_message

    # ========================================================================
    # TIER-FREE-007: AP2 transaction blocked
    # ========================================================================

    def test_TIER_FREE_007_ap2_transaction_blocked(
        self, db_session
    ):
        """
        Test ID: TIER-FREE-007
        Priority: 🔴 CRITICAL

        FREE tier: AP2 transactions blocked (limit: 0).

        Limit Enforcement: limit_enforcer.py:318-363
        """
        from src.billing.limit_enforcer import LimitEnforcer, LimitExceededError

        # Setup: FREE tier organization
        user, org, subscription = create_free_tier_user_with_org(db_session)

        # Try to use AP2 transaction
        enforcer = LimitEnforcer(db_session)

        with pytest.raises(LimitExceededError) as exc_info:
            enforcer.check_ap2_transaction_limit(org.id, count=1, raise_error=True)

        # Verify error details
        error = exc_info.value
        assert error.feature == "AP2 Transactions"
        assert error.limit == 0
        assert "Upgrade" in error.upgrade_message

    # ========================================================================
    # TIER-FREE-008: OCR limit (6th receipt blocked)
    # ========================================================================

    def test_TIER_FREE_008_6th_ocr_receipt_blocked(
        self, db_session
    ):
        """
        Test ID: TIER-FREE-008
        Priority: 🔴 CRITICAL

        FREE tier: 6th OCR receipt blocked (limit: 5/month).

        Limit Enforcement: limit_enforcer.py:281-317
        """
        from src.billing.limit_enforcer import LimitEnforcer, LimitExceededError
        from src.models import UsageRecord

        # Setup: FREE tier organization with 5 OCR scans this month
        user, org, subscription = create_free_tier_user_with_org(db_session)

        # Create 5 usage records for OCR (at limit)
        from datetime import datetime
        for i in range(5):
            usage = UsageRecord(
                id=f"usage_{i}",
                subscription_id=subscription.id,
                usage_type="ocr_scan",
                quantity=1,
                billable=False,
                created_at=datetime.utcnow()
            )
            db_session.add(usage)
        db_session.commit()

        # Try to use 6th OCR scan
        enforcer = LimitEnforcer(db_session)

        with pytest.raises(LimitExceededError) as exc_info:
            enforcer.check_ocr_limit(org.id, count=1, raise_error=True)

        # Verify error details
        error = exc_info.value
        assert error.feature == "OCR Scans"
        assert error.limit == 5
        assert error.current == 5

    # ========================================================================
    # TIER-FREE-009: Daily expense limit (11th today)
    # ========================================================================

    def test_TIER_FREE_009_daily_expense_limit_11th_today(
        self, db_session
    ):
        """
        Test ID: TIER-FREE-009
        Priority: 🟠 HIGH

        FREE tier: Daily limit of 10 expenses (anti-abuse).

        Limit Enforcement: limit_enforcer.py:419-501
        """
        from src.billing.limit_enforcer import LimitEnforcer, LimitExceededError
        from datetime import datetime, timedelta

        # Setup: FREE tier organization with 10 expenses today
        user, org, subscription = create_free_tier_user_with_org(db_session)

        # Create 10 expenses today (at daily limit)
        from tests.factories import create_pending_expense
        for i in range(10):
            create_pending_expense(
                db_session,
                user,
                org,
                amount=10.0 + i,
                created_at=datetime.utcnow() - timedelta(hours=i)
            )
        db_session.commit()

        # Try to create 11th expense today
        enforcer = LimitEnforcer(db_session)

        with pytest.raises(LimitExceededError) as exc_info:
            enforcer.check_daily_rate_limit(org.id, "expense", raise_error=True)

        # Verify error details
        error = exc_info.value
        assert "Daily" in error.feature
        assert error.limit == 10
        assert error.current == 10

    # ========================================================================
    # TIER-FREE-010: Recreate deleted org (slug reuse)
    # ========================================================================

    def test_TIER_FREE_010_recreate_deleted_org_slug_reuse(
        self, client, db_session
    ):
        """
        Test ID: TIER-FREE-010
        Priority: 🟠 HIGH

        FREE tier: Can recreate organization with same slug after deletion.

        Regression Test: organizations.py:144-161 (soft delete cleanup)
        """
        # Setup: FREE tier user
        user, org, subscription = create_free_tier_user_with_org(db_session)
        original_slug = org.slug

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": "TestPass123!"}
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Delete organization
        response = client.delete(
            f"/api/v1/organizations/{org.id}",
            headers=headers
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Create new organization with same slug
        new_org_data = {
            "name": "New Organization",
            "slug": original_slug  # Reuse slug
        }

        response = client.post(
            "/api/v1/organizations",
            json=new_org_data,
            headers=headers
        )

        # Should succeed (slug is available after soft delete)
        assert response.status_code == status.HTTP_201_CREATED
        new_org = response.json()
        assert new_org["slug"] == original_slug


@pytest.mark.critical
@pytest.mark.billing
class TestStarterTierSoftLimits:
    """Test STARTER tier soft limit enforcement (overages allowed with fees)"""

    def test_TIER_STR_002_51st_expense_with_overage_fee(
        self, client, db_session
    ):
        """
        Test ID: TIER-STR-002
        Priority: 🟠 HIGH

        STARTER tier: 51st expense allowed with overage fee.

        Unlike FREE tier (hard block), STARTER allows overage with billing.
        """
        # Setup: STARTER tier user with 50 expenses this month (at limit)
        scenario = create_tier_limit_scenario(
            db_session,
            SubscriptionTier.STARTER,
            expenses_at_limit=True  # Creates 50 expenses
        )
        user = scenario['user']
        org = scenario['org']

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": "TestPass123!"}
        )
        token = login_response.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": org.id
        }

        # Create 51st expense (overage)
        expense_data = {
            "amount": 50.0,
            "description": "51st expense (overage)",
            "category": "MEALS",
            "vendor": "Test Vendor",
        }

        response = client.post(
            "/api/v1/expenses",
            json=expense_data,
            headers=headers
        )

        # Should succeed (soft limit = overage allowed)
        assert response.status_code == status.HTTP_201_CREATED

        # TODO: Verify UsageRecord created with billable=True and fee charged


@pytest.mark.critical
@pytest.mark.billing
class TestProfessionalTierUnlimited:
    """Test PROFESSIONAL tier unlimited resources"""

    def test_TIER_PRO_001_unlimited_expenses(
        self, db_session
    ):
        """
        Test ID: TIER-PRO-001
        Priority: 🟡 MEDIUM

        PROFESSIONAL tier: Unlimited expenses per month.
        """
        from src.billing.limit_enforcer import LimitEnforcer

        # Setup: PROFESSIONAL tier organization
        scenario = create_tier_limit_scenario(
            db_session,
            SubscriptionTier.PROFESSIONAL,
            expenses_at_limit=False
        )
        org = scenario['org']

        # Check expense limit
        enforcer = LimitEnforcer(db_session)
        can_add, message = enforcer.check_expense_limit(org.id, raise_error=False)

        # Should be unlimited
        assert can_add == True
        assert "Unlimited" in message
