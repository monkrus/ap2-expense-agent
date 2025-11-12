"""
Tests for Subscription Service
Critical billing module - targets 80%+ coverage
"""

import pytest
from datetime import datetime, timedelta
from freezegun import freeze_time

from src.billing.subscription_service import SubscriptionService
from src.models import Subscription, SubscriptionTier, User


@pytest.fixture
def subscription_service(db_session):
    """Create subscription service instance"""
    return SubscriptionService(db_session)


@pytest.fixture
def test_subscription_user(db_session, sample_user):
    """Create a user for subscription tests"""
    return sample_user(email="subtest@example.com")


class TestSubscriptionService:
    """Test subscription management"""

    def test_create_subscription_with_trial(
        self, subscription_service, test_subscription_user
    ):
        """Test creating subscription with trial period"""
        subscription = subscription_service.create_subscription(
            user_id=test_subscription_user.id,
            tier=SubscriptionTier.STARTER,
            trial_days=14
        )

        assert subscription is not None
        assert subscription.user_id == test_subscription_user.id
        assert subscription.tier == SubscriptionTier.STARTER
        assert subscription.status == "trialing"
        assert subscription.trial_end is not None
        assert subscription.max_users == 5  # Starter tier limit
        assert subscription.max_expenses_per_month == 100

    def test_create_subscription_without_trial(
        self, subscription_service, test_subscription_user
    ):
        """Test creating subscription without trial"""
        subscription = subscription_service.create_subscription(
            user_id=test_subscription_user.id,
            tier=SubscriptionTier.PROFESSIONAL,
            trial_days=0
        )

        assert subscription.status == "active"
        assert subscription.trial_end is None

    def test_create_subscription_with_stripe_info(
        self, subscription_service, test_subscription_user
    ):
        """Test creating subscription with Stripe integration"""
        subscription = subscription_service.create_subscription(
            user_id=test_subscription_user.id,
            tier=SubscriptionTier.BUSINESS,
            stripe_customer_id="cus_test_123",
            stripe_subscription_id="sub_test_456"
        )

        assert subscription.stripe_customer_id == "cus_test_123"
        assert subscription.stripe_subscription_id == "sub_test_456"

    def test_get_active_subscription_exists(
        self, subscription_service, test_subscription_user
    ):
        """Test getting active subscription when it exists"""
        created_sub = subscription_service.create_subscription(
            user_id=test_subscription_user.id,
            tier=SubscriptionTier.STARTER
        )

        retrieved_sub = subscription_service.get_active_subscription(
            test_subscription_user.id
        )

        assert retrieved_sub is not None
        assert retrieved_sub.id == created_sub.id
        assert retrieved_sub.status in ["active", "trialing"]

    def test_get_active_subscription_not_exists(
        self, subscription_service, test_subscription_user
    ):
        """Test getting active subscription when none exists"""
        result = subscription_service.get_active_subscription(
            test_subscription_user.id
        )

        assert result is None

    def test_upgrade_subscription_tier(
        self, subscription_service, test_subscription_user
    ):
        """Test upgrading subscription to higher tier"""
        # Create starter subscription
        subscription = subscription_service.create_subscription(
            user_id=test_subscription_user.id,
            tier=SubscriptionTier.STARTER
        )

        # Upgrade to professional
        upgraded = subscription_service.upgrade_subscription(
            subscription_id=subscription.id,
            new_tier=SubscriptionTier.PROFESSIONAL
        )

        assert upgraded is not None
        assert upgraded.tier == SubscriptionTier.PROFESSIONAL
        assert upgraded.max_users == 15  # Professional tier limit
        assert upgraded.max_expenses_per_month == 500

    def test_upgrade_subscription_not_found(
        self, subscription_service
    ):
        """Test upgrading non-existent subscription"""
        with pytest.raises(ValueError, match="not found"):
            subscription_service.upgrade_subscription(
                subscription_id="invalid_id",
                new_tier=SubscriptionTier.PROFESSIONAL
            )

    def test_cancel_subscription_immediate(
        self, subscription_service, test_subscription_user
    ):
        """Test canceling subscription immediately"""
        subscription = subscription_service.create_subscription(
            user_id=test_subscription_user.id,
            tier=SubscriptionTier.STARTER
        )

        canceled = subscription_service.cancel_subscription(
            subscription_id=subscription.id,
            immediate=True
        )

        assert canceled is not None
        assert canceled.status == "canceled"
        assert canceled.canceled_at is not None

    def test_cancel_subscription_at_period_end(
        self, subscription_service, test_subscription_user
    ):
        """Test canceling subscription at period end"""
        subscription = subscription_service.create_subscription(
            user_id=test_subscription_user.id,
            tier=SubscriptionTier.STARTER
        )

        canceled = subscription_service.cancel_subscription(
            subscription_id=subscription.id,
            immediate=False
        )

        assert canceled is not None
        assert canceled.status == "active"  # Stays active until period end
        assert canceled.canceled_at is not None

    def test_cancel_subscription_not_found(
        self, subscription_service
    ):
        """Test canceling non-existent subscription"""
        with pytest.raises(ValueError, match="not found"):
            subscription_service.cancel_subscription(
                subscription_id="invalid_id"
            )

    def test_reactivate_subscription(
        self, subscription_service, test_subscription_user
    ):
        """Test reactivating canceled subscription"""
        # Create and cancel subscription
        subscription = subscription_service.create_subscription(
            user_id=test_subscription_user.id,
            tier=SubscriptionTier.STARTER
        )
        subscription_service.cancel_subscription(
            subscription_id=subscription.id,
            immediate=True
        )

        # Reactivate
        reactivated = subscription_service.reactivate_subscription(
            subscription_id=subscription.id
        )

        assert reactivated is not None
        assert reactivated.status == "active"
        assert reactivated.canceled_at is None

    def test_reactivate_subscription_not_found(
        self, subscription_service
    ):
        """Test reactivating non-existent subscription"""
        with pytest.raises(ValueError, match="not found"):
            subscription_service.reactivate_subscription(
                subscription_id="invalid_id"
            )

    @freeze_time("2025-01-01")
    def test_subscription_period_dates(
        self, subscription_service, test_subscription_user
    ):
        """Test subscription period dates are set correctly"""
        subscription = subscription_service.create_subscription(
            user_id=test_subscription_user.id,
            tier=SubscriptionTier.STARTER,
            trial_days=14
        )

        # Check period dates
        assert subscription.current_period_start.date() == datetime(2025, 1, 1).date()
        assert subscription.current_period_end.date() == datetime(2025, 1, 31).date()

        # Check trial end
        expected_trial_end = datetime(2025, 1, 15).date()
        assert subscription.trial_end.date() == expected_trial_end

    def test_tier_limits_applied_correctly(
        self, subscription_service, test_subscription_user, db_session, sample_user
    ):
        """Test that tier limits are correctly applied"""
        # Test each tier
        tiers_and_limits = [
            (SubscriptionTier.STARTER, 5, 100, 50, 25),
            (SubscriptionTier.PROFESSIONAL, 15, 500, 200, 100),
            (SubscriptionTier.BUSINESS, 50, 2000, 1000, 500),
            (SubscriptionTier.ENTERPRISE, 999999, 999999, 999999, 999999),
        ]

        for tier, max_users, max_expenses, max_ai, max_ap2 in tiers_and_limits:
            user = sample_user(email=f"test_{tier.value}@example.com")
            subscription = subscription_service.create_subscription(
                user_id=user.id,
                tier=tier
            )

            assert subscription.max_users == max_users
            assert subscription.max_expenses_per_month == max_expenses
            assert subscription.max_ai_categorizations == max_ai
            assert subscription.max_ap2_transactions == max_ap2

    def test_multiple_subscriptions_only_one_active(
        self, subscription_service, test_subscription_user, db_session
    ):
        """Test that only one subscription can be active at a time"""
        # Create first subscription
        sub1 = subscription_service.create_subscription(
            user_id=test_subscription_user.id,
            tier=SubscriptionTier.STARTER
        )

        # Cancel first and create second
        subscription_service.cancel_subscription(
            subscription_id=sub1.id,
            immediate=True
        )

        sub2 = subscription_service.create_subscription(
            user_id=test_subscription_user.id,
            tier=SubscriptionTier.PROFESSIONAL
        )

        # Get active subscription
        active = subscription_service.get_active_subscription(
            test_subscription_user.id
        )

        assert active.id == sub2.id
        assert active.tier == SubscriptionTier.PROFESSIONAL

    def test_check_subscription_status_exists(
        self, subscription_service, test_subscription_user
    ):
        """Test checking subscription status when it exists"""
        subscription = subscription_service.create_subscription(
            user_id=test_subscription_user.id,
            tier=SubscriptionTier.STARTER,
            trial_days=14
        )

        status = subscription_service.check_subscription_status(
            test_subscription_user.id
        )

        assert status["has_subscription"] is True
        assert status["tier"] == "STARTER"
        assert status["tier_name"] == "Starter"
        assert status["status"] == "trialing"
        assert status["limits"]["max_users"] == 5
        assert status["limits"]["max_expenses_per_month"] == 100
        assert status["trial_end"] is not None

    def test_check_subscription_status_not_exists(
        self, subscription_service, test_subscription_user
    ):
        """Test checking subscription status when none exists"""
        status = subscription_service.check_subscription_status(
            test_subscription_user.id
        )

        assert status["has_subscription"] is False
        assert status["tier"] is None
        assert status["status"] == "none"
        assert status["limits"] is None

    def test_update_billing_period(
        self, subscription_service, test_subscription_user
    ):
        """Test updating subscription billing period"""
        subscription = subscription_service.create_subscription(
            user_id=test_subscription_user.id,
            tier=SubscriptionTier.STARTER
        )

        new_start = datetime(2025, 2, 1)
        new_end = datetime(2025, 3, 1)

        updated = subscription_service.update_billing_period(
            subscription_id=subscription.id,
            period_start=new_start,
            period_end=new_end
        )

        assert updated.current_period_start == new_start
        assert updated.current_period_end == new_end

    def test_update_billing_period_not_found(
        self, subscription_service
    ):
        """Test updating billing period for non-existent subscription"""
        with pytest.raises(ValueError, match="not found"):
            subscription_service.update_billing_period(
                subscription_id="invalid_id",
                period_start=datetime.utcnow(),
                period_end=datetime.utcnow() + timedelta(days=30)
            )

    def test_trial_expiration_status_change(
        self, subscription_service, test_subscription_user, db_session
    ):
        """Test that trial status changes after expiration"""
        with freeze_time("2025-01-01"):
            subscription = subscription_service.create_subscription(
                user_id=test_subscription_user.id,
                tier=SubscriptionTier.STARTER,
                trial_days=14
            )

        # Move time forward past trial end and update billing period
        with freeze_time("2025-01-16"):
            updated = subscription_service.update_billing_period(
                subscription_id=subscription.id,
                period_start=subscription.current_period_start,
                period_end=subscription.current_period_end
            )

            assert updated.status == "active"  # Trial expired, now active
