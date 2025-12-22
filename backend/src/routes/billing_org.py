"""
Organization-based billing API endpoints
Works with OrganizationSubscription instead of user-based Subscription
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..billing.tier_limits import TIER_CONFIGS
from ..database import get_db
from ..models import OrganizationMember, SubscriptionTier, User
from ..models_billing import BillingTier, OrganizationSubscription, UsageMetric

router = APIRouter(prefix="/api/billing/org", tags=["billing-org"])


class CreateSubscriptionRequest(BaseModel):
    tier: str
    trial_days: int = 14


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
            OrganizationSubscription.status == "active",
        )
        .first()
    )

    if not subscription:
        return {"has_subscription": False, "tier": None, "organization_id": org_id}

    # Get tier details
    tier = db.query(BillingTier).filter(BillingTier.id == subscription.tier_id).first()

    # Get cancel_at from Stripe if available
    cancel_at = None
    if subscription.stripe_subscription_id:
        try:
            import os

            import stripe

            stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
            stripe_sub = stripe.Subscription.retrieve(
                subscription.stripe_subscription_id
            )

            # Check if subscription is scheduled to be canceled
            if stripe_sub.get("cancel_at"):
                cancel_at = datetime.fromtimestamp(stripe_sub["cancel_at"])
        except Exception as e:
            # Log error but don't fail the request
            print(f"Error fetching Stripe cancel_at: {e}")

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
        "limits": tier.limits if tier else {},
        "features": tier.features if tier else {},
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
            UsageMetric.period_start >= period_start,
            UsageMetric.period_end <= period_end,
        )
        .all()
    )

    # Get subscription to check limits
    subscription = (
        db.query(OrganizationSubscription)
        .filter(
            OrganizationSubscription.organization_id == org_id,
            OrganizationSubscription.status == "active",
        )
        .first()
    )

    tier = None
    if subscription:
        tier = (
            db.query(BillingTier).filter(BillingTier.id == subscription.tier_id).first()
        )

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

    # Calculate overage fees
    total_overage = Decimal("0")
    usage_details = {}

    if tier and tier.limits:
        limits = tier.limits
        overage_pricing = tier.overage_pricing or {}

        for usage_type, quantity in usage_by_type.items():
            limit_key = (
                f"max_{usage_type}s"
                if not usage_type.endswith("s")
                else f"max_{usage_type}"
            )

            # Map usage types to limit keys
            limit_mapping = {
                "ai_categorization": "max_ai_categorizations",
                "ap2_transaction": "max_ap2_transactions",
                "ocr_scan": "ocr_scans_included",
                "expense": "max_expenses_per_month",
            }

            limit_key = limit_mapping.get(usage_type, limit_key)
            limit = limits.get(limit_key)

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
        max_users = limits.get("max_users")
        usage_details["active_users"] = {
            "quantity": active_members_count,
            "limit": max_users,
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

    return {
        "period_start": period_start,
        "period_end": period_end,
        "usage": usage_details,
        "total_overage_fees": float(total_overage),
    }


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
                "limits": tier.limits,
                "features": tier.features,
                "overage_pricing": tier.overage_pricing,
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
        "limits": tier.limits,
        "features": tier.features,
        "overage_pricing": tier.overage_pricing,
    }


@router.put("/subscription/upgrade")
def upgrade_subscription(
    new_tier: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upgrade organization subscription to a new tier"""

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
            OrganizationSubscription.status == "active",
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
