"""
Tests for AP2 Payment Service
Critical payment protocol module - targets 85%+ coverage
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

pytestmark = pytest.mark.asyncio

from src.models import CartMandate, IntentMandate, PaymentMandate, User
from src.payments.ap2_service import AP2PaymentService


class TestAP2PaymentService:
    """Test AP2 protocol payment service"""

    @pytest.fixture
    def ap2_service(self, db_session):
        """Create AP2 payment service instance"""
        return AP2PaymentService(db_session)

    @pytest.fixture
    def sample_constraints(self):
        """Sample purchase constraints"""
        return {
            "max_amount": 1000.00,
            "categories": ["office_supplies", "software"],
            "merchants": ["Amazon", "Microsoft"],
            "approval_required": True,
        }

    @pytest.fixture
    def sample_cart_items(self):
        """Sample cart items"""
        return [
            {
                "id": "exp-123",
                "description": "Office supplies",
                "amount": 45.99,
                "category": "office_supplies",
            },
            {
                "id": "exp-124",
                "description": "Software license",
                "amount": 99.99,
                "category": "software",
            },
        ]

    async def test_create_intent_mandate_success(
        self, ap2_service, test_user, sample_constraints
    ):
        """Test creating intent mandate successfully"""
        intent = await ap2_service.create_intent_mandate(
            user_id=test_user.id, constraints=sample_constraints, expiration_hours=24
        )

        assert intent is not None
        assert intent.user_id == test_user.id
        assert intent.status == "active"
        assert intent.signature is not None
        assert intent.expiration > datetime.utcnow()

        # Verify constraints are stored correctly
        stored_constraints = json.loads(intent.constraints)
        assert stored_constraints["max_amount"] == 1000.00

    async def test_create_intent_mandate_invalid_user(
        self, ap2_service, sample_constraints
    ):
        """Test creating intent mandate with invalid user"""
        with pytest.raises(ValueError, match="not found"):
            await ap2_service.create_intent_mandate(
                user_id="invalid_user_id", constraints=sample_constraints
            )

    async def test_create_intent_mandate_custom_expiration(
        self, ap2_service, test_user, sample_constraints
    ):
        """Test creating intent mandate with custom expiration"""
        intent = await ap2_service.create_intent_mandate(
            user_id=test_user.id, constraints=sample_constraints, expiration_hours=48
        )

        # Check expiration is approximately 48 hours from now
        expected_expiration = datetime.utcnow() + timedelta(hours=48)
        time_diff = abs((intent.expiration - expected_expiration).total_seconds())
        assert time_diff < 10  # Within 10 seconds

    async def test_create_cart_mandate_success(
        self, ap2_service, test_user, sample_constraints, sample_cart_items, db_session
    ):
        """Test creating cart mandate successfully"""
        # First create intent mandate
        intent = await ap2_service.create_intent_mandate(
            user_id=test_user.id, constraints=sample_constraints
        )

        # Create cart mandate
        cart = await ap2_service.create_cart_mandate(
            intent_mandate_id=intent.id,
            items=sample_cart_items,
            merchant="Amazon",
            user_signature="test_signature",
        )

        assert cart is not None
        assert cart.intent_mandate_id == intent.id
        assert cart.merchant == "Amazon"
        assert cart.status == "pending"
        assert cart.user_signature == "test_signature"
        assert float(cart.total) == 145.98  # 45.99 + 99.99

    async def test_create_cart_mandate_invalid_intent(
        self, ap2_service, sample_cart_items
    ):
        """Test creating cart mandate with invalid intent mandate"""
        with pytest.raises(ValueError, match="not found or inactive"):
            await ap2_service.create_cart_mandate(
                intent_mandate_id="invalid_intent_id",
                items=sample_cart_items,
                merchant="Amazon",
                user_signature="test_sig",
            )

    async def test_create_cart_mandate_expired_intent(
        self, ap2_service, test_user, sample_constraints, sample_cart_items, db_session
    ):
        """Test creating cart mandate with expired intent mandate"""
        # Create intent mandate with immediate expiration
        intent = await ap2_service.create_intent_mandate(
            user_id=test_user.id,
            constraints=sample_constraints,
            expiration_hours=-1,  # Expired
        )

        with pytest.raises(ValueError, match="expired"):
            await ap2_service.create_cart_mandate(
                intent_mandate_id=intent.id,
                items=sample_cart_items,
                merchant="Amazon",
                user_signature="test_sig",
            )

    async def test_create_cart_mandate_exceeds_max_amount(
        self, ap2_service, test_user, db_session
    ):
        """Test creating cart mandate that exceeds max amount constraint"""
        # Create intent mandate with low max_amount
        constraints = {"max_amount": 100.00}
        intent = await ap2_service.create_intent_mandate(
            user_id=test_user.id, constraints=constraints
        )

        # Try to create cart with amount exceeding constraint
        expensive_items = [
            {"id": "exp-1", "description": "Expensive item", "amount": 150.00}
        ]

        with pytest.raises(ValueError, match="exceeds max amount"):
            await ap2_service.create_cart_mandate(
                intent_mandate_id=intent.id,
                items=expensive_items,
                merchant="Amazon",
                user_signature="test_sig",
            )

    async def test_create_payment_mandate_success(
        self, ap2_service, test_user, sample_constraints, sample_cart_items, db_session
    ):
        """Test creating payment mandate successfully"""
        # Create intent and cart mandates first
        intent = await ap2_service.create_intent_mandate(
            user_id=test_user.id, constraints=sample_constraints
        )

        cart = await ap2_service.create_cart_mandate(
            intent_mandate_id=intent.id,
            items=sample_cart_items,
            merchant="Amazon",
            user_signature="test_sig",
        )

        # Create payment mandate
        payment = await ap2_service.create_payment_mandate(
            cart_mandate_id=cart.id, payment_method="stripe"
        )

        assert payment is not None
        assert payment.cart_mandate_id == cart.id
        assert payment.payment_method == "stripe"
        assert payment.status == "pending"

        # Verify audit trail
        audit_trail = json.loads(payment.audit_trail)
        assert audit_trail["cart_mandate_id"] == cart.id
        assert audit_trail["intent_mandate_id"] == intent.id
        assert audit_trail["total_amount"] == 145.98
        assert audit_trail["merchant"] == "Amazon"

    async def test_create_payment_mandate_invalid_cart(self, ap2_service):
        """Test creating payment mandate with invalid cart"""
        with pytest.raises(ValueError, match="not found"):
            await ap2_service.create_payment_mandate(
                cart_mandate_id="invalid_cart_id", payment_method="stripe"
            )

    async def test_create_payment_mandate_non_pending_cart(
        self, ap2_service, test_user, sample_constraints, sample_cart_items, db_session
    ):
        """Test creating payment mandate with non-pending cart"""
        # Create cart and mark it as completed
        intent = await ap2_service.create_intent_mandate(
            user_id=test_user.id, constraints=sample_constraints
        )

        cart = await ap2_service.create_cart_mandate(
            intent_mandate_id=intent.id,
            items=sample_cart_items,
            merchant="Amazon",
            user_signature="test_sig",
        )

        # Change cart status
        cart.status = "completed"
        db_session.commit()

        with pytest.raises(ValueError, match="must be pending"):
            await ap2_service.create_payment_mandate(
                cart_mandate_id=cart.id, payment_method="stripe"
            )

    @patch("src.payments.ap2_service.StripePaymentProcessor.process_payment_mandate")
    async def test_execute_payment_success(
        self,
        mock_stripe,
        ap2_service,
        test_user,
        sample_constraints,
        sample_cart_items,
        db_session,
    ):
        """Test executing payment successfully"""
        # Mock Stripe response
        mock_stripe.return_value = {
            "success": True,
            "transaction_id": "txn_123",
            "status": "succeeded",
        }

        # Create full mandate chain
        intent = await ap2_service.create_intent_mandate(
            user_id=test_user.id, constraints=sample_constraints
        )

        cart = await ap2_service.create_cart_mandate(
            intent_mandate_id=intent.id,
            items=sample_cart_items,
            merchant="Amazon",
            user_signature="test_sig",
        )

        payment = await ap2_service.create_payment_mandate(
            cart_mandate_id=cart.id, payment_method="stripe"
        )

        # Execute payment
        result = await ap2_service.execute_payment(
            payment_mandate_id=payment.id, stripe_customer_id="cus_test_123"
        )

        assert result["success"] is True
        assert result["transaction_id"] == "txn_123"
        assert result["amount"] == 145.98
        assert result["status"] == "completed"

        # Verify database updates
        db_session.refresh(payment)
        db_session.refresh(cart)
        assert payment.status == "completed"
        assert cart.status == "completed"

    @patch("src.payments.ap2_service.StripePaymentProcessor.process_payment_mandate")
    async def test_execute_payment_failure(
        self,
        mock_stripe,
        ap2_service,
        test_user,
        sample_constraints,
        sample_cart_items,
        db_session,
    ):
        """Test executing payment with failure"""
        # Mock Stripe failure response
        mock_stripe.return_value = {
            "success": False,
            "error": "card_declined",
            "message": "Card was declined",
        }

        # Create mandate chain
        intent = await ap2_service.create_intent_mandate(
            user_id=test_user.id, constraints=sample_constraints
        )

        cart = await ap2_service.create_cart_mandate(
            intent_mandate_id=intent.id,
            items=sample_cart_items,
            merchant="Amazon",
            user_signature="test_sig",
        )

        payment = await ap2_service.create_payment_mandate(
            cart_mandate_id=cart.id, payment_method="stripe"
        )

        # Execute payment
        result = await ap2_service.execute_payment(payment_mandate_id=payment.id)

        assert result["success"] is False
        assert result["error"] == "card_declined"

        # Verify statuses updated to failed
        db_session.refresh(payment)
        db_session.refresh(cart)
        assert payment.status == "failed"
        assert cart.status == "failed"

    async def test_execute_payment_invalid_mandate(self, ap2_service):
        """Test executing payment with invalid mandate"""
        with pytest.raises(ValueError, match="not found"):
            await ap2_service.execute_payment(payment_mandate_id="invalid_payment_id")

    async def test_get_mandate_status_intent(
        self, ap2_service, test_user, sample_constraints
    ):
        """Test getting intent mandate status"""
        intent = await ap2_service.create_intent_mandate(
            user_id=test_user.id, constraints=sample_constraints
        )

        status = await ap2_service.get_mandate_status(
            mandate_id=intent.id, mandate_type="intent"
        )

        assert status["id"] == intent.id
        assert status["type"] == "intent"
        assert status["status"] == "active"

    async def test_get_mandate_status_cart(
        self, ap2_service, test_user, sample_constraints, sample_cart_items
    ):
        """Test getting cart mandate status"""
        intent = await ap2_service.create_intent_mandate(
            user_id=test_user.id, constraints=sample_constraints
        )

        cart = await ap2_service.create_cart_mandate(
            intent_mandate_id=intent.id,
            items=sample_cart_items,
            merchant="Amazon",
            user_signature="test_sig",
        )

        status = await ap2_service.get_mandate_status(
            mandate_id=cart.id, mandate_type="cart"
        )

        assert status["id"] == cart.id
        assert status["type"] == "cart"
        assert status["status"] == "pending"

    async def test_get_mandate_status_invalid_type(self, ap2_service):
        """Test getting mandate status with invalid type"""
        with pytest.raises(ValueError, match="Invalid mandate type"):
            await ap2_service.get_mandate_status(
                mandate_id="some_id", mandate_type="invalid_type"
            )

    async def test_get_mandate_status_not_found(self, ap2_service):
        """Test getting non-existent mandate status"""
        with pytest.raises(ValueError, match="not found"):
            await ap2_service.get_mandate_status(
                mandate_id="nonexistent_id", mandate_type="payment"
            )

    @patch("src.payments.ap2_service.StripePaymentProcessor.process_payment_mandate")
    async def test_complete_ap2_flow_success(
        self, mock_stripe, ap2_service, test_user, sample_cart_items
    ):
        """Test complete AP2 flow from start to finish"""
        # Mock Stripe success
        mock_stripe.return_value = {
            "success": True,
            "transaction_id": "txn_full_flow_123",
            "status": "succeeded",
        }

        # Execute complete flow
        result = await ap2_service.complete_ap2_flow(
            user_id=test_user.id,
            items=sample_cart_items,
            merchant="Amazon",
            stripe_customer_id="cus_123",
        )

        assert result["ap2_flow_complete"] is True
        assert "intent_mandate_id" in result
        assert "cart_mandate_id" in result
        assert "payment_mandate_id" in result
        assert result["payment_result"]["success"] is True

    @patch("src.payments.ap2_service.StripePaymentProcessor.process_payment_mandate")
    async def test_complete_ap2_flow_with_custom_constraints(
        self, mock_stripe, ap2_service, test_user, sample_cart_items
    ):
        """Test complete AP2 flow with custom constraints"""
        mock_stripe.return_value = {
            "success": True,
            "transaction_id": "txn_custom_123",
            "status": "succeeded",
        }

        custom_constraints = {
            "max_amount": 200.00,
            "merchant": "Amazon",
            "approval_required": True,
        }

        result = await ap2_service.complete_ap2_flow(
            user_id=test_user.id,
            items=sample_cart_items,
            merchant="Amazon",
            constraints=custom_constraints,
        )

        assert result["ap2_flow_complete"] is True

    async def test_generate_signature_consistency(self, ap2_service, test_user):
        """Test that signature generation is consistent"""
        constraints = {"max_amount": 1000.00}
        timestamp = datetime.utcnow()

        sig1 = ap2_service._generate_signature(test_user.id, constraints, timestamp)
        sig2 = ap2_service._generate_signature(test_user.id, constraints, timestamp)

        # Same inputs should produce same signature
        assert sig1 == sig2

    async def test_generate_signature_different_inputs(self, ap2_service, test_user):
        """Test that different inputs produce different signatures"""
        timestamp = datetime.utcnow()

        sig1 = ap2_service._generate_signature(
            test_user.id, {"max_amount": 1000.00}, timestamp
        )

        sig2 = ap2_service._generate_signature(
            test_user.id, {"max_amount": 2000.00}, timestamp
        )

        # Different constraints should produce different signatures
        assert sig1 != sig2

    async def test_cart_total_calculation(
        self, ap2_service, test_user, sample_constraints
    ):
        """Test that cart total is calculated correctly"""
        intent = await ap2_service.create_intent_mandate(
            user_id=test_user.id, constraints=sample_constraints
        )

        items = [
            {
                "id": "1",
                "description": "Item 1",
                "amount": 10.50,
                "category": "office_supplies",
            },
            {
                "id": "2",
                "description": "Item 2",
                "amount": 20.25,
                "category": "software",
            },
            {
                "id": "3",
                "description": "Item 3",
                "amount": 5.00,
                "category": "office_supplies",
            },
        ]

        cart = await ap2_service.create_cart_mandate(
            intent_mandate_id=intent.id,
            items=items,
            merchant="Amazon",
            user_signature="test_sig",
        )

        assert float(cart.total) == 35.75  # 10.50 + 20.25 + 5.00

    async def test_empty_cart_items(self, ap2_service, test_user, sample_constraints):
        """Test creating cart with empty items list"""
        intent = await ap2_service.create_intent_mandate(
            user_id=test_user.id, constraints=sample_constraints
        )

        cart = await ap2_service.create_cart_mandate(
            intent_mandate_id=intent.id,
            items=[],
            merchant="Amazon",
            user_signature="test_sig",
        )

        assert float(cart.total) == 0.0
