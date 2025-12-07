"""
Payment API routes for Stripe integration
Handles subscription creation, payment methods, and customer portal access
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..config import settings
from ..database import get_db
from ..integrations.stripe_integration import StripeIntegration
from ..models import Organization, OrganizationMember, User
from ..models_billing import (BillingEvent, BillingTier,
                              OrganizationSubscription)
from ..rate_limit import RateLimits, limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payment", tags=["payment"])

# Initialize Stripe
stripe.api_key = settings.stripe_secret_key
# Reload trigger for portal-session endpoint


@router.post("/setup-intent")
async def create_setup_intent(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Create a Setup Intent for collecting payment method

    This is used to securely collect payment method details without charging
    the customer yet. Used during trial signup or payment method updates.
    """
    try:
        # Get user's organization
        membership = (
            db.query(OrganizationMember)
            .filter(OrganizationMember.user_id == current_user.id)
            .first()
        )

        if not membership:
            raise HTTPException(status_code=400, detail="User not in any organization")

        organization = (
            db.query(Organization)
            .filter(Organization.id == membership.organization_id)
            .first()
        )

        if not organization:
            raise HTTPException(status_code=404, detail="Organization not found")

        # Create or get Stripe customer
        if not organization.stripe_customer_id:
            customer = StripeIntegration.create_customer(
                email=current_user.email,
                name=organization.name,
                metadata={
                    "organization_id": organization.id,
                    "user_id": current_user.id,
                },
            )
            organization.stripe_customer_id = customer.id
            db.commit()
        else:
            customer_id = organization.stripe_customer_id

        # Create setup intent
        setup_intent = stripe.SetupIntent.create(
            customer=organization.stripe_customer_id,
            payment_method_types=["card"],
            metadata={"organization_id": organization.id, "user_id": current_user.id},
        )

        return {
            "client_secret": setup_intent.client_secret,
            "customer_id": organization.stripe_customer_id,
        }

    except stripe.StripeError as e:
        logger.error(f"Stripe error creating setup intent: {e}")
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")
    except Exception as e:
        logger.error(f"Error creating setup intent: {e}")
        raise HTTPException(status_code=500, detail="Failed to create setup intent")


