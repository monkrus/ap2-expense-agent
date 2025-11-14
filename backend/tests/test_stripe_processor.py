"""
Tests for Stripe Payment Processor
Critical module - targets 80%+ coverage
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from stripe import _error as stripe_error

from src.payments.stripe_processor import StripePaymentProcessor
from src.models import PaymentMandate


@pytest.fixture
def payment_processor(db_session):
    """Create Stripe payment processor instance"""
    return StripePaymentProcessor(db_session)


@pytest.fixture
def mock_payment_mandate():
    """Create mock payment mandate"""
    mandate = Mock(spec=PaymentMandate)
    mandate.id = "payment_test_001"
    mandate.cart_mandate_id = "cart_test_001"
    mandate.timestamp = datetime.utcnow()
    mandate.status = "pending"
    return mandate


class TestStripePaymentProcessor:
    """Test Stripe payment processing"""

    @pytest.mark.asyncio
    @patch("src.payments.stripe_processor.settings")
    async def test_process_payment_without_stripe_configured(
        self, mock_settings, payment_processor, mock_payment_mandate
    ):
        """Test payment fails gracefully when Stripe is not configured"""
        mock_settings.stripe_secret_key = None

        result = await payment_processor.process_payment_mandate(
            mock_payment_mandate, 100.00
        )

        assert result["success"] is False
        assert result["error"] == "stripe_not_configured"
        assert "Stripe is not configured" in result["message"]

    @pytest.mark.asyncio
    @patch("src.payments.stripe_processor.stripe.PaymentIntent.create")
    @patch("src.payments.stripe_processor.settings")
    async def test_process_payment_success(
        self, mock_settings, mock_stripe_create, payment_processor, mock_payment_mandate
    ):
        """Test successful payment processing"""
        mock_settings.stripe_secret_key = "sk_test_123"

        # Mock successful Stripe response
        mock_payment_intent = Mock()
        mock_payment_intent.id = "pi_test_123"
        mock_payment_intent.status = "succeeded"
        mock_payment_intent.created = 1234567890
        mock_stripe_create.return_value = mock_payment_intent

        result = await payment_processor.process_payment_mandate(
            mock_payment_mandate, 100.00, currency="usd", customer_id="cus_123"
        )

        assert result["success"] is True
        assert result["transaction_id"] == "pi_test_123"
        assert result["status"] == "succeeded"
        assert result["amount"] == 100.00
        assert result["currency"] == "usd"
        assert "created" in result

        # Verify Stripe was called with correct parameters
        mock_stripe_create.assert_called_once()
        call_args = mock_stripe_create.call_args[1]
        assert call_args["amount"] == 10000  # 100.00 * 100 cents
        assert call_args["currency"] == "usd"
        assert call_args["customer"] == "cus_123"
        assert call_args["metadata"]["ap2_payment_mandate_id"] == "payment_test_001"

    @pytest.mark.asyncio
    @patch("src.payments.stripe_processor.stripe.PaymentIntent.create")
    @patch("src.payments.stripe_processor.settings")
    async def test_process_payment_card_error(
        self, mock_settings, mock_stripe_create, payment_processor, mock_payment_mandate
    ):
        """Test handling of card errors"""
        mock_settings.stripe_secret_key = "sk_test_123"

        # Mock card error from Stripe
        mock_error = stripe_error.CardError(
            "Your card was declined", param="card", code="card_declined"
        )
        mock_stripe_create.side_effect = mock_error

        result = await payment_processor.process_payment_mandate(
            mock_payment_mandate, 50.00
        )

        assert result["success"] is False
        assert result["error"] == "card_error"
        assert "declined" in result["message"].lower()

    @pytest.mark.asyncio
    @patch("src.payments.stripe_processor.stripe.PaymentIntent.create")
    @patch("src.payments.stripe_processor.settings")
    async def test_process_payment_invalid_request(
        self, mock_settings, mock_stripe_create, payment_processor, mock_payment_mandate
    ):
        """Test handling of invalid request errors"""
        mock_settings.stripe_secret_key = "sk_test_123"

        mock_error = stripe_error.InvalidRequestError(
            "Invalid currency", param="currency"
        )
        mock_stripe_create.side_effect = mock_error

        result = await payment_processor.process_payment_mandate(
            mock_payment_mandate, 75.00, currency="INVALID"
        )

        assert result["success"] is False
        assert result["error"] == "stripe_error"

    @pytest.mark.asyncio
    @patch("src.payments.stripe_processor.stripe.PaymentIntent.create")
    @patch("src.payments.stripe_processor.settings")
    async def test_process_payment_authentication_error(
        self, mock_settings, mock_stripe_create, payment_processor, mock_payment_mandate
    ):
        """Test handling of authentication errors"""
        mock_settings.stripe_secret_key = "sk_test_invalid"

        mock_error = stripe_error.AuthenticationError("Invalid API key")
        mock_stripe_create.side_effect = mock_error

        result = await payment_processor.process_payment_mandate(
            mock_payment_mandate, 25.00
        )

        assert result["success"] is False
        assert result["error"] == "stripe_error"

    @pytest.mark.asyncio
    @patch("src.payments.stripe_processor.stripe.PaymentIntent.create")
    @patch("src.payments.stripe_processor.settings")
    async def test_process_payment_api_error(
        self, mock_settings, mock_stripe_create, payment_processor, mock_payment_mandate
    ):
        """Test handling of Stripe API errors"""
        mock_settings.stripe_secret_key = "sk_test_123"

        mock_error = stripe_error.APIError("Internal server error")
        mock_stripe_create.side_effect = mock_error

        result = await payment_processor.process_payment_mandate(
            mock_payment_mandate, 150.00
        )

        assert result["success"] is False
        assert result["error"] == "stripe_error"

    @pytest.mark.asyncio
    @patch("src.payments.stripe_processor.stripe.PaymentIntent.create")
    @patch("src.payments.stripe_processor.settings")
    async def test_process_payment_rate_limit_error(
        self, mock_settings, mock_stripe_create, payment_processor, mock_payment_mandate
    ):
        """Test handling of rate limit errors"""
        mock_settings.stripe_secret_key = "sk_test_123"

        mock_error = stripe_error.RateLimitError("Too many requests")
        mock_stripe_create.side_effect = mock_error

        result = await payment_processor.process_payment_mandate(
            mock_payment_mandate, 200.00
        )

        assert result["success"] is False
        assert result["error"] == "stripe_error"

    @pytest.mark.asyncio
    @patch("src.payments.stripe_processor.stripe.PaymentIntent.create")
    @patch("src.payments.stripe_processor.settings")
    async def test_process_payment_generic_error(
        self, mock_settings, mock_stripe_create, payment_processor, mock_payment_mandate
    ):
        """Test handling of unexpected errors"""
        mock_settings.stripe_secret_key = "sk_test_123"

        mock_stripe_create.side_effect = Exception("Unexpected error")

        result = await payment_processor.process_payment_mandate(
            mock_payment_mandate, 300.00
        )

        assert result["success"] is False
        assert result["error"] == "stripe_error"

    @pytest.mark.asyncio
    @patch("src.payments.stripe_processor.stripe.PaymentIntent.create")
    @patch("src.payments.stripe_processor.settings")
    async def test_process_payment_with_metadata(
        self, mock_settings, mock_stripe_create, payment_processor, mock_payment_mandate
    ):
        """Test that AP2 metadata is correctly attached to Stripe payment"""
        mock_settings.stripe_secret_key = "sk_test_123"

        mock_payment_intent = Mock()
        mock_payment_intent.id = "pi_test_456"
        mock_payment_intent.status = "succeeded"
        mock_payment_intent.created = 1234567890
        mock_stripe_create.return_value = mock_payment_intent

        result = await payment_processor.process_payment_mandate(
            mock_payment_mandate, 100.00
        )

        # Verify metadata includes AP2 mandate information
        call_args = mock_stripe_create.call_args[1]
        metadata = call_args["metadata"]
        assert "ap2_payment_mandate_id" in metadata
        assert "ap2_cart_mandate_id" in metadata
        assert "mandate_timestamp" in metadata
        assert metadata["ap2_payment_mandate_id"] == "payment_test_001"
        assert metadata["ap2_cart_mandate_id"] == "cart_test_001"

    @pytest.mark.asyncio
    @patch("src.payments.stripe_processor.stripe.PaymentIntent.create")
    @patch("src.payments.stripe_processor.settings")
    async def test_process_payment_amount_conversion(
        self, mock_settings, mock_stripe_create, payment_processor, mock_payment_mandate
    ):
        """Test that amounts are correctly converted to cents"""
        mock_settings.stripe_secret_key = "sk_test_123"

        mock_payment_intent = Mock()
        mock_payment_intent.id = "pi_test_789"
        mock_payment_intent.status = "succeeded"
        mock_payment_intent.created = 1234567890
        mock_stripe_create.return_value = mock_payment_intent

        # Test various amounts
        test_amounts = [1.00, 99.99, 1234.56, 0.50]

        for amount in test_amounts:
            result = await payment_processor.process_payment_mandate(
                mock_payment_mandate, amount
            )

            call_args = mock_stripe_create.call_args[1]
            expected_cents = int(amount * 100)
            assert call_args["amount"] == expected_cents
