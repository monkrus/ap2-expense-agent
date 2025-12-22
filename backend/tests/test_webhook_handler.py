"""
Tests for Stripe Webhook Handler
Critical payment webhook module - targets 80%+ coverage
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

pytestmark = pytest.mark.asyncio
from fastapi import HTTPException

from src.models import CartMandate, PaymentMandate
from src.payments.webhook_handler import StripeWebhookHandler


class TestStripeWebhookHandler:
    """Test Stripe webhook handler"""

    @pytest.fixture
    def webhook_handler(self, db_session):
        """Create webhook handler instance"""
        return StripeWebhookHandler(db_session)

    @pytest.fixture
    def mock_request(self):
        """Create mock FastAPI request"""
        request = Mock()
        request.body = AsyncMock(return_value=b'{"test": "data"}')
        request.headers = {"stripe-signature": "test_signature"}
        return request

    @pytest.fixture
    def payment_intent_data(self):
        """Sample payment intent data"""
        return Mock(
            id="pi_test_123",
            status="succeeded",
            amount=10000,  # $100.00 in cents
            currency="usd",
            created=1234567890,
            metadata={"ap2_payment_mandate_id": "mandate_test_123"},
            last_payment_error=None,
        )

    @patch("src.payments.webhook_handler.settings")
    async def test_handle_webhook_missing_secret(
        self, mock_settings, webhook_handler, mock_request
    ):
        """Test webhook handling without webhook secret"""
        mock_settings.stripe_webhook_secret = None

        with pytest.raises(HTTPException) as exc_info:
            await webhook_handler.handle_webhook(mock_request)

        assert exc_info.value.status_code == 500
        assert "not configured" in exc_info.value.detail

    @patch("src.payments.webhook_handler.stripe.Webhook.construct_event")
    @patch("src.payments.webhook_handler.settings")
    async def test_handle_webhook_invalid_payload(
        self, mock_settings, mock_construct, webhook_handler, mock_request
    ):
        """Test webhook with invalid payload"""
        mock_settings.stripe_webhook_secret = "test_secret"
        mock_construct.side_effect = ValueError("Invalid payload")

        with pytest.raises(HTTPException) as exc_info:
            await webhook_handler.handle_webhook(mock_request)

        assert exc_info.value.status_code == 400
        assert "Invalid payload" in exc_info.value.detail

    @patch("src.payments.webhook_handler.stripe.Webhook.construct_event")
    @patch("src.payments.webhook_handler.settings")
    async def test_handle_webhook_invalid_signature(
        self, mock_settings, mock_construct, webhook_handler, mock_request
    ):
        """Test webhook with invalid signature"""
        from stripe import _error as stripe_error

        mock_settings.stripe_webhook_secret = "test_secret"
        mock_construct.side_effect = stripe_error.SignatureVerificationError(
            "Invalid signature", "sig_header"
        )

        with pytest.raises(HTTPException) as exc_info:
            await webhook_handler.handle_webhook(mock_request)

        assert exc_info.value.status_code == 400
        assert "Invalid signature" in exc_info.value.detail

    @patch("src.payments.webhook_handler.stripe.Webhook.construct_event")
    @patch("src.payments.webhook_handler.settings")
    async def test_handle_payment_intent_succeeded(
        self,
        mock_settings,
        mock_construct,
        webhook_handler,
        mock_request,
        payment_intent_data,
        db_session,
    ):
        """Test handling successful payment intent"""
        mock_settings.stripe_webhook_secret = "test_secret"

        # Create test payment mandate
        cart_mandate = CartMandate(
            id="cart_test_123",
            intent_mandate_id="intent_test",
            items=json.dumps([]),
            total=100.00,
            merchant="Test",
            timestamp=datetime.utcnow(),
            user_signature="sig",
            status="pending",
        )
        db_session.add(cart_mandate)

        payment_mandate = PaymentMandate(
            id="mandate_test_123",
            cart_mandate_id=cart_mandate.id,
            payment_method="stripe",
            status="pending",
            audit_trail="{}",
            timestamp=datetime.utcnow(),
        )
        db_session.add(payment_mandate)
        db_session.commit()

        # Mock webhook event
        mock_event = Mock()
        mock_event.type = "payment_intent.succeeded"
        mock_event.data.object = payment_intent_data
        mock_construct.return_value = mock_event

        # Handle webhook
        result = await webhook_handler.handle_webhook(mock_request)

        assert result["status"] == "success"
        assert result["event_type"] == "payment_intent.succeeded"

        # Verify mandate status updated
        db_session.refresh(payment_mandate)
        db_session.refresh(cart_mandate)
        assert payment_mandate.status == "completed"
        assert cart_mandate.status == "completed"

    @patch("src.payments.webhook_handler.stripe.Webhook.construct_event")
    @patch("src.payments.webhook_handler.settings")
    async def test_handle_payment_intent_failed(
        self,
        mock_settings,
        mock_construct,
        webhook_handler,
        mock_request,
        payment_intent_data,
        db_session,
    ):
        """Test handling failed payment intent"""
        mock_settings.stripe_webhook_secret = "test_secret"

        # Setup failed payment data
        payment_intent_data.status = "failed"
        payment_intent_data.last_payment_error = Mock(message="Card declined")

        # Create test mandate
        cart_mandate = CartMandate(
            id="cart_fail_123",
            intent_mandate_id="intent_test",
            items=json.dumps([]),
            total=100.00,
            merchant="Test",
            timestamp=datetime.utcnow(),
            user_signature="sig",
            status="pending",
        )
        db_session.add(cart_mandate)

        payment_mandate = PaymentMandate(
            id="mandate_test_123",
            cart_mandate_id=cart_mandate.id,
            payment_method="stripe",
            status="pending",
            audit_trail="{}",
            timestamp=datetime.utcnow(),
        )
        db_session.add(payment_mandate)
        db_session.commit()

        # Mock webhook event
        mock_event = Mock()
        mock_event.type = "payment_intent.payment_failed"
        mock_event.data.object = payment_intent_data
        mock_construct.return_value = mock_event

        # Handle webhook
        result = await webhook_handler.handle_webhook(mock_request)

        assert result["status"] == "success"

        # Verify mandate status updated to failed
        db_session.refresh(payment_mandate)
        db_session.refresh(cart_mandate)
        assert payment_mandate.status == "failed"
        assert cart_mandate.status == "failed"

    @patch("src.payments.webhook_handler.stripe.Webhook.construct_event")
    @patch("src.payments.webhook_handler.settings")
    async def test_handle_unknown_event_type(
        self, mock_settings, mock_construct, webhook_handler, mock_request
    ):
        """Test handling unknown event type"""
        mock_settings.stripe_webhook_secret = "test_secret"

        # Mock webhook event with unknown type
        mock_event = Mock()
        mock_event.type = "unknown.event.type"
        mock_event.data.object = {}
        mock_construct.return_value = mock_event

        # Handle webhook - should not raise error
        result = await webhook_handler.handle_webhook(mock_request)

        assert result["status"] == "ignored"
        assert result["event_type"] == "unknown.event.type"

    @patch("src.payments.webhook_handler.stripe.Webhook.construct_event")
    @patch("src.payments.webhook_handler.settings")
    async def test_handle_payment_without_mandate(
        self,
        mock_settings,
        mock_construct,
        webhook_handler,
        mock_request,
        payment_intent_data,
    ):
        """Test handling payment for non-existent mandate"""
        mock_settings.stripe_webhook_secret = "test_secret"

        # Mock webhook event
        mock_event = Mock()
        mock_event.type = "payment_intent.succeeded"
        mock_event.data.object = payment_intent_data
        mock_construct.return_value = mock_event

        # Handle webhook - should not crash
        result = await webhook_handler.handle_webhook(mock_request)

        assert result["status"] == "success"
