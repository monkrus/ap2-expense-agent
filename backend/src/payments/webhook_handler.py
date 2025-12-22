"""
Stripe Webhook Handler
Processes Stripe webhook events for payment status updates
"""

import json
from datetime import datetime
from typing import Dict

import stripe
from stripe import _error as stripe_error
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from ..config import settings
from ..models import PaymentMandate


class StripeWebhookHandler:
    """Handle Stripe webhook events"""

    def __init__(self, db: Session):
        self.db = db

    async def handle_webhook(self, request: Request) -> Dict:
        """
        Process incoming Stripe webhook

        Args:
            request: FastAPI request object

        Returns:
            Processing result
        """
        if not settings.stripe_webhook_secret:
            raise HTTPException(
                status_code=500, detail="Stripe webhook secret not configured"
            )

        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.stripe_webhook_secret
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe_error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")

        # Handle different event types
        event_type = event.type
        event_data = event.data.object

        if event_type == "payment_intent.succeeded":
            await self._handle_payment_success(event_data)
            return {"status": "success", "event_type": event_type}
        if event_type == "payment_intent.payment_failed":
            await self._handle_payment_failed(event_data)
            return {"status": "success", "event_type": event_type}
        if event_type == "charge.refunded":
            await self._handle_refund(event_data)
            return {"status": "success", "event_type": event_type}

        return {"status": "ignored", "event_type": event_type}

    async def _handle_payment_success(self, payment_intent):
        """Handle successful payment"""
        mandate_id = payment_intent.metadata.get("ap2_payment_mandate_id")

        if mandate_id:
            mandate = self.db.query(PaymentMandate).filter_by(id=mandate_id).first()
            if mandate:
                mandate.status = "completed"
                mandate.payment_processor_response = json.dumps(
                    {
                        "stripe_payment_intent_id": payment_intent.id,
                        "status": payment_intent.status,
                        "amount": payment_intent.amount / 100,
                        "currency": payment_intent.currency,
                        "created": datetime.fromtimestamp(
                            payment_intent.created
                        ).isoformat(),
                    }
                )

                # Update cart mandate status
                if mandate.cart_mandate:
                    mandate.cart_mandate.status = "completed"

                self.db.commit()

    async def _handle_payment_failed(self, payment_intent):
        """Handle failed payment"""
        mandate_id = payment_intent.metadata.get("ap2_payment_mandate_id")

        if mandate_id:
            mandate = self.db.query(PaymentMandate).filter_by(id=mandate_id).first()
            if mandate:
                mandate.status = "failed"
                mandate.payment_processor_response = json.dumps(
                    {
                        "stripe_payment_intent_id": payment_intent.id,
                        "status": payment_intent.status,
                        "error": (
                            payment_intent.last_payment_error.message
                            if payment_intent.last_payment_error
                            else None
                        ),
                    }
                )

                # Update cart mandate status
                if mandate.cart_mandate:
                    mandate.cart_mandate.status = "failed"

                self.db.commit()

    async def _handle_refund(self, charge):
        """Handle refund"""
        # Find payment mandate by charge ID
        # Update status to refunded
        pass

    # Subscription/invoice events are ignored here; Marketplace handles billing.
