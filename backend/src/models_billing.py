"""
Billing and usage tracking models for Google Cloud Marketplace integration
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from .models import Base


class UsageMetric(Base):
    """Track usage metrics for billing purposes"""

    __tablename__ = "usage_metrics"

    id = Column(String(255), primary_key=True)

    # Organization/Account identification
    organization_id = Column(String(255), nullable=False, index=True)
    account_id = Column(String(255), nullable=True)  # GCP account ID from marketplace

    # Metric information
    metric_type = Column(
        String(100), nullable=False
    )  # api_calls, storage_gb, active_users, etc.
    metric_value = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)  # calls, gb, users, etc.

    # Time period
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False, index=True)

    # Reporting
    reported_at = Column(DateTime, nullable=True)
    reported_to_gcp = Column(Boolean, default=False, nullable=False)
    report_response = Column(JSON, nullable=True)

    # Additional data
    additional_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Indexes for efficient querying
    __table_args__ = (
        Index("idx_usage_org_period", "organization_id", "period_start", "period_end"),
        Index("idx_usage_reported", "reported_to_gcp", "period_end"),
    )


class BillingTier(Base):
    """Billing tier/plan configuration"""

    __tablename__ = "billing_tiers"

    id = Column(String(255), primary_key=True)

    # Tier information
    tier_name = Column(
        String(100), nullable=False, unique=True
    )  # free, starter, professional, enterprise
    display_name = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)

    # Pricing
    base_price_monthly = Column(Float, nullable=False)  # USD per month
    currency = Column(String(3), default="USD", nullable=False)

    # Usage limits
    limits = Column(
        JSON, nullable=False
    )  # {api_calls: 10000, storage_gb: 5, active_users: 10}
    overage_pricing = Column(JSON, nullable=True)  # {api_calls: 0.01, storage_gb: 0.50}

    # Features
    features = Column(JSON, nullable=False)  # List of features included

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_public = Column(Boolean, default=True, nullable=False)  # Visible in marketplace

    # Metadata
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class OrganizationSubscription(Base):
    """Track organization subscription status"""

    __tablename__ = "organization_subscriptions"

    id = Column(String(255), primary_key=True)

    # Organization
    organization_id = Column(String(255), nullable=False, unique=True, index=True)

    # Subscription details
    tier_id = Column(String(255), nullable=False)
    tier_name = Column(String(100), nullable=False)

    # GCP Marketplace
    gcp_account_id = Column(String(255), nullable=True, unique=True)
    gcp_entitlement_id = Column(String(255), nullable=True)
    marketplace_order_id = Column(String(255), nullable=True)

    # Status
    status = Column(
        String(50), nullable=False, default="active"
    )  # trial, active, suspended, cancelled

    # Billing
    billing_period_start = Column(DateTime, nullable=True)
    billing_period_end = Column(DateTime, nullable=True)
    next_billing_date = Column(DateTime, nullable=True)

    # Trial
    trial_start = Column(DateTime, nullable=True)
    trial_end = Column(DateTime, nullable=True)
    is_trial = Column(Boolean, default=False, nullable=False)

    # Usage tracking
    current_period_usage = Column(JSON, nullable=True)  # Current billing period usage
    usage_alerts_sent = Column(JSON, nullable=True)  # Track alert thresholds

    # Additional data
    additional_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class BillingEvent(Base):
    """Audit log for billing-related events"""

    __tablename__ = "billing_events"

    id = Column(String(255), primary_key=True)

    # Organization
    organization_id = Column(String(255), nullable=False, index=True)

    # Event details
    event_type = Column(
        String(100), nullable=False, index=True
    )  # subscription_created, usage_reported, tier_changed, etc.
    event_data = Column(JSON, nullable=False)

    # Status
    status = Column(String(50), nullable=False)  # success, failed, pending
    error_message = Column(String(1000), nullable=True)

    # Timing
    occurred_at = Column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )

    # Additional event data
    event_metadata = Column(JSON, nullable=True)


class MarketplaceAccount(Base):
    """
    Links a GCP Consumer Procurement account/consumer to an organization.

    Stores linkage state to support re-linking and account ownership checks.
    """

    __tablename__ = "marketplace_accounts"

    id = Column(String(255), primary_key=True)
    organization_id = Column(String(255), nullable=False, index=True)

    account_id = Column(String(255), nullable=False, unique=True, index=True)
    consumer_id = Column(String(255), nullable=True, unique=True, index=True)

    status = Column(
        String(50), nullable=False, default="linked"
    )  # linked, pending, unlinked
    linked_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    account_metadata = Column(JSON, nullable=True)  # Renamed from 'metadata' (SQLAlchemy reserved)

    __table_args__ = (
        Index("ix_marketplace_accounts_org", "organization_id"),
    )


class MarketplaceEntitlement(Base):
    """
    Tracks Consumer Procurement entitlements and their lifecycle state.
    """

    __tablename__ = "marketplace_entitlements"

    id = Column(String(255), primary_key=True)
    entitlement_id = Column(String(255), nullable=False, unique=True, index=True)
    account_id = Column(String(255), nullable=True, index=True)
    consumer_id = Column(String(255), nullable=True, index=True)
    organization_id = Column(String(255), nullable=False, index=True)

    plan = Column(String(100), nullable=False)
    state = Column(
        String(50), nullable=False, default="ACTIVE"
    )  # ACTIVE, CANCELLED, SUSPENDED, PENDING

    current_period_end = Column(DateTime, nullable=True)
    trial_start = Column(DateTime, nullable=True)
    trial_end = Column(DateTime, nullable=True)
    grace_start = Column(DateTime, nullable=True)
    grace_end = Column(DateTime, nullable=True)
    last_event_at = Column(DateTime, nullable=True)

    entitlement_metadata = Column(JSON, nullable=True)  # Renamed from 'metadata' (SQLAlchemy reserved)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_marketplace_entitlements_org", "organization_id"),
        Index("ix_marketplace_entitlements_state", "state"),
    )


class MarketplaceWebhookEvent(Base):
    """
    Idempotency log for webhook/event handling to ensure at-least-once delivery safety.
    """

    __tablename__ = "marketplace_webhook_events"

    id = Column(String(255), primary_key=True)  # requestId or generated uuid
    handler = Column(String(100), nullable=False)
    dedupe_key = Column(String(255), nullable=False)

    status = Column(
        String(50), nullable=False, default="pending"
    )  # pending, success, failed
    error_message = Column(String(1000), nullable=True)
    payload = Column(JSON, nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    processed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("handler", "dedupe_key", name="uq_marketplace_event_dedupe"),
        Index("ix_marketplace_webhook_handler_status", "handler", "status"),
    )
