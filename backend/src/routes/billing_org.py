"""
Organization-based billing API endpoints
Works with OrganizationSubscription instead of user-based Subscription
"""

import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..billing.limit_enforcer import LimitEnforcer
from ..billing.usage_tracker import UsageTracker
from ..config import settings
from ..database import get_db
from ..models import OrganizationMember, User
from ..models_billing import BillingTier, OrganizationSubscription, UsageMetric

router = APIRouter(prefix="/api/billing/org", tags=["billing-org"])


class CreateSubscriptionRequest(BaseModel):
    tier: str
    trial_days: int = 14


VALID_USAGE_TYPES = {"expense", "ai_categorization", "ocr_scan", "ap2_transaction"}


class UsageTrackRequest(BaseModel):
    usage_type: str
    quantity: int = Field(1, ge=1, description="Must be a positive integer")
    metadata: Optional[dict] = None

    @validator("usage_type")
    def validate_usage_type(cls, v):
        if v not in VALID_USAGE_TYPES:
            raise ValueError(
                f"Invalid usage_type '{v}'. Must be one of: {sorted(VALID_USAGE_TYPES)}"
            )
        return v


def get_user_organization(db: Session, user_id: str) -> Optional[str]:
    """Get the organization ID for a user"""
    member = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.user_id == user_id, OrganizationMember.is_active == True
        )
        .first()
    )

    return member.organization_id if member else None


@router.get("/subscription")
def get_organization_subscription(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Get current user's organization subscription status"""

    # Get user's organization
    org_id = get_user_organization(db, current_user.id)
    if not org_id:
        return {
            "has_subscription": False,
            "tier": None,
            "message": "User not part of any organization",
        }

    # Get organization subscription
    subscription = (
        db.query(OrganizationSubscription)
        .filter(
            OrganizationSubscription.organization_id == org_id,
            OrganizationSubscription.status.in_(["active", "trialing"]),
        )
        .first()
    )

    if not subscription:
        # No subscription = Free tier
        # Get the free tier details
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"No subscription found for org {org_id}, fetching free tier")

        free_tier = db.query(BillingTier).filter(BillingTier.tier_name == "free").first()
        logger.info(f"Free tier found: {free_tier is not None}")

        if not free_tier:
            logger.warning("Free tier not found in database!")
            return {"has_subscription": False, "tier": "free", "organization_id": org_id}

        # Parse limits and features
        limits = free_tier.limits if free_tier else {}
        features = free_tier.features if free_tier else []
        if isinstance(limits, str):
            try:
                limits = json.loads(limits)
            except json.JSONDecodeError:
                limits = {}
        if isinstance(features, str):
            try:
                features = json.loads(features)
            except json.JSONDecodeError:
                features = []

        return {
            "has_subscription": False,
            "tier": "free",
            "tier_display_name": free_tier.display_name,
            "tier_price": 0,
            "status": "active",
            "limits": limits,
            "features": features,
            "organization_id": org_id,
            "is_trial": False,
        }

    # Get tier details
    tier = db.query(BillingTier).filter(BillingTier.id == subscription.tier_id).first()

    cancel_at = None

    limits = tier.limits if tier else {}
    features = tier.features if tier else {}
    if isinstance(limits, str):
        try:
            limits = json.loads(limits)
        except json.JSONDecodeError:
            limits = {}
    if isinstance(features, str):
        try:
            features = json.loads(features)
        except json.JSONDecodeError:
            features = []

    return {
        "has_subscription": True,
        "subscription_id": subscription.id,
        "tier": subscription.tier_name,
        "tier_display_name": tier.display_name if tier else subscription.tier_name,
        "tier_price": float(tier.base_price_monthly) if tier else 0,
        "status": subscription.status,
        "billing_period_start": subscription.billing_period_start,
        "billing_period_end": subscription.billing_period_end,
        "next_billing_date": subscription.next_billing_date,
        "cancel_at": cancel_at,
        "is_trial": subscription.is_trial,
        "trial_end": subscription.trial_end,
        "limits": limits,
        "features": features,
        "gcp_entitlement_id": subscription.gcp_entitlement_id,
        "gcp_account_id": subscription.gcp_account_id,
        "organization_id": org_id,
    }


