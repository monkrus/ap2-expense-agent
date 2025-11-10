"""
Tests for Repository Layer
Data access layer - targets 60%+ coverage
"""

import pytest
from datetime import datetime, timedelta
import json

from src.repository import (
    ExpenseRepository,
    IntentMandateRepository,
    CartMandateRepository,
    PaymentMandateRepository
)
from src.models import Expense, IntentMandate, CartMandate, PaymentMandate


class TestExpenseRepository:
    """Test expense repository"""

    @pytest.fixture
    def expense_repo(self, db_session, test_organization):
        """Create expense repository"""
        return ExpenseRepository(db_session, organization_id=test_organization.id)

    def test_create_expense(self, expense_repo, test_user, test_organization):
        """Test creating expense through repository"""
        expense_data = {
            "user_id": test_user.id,
            "organization_id": test_organization.id,
            "amount": 100.50,
            "description": "Test expense",
            "category": "OFFICE_SUPPLIES",
            "date": datetime.utcnow()
        }
        expense = expense_repo.create(expense_data)

        assert expense is not None
        assert expense.amount == 100.50
        assert expense.user_id == test_user.id

    def test_create_expense_negative_amount_fails(self, expense_repo, test_user, test_organization):
        """Test creating expense with negative amount fails"""
        expense_data = {
            "user_id": test_user.id,
            "organization_id": test_organization.id,
            "amount": -50.00,
            "description": "Invalid expense",
            "category": "OTHER",
            "date": datetime.utcnow()
        }

        with pytest.raises(ValueError, match="must be positive"):
            expense_repo.create(expense_data)

    def test_get_expense_by_id(self, expense_repo, sample_expense):
        """Test getting expense by ID"""
        expense = expense_repo.get_by_id(sample_expense.id)

        assert expense is not None
        assert expense.id == sample_expense.id

    def test_get_nonexistent_expense(self, expense_repo):
        """Test getting non-existent expense"""
        expense = expense_repo.get_by_id("nonexistent_id")

        assert expense is None

    def test_get_expenses_by_user(self, expense_repo, test_user, sample_expense):
        """Test getting expenses by user"""
        expenses = expense_repo.get_by_user_id(test_user.id)

        assert len(expenses) > 0
        assert all(e.user_id == test_user.id for e in expenses)

    def test_get_expenses_by_organization(
        self, expense_repo, test_organization, sample_expense
    ):
        """Test getting expenses by organization"""
        expenses = expense_repo.get_all()

        assert len(expenses) > 0

    def test_get_expenses_by_status(self, expense_repo, sample_expense):
        """Test getting expenses by status"""
        expenses = expense_repo.get_by_status("PENDING")

        assert len(expenses) > 0
        assert all(e.status == "PENDING" for e in expenses)

    def test_update_expense(self, expense_repo, sample_expense):
        """Test updating expense"""
        updated = expense_repo.update(
            sample_expense.id,
            {"description": "Updated description", "amount": 150.00}
        )

        assert updated.description == "Updated description"
        assert updated.amount == 150.00

    def test_delete_expense(self, expense_repo, sample_expense):
        """Test deleting expense"""
        result = expense_repo.delete(sample_expense.id)

        assert result is True

        # Verify deleted
        expense = expense_repo.get_by_id(sample_expense.id)
        assert expense is None

    def test_get_expenses_with_pagination(self, expense_repo, test_user):
        """Test getting expenses with pagination"""
        expenses = expense_repo.get_by_user_id(
            test_user.id,
            skip=0,
            limit=10
        )

        assert len(expenses) <= 10

    def test_tenant_isolation(self, db_session, test_user, test_organization, sample_expense):
        """Test that tenant isolation works"""
        # Create repository with different organization
        other_repo = ExpenseRepository(db_session, organization_id="other_org")

        # Should not see expenses from other org
        expenses = other_repo.get_all()

        # Should be empty or not contain sample_expense
        assert sample_expense.id not in [e.id for e in expenses]


