"""
Usage tracking for billing
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import UsageRecord, Subscription, SubscriptionTier
from .tier_limits import get_tier_limits, USAGE_FEES


class UsageTracker:
    """Track and record usage for billing purposes"""

    def __init__(self, db: Session):
        self.db = db

    def track_usage(
        self,
        user_id: str,
        usage_type: str,
        quantity: int = 1,
        metadata: Optional[dict] = None
    ) -> UsageRecord:
        """
        Track a usage event

        Args:
            user_id: User ID
            usage_type: Type of usage (expense, ai_categorization, ocr_scan, ap2_transaction)
            quantity: Quantity used
            metadata: Optional metadata

        Returns:
            UsageRecord
        """
        # Get user's subscription
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == "active"
        ).first()

        if not subscription:
            # Create a default starter subscription if none exists
            subscription = self._create_default_subscription(user_id)

        # Get tier limits
        limits = get_tier_limits(subscription.tier)

        # Check if this usage is billable (over tier limits)
        billable, fee = self._calculate_billable(
            subscription=subscription,
            usage_type=usage_type,
            quantity=quantity
        )

        # Create usage record
        usage_record = UsageRecord(
            id=str(uuid.uuid4()),
            subscription_id=subscription.id,
            user_id=user_id,
            usage_type=usage_type,
            quantity=quantity,
            billable=billable,
            fee=fee,
            extra_data=str(metadata) if metadata else None
        )

        self.db.add(usage_record)
        self.db.commit()
        self.db.refresh(usage_record)

        return usage_record

    def _calculate_billable(
        self,
        subscription: Subscription,
        usage_type: str,
        quantity: int
    ) -> tuple[bool, Optional[float]]:
        """
        Calculate if usage is billable and the fee

        Returns:
            (billable: bool, fee: Optional[float])
        """
        # Get tier limits
        limits = get_tier_limits(subscription.tier)

        # Get current month's usage
        start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_usage = self.db.query(func.sum(UsageRecord.quantity)).filter(
            UsageRecord.subscription_id == subscription.id,
            UsageRecord.usage_type == usage_type,
            UsageRecord.created_at >= start_of_month
        ).scalar() or 0

        # Determine if over limit
        limit_map = {
            "expense": limits.max_expenses_per_month,
            "ai_categorization": limits.max_ai_categorizations,
            "ap2_transaction": limits.max_ap2_transactions,
            "ocr_scan": limits.ocr_scans_included
        }

        limit = limit_map.get(usage_type)

        # If no limit (None = unlimited), not billable
        if limit is None:
            return False, None

        # If under limit, not billable
        if current_usage < limit:
            return False, None

        # Over limit - calculate fee
        fee_per_unit = USAGE_FEES.get(usage_type, 0)
        total_fee = fee_per_unit * quantity

        return True, total_fee

    def _create_default_subscription(self, user_id: str) -> Subscription:
        """Create a default starter subscription for new user"""
        limits = get_tier_limits(SubscriptionTier.STARTER)

        subscription = Subscription(
            id=str(uuid.uuid4()),
            user_id=user_id,
            tier=SubscriptionTier.STARTER,
            status="trialing",
            max_users=limits.max_users,
            max_expenses_per_month=limits.max_expenses_per_month,
            max_ai_categorizations=limits.max_ai_categorizations,
            max_ap2_transactions=limits.max_ap2_transactions,
            trial_end=datetime.utcnow() + timedelta(days=14)  # 14-day trial
        )

        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)

        return subscription

    def get_monthly_usage(self, subscription_id: str, usage_type: Optional[str] = None) -> dict:
        """
        Get current month's usage for a subscription

        Args:
            subscription_id: Subscription ID
            usage_type: Optional filter by usage type

        Returns:
            Dictionary with usage statistics
        """
        start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        query = self.db.query(
            UsageRecord.usage_type,
            func.sum(UsageRecord.quantity).label('total_quantity'),
            func.sum(UsageRecord.fee).label('total_fees'),
            func.count(UsageRecord.id).label('record_count')
        ).filter(
            UsageRecord.subscription_id == subscription_id,
            UsageRecord.created_at >= start_of_month
        )

        if usage_type:
            query = query.filter(UsageRecord.usage_type == usage_type)

        results = query.group_by(UsageRecord.usage_type).all()

        usage_data = {}
        total_fees = 0

        for row in results:
            usage_data[row.usage_type] = {
                "quantity": int(row.total_quantity or 0),
                "fees": float(row.total_fees or 0),
                "count": row.record_count
            }
            total_fees += float(row.total_fees or 0)

        return {
            "period_start": start_of_month,
            "period_end": datetime.utcnow(),
            "usage": usage_data,
            "total_overage_fees": total_fees
        }

    def check_limit_exceeded(
        self,
        user_id: str,
        usage_type: str
    ) -> tuple[bool, Optional[int], Optional[int]]:
        """
        Check if user has exceeded their tier limit

        Returns:
            (exceeded: bool, current_usage: Optional[int], limit: Optional[int])
        """
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status.in_(["active", "trialing"])
        ).first()

        if not subscription:
            return False, 0, None

        limits = get_tier_limits(subscription.tier)

        limit_map = {
            "expense": limits.max_expenses_per_month,
            "ai_categorization": limits.max_ai_categorizations,
            "ap2_transaction": limits.max_ap2_transactions,
            "ocr_scan": limits.ocr_scans_included
        }

        limit = limit_map.get(usage_type)

        # No limit means unlimited
        if limit is None:
            return False, None, None

        # Get current usage
        start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_usage = self.db.query(func.sum(UsageRecord.quantity)).filter(
            UsageRecord.subscription_id == subscription.id,
            UsageRecord.usage_type == usage_type,
            UsageRecord.created_at >= start_of_month
        ).scalar() or 0

        exceeded = current_usage >= limit

        return exceeded, int(current_usage), limit
