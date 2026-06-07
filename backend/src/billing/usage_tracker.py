"""
Usage tracking for Marketplace billing.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from ..config import settings
from ..models import OrganizationMember
from ..models_billing import OrganizationSubscription, UsageMetric


class UsageTracker:
    """Track usage events at the organization level."""

    def __init__(self, db: Session):
        self.db = db

    def track_usage(
        self,
        user_id: str,
        usage_type: str,
        quantity: int = 1,
        metadata: Optional[dict] = None,
        organization_id: Optional[str] = None,
    ) -> UsageMetric:
        """
        Track a usage event for Marketplace billing.

        Args:
            user_id: User ID
            usage_type: expense, ai_categorization, ocr_scan, ap2_transaction
            quantity: Quantity used
            metadata: Optional metadata
            organization_id: Optional organization ID (auto-detected if not provided)
        """
        if not organization_id:
            membership = (
                self.db.query(OrganizationMember)
                .filter(
                    OrganizationMember.user_id == user_id,
                    OrganizationMember.is_active == True,
                )
                .first()
            )
            if membership:
                organization_id = membership.organization_id

        if not organization_id:
            raise ValueError("User is not a member of an organization")

        org_subscription = (
            self.db.query(OrganizationSubscription)
            .filter(
                OrganizationSubscription.organization_id == organization_id,
                OrganizationSubscription.status.in_(["active", "trialing"]),
            )
            .first()
        )

        if not org_subscription and settings.enable_billing:
            raise ValueError("Organization does not have an active subscription")

        usage_metric = UsageMetric(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            account_id=org_subscription.stripe_customer_id if org_subscription else None,
            metric_type=usage_type,
            metric_value=float(quantity),
            unit="count",
            period_start=datetime.utcnow(),
            period_end=datetime.utcnow(),
            reported=False,
            additional_metadata=metadata,
        )

        self.db.add(usage_metric)
        self.db.commit()
        self.db.refresh(usage_metric)

        return usage_metric
