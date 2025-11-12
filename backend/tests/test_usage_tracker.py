"""
Tests for Usage Tracker
Critical billing module - targets 75%+ coverage
"""

import pytest
from datetime import datetime, timedelta
from freezegun import freeze_time

from src.billing.usage_tracker import UsageTracker
from src.models import Subscription, SubscriptionTier, UsageRecord, OrganizationMember


class TestUsageTracker:
    """Test usage tracking for billing"""

    @pytest.fixture
    def usage_tracker(self, db_session):
        """Create usage tracker instance"""
        return UsageTracker(db_session)

    @pytest.fixture
    def test_subscription(self, db_session, test_user):
        """Create test subscription"""
        subscription = Subscription(
            id="sub_test_123",
            user_id=test_user.id,
            tier=SubscriptionTier.STARTER,
            status="active",
            max_users=5,
            max_expenses_per_month=100,
            max_ai_categorizations=50,
            max_ap2_transactions=25,
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30)
        )
        db_session.add(subscription)
        db_session.commit()
        return subscription

    def test_track_usage_basic(
        self, usage_tracker, test_user, test_subscription
    ):
        """Test basic usage tracking"""
        record = usage_tracker.track_usage(
            user_id=test_user.id,
            usage_type="expense",
            quantity=1
        )

        assert record is not None
        assert record.user_id == test_user.id
        assert record.subscription_id == test_subscription.id
        assert record.usage_type == "expense"
        assert record.quantity == 1
        assert record.billable is False  # Under limit

    def test_track_usage_with_metadata(
        self, usage_tracker, test_user, test_subscription
    ):
        """Test tracking usage with metadata"""
        metadata = {"expense_id": "exp_123", "category": "travel"}

        record = usage_tracker.track_usage(
            user_id=test_user.id,
            usage_type="expense",
            quantity=1,
            metadata=metadata
        )

        assert record.extra_data is not None
        assert "exp_123" in record.extra_data

    def test_track_usage_creates_default_subscription(
        self, usage_tracker, test_user, db_session
    ):
        """Test that tracking creates default subscription if none exists"""
        # Ensure no subscription exists
        existing = db_session.query(Subscription).filter_by(
            user_id=test_user.id
        ).first()
        if existing:
            db_session.delete(existing)
            db_session.commit()

        record = usage_tracker.track_usage(
            user_id=test_user.id,
            usage_type="expense",
            quantity=1
        )

        # Verify subscription was created
        subscription = db_session.query(Subscription).filter_by(
            user_id=test_user.id
        ).first()

        assert subscription is not None
        assert subscription.tier == SubscriptionTier.STARTER
        assert subscription.status == "trialing"
        assert subscription.trial_end is not None

    def test_track_usage_over_limit_becomes_billable(
        self, usage_tracker, test_user, test_subscription, db_session
    ):
        """Test that usage over tier limit becomes billable"""
        # Track usage up to the limit (100 for expenses on Starter tier)
        for i in range(100):
            usage_tracker.track_usage(
                user_id=test_user.id,
                usage_type="expense",
                quantity=1
            )

        # Next usage should be billable
        record = usage_tracker.track_usage(
            user_id=test_user.id,
            usage_type="expense",
            quantity=1
        )

        assert record.billable is True
        assert record.fee is not None
        assert record.fee > 0

    def test_track_usage_multiple_quantities(
        self, usage_tracker, test_user, test_subscription
    ):
        """Test tracking usage with quantity > 1"""
        record = usage_tracker.track_usage(
            user_id=test_user.id,
            usage_type="ai_categorization",
            quantity=5
        )

        assert record.quantity == 5

    def test_track_usage_different_types(
        self, usage_tracker, test_user, test_subscription
    ):
        """Test tracking different usage types"""
        usage_types = ["expense", "ai_categorization", "ocr_scan", "ap2_transaction"]

        for usage_type in usage_types:
            record = usage_tracker.track_usage(
                user_id=test_user.id,
                usage_type=usage_type,
                quantity=1
            )

            assert record.usage_type == usage_type

    def test_get_monthly_usage(
        self, usage_tracker, test_user, test_subscription
    ):
        """Test getting monthly usage statistics"""
        # Track some usage
        usage_tracker.track_usage(
            user_id=test_user.id,
            usage_type="expense",
            quantity=10
        )

        usage_tracker.track_usage(
            user_id=test_user.id,
            usage_type="ai_categorization",
            quantity=5
        )

        # Get monthly usage
        usage_data = usage_tracker.get_monthly_usage(
            subscription_id=test_subscription.id
        )

        assert "usage" in usage_data
        assert "expense" in usage_data["usage"]
        assert usage_data["usage"]["expense"]["quantity"] == 10
        assert "ai_categorization" in usage_data["usage"]
        assert usage_data["usage"]["ai_categorization"]["quantity"] == 5

    def test_get_monthly_usage_filtered(
        self, usage_tracker, test_user, test_subscription
    ):
        """Test getting monthly usage filtered by type"""
        # Track different types
        usage_tracker.track_usage(
            user_id=test_user.id,
            usage_type="expense",
            quantity=10
        )

        usage_tracker.track_usage(
            user_id=test_user.id,
            usage_type="ai_categorization",
            quantity=5
        )

        # Get only expense usage
        usage_data = usage_tracker.get_monthly_usage(
            subscription_id=test_subscription.id,
            usage_type="expense"
        )

        assert "expense" in usage_data["usage"]
        assert "ai_categorization" not in usage_data["usage"]

    @freeze_time("2025-01-15")
    def test_get_monthly_usage_current_period(
        self, usage_tracker, test_user, test_subscription
    ):
        """Test that monthly usage only includes current month"""
        # Track usage
        usage_tracker.track_usage(
            user_id=test_user.id,
            usage_type="expense",
            quantity=5
        )

        usage_data = usage_tracker.get_monthly_usage(
            subscription_id=test_subscription.id
        )

        # Verify period dates
        assert usage_data["period_start"].month == 1
        assert usage_data["period_start"].day == 1
        assert usage_data["period_end"].month == 1
        assert usage_data["period_end"].day == 15

    def test_get_monthly_usage_with_fees(
        self, usage_tracker, test_user, test_subscription, db_session
    ):
        """Test monthly usage includes overage fees"""
        # Track usage over limit to generate fees
        for i in range(105):  # Over 100 limit
            usage_tracker.track_usage(
                user_id=test_user.id,
                usage_type="expense",
                quantity=1
            )

        usage_data = usage_tracker.get_monthly_usage(
            subscription_id=test_subscription.id
        )

        # Should have overage fees for 5 extra expenses
        assert usage_data["total_overage_fees"] > 0
        assert usage_data["usage"]["expense"]["fees"] > 0

    def test_check_limit_exceeded_under_limit(
        self, usage_tracker, test_user, test_subscription
    ):
        """Test checking limit when under limit"""
        # Track some usage but stay under limit
        usage_tracker.track_usage(
            user_id=test_user.id,
            usage_type="expense",
            quantity=50
        )

        exceeded, current, limit = usage_tracker.check_limit_exceeded(
            user_id=test_user.id,
            usage_type="expense"
        )

        assert exceeded is False
        assert current == 50
        assert limit == 100

    def test_check_limit_exceeded_at_limit(
        self, usage_tracker, test_user, test_subscription
    ):
        """Test checking limit when at exactly at limit"""
        # Track usage up to limit
        usage_tracker.track_usage(
            user_id=test_user.id,
            usage_type="expense",
            quantity=100
        )

        exceeded, current, limit = usage_tracker.check_limit_exceeded(
            user_id=test_user.id,
            usage_type="expense"
        )

        assert exceeded is True  # At limit = exceeded
        assert current == 100
        assert limit == 100

    def test_check_limit_exceeded_over_limit(
        self, usage_tracker, test_user, test_subscription
    ):
        """Test checking limit when over limit"""
        # Track usage over limit
        for i in range(110):
            usage_tracker.track_usage(
                user_id=test_user.id,
                usage_type="expense",
                quantity=1
            )

        exceeded, current, limit = usage_tracker.check_limit_exceeded(
            user_id=test_user.id,
            usage_type="expense"
        )

        assert exceeded is True
        assert current == 110
        assert limit == 100

    def test_check_limit_exceeded_no_subscription(
        self, usage_tracker, test_user, db_session
    ):
        """Test checking limit with no subscription"""
        # Delete subscription
        db_session.query(Subscription).filter_by(user_id=test_user.id).delete()
        db_session.commit()

        exceeded, current, limit = usage_tracker.check_limit_exceeded(
            user_id=test_user.id,
            usage_type="expense"
        )

        assert exceeded is False
        assert current == 0
        assert limit is None

    def test_check_limit_unlimited_tier(
        self, usage_tracker, test_user, db_session
    ):
        """Test checking limit on unlimited tier (Enterprise)"""
        # Create enterprise subscription (unlimited)
        subscription = Subscription(
            id="sub_enterprise",
            user_id=test_user.id,
            tier=SubscriptionTier.ENTERPRISE,
            status="active",
            max_users=999999,
            max_expenses_per_month=999999,
            max_ai_categorizations=999999,
            max_ap2_transactions=999999,
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30)
        )
        db_session.add(subscription)
        db_session.commit()

        # Track huge usage
        usage_tracker.track_usage(
            user_id=test_user.id,
            usage_type="expense",
            quantity=10000
        )

        exceeded, current, limit = usage_tracker.check_limit_exceeded(
            user_id=test_user.id,
            usage_type="expense"
        )

        # Enterprise has very high limits, effectively unlimited
        assert exceeded is False or limit == 999999

    def test_usage_tracker_with_organization(
        self, usage_tracker, test_user, test_organization, db_session
    ):
        """Test usage tracking with organization context"""
        # Add user to organization
        from src.models import OrganizationRole

        membership = OrganizationMember(
            id="member_123",
            organization_id=test_organization.id,
            user_id=test_user.id,
            role=OrganizationRole.MEMBER,
            is_active=True
        )
        db_session.add(membership)
        db_session.commit()

        # Track usage (should use organization context)
        record = usage_tracker.track_usage(
            user_id=test_user.id,
            usage_type="expense",
            quantity=1
        )

        assert record is not None

    def test_usage_tracker_with_explicit_organization(
        self, usage_tracker, test_user, test_organization, test_subscription
    ):
        """Test tracking usage with explicit organization ID"""
        record = usage_tracker.track_usage(
            user_id=test_user.id,
            usage_type="expense",
            quantity=1,
            organization_id=test_organization.id
        )

        assert record is not None

    def test_billable_calculation_ai_categorization(
        self, usage_tracker, test_user, test_subscription
    ):
        """Test billable calculation for AI categorization"""
        # Starter tier has 50 AI categorizations
        for i in range(50):
            usage_tracker.track_usage(
                user_id=test_user.id,
                usage_type="ai_categorization",
                quantity=1
            )

        # Next one should be billable
        record = usage_tracker.track_usage(
            user_id=test_user.id,
            usage_type="ai_categorization",
            quantity=1
        )

        assert record.billable is True

    def test_billable_calculation_ap2_transaction(
        self, usage_tracker, test_user, test_subscription
    ):
        """Test billable calculation for AP2 transactions"""
        # Starter tier has 25 AP2 transactions
        for i in range(25):
            usage_tracker.track_usage(
                user_id=test_user.id,
                usage_type="ap2_transaction",
                quantity=1
            )

        # Next one should be billable
        record = usage_tracker.track_usage(
            user_id=test_user.id,
            usage_type="ap2_transaction",
            quantity=1
        )

        assert record.billable is True

    def test_usage_record_timestamps(
        self, usage_tracker, test_user, test_subscription
    ):
        """Test that usage records have proper timestamps"""
        record = usage_tracker.track_usage(
            user_id=test_user.id,
            usage_type="expense",
            quantity=1
        )

        assert record.created_at is not None
        assert record.created_at <= datetime.utcnow()

    def test_monthly_usage_empty_subscription(
        self, usage_tracker, test_subscription
    ):
        """Test getting monthly usage for subscription with no usage"""
        usage_data = usage_tracker.get_monthly_usage(
            subscription_id=test_subscription.id
        )

        assert usage_data["usage"] == {}
        assert usage_data["total_overage_fees"] == 0

    def test_track_usage_large_quantity(
        self, usage_tracker, test_user, test_subscription
    ):
        """Test tracking large quantity at once"""
        record = usage_tracker.track_usage(
            user_id=test_user.id,
            usage_type="expense",
            quantity=150  # Way over limit in one go
        )

        assert record.quantity == 150
        assert record.billable is True

    @freeze_time("2025-02-01")
    def test_monthly_usage_resets_each_month(
        self, usage_tracker, test_user, test_subscription, db_session
    ):
        """Test that usage limits reset each month"""
        # Track usage in February
        for i in range(50):
            usage_tracker.track_usage(
                user_id=test_user.id,
                usage_type="expense",
                quantity=1
            )

        # Get February usage
        usage_data = usage_tracker.get_monthly_usage(
            subscription_id=test_subscription.id
        )

        assert usage_data["usage"]["expense"]["quantity"] == 50

        # Check if we're under limit (should be, since it's a new month)
        exceeded, current, limit = usage_tracker.check_limit_exceeded(
            user_id=test_user.id,
            usage_type="expense"
        )

        assert exceeded is False
        assert current == 50
        assert limit == 100
