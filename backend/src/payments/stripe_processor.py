"""
Stripe Payment Processor Integration
Processes AP2 payment mandates through Stripe
"""
import stripe
from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from ..config import settings
from ..models import PaymentMandate

# Initialize Stripe with API key from settings
if settings.stripe_secret_key:
    stripe.api_key = settings.stripe_secret_key


class StripePaymentProcessor:
    """Process payments using Stripe with AP2 mandates"""

    def __init__(self, db: Session):
        self.db = db

    async def process_payment_mandate(
        self,
        payment_mandate: PaymentMandate,
        amount: float,
        currency: str = "usd",
        customer_id: Optional[str] = None
    ) -> Dict:
        """
        Process payment using AP2 mandate through Stripe

        Args:
            payment_mandate: AP2 Payment Mandate
            amount: Amount in dollars
            currency: Currency code
            customer_id: Stripe customer ID

        Returns:
            Payment result with transaction details
        """
        if not settings.stripe_secret_key:
            return {
                "success": False,
                "error": "stripe_not_configured",
                "message": "Stripe is not configured. Set STRIPE_SECRET_KEY environment variable."
            }

        try:
            # Create PaymentIntent
            payment_intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Convert to cents
                currency=currency,
                customer=customer_id,
                metadata={
                    "ap2_payment_mandate_id": payment_mandate.id,
                    "ap2_cart_mandate_id": payment_mandate.cart_mandate_id,
                    "mandate_timestamp": payment_mandate.timestamp.isoformat()
                },
                confirm=True,
                automatic_payment_methods={"enabled": True, "allow_redirects": "never"}
            )

            return {
                "success": True,
                "transaction_id": payment_intent.id,
                "status": payment_intent.status,
                "amount": amount,
                "currency": currency,
                "created": datetime.fromtimestamp(payment_intent.created).isoformat()
            }

        except stripe.error.CardError as e:
            return {
                "success": False,
                "error": "card_error",
                "message": str(e.user_message)
            }

        except stripe.error.StripeError as e:
            return {
                "success": False,
                "error": "stripe_error",
                "message": str(e)
            }

    async def create_customer(self, email: str, name: Optional[str] = None, metadata: Optional[Dict] = None) -> Dict:
        """Create Stripe customer"""
        if not settings.stripe_secret_key:
            return {
                "success": False,
                "error": "stripe_not_configured"
            }

        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=metadata or {}
            )

            return {
                "success": True,
                "customer_id": customer.id,
                "email": customer.email
            }

        except stripe.error.StripeError as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        trial_period_days: Optional[int] = None
    ) -> Dict:
        """Create Stripe subscription"""
        if not settings.stripe_secret_key:
            return {
                "success": False,
                "error": "stripe_not_configured"
            }

        try:
            subscription_params = {
                "customer": customer_id,
                "items": [{"price": price_id}]
            }

            if trial_period_days:
                subscription_params["trial_period_days"] = trial_period_days

            subscription = stripe.Subscription.create(**subscription_params)

            return {
                "success": True,
                "subscription_id": subscription.id,
                "status": subscription.status,
                "current_period_start": datetime.fromtimestamp(subscription.current_period_start).isoformat(),
                "current_period_end": datetime.fromtimestamp(subscription.current_period_end).isoformat(),
                "trial_end": datetime.fromtimestamp(subscription.trial_end).isoformat() if subscription.trial_end else None
            }

        except stripe.error.StripeError as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> Dict:
        """Cancel Stripe subscription"""
        if not settings.stripe_secret_key:
            return {
                "success": False,
                "error": "stripe_not_configured"
            }

        try:
            if at_period_end:
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
            else:
                subscription = stripe.Subscription.delete(subscription_id)

            return {
                "success": True,
                "subscription_id": subscription.id,
                "status": subscription.status,
                "canceled_at": datetime.fromtimestamp(subscription.canceled_at).isoformat() if subscription.canceled_at else None
            }

        except stripe.error.StripeError as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def create_setup_intent(self, customer_id: str) -> Dict:
        """Create SetupIntent for saving payment methods"""
        if not settings.stripe_secret_key:
            return {
                "success": False,
                "error": "stripe_not_configured"
            }

        try:
            setup_intent = stripe.SetupIntent.create(
                customer=customer_id,
                payment_method_types=["card"]
            )

            return {
                "success": True,
                "client_secret": setup_intent.client_secret,
                "id": setup_intent.id
            }

        except stripe.error.StripeError as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def refund_payment(
        self,
        transaction_id: str,
        amount: Optional[float] = None
    ) -> Dict:
        """Refund a payment"""
        if not settings.stripe_secret_key:
            return {
                "success": False,
                "error": "stripe_not_configured"
            }

        try:
            refund_params = {"payment_intent": transaction_id}
            if amount:
                refund_params["amount"] = int(amount * 100)

            refund = stripe.Refund.create(**refund_params)

            return {
                "success": True,
                "refund_id": refund.id,
                "status": refund.status,
                "amount": refund.amount / 100
            }

        except stripe.error.StripeError as e:
            return {
                "success": False,
                "error": str(e)
            }