@router.get("/usage/monthly")
def get_monthly_usage(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Get current month's usage statistics for user's organization"""

    # Get user's organization
    org_id = get_user_organization(db, current_user.id)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not part of any organization",
        )

    # Get current month's date range
    now = datetime.utcnow()
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    next_month = period_start + timedelta(days=32)
    period_end = next_month.replace(day=1) - timedelta(seconds=1)

    # Get usage metrics for this organization
    usage_metrics = (
        db.query(UsageMetric)
        .filter(
            UsageMetric.organization_id == org_id,
            UsageMetric.created_at >= period_start,
            UsageMetric.created_at <= period_end,
        )
        .all()
    )

    # Get subscription to check limits
    subscription = (
        db.query(OrganizationSubscription)
        .filter(
            OrganizationSubscription.organization_id == org_id,
            OrganizationSubscription.status.in_(["active", "trialing"]),
        )
        .first()
    )

    tier = None
    if subscription:
        tier = (
            db.query(BillingTier).filter(BillingTier.id == subscription.tier_id).first()
        )
    else:
        # No subscription = Free tier
        tier = db.query(BillingTier).filter(BillingTier.tier_name == "free").first()

    # Count active organization members
    active_members_count = (
        db.query(func.count(OrganizationMember.id))
        .filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.is_active == True,
        )
        .scalar()
    )

    # Aggregate usage by type
    usage_by_type = {}
    for metric in usage_metrics:
        if metric.metric_type not in usage_by_type:
            usage_by_type[metric.metric_type] = 0
        usage_by_type[metric.metric_type] += metric.metric_value

    # CRITICAL FIX: Use actual expense count, not usage metrics
    # Usage metrics track API calls (60), but we need actual expenses (11)
    # This matches what LimitEnforcer.check_expense_limit() uses
    from ..models import Expense
    actual_expense_count = (
        db.query(func.count(Expense.id))
        .filter(
            Expense.organization_id == org_id,
            Expense.created_at >= period_start,
            Expense.created_at <= period_end,
        )
        .scalar()
        or 0
    )
    # Override the usage metrics sum with actual expense count
    usage_by_type["expense"] = actual_expense_count

    # Calculate overage fees
    total_overage = Decimal("0")
    usage_details = {}

    if tier and tier.limits:
        limits = tier.limits
        if isinstance(limits, str):
            try:
                limits = json.loads(limits)
            except json.JSONDecodeError:
                limits = {}
        overage_pricing = tier.overage_pricing or {}
        if isinstance(overage_pricing, str):
            try:
                overage_pricing = json.loads(overage_pricing)
            except json.JSONDecodeError:
                overage_pricing = {}

        def normalize_limit(value):
            if value is None:
                return None
            try:
                limit = int(value)
            except (TypeError, ValueError):
                return None
            if limit < 0:
                return None
            return limit

        for usage_type, quantity in usage_by_type.items():
            limit_key = (
                f"max_{usage_type}s"
                if not usage_type.endswith("s")
                else f"max_{usage_type}"
            )

            # Map usage types to limit keys (try multiple keys for compatibility)
            limit_mapping = {
                "ai_categorization": ["max_ai_categorizations", "ai_categorizations_included"],
                "ap2_transaction": ["max_ap2_transactions", "ap2_transactions_included"],
                "ocr_scan": ["ocr_scans_included"],
                "expense": ["max_expenses_per_month"],
            }

            # Try multiple keys to find the limit
            limit_keys = limit_mapping.get(usage_type, [limit_key])
            if not isinstance(limit_keys, list):
                limit_keys = [limit_keys]

            limit = None
            for key in limit_keys:
                limit = normalize_limit(limits.get(key))
                if limit is not None:
                    break

            overage = 0
            overage_fee = Decimal("0")

            if limit is not None and limit != float("inf"):
                if quantity > limit:
                    overage = quantity - limit

                    # Calculate overage fees
                    overage_rate_mapping = {
                        "ai_categorization": "ai_categorization_overage",
                        "ap2_transaction": "ap2_transaction_overage",
                        "ocr_scan": "ocr_scan_overage",
                    }
                    overage_rate_key = overage_rate_mapping.get(usage_type)

                    if overage_rate_key and overage_rate_key in overage_pricing:
                        rate = Decimal(str(overage_pricing[overage_rate_key]))
                        overage_fee = rate * Decimal(str(overage))
                        total_overage += overage_fee

            usage_details[usage_type] = {
                "quantity": int(quantity),
                "limit": limit,
                "overage": int(overage) if overage else 0,
                "overage_fee": float(overage_fee),
            }

        # Add active users count to usage details
        max_users = normalize_limit(limits.get("max_users"))
        usage_details["active_users"] = {
            "quantity": active_members_count,
            "limit": max_users,
            "overage": 0,
            "overage_fee": 0.0,
        }

        # BUGFIX: Always include all metric types even if they have 0 usage
        # This ensures the frontend can display all metrics consistently
        all_metric_types = ["expense", "ai_categorization", "ocr_scan", "ap2_transaction"]
        for metric_type in all_metric_types:
            if metric_type not in usage_details:
                # Map usage types to limit keys (try multiple keys for compatibility)
                limit_mapping = {
                    "ai_categorization": ["max_ai_categorizations", "ai_categorizations_included"],
                    "ap2_transaction": ["max_ap2_transactions", "ap2_transactions_included"],
                    "ocr_scan": ["ocr_scans_included"],
                    "expense": ["max_expenses_per_month"],
                }
                # Try multiple keys to find the limit
                limit_keys = limit_mapping.get(metric_type, [])
                limit = None
                for key in limit_keys:
                    limit = normalize_limit(limits.get(key))
                    if limit is not None:
                        break
                usage_details[metric_type] = {
                    "quantity": 0,
                    "limit": limit,
                    "overage": 0,
                    "overage_fee": 0.0,
                }
    else:
        # No tier limits, just return usage
        for usage_type, quantity in usage_by_type.items():
            usage_details[usage_type] = {
                "quantity": int(quantity),
                "limit": None,
                "overage": 0,
                "overage_fee": 0.0,
            }

        # Add active users count even when no tier
        usage_details["active_users"] = {
            "quantity": active_members_count,
            "limit": None,
            "overage": 0,
            "overage_fee": 0.0,
        }

        # BUGFIX: Always include all metric types even if they have 0 usage
        all_metric_types = ["expense", "ai_categorization", "ocr_scan", "ap2_transaction"]
        for metric_type in all_metric_types:
            if metric_type not in usage_details:
                usage_details[metric_type] = {
                    "quantity": 0,
                    "limit": None,
                    "overage": 0,
                    "overage_fee": 0.0,
                }

    return {
        "period_start": period_start,
        "period_end": period_end,
        "usage": usage_details,
        "total_overage_fees": float(total_overage),
    }


@router.post("/usage/track")
def track_usage(
    request: UsageTrackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Track a usage event for the current user's organization."""
    org_id = get_user_organization(db, current_user.id)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not part of any organization",
        )

    tracker = UsageTracker(db)
    try:
        metric = tracker.track_usage(
            user_id=current_user.id,
            usage_type=request.usage_type,
            quantity=request.quantity,
            metadata=request.metadata,
            organization_id=org_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return {
        "success": True,
        "usage_metric_id": metric.id,
        "usage_type": metric.metric_type,
        "quantity": metric.metric_value,
    }


@router.get("/usage/check-limit/{usage_type}")
def check_usage_limit(
    usage_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check usage limits for a specific usage type."""
    org_id = get_user_organization(db, current_user.id)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not part of any organization",
        )

    limit_enforcer = LimitEnforcer(db)
    summary = limit_enforcer.get_usage_summary(org_id)

    key_map = {
        "expense": "expenses",
        "expenses": "expenses",
        "user": "users",
        "users": "users",
        "ai_categorization": "ai_categorizations",
        "ai_categorizations": "ai_categorizations",
        "ocr_scan": "ocr_scans",
        "ocr_scans": "ocr_scans",
        "ap2_transaction": "ap2_transactions",
        "ap2_transactions": "ap2_transactions",
    }

    summary_key = key_map.get(usage_type)
    if not summary_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported usage type: {usage_type}",
        )

    usage_info = summary.get("usage", {}).get(summary_key)
    if not usage_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No usage data for type: {usage_type}",
        )

    return {
        "usage_type": usage_type,
        "exceeded": usage_info.get("blocked", False),
        "current_usage": usage_info.get("current"),
        "limit": usage_info.get("limit"),
        "unlimited": usage_info.get("unlimited", False),
    }


@router.get("/usage/summary")
def get_usage_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get usage summary and limits for the current organization."""
    org_id = get_user_organization(db, current_user.id)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not part of any organization",
        )

    limit_enforcer = LimitEnforcer(db)
    return limit_enforcer.get_usage_summary(org_id)


@router.get("/tiers")
def get_all_tiers(db: Session = Depends(get_db)):
    """Get all available billing tiers"""

    tiers = (
        db.query(BillingTier)
        .filter(BillingTier.is_active == True, BillingTier.is_public == True)
        .all()
    )

    return {
        "tiers": [
            {
                "tier": tier.tier_name,
                "display_name": tier.display_name,
                "price_monthly": float(tier.base_price_monthly),
                "limits": json.loads(tier.limits) if isinstance(tier.limits, str) else tier.limits,
                "features": json.loads(tier.features) if isinstance(tier.features, str) else tier.features,
                "overage_pricing": json.loads(tier.overage_pricing) if isinstance(tier.overage_pricing, str) else tier.overage_pricing,
            }
            for tier in tiers
        ]
    }


@router.get("/tiers/{tier_name}")
def get_tier_info(tier_name: str, db: Session = Depends(get_db)):
    """Get detailed information about a specific tier"""

    tier = (
        db.query(BillingTier)
        .filter(BillingTier.tier_name == tier_name, BillingTier.is_active == True)
        .first()
    )

    if not tier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tier '{tier_name}' not found",
        )

    return {
        "tier": tier.tier_name,
        "display_name": tier.display_name,
        "price_monthly": float(tier.base_price_monthly),
        "limits": json.loads(tier.limits) if isinstance(tier.limits, str) else tier.limits,
        "features": json.loads(tier.features) if isinstance(tier.features, str) else tier.features,
        "overage_pricing": json.loads(tier.overage_pricing) if isinstance(tier.overage_pricing, str) else tier.overage_pricing,
    }