class TestIntentMandateRepository:
    """Test intent mandate repository"""

    @pytest.fixture
    def intent_repo(self, db_session):
        """Create intent mandate repository"""
        return IntentMandateRepository(db_session)

    def test_create_intent_mandate(self, intent_repo, test_user):
        """Test creating intent mandate"""
        constraints = {
            "amount_max": 1000.00,
            "merchant_allowlist": ["Amazon", "Walmart"]
        }

        intent_data = {
            "user_id": test_user.id,
            "constraints": json.dumps(constraints),
            "expiration": datetime.utcnow() + timedelta(hours=24),
            "signature": "test_signature_123",
            "status": "active"
        }

        intent = intent_repo.create(intent_data)

        assert intent is not None
        assert intent.user_id == test_user.id
        assert intent.status == "active"

    def test_get_intent_by_id(self, intent_repo, db_session, test_user):
        """Test getting intent by ID"""
        # Create test intent
        intent = IntentMandate(
            id="intent_test",
            user_id=test_user.id,
            constraints="{}",
            expiration=datetime.utcnow() + timedelta(hours=24),
            signature="sig",
            status="active"
        )
        db_session.add(intent)
        db_session.commit()

        retrieved = intent_repo.get_by_id("intent_test")

        assert retrieved is not None
        assert retrieved.id == "intent_test"

    def test_get_active_intents(self, intent_repo, db_session, test_user):
        """Test getting active intents"""
        # Create active intent
        intent = IntentMandate(
            id="intent_active",
            user_id=test_user.id,
            constraints="{}",
            expiration=datetime.utcnow() + timedelta(hours=24),
            signature="sig",
            status="active"
        )
        db_session.add(intent)
        db_session.commit()

        actives = intent_repo.get_active_by_user(test_user.id)

        assert len(actives) > 0
        assert all(i.status == "active" for i in actives)

    def test_expire_old_intents(self, intent_repo, db_session, test_user):
        """Test expiring old intents"""
        # Create expired intent
        intent = IntentMandate(
            id="intent_expired",
            user_id=test_user.id,
            constraints="{}",
            expiration=datetime.utcnow() - timedelta(hours=1),
            signature="sig",
            status="active"
        )
        db_session.add(intent)
        db_session.commit()

        count = intent_repo.expire_old_intents()

        assert count >= 1

        db_session.refresh(intent)
        assert intent.status == "expired"


class TestCartMandateRepository:
    """Test cart mandate repository"""

    @pytest.fixture
    def cart_repo(self, db_session):
        """Create cart mandate repository"""
        return CartMandateRepository(db_session)

    def test_create_cart_mandate(self, cart_repo, db_session, test_user):
        """Test creating cart mandate"""
        # Create intent first
        intent = IntentMandate(
            id="intent_for_cart",
            user_id=test_user.id,
            constraints="{}",
            expiration=datetime.utcnow() + timedelta(hours=24),
            signature="sig",
            status="active"
        )
        db_session.add(intent)
        db_session.commit()

        cart_data = {
            "intent_mandate_id": "intent_for_cart",
            "items": json.dumps([{"name": "Item", "price": 50.00}]),
            "total": 50.00,
            "merchant": "Amazon",
            "timestamp": datetime.utcnow(),
            "user_signature": "user_sig",
            "status": "pending"
        }

        cart = cart_repo.create(cart_data)

        assert cart is not None
        assert cart.total == 50.00
        assert cart.merchant == "Amazon"

    def test_get_cart_by_id(self, cart_repo, db_session, test_user):
        """Test getting cart by ID"""
        # Create intent and cart
        intent = IntentMandate(
            id="intent_test",
            user_id=test_user.id,
            constraints="{}",
            expiration=datetime.utcnow() + timedelta(hours=24),
            signature="sig",
            status="active"
        )
        db_session.add(intent)

        cart = CartMandate(
            id="cart_test",
            intent_mandate_id="intent_test",
            items="[]",
            total=100.00,
            merchant="Test",
            timestamp=datetime.utcnow(),
            user_signature="sig",
            status="pending"
        )
        db_session.add(cart)
        db_session.commit()

        retrieved = cart_repo.get_by_id("cart_test")

        assert retrieved is not None
        assert retrieved.id == "cart_test"

    def test_get_carts_by_intent(self, cart_repo, db_session, test_user):
        """Test getting carts by intent mandate"""
        intent = IntentMandate(
            id="intent_multi",
            user_id=test_user.id,
            constraints="{}",
            expiration=datetime.utcnow() + timedelta(hours=24),
            signature="sig",
            status="active"
        )
        db_session.add(intent)

        cart = CartMandate(
            id="cart_for_intent",
            intent_mandate_id="intent_multi",
            items="[]",
            total=100.00,
            merchant="Test",
            timestamp=datetime.utcnow(),
            user_signature="sig",
            status="pending"
        )
        db_session.add(cart)
        db_session.commit()

        carts = cart_repo.get_by_intent_id("intent_multi")

        assert len(carts) > 0


