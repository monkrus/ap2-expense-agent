"""
Stripe Payment Integration
Production-ready Stripe integration for payment processing
"""

import stripe
import os
from typing import Optional, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Initialize Stripe API key
stripe.api_key = os.getenv("STRIPE_API_KEY")


class StripeIntegration:
    """Stripe payment processing service"""

    @staticmethod
    def create_customer(
        email: str,
        name: str,
        metadata: Optional[Dict] = None
    ) -> stripe.Customer:
        """
        Create a new Stripe customer

        Args:
            email: Customer email address
            name: Customer full name
            metadata: Optional metadata dictionary

        Returns:
            stripe.Customer object
        """
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=metadata or {}
            )
            logger.info(f"Created Stripe customer: {customer.id} for {email}")
            return customer
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer: {str(e)}")
            raise

    @staticmethod
    def create_subscription(
        customer_id: str,
        price_id: str,
        trial_days: int = 0,
        metadata: Optional[Dict] = None
    ) -> stripe.Subscription:
        """
        Create a subscription for a customer

        Args:
            customer_id: Stripe customer ID
            price_id: Stripe price ID
            trial_days: Number of trial days (default 0)
            metadata: Optional metadata dictionary

        Returns:
            stripe.Subscription object
        """
        try:
            params = {
                "customer": customer_id,
                "items": [{"price": price_id}],
                "expand": ["latest_invoice.payment_intent"],
                "metadata": metadata or {}
            }

            if trial_days > 0:
                params["trial_period_days"] = trial_days

            subscription = stripe.Subscription.create(**params)
            logger.info(f"Created subscription: {subscription.id} for customer: {customer_id}")
            return subscription
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create subscription: {str(e)}")
            raise

    @staticmethod
    def create_checkout_session(
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        metadata: Optional[Dict] = None
    ) -> stripe.checkout.Session:
        """
        Create a Stripe Checkout session for subscription

        Args:
            customer_id: Stripe customer ID
            price_id: Stripe price ID
            success_url: URL to redirect on success
            cancel_url: URL to redirect on cancel
            metadata: Optional metadata dictionary

        Returns:
            stripe.checkout.Session object
        """
        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                line_items=[{"price": price_id, "quantity": 1}],
                mode="subscription",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata or {}
            )
            logger.info(f"Created checkout session: {session.id}")
            return session
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create checkout session: {str(e)}")
            raise

    @staticmethod
    def create_portal_session(
        customer_id: str,
        return_url: str
    ) -> stripe.billing_portal.Session:
        """
        Create a customer portal session for subscription management

        Args:
            customer_id: Stripe customer ID
            return_url: URL to return to after portal session

        Returns:
            stripe.billing_portal.Session object
        """
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url
            )
            logger.info(f"Created portal session for customer: {customer_id}")
            return session
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create portal session: {str(e)}")
            raise

    @staticmethod
    def cancel_subscription(subscription_id: str) -> stripe.Subscription:
        """
        Cancel a subscription immediately

        Args:
            subscription_id: Stripe subscription ID

        Returns:
            stripe.Subscription object
        """
        try:
            subscription = stripe.Subscription.delete(subscription_id)
            logger.info(f"Cancelled subscription: {subscription_id}")
            return subscription
        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel subscription: {str(e)}")
            raise

    @staticmethod
    def update_subscription(
        subscription_id: str,
        price_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> stripe.Subscription:
        """
        Update an existing subscription

        Args:
            subscription_id: Stripe subscription ID
            price_id: Optional new price ID
            metadata: Optional metadata to update

        Returns:
            stripe.Subscription object
        """
        try:
            params = {}

            if price_id:
                subscription = stripe.Subscription.retrieve(subscription_id)
                params["items"] = [{
                    "id": subscription["items"]["data"][0].id,
                    "price": price_id
                }]

            if metadata:
                params["metadata"] = metadata

            subscription = stripe.Subscription.modify(subscription_id, **params)
            logger.info(f"Updated subscription: {subscription_id}")
            return subscription
        except stripe.error.StripeError as e:
            logger.error(f"Failed to update subscription: {str(e)}")
            raise

    @staticmethod
    def retrieve_customer(customer_id: str) -> stripe.Customer:
        """
        Retrieve customer details

        Args:
            customer_id: Stripe customer ID

        Returns:
            stripe.Customer object
        """
        try:
            return stripe.Customer.retrieve(customer_id)
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve customer: {str(e)}")
            raise

    @staticmethod
    def retrieve_subscription(subscription_id: str) -> stripe.Subscription:
        """
        Retrieve subscription details

        Args:
            subscription_id: Stripe subscription ID

        Returns:
            stripe.Subscription object
        """
        try:
            return stripe.Subscription.retrieve(subscription_id)
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve subscription: {str(e)}")
            raise

    @staticmethod
    def verify_webhook(payload: bytes, sig_header: str) -> stripe.Event:
        """
        Verify Stripe webhook signature and construct event

        Args:
            payload: Raw request payload
            sig_header: Stripe signature header

        Returns:
            stripe.Event object

        Raises:
            ValueError: If signature verification fails
        """
        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        if not webhook_secret:
            raise ValueError("STRIPE_WEBHOOK_SECRET not configured")

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
            logger.info(f"Verified webhook event: {event['type']}")
            return event
        except ValueError as e:
            logger.error(f"Invalid webhook payload: {str(e)}")
            raise
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {str(e)}")
            raise

    @staticmethod
    def list_prices(active: bool = True) -> stripe.ListObject:
        """
        List available prices

        Args:
            active: Only return active prices (default True)

        Returns:
            stripe.ListObject of prices
        """
        try:
            return stripe.Price.list(active=active)
        except stripe.error.StripeError as e:
            logger.error(f"Failed to list prices: {str(e)}")
            raise

    @staticmethod
    def create_payment_intent(
        amount: int,
        currency: str,
        customer_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> stripe.PaymentIntent:
        """
        Create a payment intent for one-time payments

        Args:
            amount: Amount in cents
            currency: Currency code (e.g., 'usd')
            customer_id: Optional Stripe customer ID
            metadata: Optional metadata dictionary

        Returns:
            stripe.PaymentIntent object
        """
        try:
            params = {
                "amount": amount,
                "currency": currency,
                "metadata": metadata or {}
            }

            if customer_id:
                params["customer"] = customer_id

            payment_intent = stripe.PaymentIntent.create(**params)
            logger.info(f"Created payment intent: {payment_intent.id}")
            return payment_intent
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create payment intent: {str(e)}")
            raise
