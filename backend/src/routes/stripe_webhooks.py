"""
Stripe subscription webhook handler and checkout session routes.

Handles subscription lifecycle events from Stripe and provides
endpoints for creating Checkout sessions and Customer Portal links.
"""

import logging
import uuid
from datetime import datetime, timedelta

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..config import settings
from ..database import get_db
from ..models import OrganizationMember, User
from ..models_billing import BillingEvent, BillingTier, OrganizationSubscription

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/stripe", tags=["stripe-billing"])

# Tier name -> Stripe Price ID mapping (set via env or admin)
# In production, populate these from your Stripe dashboard
TIER_PRICE_MAP = {
    "starter": None,  # Set STRIPE_STARTER_PRICE_ID in env
    "professional": None,  # Set STRIPE_PROFESSIONAL_PRICE_ID in env
}


class CheckoutRequest(BaseModel):
    tier: str
    success_url: str = "http://localhost:5173/billing?session_id={CHECKOUT_SESSION_ID}"
    cancel_url: str = "http://localhost:5173/pricing"


class PortalRequest(BaseModel):
    return_url: str = "http://localhost:5173/billing"


def _get_org_for_user(db: Session, user_id: str):
    """Get org ID and require admin role."""
    member = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.user_id == user_id,
            OrganizationMember.is_active == True,
        )
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="User not part of any organization")
    if member.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=403, detail="Only owners/admins can manage billing"
        )
    return member.organization_id