@router.put("/subscription/upgrade")
def upgrade_subscription(
    new_tier: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upgrade organization subscription to a new tier"""
    if settings.enable_gcp_marketplace:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Subscriptions are managed via Google Cloud Marketplace.",
        )

    # Get user's organization
    org_id = get_user_organization(db, current_user.id)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not part of any organization",
        )

    # Check user has permission (should be owner or admin)
    member = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.organization_id == org_id,
        )
        .first()
    )

    if not member or member.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners/admins can change subscription",
        )

    # Get new tier
    new_tier_obj = (
        db.query(BillingTier)
        .filter(BillingTier.tier_name == new_tier, BillingTier.is_active == True)
        .first()
    )

    if not new_tier_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Tier '{new_tier}' not found"
        )

    # Get organization subscription
    subscription = (
        db.query(OrganizationSubscription)
        .filter(
            OrganizationSubscription.organization_id == org_id,
            OrganizationSubscription.status.in_(["active", "trialing"]),
        )
        .first()
    )

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active subscription found"
        )

    # Update subscription
    old_tier = subscription.tier_name
    subscription.tier_id = new_tier_obj.id
    subscription.tier_name = new_tier
    subscription.updated_at = datetime.utcnow()

    db.commit()

    return {
        "success": True,
        "old_tier": old_tier,
        "new_tier": new_tier,
        "message": f"Subscription upgraded from {old_tier} to {new_tier}",
    }


@router.post("/subscription")
def create_organization_subscription(
    request: CreateSubscriptionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new subscription for the user's organization"""
    import uuid
    if settings.enable_gcp_marketplace:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Subscriptions are managed via Google Cloud Marketplace.",
        )

    tier = request.tier
    trial_days = request.trial_days

    # Get user's organization
    org_id = get_user_organization(db, current_user.id)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not part of any organization. Please create or join an organization first.",
        )

    # Check user has permission (should be owner or admin)
    member = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.organization_id == org_id,
        )
        .first()
    )

    if not member or member.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners/admins can create subscriptions",
        )

    # Check if organization already has an active subscription
    existing = (
        db.query(OrganizationSubscription)
        .filter(
            OrganizationSubscription.organization_id == org_id,
            OrganizationSubscription.status == "active",
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization already has an active subscription",
        )

    # Get tier
    tier_obj = (
        db.query(BillingTier)
        .filter(BillingTier.tier_name == tier, BillingTier.is_active == True)
        .first()
    )

    if not tier_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Tier '{tier}' not found"
        )

    # Create subscription
    now = datetime.utcnow()
    trial_end = now + timedelta(days=trial_days) if trial_days > 0 else None

    subscription = OrganizationSubscription(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        tier_id=tier_obj.id,
        tier_name=tier,
        status="active",
        is_trial=trial_days > 0,
        trial_end=trial_end,
        billing_period_start=now,
        billing_period_end=now + timedelta(days=30),
        next_billing_date=trial_end if trial_end else now + timedelta(days=30),
        created_at=now,
        updated_at=now,
    )

    db.add(subscription)
    db.commit()
    db.refresh(subscription)

    return {
        "success": True,
        "subscription_id": subscription.id,
        "tier": subscription.tier_name,
        "status": subscription.status,
        "is_trial": subscription.is_trial,
        "trial_end": subscription.trial_end,
        "organization_id": org_id,
        "message": f"Successfully subscribed to {tier} plan"
        + (f" with {trial_days}-day trial" if trial_days > 0 else ""),
    }