class TestPaymentMandateRepository:
    """Test payment mandate repository"""

    @pytest.fixture
    def payment_repo(self, db_session):
        """Create payment mandate repository"""
        return PaymentMandateRepository(db_session)

    def test_create_payment_mandate(self, payment_repo, db_session, test_user):
        """Test creating payment mandate"""
        # Create intent and cart
        intent = IntentMandate(
            id="intent_pay",
            user_id=test_user.id,
            constraints="{}",
            expiration=datetime.utcnow() + timedelta(hours=24),
            signature="sig",
            status="active"
        )
        db_session.add(intent)

        cart = CartMandate(
            id="cart_pay",
            intent_mandate_id="intent_pay",
            items="[]",
            total=100.00,
            merchant="Test",
            timestamp=datetime.utcnow(),
            user_signature="sig",
            status="pending"
        )
        db_session.add(cart)
        db_session.commit()

        payment_data = {
            "cart_mandate_id": "cart_pay",
            "payment_method": "stripe",
            "status": "pending",
            "audit_trail": "{}",
            "timestamp": datetime.utcnow()
        }

        payment = payment_repo.create(payment_data)

        assert payment is not None
        assert payment.payment_method == "stripe"
        assert payment.status == "pending"

    def test_get_payment_by_id(self, payment_repo, db_session, test_user):
        """Test getting payment by ID"""
        # Create full chain
        intent = IntentMandate(
            id="intent_get",
            user_id=test_user.id,
            constraints="{}",
            expiration=datetime.utcnow() + timedelta(hours=24),
            signature="sig",
            status="active"
        )
        db_session.add(intent)

        cart = CartMandate(
            id="cart_get",
            intent_mandate_id="intent_get",
            items="[]",
            total=100.00,
            merchant="Test",
            timestamp=datetime.utcnow(),
            user_signature="sig",
            status="pending"
        )
        db_session.add(cart)

        payment = PaymentMandate(
            id="payment_test",
            cart_mandate_id="cart_get",
            payment_method="stripe",
            status="pending",
            audit_trail="{}",
            timestamp=datetime.utcnow()
        )
        db_session.add(payment)
        db_session.commit()

        retrieved = payment_repo.get_by_id("payment_test")

        assert retrieved is not None
        assert retrieved.id == "payment_test"

    def test_update_payment_status(self, payment_repo, db_session, test_user):
        """Test updating payment status"""
        # Create payment
        intent = IntentMandate(
            id="intent_update",
            user_id=test_user.id,
            constraints="{}",
            expiration=datetime.utcnow() + timedelta(hours=24),
            signature="sig",
            status="active"
        )
        db_session.add(intent)

        cart = CartMandate(
            id="cart_update",
            intent_mandate_id="intent_update",
            items="[]",
            total=100.00,
            merchant="Test",
            timestamp=datetime.utcnow(),
            user_signature="sig",
            status="pending"
        )
        db_session.add(cart)

        payment = PaymentMandate(
            id="payment_update",
            cart_mandate_id="cart_update",
            payment_method="stripe",
            status="pending",
            audit_trail="{}",
            timestamp=datetime.utcnow()
        )
        db_session.add(payment)
        db_session.commit()

        updated = payment_repo.update(
            "payment_update",
            {"status": "completed"}
        )

        assert updated.status == "completed"

    def test_get_payments_by_cart(self, payment_repo, db_session, test_user):
        """Test getting payments by cart mandate"""
        intent = IntentMandate(
            id="intent_list",
            user_id=test_user.id,
            constraints="{}",
            expiration=datetime.utcnow() + timedelta(hours=24),
            signature="sig",
            status="active"
        )
        db_session.add(intent)

        cart = CartMandate(
            id="cart_list",
            intent_mandate_id="intent_list",
            items="[]",
            total=100.00,
            merchant="Test",
            timestamp=datetime.utcnow(),
            user_signature="sig",
            status="pending"
        )
        db_session.add(cart)

        payment = PaymentMandate(
            id="payment_list",
            cart_mandate_id="cart_list",
            payment_method="stripe",
            status="pending",
            audit_trail="{}",
            timestamp=datetime.utcnow()
        )
        db_session.add(payment)
        db_session.commit()

        payments = payment_repo.get_by_cart_id("cart_list")

        assert len(payments) > 0
        assert payments[0].cart_mandate_id == "cart_list"