@router.post("/checkout")
async def create_checkout_session(
    request: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout session for subscribing to a paid tier."""
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    stripe.api_key = settings.stripe_secret_key
    org_id = _get_org_for_user(db, current_user.id)

    # Validate tier
    tier = (
        db.query(BillingTier)
        .filter(BillingTier.tier_name == request.tier, BillingTier.is_active == True)
        .first()
    )
    if not tier:
        raise HTTPException(status_code=404, detail=f"Tier '{request.tier}' not found")
    if tier.base_price_monthly == 0:
        raise HTTPException(
            status_code=400, detail="Free tier does not require checkout"
        )

    # Get or create Stripe customer
    subscription = (
        db.query(OrganizationSubscription)
        .filter(OrganizationSubscription.organization_id == org_id)
        .first()
    )

    customer_id = subscription.stripe_customer_id if subscription else None
    if not customer_id:
        customer = stripe.Customer.create(
            email=current_user.email,
            metadata={"organization_id": org_id, "user_id": current_user.id},
        )
        customer_id = customer.id

    # Look up price ID from env or tier config
    import os

    price_id = os.environ.get(f"STRIPE_{request.tier.upper()}_PRICE_ID")
    if not price_id:
        # Create an ad-hoc price (for dev/testing)
        price = stripe.Price.create(
            unit_amount=int(tier.base_price_monthly * 100),
            currency="usd",
            recurring={"interval": "month"},
            product_data={"name": f"AP2 Expense - {tier.display_name}"},
        )
        price_id = price.id

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=request.success_url,
        cancel_url=request.cancel_url,
        metadata={"organization_id": org_id, "tier": request.tier},
    )

    return {"checkout_url": session.url, "session_id": session.id}


@router.post("/portal")
async def create_portal_session(
    request: PortalRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Customer Portal session for managing billing."""
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    stripe.api_key = settings.stripe_secret_key
    org_id = _get_org_for_user(db, current_user.id)

    subscription = (
        db.query(OrganizationSubscription)
        .filter(OrganizationSubscription.organization_id == org_id)
        .first()
    )

    if not subscription or not subscription.stripe_customer_id:
        raise HTTPException(status_code=404, detail="No Stripe subscription found")

    session = stripe.billing_portal.Session.create(
        customer=subscription.stripe_customer_id,
        return_url=request.return_url,
    )

    return {"portal_url": session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Stripe subscription webhook events."""
    payload = await request.body()
    sig = request.headers.get("stripe-signature")

    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook secret not configured")

    stripe.api_key = settings.stripe_secret_key

    try:
        event = stripe.Webhook.construct_event(
            payload, sig, settings.stripe_webhook_secret
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(db, data)
    elif event_type == "customer.subscription.updated":
        _handle_subscription_updated(db, data)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(db, data)
    elif event_type == "invoice.payment_failed":
        _handle_payment_failed(db, data)

    return {"received": True}


def _handle_checkout_completed(db: Session, session_data: dict):
    """Handle successful checkout — create or update subscription."""
    org_id = session_data.get("metadata", {}).get("organization_id")
    tier_name = session_data.get("metadata", {}).get("tier")
    customer_id = session_data.get("customer")
    subscription_id = session_data.get("subscription")

    if not org_id or not tier_name:
        logger.warning("Checkout completed without org/tier metadata")
        return

    tier = db.query(BillingTier).filter(BillingTier.tier_name == tier_name).first()

    # Upsert subscription
    sub = (
        db.query(OrganizationSubscription)
        .filter(OrganizationSubscription.organization_id == org_id)
        .first()
    )

    now = datetime.utcnow()
    if sub:
        sub.tier_id = tier.id if tier else sub.tier_id
        sub.tier_name = tier_name
        sub.stripe_customer_id = customer_id
        sub.stripe_subscription_id = subscription_id
        sub.status = "active"
        sub.is_trial = False
        sub.billing_period_start = now
        sub.billing_period_end = now + timedelta(days=30)
        sub.next_billing_date = now + timedelta(days=30)
        sub.updated_at = now
    else:
        sub = OrganizationSubscription(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            tier_id=tier.id if tier else "",
            tier_name=tier_name,
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
            status="active",
            is_trial=False,
            billing_period_start=now,
            billing_period_end=now + timedelta(days=30),
            next_billing_date=now + timedelta(days=30),
        )
        db.add(sub)

    # Log billing event
    event = BillingEvent(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        event_type="subscription_created",
        event_data={"tier": tier_name, "stripe_subscription_id": subscription_id},
        status="success",
    )
    db.add(event)
    db.commit()
    logger.info(f"Subscription created for org {org_id}: {tier_name}")


def _handle_subscription_updated(db: Session, sub_data: dict):
    """Handle subscription changes (upgrades, downgrades)."""
    stripe_sub_id = sub_data.get("id")
    sub = (
        db.query(OrganizationSubscription)
        .filter(OrganizationSubscription.stripe_subscription_id == stripe_sub_id)
        .first()
    )
    if not sub:
        logger.warning(f"Subscription {stripe_sub_id} not found in DB")
        return

    stripe_status = sub_data.get("status")
    status_map = {
        "active": "active",
        "trialing": "trialing",
        "past_due": "past_due",
        "canceled": "cancelled",
        "unpaid": "suspended",
    }
    sub.status = status_map.get(stripe_status, stripe_status)
    sub.updated_at = datetime.utcnow()
    db.commit()
    logger.info(f"Subscription {stripe_sub_id} updated to {sub.status}")


def _handle_subscription_deleted(db: Session, sub_data: dict):
    """Handle subscription cancellation."""
    stripe_sub_id = sub_data.get("id")
    sub = (
        db.query(OrganizationSubscription)
        .filter(OrganizationSubscription.stripe_subscription_id == stripe_sub_id)
        .first()
    )
    if not sub:
        return

    sub.status = "cancelled"
    sub.updated_at = datetime.utcnow()

    event = BillingEvent(
        id=str(uuid.uuid4()),
        organization_id=sub.organization_id,
        event_type="subscription_cancelled",
        event_data={"stripe_subscription_id": stripe_sub_id},
        status="success",
    )
    db.add(event)
    db.commit()
    logger.info(f"Subscription {stripe_sub_id} cancelled")


def _handle_payment_failed(db: Session, invoice_data: dict):
    """Handle failed payment — log event and notify org owner."""
    customer_id = invoice_data.get("customer")
    sub = (
        db.query(OrganizationSubscription)
        .filter(OrganizationSubscription.stripe_customer_id == customer_id)
        .first()
    )
    if not sub:
        return

    event = BillingEvent(
        id=str(uuid.uuid4()),
        organization_id=sub.organization_id,
        event_type="payment_failed",
        event_data={
            "invoice_id": invoice_data.get("id"),
            "amount_due": invoice_data.get("amount_due"),
        },
        status="failed",
    )
    db.add(event)
    db.commit()
    logger.warning(f"Payment failed for org {sub.organization_id}")

    # Send email notification to org owner
    import asyncio

    try:
        from ..billing.scheduled_tasks import send_payment_failure_email

        asyncio.create_task(
            send_payment_failure_email(db, sub.organization_id, invoice_data)
        )
    except Exception as e:
        logger.error(f"Failed to queue payment failure email: {e}")
