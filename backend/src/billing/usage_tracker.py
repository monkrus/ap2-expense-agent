"""
Usage tracking for billing
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import Subscription, SubscriptionTier, UsageRecord
from .tier_limits import USAGE_FEES, get_tier_limits


class UsageTracker:
    """Track and record usage for billing purposes"""

    def __init__(self, db: Session):
        self.db = db

    def track_usage(
        self,
        user_id: str,
        usage_type: str,
        quantity: int = 1,
        metadata: Optional[dict] = None,
        organization_id: Optional[str] = None,
    ) -> UsageRecord:
        """
        Track a usage event (organization-scoped for GCP Marketplace)

        Args:
            user_id: User ID
            usage_type: Type of usage (expense, ai_categorization, ocr_scan, ap2_transaction)
            quantity: Quantity used
            metadata: Optional metadata
            organization_id: Optional organization ID (auto-detected if not provided)

        Returns:
            UsageRecord
        """
        # Get organization from user if not provided
        if not organization_id:
            from ..models import OrganizationMember

            org_membership = (
                self.db.query(OrganizationMember)
                .filter(
                    OrganizationMember.user_id == user_id,
                    OrganizationMember.is_active == True,
                )
                .first()
            )

            if org_membership:
                organization_id = org_membership.organization_id

        # Get user's subscription (try organization subscription first for GCP customers)
        subscription = None

        if organization_id:
            # For GCP Marketplace customers, use organization subscription
            from ..models_billing import OrganizationSubscription, UsageMetric

            org_subscription = (
                self.db.query(OrganizationSubscription)
                .filter(
                    OrganizationSubscription.organization_id == organization_id,
                    OrganizationSubscription.status == "active",
                )
                .first()
            )

            if org_subscription:
                # Track in GCP-compatible format
                usage_metric = UsageMetric(
                    id=str(uuid.uuid4()),
                    organization_id=organization_id,
                    account_id=org_subscription.gcp_account_id,
                    metric_type=usage_type,
                    metric_value=float(quantity),
                    unit="count",
                    period_start=datetime.utcnow(),
                    period_end=datetime.utcnow(),
                    reported_to_gcp=False,
                    additional_metadata=metadata,
                    created_at=datetime.utcnow(),
                )
                self.db.add(usage_metric)
                self.db.commit()

                # Also create UsageRecord for backward compatibility
                usage_record = UsageRecord(
                    id=str(uuid.uuid4()),
                    subscription_id=org_subscription.id,
                    user_id=user_id,
                    usage_type=usage_type,
                    quantity=quantity,
                    billable=False,  # GCP handles billing
                    fee=None,
                    extra_data=str(metadata) if metadata else None,
                )
                self.db.add(usage_record)
                self.db.commit()
                self.db.refresh(usage_record)

                return usage_record

        # Fall back to old user-based subscription model
        subscription = (
            self.db.query(Subscription)
            .filter(Subscription.user_id == user_id, Subscription.status == "active")
            .first()
        )

        if not subscription:
            # Create a default starter subscription if none exists
            subscription = self._create_default_subscription(user_id)

        # Get tier limits
        limits = get_tier_limits(subscription.tier)

        # Check if this usage is billable (over tier limits)
        billable, fee = self._calculate_billable(
            subscription=subscription, usage_type=usage_type, quantity=quantity
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
            extra_data=str(metadata) if metadata else None,
        )

        self.db.add(usage_record)
        self.db.commit()
        self.db.refresh(usage_record)

        return usage_record

    def _calculate_billable(
        self, subscription: Subscription, usage_type: str, quantity: int
    ) -> tuple[bool, Optional[float]]:
        """
        Calculate if usage is billable and the fee

        Returns:
            (billable: bool, fee: Optional[float])
        """
        # Get tier limits
        limits = get_tier_limits(subscription.tier)

        # Get current month's usage
        start_of_month = datetime.utcnow().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        current_usage = (
            self.db.query(func.sum(UsageRecord.quantity))
            .filter(
                UsageRecord.subscription_id == subscription.id,
                UsageRecord.usage_type == usage_type,
                UsageRecord.created_at >= start_of_month,
            )
            .scalar()
            or 0
        )

        # Determine if over limit
        limit_map = {
            "expense": limits.max_expenses_per_month,
            "ai_categorization": limits.max_ai_categorizations,
            "ap2_transaction": limits.max_ap2_transactions,
            "ocr_scan": limits.ocr_scans_included,
        }

        limit = limit_map.get(usage_type)

        # If no limit (None = unlimited), not billable
        if limit is None:
            return False, None

        # Check if current + new usage exceeds limit
        new_total = current_usage + quantity

        # If new total is under or at limit, not billable
        if new_total <= limit:
            return False, None

        # Over limit - calculate fee for the overage portion
        overage_quantity = new_total - limit
        fee_per_unit = USAGE_FEES.get(usage_type, 0)
        total_fee = fee_per_unit * overage_quantity

        return True, total_fee

    def _create_default_subscription(self, user_id: str) -> Subscription:
        """Create a default FREE subscription for new user"""
        limits = get_tier_limits(SubscriptionTier.FREE)

        subscription = Subscription(
            id=str(uuid.uuid4()),
            user_id=user_id,
            tier=SubscriptionTier.FREE,
            status="active",  # Free tier is always active (no trial needed)
            max_users=limits.max_users,
            max_expenses_per_month=limits.max_expenses_per_month,
            max_ai_categorizations=limits.max_ai_categorizations,
            max_ap2_transactions=limits.max_ap2_transactions,
            trial_end=None,  # Free tier has no trial
        )

        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)

        return subscription

    def get_monthly_usage(
        self, subscription_id: str, usage_type: Optional[str] = None
    ) -> dict:
        """
        Get current month's usage for a subscription

        Args:
            subscription_id: Subscription ID
            usage_type: Optional filter by usage type

        Returns:
            Dictionary with usage statistics
        """
        start_of_month = datetime.utcnow().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )

        query = self.db.query(
            UsageRecord.usage_type,
            func.sum(UsageRecord.quantity).label("total_quantity"),
            func.sum(UsageRecord.fee).label("total_fees"),
            func.count(UsageRecord.id).label("record_count"),
        ).filter(
            UsageRecord.subscription_id == subscription_id,
            UsageRecord.created_at >= start_of_month,
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
                "count": row.record_count,
            }
            total_fees += float(row.total_fees or 0)

        return {
            "period_start": start_of_month,
            "period_end": datetime.utcnow(),
            "usage": usage_data,
            "total_overage_fees": total_fees,
        }

    def check_limit_exceeded(
        self, user_id: str, usage_type: str
    ) -> tuple[bool, Optional[int], Optional[int]]:
        """
        Check if user has exceeded their tier limit

        Returns:
            (exceeded: bool, current_usage: Optional[int], limit: Optional[int])
        """
        subscription = (
            self.db.query(Subscription)
            .filter(
                Subscription.user_id == user_id,
                Subscription.status.in_(["active", "trialing"]),
            )
            .first()
        )

        if not subscription:
            return False, 0, None

        limits = get_tier_limits(subscription.tier)

        limit_map = {
            "expense": limits.max_expenses_per_month,
            "ai_categorization": limits.max_ai_categorizations,
            "ap2_transaction": limits.max_ap2_transactions,
            "ocr_scan": limits.ocr_scans_included,
        }

        limit = limit_map.get(usage_type)

        # No limit means unlimited
        if limit is None:
            return False, None, None

        # Get current usage
        start_of_month = datetime.utcnow().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        current_usage = (
            self.db.query(func.sum(UsageRecord.quantity))
            .filter(
                UsageRecord.subscription_id == subscription.id,
                UsageRecord.usage_type == usage_type,
                UsageRecord.created_at >= start_of_month,
            )
            .scalar()
            or 0
        )

        exceeded = current_usage >= limit

        return exceeded, int(current_usage), limit
