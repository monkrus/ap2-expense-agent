"""
Billing and usage API endpoints
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..billing import SubscriptionService, UsageTracker, get_tier_limits
from ..billing.limit_enforcer import LimitEnforcer
from ..database import get_db
from ..models import SubscriptionTier, User, OrganizationMember

router = APIRouter(prefix="/api/billing", tags=["billing"])


# Pydantic models for requests/responses
class UsageTrackRequest(BaseModel):
    usage_type: str  # expense, ai_categorization, ocr_scan, ap2_transaction
    quantity: int = 1
    metadata: Optional[dict] = None


class UsageStatsResponse(BaseModel):
    period_start: datetime
    period_end: datetime
    usage: dict
    total_overage_fees: float


class SubscriptionResponse(BaseModel):
    has_subscription: bool
    tier: Optional[str]
    tier_name: Optional[str]
    status: Optional[str]
    current_period_start: Optional[datetime]
    current_period_end: Optional[datetime]
    trial_end: Optional[datetime]
    limits: Optional[dict]
    stripe_customer_id: Optional[str]
    stripe_subscription_id: Optional[str]


class CreateSubscriptionRequest(BaseModel):
    tier: SubscriptionTier
    trial_days: int = 14


class UpgradeSubscriptionRequest(BaseModel):
    new_tier: SubscriptionTier


# Usage tracking endpoints
@router.post("/usage/track")
def track_usage(
    request: UsageTrackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Track a usage event for billing

    Usage types:
    - expense: Expense submission
    - ai_categorization: AI expense categorization
    - ocr_scan: Receipt OCR scan
    - ap2_transaction: AP2 automated payment
    """
    tracker = UsageTracker(db)

    usage_record = tracker.track_usage(
        user_id=current_user.id,
        usage_type=request.usage_type,
        quantity=request.quantity,
        metadata=request.metadata,
    )

    return {
        "success": True,
        "usage_record_id": usage_record.id,
        "billable": usage_record.billable,
        "fee": float(usage_record.fee) if usage_record.fee else 0,
    }


