"""
Stripe Webhook Handler
Processes Stripe webhook events for payment status updates
"""
import stripe
import json
from fastapi import Request, HTTPException
from typing import Dict
from datetime import datetime
from sqlalchemy.orm import Session
from ..config import settings
from ..models import PaymentMandate, Subscription
from ..billing.subscription_service import SubscriptionService


class StripeWebhookHandler:
    """Handle Stripe webhook events"""

    def __init__(self, db: Session):
        self.db = db
        self.subscription_service = SubscriptionService(db)

    async def handle_webhook(self, request: Request) -> Dict:
        """
        Process incoming Stripe webhook

        Args:
            request: FastAPI request object

        Returns:
            Processing result
        """
        if not settings.stripe_webhook_secret:
            raise HTTPException(status_code=500, detail="Stripe webhook secret not configured")

        payload = await request.body()
        sig_header = request.headers.get('stripe-signature')

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.stripe_webhook_secret
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")

        # Handle different event types
        event_type = event.type
        event_data = event.data.object

        if event_type == 'payment_intent.succeeded':
            await self._handle_payment_success(event_data)
        elif event_type == 'payment_intent.payment_failed':
            await self._handle_payment_failed(event_data)
        elif event_type == 'charge.refunded':
            await self._handle_refund(event_data)
        elif event_type == 'customer.subscription.created':
            await self._handle_subscription_created(event_data)
        elif event_type == 'customer.subscription.updated':
            await self._handle_subscription_updated(event_data)
        elif event_type == 'customer.subscription.deleted':
            await self._handle_subscription_deleted(event_data)
        elif event_type == 'invoice.paid':
            await self._handle_invoice_paid(event_data)
        elif event_type == 'invoice.payment_failed':
            await self._handle_invoice_payment_failed(event_data)

        return {"status": "success", "event_type": event_type}

    async def _handle_payment_success(self, payment_intent):
        """Handle successful payment"""
        mandate_id = payment_intent.metadata.get('ap2_payment_mandate_id')

        if mandate_id:
            mandate = self.db.query(PaymentMandate).filter_by(id=mandate_id).first()
            if mandate:
                mandate.status = 'completed'
                mandate.payment_processor_response = json.dumps({
                    "stripe_payment_intent_id": payment_intent.id,
                    "status": payment_intent.status,
                    "amount": payment_intent.amount / 100,
                    "currency": payment_intent.currency,
                    "created": datetime.fromtimestamp(payment_intent.created).isoformat()
                })

                # Update cart mandate status
                if mandate.cart_mandate:
                    mandate.cart_mandate.status = 'completed'

                self.db.commit()

    async def _handle_payment_failed(self, payment_intent):
        """Handle failed payment"""
        mandate_id = payment_intent.metadata.get('ap2_payment_mandate_id')

        if mandate_id:
            mandate = self.db.query(PaymentMandate).filter_by(id=mandate_id).first()
            if mandate:
                mandate.status = 'failed'
                mandate.payment_processor_response = json.dumps({
                    "stripe_payment_intent_id": payment_intent.id,
                    "status": payment_intent.status,
                    "error": payment_intent.last_payment_error.message if payment_intent.last_payment_error else None
                })

                # Update cart mandate status
                if mandate.cart_mandate:
                    mandate.cart_mandate.status = 'failed'

                self.db.commit()

    async def _handle_refund(self, charge):
        """Handle refund"""
        # Find payment mandate by charge ID
        # Update status to refunded
        pass

    async def _handle_subscription_created(self, subscription_data):
        """Handle subscription created"""
        customer_id = subscription_data.customer
        subscription_id = subscription_data.id

        # Find user by Stripe customer ID
        subscription = self.db.query(Subscription).filter_by(
            stripe_customer_id=customer_id
        ).first()

        if subscription:
            subscription.stripe_subscription_id = subscription_id
            subscription.status = subscription_data.status
            subscription.current_period_start = datetime.fromtimestamp(subscription_data.current_period_start)
            subscription.current_period_end = datetime.fromtimestamp(subscription_data.current_period_end)

            if subscription_data.trial_end:
                subscription.trial_end = datetime.fromtimestamp(subscription_data.trial_end)

            self.db.commit()

    async def _handle_subscription_updated(self, subscription_data):
        """Handle subscription updated"""
        subscription = self.db.query(Subscription).filter_by(
            stripe_subscription_id=subscription_data.id
        ).first()

        if subscription:
            subscription.status = subscription_data.status
            subscription.current_period_start = datetime.fromtimestamp(subscription_data.current_period_start)
            subscription.current_period_end = datetime.fromtimestamp(subscription_data.current_period_end)

            if subscription_data.canceled_at:
                subscription.canceled_at = datetime.fromtimestamp(subscription_data.canceled_at)

            # Update price if changed
            if subscription_data.items.data:
                subscription.stripe_price_id = subscription_data.items.data[0].price.id

            self.db.commit()

    async def _handle_subscription_deleted(self, subscription_data):
        """Handle subscription deleted/canceled"""
        subscription = self.db.query(Subscription).filter_by(
            stripe_subscription_id=subscription_data.id
        ).first()

        if subscription:
            subscription.status = "canceled"
            subscription.canceled_at = datetime.fromtimestamp(subscription_data.canceled_at) if subscription_data.canceled_at else datetime.utcnow()

            self.db.commit()

    async def _handle_invoice_paid(self, invoice_data):
        """Handle invoice paid"""
        subscription = self.db.query(Subscription).filter_by(
            stripe_subscription_id=invoice_data.subscription
        ).first()

        if subscription:
            # Update subscription status to active
            subscription.status = "active"
            self.db.commit()

    async def _handle_invoice_payment_failed(self, invoice_data):
        """Handle invoice payment failed"""
        subscription = self.db.query(Subscription).filter_by(
            stripe_subscription_id=invoice_data.subscription
        ).first()

        if subscription:
            # Update subscription status to past_due
            subscription.status = "past_due"
            self.db.commit()