@router.post("/subscribe")
async def create_subscription(
    tier_name: str,
    payment_method_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a Stripe subscription for the organization

    Args:
        tier_name: Billing tier (starter, professional, enterprise)
        payment_method_id: Optional Stripe payment method ID (required if not GCP customer)
    """
    try:
        # Get user's organization
        membership = (
            db.query(OrganizationMember)
            .filter(OrganizationMember.user_id == current_user.id)
            .first()
        )

        if not membership:
            raise HTTPException(status_code=400, detail="User not in any organization")

        # Check permissions (only owner/admin can manage billing)
        if membership.role not in ["owner", "admin"]:
            raise HTTPException(
                status_code=403,
                detail="Only organization owners/admins can manage billing",
            )

        organization = (
            db.query(Organization)
            .filter(Organization.id == membership.organization_id)
            .first()
        )

        if not organization:
            raise HTTPException(status_code=404, detail="Organization not found")

        # Get billing tier
        tier = (
            db.query(BillingTier)
            .filter(BillingTier.tier_name == tier_name.lower())
            .first()
        )

        if not tier:
            raise HTTPException(
                status_code=404, detail=f"Billing tier '{tier_name}' not found"
            )

        # Check if organization already has GCP entitlement
        existing_sub = (
            db.query(OrganizationSubscription)
            .filter(
                OrganizationSubscription.organization_id == organization.id,
                OrganizationSubscription.gcp_entitlement_id.isnot(None),
            )
            .first()
        )

        if existing_sub:
            raise HTTPException(
                status_code=400,
                detail="Organization already subscribed via Google Cloud Marketplace. Please manage your subscription through GCP Console.",
            )

        # Get Stripe price ID for tier
        price_id_map = {
            "starter": settings.stripe_price_id_starter,
            "professional": settings.stripe_price_id_professional,
            "enterprise": settings.stripe_price_id_enterprise,
        }

        price_id = price_id_map.get(tier_name.lower())
        if not price_id:
            raise HTTPException(
                status_code=400,
                detail=f"Stripe pricing not configured for tier '{tier_name}'",
            )

        # Create or get Stripe customer
        if not organization.stripe_customer_id:
            customer = StripeIntegration.create_customer(
                email=current_user.email,
                name=organization.name,
                metadata={
                    "organization_id": organization.id,
                    "user_id": current_user.id,
                },
            )
            organization.stripe_customer_id = customer.id

        # Attach payment method if provided
        if payment_method_id:
            stripe.PaymentMethod.attach(
                payment_method_id, customer=organization.stripe_customer_id
            )
            # Set as default payment method
            stripe.Customer.modify(
                organization.stripe_customer_id,
                invoice_settings={"default_payment_method": payment_method_id},
            )

        # Create subscription
        subscription = StripeIntegration.create_subscription(
            customer_id=organization.stripe_customer_id,
            price_id=price_id,
            trial_days=0,  # No trial for direct subscriptions
            metadata={"organization_id": organization.id, "tier_name": tier_name},
        )

        # Update organization
        organization.stripe_subscription_id = subscription.id
        organization.stripe_price_id = price_id

        # Create or update OrganizationSubscription
        org_sub = (
            db.query(OrganizationSubscription)
            .filter(OrganizationSubscription.organization_id == organization.id)
            .first()
        )

        if org_sub:
            org_sub.tier_id = tier.id
            org_sub.status = "active"
            org_sub.billing_period_start = datetime.utcnow()
        else:
            org_sub = OrganizationSubscription(
                id=f"sub_{uuid.uuid4().hex[:12]}",
                organization_id=organization.id,
                tier_id=tier.id,
                status="active",
                billing_period_start=datetime.utcnow(),
                is_trial=False,
            )
            db.add(org_sub)

        # Log billing event
        event = BillingEvent(
            id=f"event_{uuid.uuid4().hex[:12]}",
            organization_id=organization.id,
            event_type="subscription_created",
            event_data={
                "tier_name": tier_name,
                "stripe_subscription_id": subscription.id,
                "stripe_customer_id": organization.stripe_customer_id,
            },
            status="success",
        )
        db.add(event)

        db.commit()

        return {
            "success": True,
            "subscription_id": subscription.id,
            "status": subscription.status,
            "tier": tier_name,
        }

    except stripe.StripeError as e:
        logger.error(f"Stripe error creating subscription: {e}")
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create subscription")


@router.post("/checkout-session")
@limiter.limit(RateLimits.CHECKOUT)
async def create_checkout_session(
    request: Request,
    tier_name: str,
    billing_cycle: str = "monthly",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a Stripe Checkout session for subscription signup

    This provides a hosted checkout page for easier payment collection

    Args:
        tier_name: Billing tier (starter, professional, enterprise)
        billing_cycle: "monthly" or "annual"
    """
    try:
        # Validate billing cycle
        if billing_cycle not in ["monthly", "annual"]:
            raise HTTPException(
                status_code=400,
                detail="billing_cycle must be 'monthly' or 'annual'",
            )

        # Get user's organization
        membership = (
            db.query(OrganizationMember)
            .filter(OrganizationMember.user_id == current_user.id)
            .first()
        )

        if not membership:
            raise HTTPException(status_code=400, detail="User not in any organization")

        if membership.role not in ["owner", "admin"]:
            raise HTTPException(
                status_code=403,
                detail="Only organization owners/admins can manage billing",
            )

        organization = (
            db.query(Organization)
            .filter(Organization.id == membership.organization_id)
            .first()
        )

        # SAFEGUARD 1: Check if organization already has an active Stripe subscription
        if organization.stripe_subscription_id:
            try:
                # Verify the subscription still exists and is active in Stripe
                existing_sub = stripe.Subscription.retrieve(
                    organization.stripe_subscription_id
                )
                if existing_sub.status in ["active", "trialing", "past_due"]:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Organization already has an active subscription. Please cancel your current subscription before subscribing to a new plan, or use the billing portal to change your plan.",
                    )
            except stripe.error.InvalidRequestError:
                # Subscription doesn't exist in Stripe anymore, safe to continue
                logger.warning(
                    f"Stripe subscription {organization.stripe_subscription_id} not found, allowing new checkout"
                )
                pass

        # SAFEGUARD 2: Check for existing active subscription in database
        existing_db_sub = (
            db.query(OrganizationSubscription)
            .filter(
                OrganizationSubscription.organization_id == organization.id,
                OrganizationSubscription.status.in_(["active", "trialing"]),
            )
            .first()
        )
        if existing_db_sub:
            raise HTTPException(
                status_code=400,
                detail="Organization already has an active subscription. Please manage your subscription through the billing dashboard.",
            )

        # Get Stripe price ID based on tier and billing cycle
        price_id_map = {
            ("starter", "monthly"): settings.stripe_price_id_starter_monthly,
            ("starter", "annual"): settings.stripe_price_id_starter_annual,
            ("professional", "monthly"): settings.stripe_price_id_professional_monthly,
            ("professional", "annual"): settings.stripe_price_id_professional_annual,
            ("enterprise", "monthly"): settings.stripe_price_id_enterprise_monthly,
            ("enterprise", "annual"): settings.stripe_price_id_enterprise_annual,
        }

        price_id = price_id_map.get((tier_name.lower(), billing_cycle))
        if not price_id:
            raise HTTPException(
                status_code=400,
                detail=f"Stripe pricing not configured for tier '{tier_name}' with {billing_cycle} billing",
            )

        # Create or get Stripe customer
        if not organization.stripe_customer_id:
            customer = StripeIntegration.create_customer(
                email=current_user.email,
                name=organization.name,
                metadata={
                    "organization_id": organization.id,
                    "user_id": current_user.id,
                },
            )
            organization.stripe_customer_id = customer.id
            db.commit()

        # SAFEGUARD 3: Create checkout session with idempotency key to prevent duplicate sessions
        frontend_url = settings.frontend_url or "http://localhost:5173"

        # Generate idempotency key based on org + tier + billing cycle
        # This ensures the same request can't create multiple checkout sessions
        import hashlib

        idempotency_data = f"{organization.id}:{tier_name}:{billing_cycle}:{datetime.utcnow().strftime('%Y-%m-%d-%H')}"
        idempotency_key = hashlib.sha256(idempotency_data.encode()).hexdigest()[:32]

        session = stripe.checkout.Session.create(
            customer=organization.stripe_customer_id,
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=f"{frontend_url}/billing?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{frontend_url}/pricing",
            metadata={
                "organization_id": organization.id,
                "tier_name": tier_name,
                "billing_cycle": billing_cycle,
            },
            idempotency_key=idempotency_key,
        )
        logger.info(
            f"Created checkout session {session.id} with idempotency key {idempotency_key}"
        )

        return {
            "session_id": session.id,
            "url": session.url,
            "billing_cycle": billing_cycle,
        }

    except stripe.StripeError as e:
        logger.error(f"Stripe error creating checkout session: {e}")
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.post("/portal-session")
async def create_portal_session(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Create a Stripe Customer Portal session

    Allows customers to manage their subscription, update payment methods,
    view invoices, etc.
    """
    try:
        # Get user's organization
        membership = (
            db.query(OrganizationMember)
            .filter(OrganizationMember.user_id == current_user.id)
            .first()
        )

        if not membership:
            raise HTTPException(status_code=400, detail="User not in any organization")

        organization = (
            db.query(Organization)
            .filter(Organization.id == membership.organization_id)
            .first()
        )

        if not organization:
            raise HTTPException(status_code=404, detail="Organization not found")

        # Create Stripe customer if not exists
        if not organization.stripe_customer_id:
            customer = StripeIntegration.create_customer(
                email=current_user.email,
                name=organization.name,
                metadata={
                    "organization_id": organization.id,
                    "user_id": current_user.id,
                },
            )
            organization.stripe_customer_id = customer.id
            db.commit()

        # Create portal session
        frontend_url = settings.frontend_url or "http://localhost:5173"
        session = StripeIntegration.create_portal_session(
            customer_id=organization.stripe_customer_id,
            return_url=f"{frontend_url}/billing",
        )

        return {"url": session.url}

    except stripe.StripeError as e:
        logger.error(f"Stripe error creating portal session: {e}")
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")
    except Exception as e:
        logger.error(f"Error creating portal session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create portal session")


@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    db: Session = Depends(get_db),
):
    """
    Handle Stripe webhook events

    Events handled:
    - customer.subscription.created
    - customer.subscription.updated
    - customer.subscription.deleted
    - invoice.paid
    - invoice.payment_failed
    """
    try:
        # Get raw body
        payload = await request.body()

        # Verify webhook signature
        if not settings.stripe_webhook_secret:
            logger.warning(
                "Stripe webhook secret not configured - skipping signature verification"
            )
            event = stripe.Event.construct_from(await request.json(), stripe.api_key)
        else:
            try:
                event = stripe.Webhook.construct_event(
                    payload, stripe_signature, settings.stripe_webhook_secret
                )
            except stripe.SignatureVerificationError as e:
                logger.error(f"Stripe webhook signature verification failed: {e}")
                raise HTTPException(status_code=400, detail="Invalid signature")

        logger.info(f"Received Stripe webhook: {event.type}")

        # Handle different event types
        if event.type == "checkout.session.completed":
            session = event.data.object
            await handle_checkout_completed(session, db)

        elif event.type == "customer.subscription.created":
            subscription = event.data.object
            await handle_subscription_created(subscription, db)

        elif event.type == "customer.subscription.updated":
            subscription = event.data.object
            await handle_subscription_updated(subscription, db)

        elif event.type == "customer.subscription.deleted":
            subscription = event.data.object
            await handle_subscription_deleted(subscription, db)

        elif event.type == "invoice.paid":
            invoice = event.data.object
            await handle_invoice_paid(invoice, db)

        elif event.type == "invoice.payment_failed":
            invoice = event.data.object
            await handle_invoice_payment_failed(invoice, db)

        return {"status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Stripe webhook: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


async def handle_checkout_completed(session, db: Session):
    """Handle checkout.session.completed event - CRITICAL for subscription activation"""
    try:
        logger.info(f"Processing checkout.session.completed: {session.id}")

        # Extract metadata from checkout session
        metadata = session.metadata
        organization_id = metadata.get("organization_id")
        tier_name = metadata.get("tier_name")
        billing_cycle = metadata.get("billing_cycle", "monthly")

        if not organization_id or not tier_name:
            logger.error(
                f"Missing metadata in checkout session {session.id}: org_id={organization_id}, tier={tier_name}"
            )
            return

        # Find organization
        organization = (
            db.query(Organization).filter(Organization.id == organization_id).first()
        )

        if not organization:
            logger.error(
                f"Organization {organization_id} not found for checkout session {session.id}"
            )
            return

        # Update organization with Stripe IDs
        organization.stripe_customer_id = session.customer
        organization.stripe_subscription_id = session.subscription

        # Get or create billing tier
        tier = (
            db.query(BillingTier)
            .filter(BillingTier.tier_name == tier_name.lower())
            .first()
        )

        if not tier:
            logger.warning(f"Billing tier '{tier_name}' not found, creating default")
            # Create default tier (should be seeded in production)
            tier = BillingTier(
                id=f"tier_{uuid.uuid4().hex[:12]}",
                tier_name=tier_name.lower(),
                display_name=tier_name.capitalize(),
                base_price_monthly=0,  # Will be updated from Stripe
                limits={},
                features=[],
            )
            db.add(tier)
            db.flush()

        # Create or update organization subscription
        org_sub = (
            db.query(OrganizationSubscription)
            .filter(OrganizationSubscription.organization_id == organization_id)
            .first()
        )

        # Determine if trial (check if subscription has trial in Stripe)
        is_trial = False
        trial_end = None
        if session.subscription:
            try:
                stripe_sub = stripe.Subscription.retrieve(session.subscription)
                if stripe_sub.trial_end:
                    is_trial = True
                    trial_end = datetime.fromtimestamp(stripe_sub.trial_end)
            except Exception as e:
                logger.warning(f"Could not retrieve subscription details: {e}")

        now = datetime.utcnow()

        if org_sub:
            # Update existing subscription
            logger.info(f"Updating existing subscription for org {organization_id}")
            org_sub.tier_id = tier.id
            org_sub.tier_name = tier_name.lower()
            org_sub.status = "trialing" if is_trial else "active"
            org_sub.billing_period_start = now
            org_sub.is_trial = is_trial
            org_sub.trial_end = trial_end
            org_sub.additional_metadata = {
                "billing_cycle": billing_cycle,
                "checkout_session_id": session.id,
                "activated_at": now.isoformat(),
            }
        else:
            # Create new subscription
            logger.info(f"Creating new subscription for org {organization_id}")
            org_sub = OrganizationSubscription(
                id=f"sub_{uuid.uuid4().hex[:12]}",
                organization_id=organization_id,
                tier_id=tier.id,
                tier_name=tier_name.lower(),
                status="trialing" if is_trial else "active",
                billing_period_start=now,
                is_trial=is_trial,
                trial_end=trial_end,
                additional_metadata={
                    "billing_cycle": billing_cycle,
                    "checkout_session_id": session.id,
                    "activated_at": now.isoformat(),
                },
            )
            db.add(org_sub)

        # Log billing event
        event = BillingEvent(
            id=f"event_{uuid.uuid4().hex[:12]}",
            organization_id=organization_id,
            event_type="checkout_completed",
            event_data={
                "checkout_session_id": session.id,
                "tier_name": tier_name,
                "billing_cycle": billing_cycle,
                "stripe_customer_id": session.customer,
                "stripe_subscription_id": session.subscription,
                "is_trial": is_trial,
                "trial_end": trial_end.isoformat() if trial_end else None,
                "amount_total": (
                    session.amount_total / 100 if session.amount_total else 0
                ),
            },
            status="success",
        )
        db.add(event)

        db.commit()
        logger.info(
            f"Successfully processed checkout for org {organization_id}: tier={tier_name}, status={org_sub.status}"
        )

    except Exception as e:
        logger.error(f"Error handling checkout.session.completed: {e}", exc_info=True)
        db.rollback()


async def handle_subscription_created(subscription, db: Session):
    """Handle subscription.created event"""
    try:
        customer_id = subscription.customer

        # Find organization by Stripe customer ID
        organization = (
            db.query(Organization)
            .filter(Organization.stripe_customer_id == customer_id)
            .first()
        )

        if not organization:
            logger.warning(f"Organization not found for Stripe customer {customer_id}")
            return

        # Update subscription ID
        organization.stripe_subscription_id = subscription.id

        # Log event
        event = BillingEvent(
            id=f"event_{uuid.uuid4().hex[:12]}",
            organization_id=organization.id,
            event_type="stripe_subscription_created",
            event_data={
                "subscription_id": subscription.id,
                "status": subscription.status,
            },
            status="success",
        )
        db.add(event)
        db.commit()

        logger.info(f"Handled subscription.created for org {organization.id}")

    except Exception as e:
        logger.error(f"Error handling subscription.created: {e}")
        db.rollback()


async def handle_subscription_updated(subscription, db: Session):
    """Handle subscription.updated event"""
    try:
        # Find organization
        organization = (
            db.query(Organization)
            .filter(Organization.stripe_subscription_id == subscription.id)
            .first()
        )

        if not organization:
            logger.warning(f"Organization not found for subscription {subscription.id}")
            return

        # Update subscription status
        org_sub = (
            db.query(OrganizationSubscription)
            .filter(OrganizationSubscription.organization_id == organization.id)
            .first()
        )

        if org_sub:
            status_map = {
                "active": "active",
                "past_due": "active",  # Keep active but warn user
                "canceled": "cancelled",
                "unpaid": "suspended",
            }
            org_sub.status = status_map.get(subscription.status, "active")

        # Log event
        event = BillingEvent(
            id=f"event_{uuid.uuid4().hex[:12]}",
            organization_id=organization.id,
            event_type="stripe_subscription_updated",
            event_data={
                "subscription_id": subscription.id,
                "status": subscription.status,
            },
            status="success",
        )
        db.add(event)
        db.commit()

        logger.info(f"Handled subscription.updated for org {organization.id}")

    except Exception as e:
        logger.error(f"Error handling subscription.updated: {e}")
        db.rollback()


async def handle_subscription_deleted(subscription, db: Session):
    """Handle subscription.deleted event"""
    try:
        # Find organization
        organization = (
            db.query(Organization)
            .filter(Organization.stripe_subscription_id == subscription.id)
            .first()
        )

        if not organization:
            logger.warning(f"Organization not found for subscription {subscription.id}")
            return

        # Update subscription status
        org_sub = (
            db.query(OrganizationSubscription)
            .filter(OrganizationSubscription.organization_id == organization.id)
            .first()
        )

        if org_sub:
            org_sub.status = "cancelled"

        # Log event
        event = BillingEvent(
            id=f"event_{uuid.uuid4().hex[:12]}",
            organization_id=organization.id,
            event_type="stripe_subscription_deleted",
            event_data={"subscription_id": subscription.id},
            status="success",
        )
        db.add(event)
        db.commit()

        logger.info(f"Handled subscription.deleted for org {organization.id}")

    except Exception as e:
        logger.error(f"Error handling subscription.deleted: {e}")
        db.rollback()


async def handle_invoice_paid(invoice, db: Session):
    """Handle invoice.paid event"""
    try:
        customer_id = invoice.customer

        # Find organization
        organization = (
            db.query(Organization)
            .filter(Organization.stripe_customer_id == customer_id)
            .first()
        )

        if not organization:
            logger.warning(f"Organization not found for customer {customer_id}")
            return

        # Update billing period
        org_sub = (
            db.query(OrganizationSubscription)
            .filter(OrganizationSubscription.organization_id == organization.id)
            .first()
        )

        if org_sub:
            org_sub.billing_period_start = datetime.utcnow()
            org_sub.status = "active"

        # Log event
        event = BillingEvent(
            id=f"event_{uuid.uuid4().hex[:12]}",
            organization_id=organization.id,
            event_type="stripe_invoice_paid",
            event_data={"invoice_id": invoice.id, "amount": invoice.amount_paid},
            status="success",
        )
        db.add(event)
        db.commit()

        logger.info(f"Handled invoice.paid for org {organization.id}")

    except Exception as e:
        logger.error(f"Error handling invoice.paid: {e}")
        db.rollback()


async def handle_invoice_payment_failed(invoice, db: Session):
    """Handle invoice.payment_failed event"""
    try:
        customer_id = invoice.customer

        # Find organization
        organization = (
            db.query(Organization)
            .filter(Organization.stripe_customer_id == customer_id)
            .first()
        )

        if not organization:
            logger.warning(f"Organization not found for customer {customer_id}")
            return

        # Log event
        event = BillingEvent(
            id=f"event_{uuid.uuid4().hex[:12]}",
            organization_id=organization.id,
            event_type="stripe_invoice_payment_failed",
            event_data={"invoice_id": invoice.id, "amount": invoice.amount_due},
            status="failed",
        )
        db.add(event)
        db.commit()

        # TODO: Send notification email to organization admins

        logger.warning(f"Invoice payment failed for org {organization.id}")

    except Exception as e:
        logger.error(f"Error handling invoice.payment_failed: {e}")
        db.rollback()