@router.get("/usage/monthly", response_model=UsageStatsResponse)
def get_monthly_usage(
    usage_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get current month's usage statistics

    Optionally filter by usage_type
    """
    # Get user's subscription
    subscription_service = SubscriptionService(db)
    subscription = subscription_service.get_active_subscription(current_user.id)

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active subscription found"
        )

    tracker = UsageTracker(db)
    usage_stats = tracker.get_monthly_usage(subscription.id, usage_type)

    return usage_stats


@router.get("/usage/check-limit/{usage_type}")
def check_usage_limit(
    usage_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Check if user has exceeded their tier limit for a specific usage type

    Returns:
    - exceeded: bool
    - current_usage: int (current month's usage)
    - limit: int (tier limit, null if unlimited)
    """
    tracker = UsageTracker(db)
    exceeded, current_usage, limit = tracker.check_limit_exceeded(
        current_user.id, usage_type
    )

    return {
        "usage_type": usage_type,
        "exceeded": exceeded,
        "current_usage": current_usage,
        "limit": limit,
        "unlimited": limit is None,
    }


# Subscription management endpoints
@router.get("/subscription", response_model=SubscriptionResponse)
def get_subscription_status(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Get current user's subscription status and limits"""
    subscription_service = SubscriptionService(db)
    status = subscription_service.check_subscription_status(current_user.id)

    return status


@router.post("/subscription")
def create_subscription(
    request: CreateSubscriptionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new subscription for the user

    Note: This creates the subscription record but does not process payment.
    Use Stripe integration for payment processing.
    """
    subscription_service = SubscriptionService(db)

    # Check if user already has an active subscription
    existing = subscription_service.get_active_subscription(current_user.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has an active subscription",
        )

    subscription = subscription_service.create_subscription(
        user_id=current_user.id, tier=request.tier, trial_days=request.trial_days
    )

    return {
        "success": True,
        "subscription_id": subscription.id,
        "tier": subscription.tier.value,
        "status": subscription.status,
        "trial_end": subscription.trial_end,
    }


@router.put("/subscription/{subscription_id}/upgrade")
def upgrade_subscription(
    subscription_id: str,
    request: UpgradeSubscriptionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upgrade subscription to a new tier

    Note: This updates the subscription tier but does not process payment.
    Use Stripe webhooks for payment processing.
    """
    subscription_service = SubscriptionService(db)

    # Verify subscription belongs to user
    subscription = subscription_service.get_active_subscription(current_user.id)
    if not subscription or subscription.id != subscription_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found"
        )

    updated_subscription = subscription_service.upgrade_subscription(
        subscription_id=subscription_id, new_tier=request.new_tier
    )

    return {
        "success": True,
        "subscription_id": updated_subscription.id,
        "new_tier": updated_subscription.tier.value,
        "status": updated_subscription.status,
    }


@router.delete("/subscription/{subscription_id}")
def cancel_subscription(
    subscription_id: str,
    immediate: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Cancel a subscription

    Args:
        immediate: If True, cancel immediately. If False, cancel at period end.
    """
    subscription_service = SubscriptionService(db)

    # Verify subscription belongs to user
    subscription = subscription_service.get_active_subscription(current_user.id)
    if not subscription or subscription.id != subscription_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found"
        )

    canceled_subscription = subscription_service.cancel_subscription(
        subscription_id=subscription_id, immediate=immediate
    )

    return {
        "success": True,
        "subscription_id": canceled_subscription.id,
        "status": canceled_subscription.status,
        "canceled_at": canceled_subscription.canceled_at,
        "ends_at": (
            canceled_subscription.current_period_end
            if not immediate
            else canceled_subscription.canceled_at
        ),
    }


@router.post("/subscription/{subscription_id}/reactivate")
def reactivate_subscription(
    subscription_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reactivate a canceled subscription"""
    subscription_service = SubscriptionService(db)

    reactivated_subscription = subscription_service.reactivate_subscription(
        subscription_id=subscription_id
    )

    return {
        "success": True,
        "subscription_id": reactivated_subscription.id,
        "status": reactivated_subscription.status,
    }


# Tier information endpoints
@router.get("/tiers")
def get_all_tiers():
    """Get information about all subscription tiers"""
    from ..billing.tier_limits import TIER_CONFIGS

    tiers = []
    for tier, limits in TIER_CONFIGS.items():
        tiers.append(
            {
                "tier": tier.value,
                "name": limits.name,
                "price_monthly": limits.price_monthly,
                "max_users": limits.max_users,
                "max_expenses_per_month": limits.max_expenses_per_month,
                "max_ai_categorizations": limits.max_ai_categorizations,
                "max_ap2_transactions": limits.max_ap2_transactions,
                "ocr_scans_included": limits.ocr_scans_included,
                "data_retention_days": limits.data_retention_days,
                "priority_support": limits.priority_support,
                "custom_integrations": limits.custom_integrations,
                "sso_enabled": limits.sso_enabled,
            }
        )

    return {"tiers": tiers}


@router.get("/tiers/{tier}")
def get_tier_info(tier: SubscriptionTier):
    """Get information about a specific tier"""
    limits = get_tier_limits(tier)

    return {
        "tier": tier.value,
        "name": limits.name,
        "price_monthly": limits.price_monthly,
        "max_users": limits.max_users,
        "max_expenses_per_month": limits.max_expenses_per_month,
        "max_ai_categorizations": limits.max_ai_categorizations,
        "max_ap2_transactions": limits.max_ap2_transactions,
        "ocr_scans_included": limits.ocr_scans_included,
        "data_retention_days": limits.data_retention_days,
        "priority_support": limits.priority_support,
        "custom_integrations": limits.custom_integrations,
        "sso_enabled": limits.sso_enabled,
    }


@router.get("/usage/summary")
def get_usage_summary(
    organization_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get comprehensive usage summary for an organization.

    Returns tier info, current usage, limits, and warnings.
    Useful for displaying usage dashboards and limit warnings to users.
    """
    # Get user's organization membership
    membership = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.is_active == True,
        )
        .first()
    )

    # Security: If organization_id is provided, verify user has access to it FIRST
    # This check must happen BEFORE the early return for users without orgs
    if organization_id:
        # Check if user is a member of the requested organization
        has_access = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.is_active == True,
            )
            .first()
        )
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this organization"
            )

    if not membership:
        # Return default Free tier info for users without organizations
        free_limits = get_tier_limits(SubscriptionTier.FREE)
        return {
            "tier": "free",
            "tier_name": "Free",
            "is_free_tier": True,
            "usage": {
                "expenses": {"current": 0, "limit": 20, "percentage": 0, "warning": False, "blocked": False},
                "users": {"current": 0, "limit": 1, "percentage": 0, "warning": False, "blocked": False},
                "ai_categorizations": {"current": 0, "limit": 0, "percentage": 0, "warning": True, "blocked": True},
                "ocr_scans": {"current": 0, "limit": 5, "percentage": 0, "warning": False, "blocked": False},
                "ap2_transactions": {"current": 0, "limit": 0, "percentage": 0, "warning": True, "blocked": True},
            },
            "features": {
                "api_access": False,
                "sso_enabled": False,
                "custom_integrations": False,
                "advanced_analytics": False,
                "priority_support": False,
            },
            "data_retention_days": 30,
        }

    if not organization_id:
        # Use user's first organization
        organization_id = membership.organization_id

    # Get usage summary from LimitEnforcer
    limit_enforcer = LimitEnforcer(db)
    return limit_enforcer.get_usage_summary(organization_id)
