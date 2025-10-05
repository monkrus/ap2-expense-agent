"""
Subscription management service
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from ..models import Subscription, SubscriptionTier, User
from .tier_limits import get_tier_limits


class SubscriptionService:
    """Manage subscriptions and tier changes"""

    def __init__(self, db: Session):
        self.db = db

    def create_subscription(
        self,
        user_id: str,
        tier: SubscriptionTier = SubscriptionTier.STARTER,
        trial_days: int = 14,
        stripe_customer_id: Optional[str] = None,
        stripe_subscription_id: Optional[str] = None
    ) -> Subscription:
        """
        Create a new subscription

        Args:
            user_id: User ID
            tier: Subscription tier
            trial_days: Trial period in days
            stripe_customer_id: Stripe customer ID
            stripe_subscription_id: Stripe subscription ID

        Returns:
            Subscription
        """
        limits = get_tier_limits(tier)

        now = datetime.utcnow()
        trial_end = now + timedelta(days=trial_days)

        subscription = Subscription(
            id=str(uuid.uuid4()),
            user_id=user_id,
            tier=tier,
            status="trialing" if trial_days > 0 else "active",
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            trial_end=trial_end if trial_days > 0 else None,
            max_users=limits.max_users,
            max_expenses_per_month=limits.max_expenses_per_month,
            max_ai_categorizations=limits.max_ai_categorizations,
            max_ap2_transactions=limits.max_ap2_transactions
        )

        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)

        return subscription

    def get_active_subscription(self, user_id: str) -> Optional[Subscription]:
        """Get user's active subscription"""
        return self.db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status.in_(["active", "trialing"])
        ).first()

    def upgrade_subscription(
        self,
        subscription_id: str,
        new_tier: SubscriptionTier,
        stripe_price_id: Optional[str] = None
    ) -> Subscription:
        """
        Upgrade subscription to a new tier

        Args:
            subscription_id: Subscription ID
            new_tier: New subscription tier
            stripe_price_id: Stripe price ID for new tier

        Returns:
            Updated subscription
        """
        subscription = self.db.query(Subscription).filter_by(id=subscription_id).first()

        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")

        # Update tier and limits
        limits = get_tier_limits(new_tier)

        subscription.tier = new_tier
        subscription.stripe_price_id = stripe_price_id
        subscription.max_users = limits.max_users
        subscription.max_expenses_per_month = limits.max_expenses_per_month
        subscription.max_ai_categorizations = limits.max_ai_categorizations
        subscription.max_ap2_transactions = limits.max_ap2_transactions

        self.db.commit()
        self.db.refresh(subscription)

        return subscription

    def cancel_subscription(
        self,
        subscription_id: str,
        immediate: bool = False
    ) -> Subscription:
        """
        Cancel a subscription

        Args:
            subscription_id: Subscription ID
            immediate: If True, cancel immediately. If False, cancel at period end.

        Returns:
            Updated subscription
        """
        subscription = self.db.query(Subscription).filter_by(id=subscription_id).first()

        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")

        subscription.canceled_at = datetime.utcnow()

        if immediate:
            subscription.status = "canceled"
        else:
            # Keep active until end of billing period
            subscription.status = "active"

        self.db.commit()
        self.db.refresh(subscription)

        return subscription

    def reactivate_subscription(self, subscription_id: str) -> Subscription:
        """Reactivate a canceled subscription"""
        subscription = self.db.query(Subscription).filter_by(id=subscription_id).first()

        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")

        subscription.status = "active"
        subscription.canceled_at = None

        self.db.commit()
        self.db.refresh(subscription)

        return subscription

    def update_billing_period(
        self,
        subscription_id: str,
        period_start: datetime,
        period_end: datetime
    ) -> Subscription:
        """Update subscription billing period (typically from Stripe webhook)"""
        subscription = self.db.query(Subscription).filter_by(id=subscription_id).first()

        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")

        subscription.current_period_start = period_start
        subscription.current_period_end = period_end

        # If trial ended, make active
        if subscription.status == "trialing" and subscription.trial_end:
            if datetime.utcnow() > subscription.trial_end:
                subscription.status = "active"

        self.db.commit()
        self.db.refresh(subscription)

        return subscription

    def check_subscription_status(self, user_id: str) -> dict:
        """
        Check user's subscription status and limits

        Returns:
            Dictionary with subscription info
        """
        subscription = self.get_active_subscription(user_id)

        if not subscription:
            return {
                "has_subscription": False,
                "tier": None,
                "status": "none"
            }

        limits = get_tier_limits(subscription.tier)

        return {
            "has_subscription": True,
            "tier": subscription.tier.value,
            "tier_name": limits.name,
            "status": subscription.status,
            "current_period_start": subscription.current_period_start,
            "current_period_end": subscription.current_period_end,
            "trial_end": subscription.trial_end,
            "limits": {
                "max_users": limits.max_users,
                "max_expenses_per_month": limits.max_expenses_per_month,
                "max_ai_categorizations": limits.max_ai_categorizations,
                "max_ap2_transactions": limits.max_ap2_transactions,
                "ocr_scans_included": limits.ocr_scans_included,
                "data_retention_days": limits.data_retention_days,
                "priority_support": limits.priority_support,
                "custom_integrations": limits.custom_integrations,
                "sso_enabled": limits.sso_enabled
            },
            "stripe_customer_id": subscription.stripe_customer_id,
            "stripe_subscription_id": subscription.stripe_subscription_id
        }
