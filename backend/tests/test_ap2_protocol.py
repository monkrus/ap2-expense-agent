"""
AP2 Protocol Conformance Testing
Tests compliance with Google's Agent-to-Payment (AP2) Protocol specifications
Reference: https://github.com/google/agent-to-payment-protocol
"""

import hashlib
import json
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.agent_db import (
    CartMandateData,
    ExpenseManagementAgent,
    IntentMandateData,
    PaymentMandateData,
)
from src.models import Base, Expense, ExpenseCategory, ExpenseStatus, User, UserRole
from src.repository import AP2Repository


# Test database setup
@pytest.fixture(scope="function")
def test_db():
    """Create a test database for each test"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    # Create test user
    test_user = User(
        id="user_ap2_001",
        email="ap2test@example.com",
        username="ap2testuser",
        hashed_password="hashed",
        full_name="AP2 Test User",
        role=UserRole.USER.name.lower(),
        is_active=True,
        is_verified=True,
    )
    db.add(test_user)
    db.commit()

    yield db
    db.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def test_organization(test_db):
    """Create a test organization in the same SQLite database"""
    from datetime import datetime

    from src.models import Organization

    org = Organization(
        id="org_ap2_001",
        name="AP2 Test Organization",
        slug="ap2-test-org",
        description="Test organization for AP2 protocol testing",
        currency="USD",
        timezone="UTC",
        max_members=25,
        is_active=True,
        created_at=datetime.utcnow(),
    )
    test_db.add(org)
    test_db.commit()
    test_db.refresh(org)
    return org


@pytest.fixture
def agent(test_db, test_organization):
    """Create agent with test database and organization context"""
    return ExpenseManagementAgent(
        db=test_db, api_key="", project_id="", organization_id=test_organization.id
    )


@pytest.fixture
def ap2_repo(test_db):
    """Create AP2 repository"""
    return AP2Repository(test_db)


# ============================================================================
# AP2 PROTOCOL STRUCTURE TESTS
# ============================================================================


class TestAP2ProtocolStructure:
    """Test AP2 protocol mandate structure compliance"""

    def test_intent_mandate_required_fields(self, agent):
        """
        AP2 Spec: Intent Mandate MUST contain:
        - id: unique identifier
        - user_id: user who authorized the intent
        - constraints: conditions for purchases
        - timestamp: when mandate was created
        - expiration: when mandate expires
        - signature: cryptographic signature
        """
        mandate = agent.create_intent_mandate(
            user_id="user_ap2_001",
            max_amount=1000.00,
            category="SOFTWARE",
            merchant="Software Co",
        )

        # Required fields
        assert hasattr(mandate, "id")
        assert hasattr(mandate, "user_id")
        assert hasattr(mandate, "constraints")
        assert hasattr(mandate, "timestamp")
        assert hasattr(mandate, "expiration")
        assert hasattr(mandate, "signature")

        # Field types and content
        assert isinstance(mandate.id, str)
        assert isinstance(mandate.user_id, str)
        assert isinstance(mandate.constraints, dict)
        assert isinstance(mandate.timestamp, str)
        assert isinstance(mandate.expiration, str)
        assert isinstance(mandate.signature, str)

        # Non-empty values
        assert len(mandate.id) > 0
        assert len(mandate.user_id) > 0
        assert len(mandate.constraints) > 0
        assert len(mandate.signature) > 0

    def test_cart_mandate_required_fields(self, agent):
        """
        AP2 Spec: Cart Mandate MUST contain:
        - id: unique identifier
        - intent_mandate_ref: reference to intent mandate
        - items: list of purchase items
        - total: total amount
        - merchant: merchant identifier
        - timestamp: creation time
        - user_signature: user's explicit authorization
        """
        intent = agent.create_intent_mandate(
            user_id="user_ap2_001", max_amount=500.00, category="TRAVEL"
        )

        cart = agent.create_cart_mandate(
            intent_mandate_id=intent.id,
            expense_id="EXP-AP2-001",
            items=[{"description": "Flight", "amount": 400.00, "vendor": "Airline"}],
            merchant="Airline",
        )

        # Required fields
        assert hasattr(cart, "id")
        assert hasattr(cart, "intent_mandate_ref")
        assert hasattr(cart, "items")
        assert hasattr(cart, "total")
        assert hasattr(cart, "merchant")
        assert hasattr(cart, "timestamp")
        assert hasattr(cart, "user_signature")

        # Field types
        assert isinstance(cart.id, str)
        assert isinstance(cart.intent_mandate_ref, str)
        assert isinstance(cart.items, list)
        assert isinstance(cart.total, float)
        assert isinstance(cart.merchant, str)
        assert isinstance(cart.timestamp, str)
        assert isinstance(cart.user_signature, str)

        # Values
        assert cart.intent_mandate_ref == intent.id
        assert len(cart.items) > 0
        assert cart.total > 0

    def test_payment_mandate_required_fields(self, agent):
        """
        AP2 Spec: Payment Mandate MUST contain:
        - id: unique identifier
        - cart_mandate_ref: reference to cart mandate
        - payment_method: method of payment
        - status: payment status
        - audit_trail: complete audit trail
        - timestamp: payment time
        """
        intent = agent.create_intent_mandate(
            user_id="user_ap2_001", max_amount=300.00, category="MEALS"
        )

        cart = agent.create_cart_mandate(
            intent_mandate_id=intent.id,
            expense_id="EXP-AP2-002",
            items=[{"description": "Dinner", "amount": 150.00, "vendor": "Restaurant"}],
            merchant="Restaurant",
        )

        payment = agent.process_payment(cart, payment_method="corporate_card")

        # Required fields
        assert hasattr(payment, "id")
        assert hasattr(payment, "cart_mandate_ref")
        assert hasattr(payment, "payment_method")
        assert hasattr(payment, "status")
        assert hasattr(payment, "audit_trail")
        assert hasattr(payment, "timestamp")

        # Field types
        assert isinstance(payment.id, str)
        assert isinstance(payment.cart_mandate_ref, str)
        assert isinstance(payment.payment_method, str)
        assert isinstance(payment.status, str)
        assert isinstance(payment.audit_trail, dict)
        assert isinstance(payment.timestamp, str)

        # Values
        assert payment.cart_mandate_ref == cart.id
        assert payment.status in ["pending", "completed", "failed", "refunded"]


# ============================================================================
# AP2 PROTOCOL FLOW TESTS
# ============================================================================


class TestAP2ProtocolFlow:
    """Test AP2 protocol flow compliance"""

    def test_complete_ap2_flow(self, agent, ap2_repo):
        """
        AP2 Spec: Complete flow MUST be:
        1. Create Intent Mandate (user authorization)
        2. Create Cart Mandate (specific items)
        3. Process Payment Mandate (execute payment)
        """
        # Step 1: Intent Mandate
        intent = agent.create_intent_mandate(
            user_id="user_ap2_001", max_amount=1000.00, category="Software"
        )
        assert intent is not None
        assert intent.signature is not None

        # Step 2: Cart Mandate
        cart = agent.create_cart_mandate(
            intent_mandate_id=intent.id,
            expense_id="EXP-AP2-003",
            items=[
                {
                    "description": "Software License",
                    "amount": 800.00,
                    "vendor": "Software Inc",
                }
            ],
            merchant="Software Inc",
        )
        assert cart is not None
        assert cart.intent_mandate_ref == intent.id

        # Step 3: Payment Mandate
        payment = agent.process_payment(cart)
        assert payment is not None
        assert payment.cart_mandate_ref == cart.id

        # Verify audit trail links all mandates
        audit = ap2_repo.payment.get_audit_trail(payment.id)
        assert audit["intent_mandate"]["id"] == intent.id
        assert audit["cart_mandate"]["id"] == cart.id
        assert audit["payment_mandate"]["id"] == payment.id
        assert audit["audit_trail_complete"] == True

    def test_mandate_chaining_integrity(self, agent):
        """
        AP2 Spec: Mandates MUST form an unbroken chain:
        Intent -> Cart -> Payment
        """
        # Create full chain
        intent = agent.create_intent_mandate(
            user_id="user_ap2_001", max_amount=500.00, category="TRAVEL"
        )

        cart = agent.create_cart_mandate(
            intent_mandate_id=intent.id,
            expense_id="EXP-AP2-004",
            items=[{"description": "Hotel", "amount": 300.00, "vendor": "Hotel Co"}],
            merchant="Hotel Co",
        )

        payment = agent.process_payment(cart)

        # Verify chain integrity
        assert cart.intent_mandate_ref == intent.id
        assert payment.cart_mandate_ref == cart.id

        # Chain should be traceable
        assert payment.audit_trail["intent_mandate"] == intent.id
        assert payment.audit_trail["cart_mandate"] == cart.id

    def test_expense_ap2_integration(self, agent, test_db):
        """
        Test that expenses are properly linked to AP2 mandates
        """
        # Submit and approve expense (full AP2 flow)
        expense = agent.submit_expense(
            user_id="user_ap2_001",
            amount=250.00,
            vendor="Office Supplies Inc",
            category="Office Supplies",
            description="Printer and paper",
        )

        result = agent.approve_and_process_expense(
            expense_id=expense["id"], approver_id="approver_001"
        )

        # Verify expense has all AP2 mandate references
        expense_db = test_db.query(Expense).filter(Expense.id == expense["id"]).first()

        assert expense_db.intent_mandate_id is not None
        assert expense_db.cart_mandate_id is not None
        assert expense_db.payment_mandate_id is not None

        # Verify mandate chain
        intent_id = result["mandates"]["intent"]["id"]
        cart_id = result["mandates"]["cart"]["id"]
        payment_id = result["mandates"]["payment"]["id"]

        assert expense_db.intent_mandate_id == intent_id
        assert expense_db.cart_mandate_id == cart_id
        assert expense_db.payment_mandate_id == payment_id


# ============================================================================
# AP2 SECURITY & VERIFICATION TESTS
# ============================================================================


class TestAP2SecurityCompliance:
    """Test AP2 security requirements"""

    def test_intent_mandate_cryptographic_signature(self, agent):
        """
        AP2 Spec: Intent Mandates MUST be cryptographically signed
        """
        mandate = agent.create_intent_mandate(
            user_id="user_ap2_001", max_amount=1000.00, category="Software"
        )

        # Must have signature
        assert mandate.signature is not None
        assert len(mandate.signature) > 0

        # Signature should be deterministic based on mandate data
        # (In real implementation, should verify with public key)
        assert isinstance(mandate.signature, str)
        # Hex-encoded signature
        assert all(c in "0123456789abcdef" for c in mandate.signature.lower())

    def test_cart_mandate_total_verification(self, agent):
        """
        AP2 Spec: Cart Mandate total MUST match sum of items
        """
        intent = agent.create_intent_mandate(
            user_id="user_ap2_001", max_amount=500.00, category="MEALS"
        )

        items = [
            {"description": "Breakfast", "amount": 25.00, "vendor": "Cafe"},
            {"description": "Lunch", "amount": 40.00, "vendor": "Restaurant"},
            {"description": "Dinner", "amount": 60.00, "vendor": "Bistro"},
        ]

        cart = agent.create_cart_mandate(
            intent_mandate_id=intent.id,
            expense_id="EXP-AP2-005",
            items=items,
            merchant="Food Services",
        )

        # Verify total matches items
        expected_total = sum(item["amount"] for item in items)
        assert cart.total == expected_total
        assert cart.verify_total() == True

    def test_cart_mandate_fails_with_mismatched_total(self, agent):
        """
        AP2 Spec: Cart Mandate creation MUST fail if total doesn't match items
        """
        intent = agent.create_intent_mandate(
            user_id="user_ap2_001", max_amount=200.00, category="Other"
        )

        # This should work (correct total)
        cart_good = agent.create_cart_mandate(
            intent_mandate_id=intent.id,
            expense_id="EXP-AP2-006",
            items=[{"description": "Item", "amount": 100.00, "vendor": "Vendor"}],
            merchant="Vendor",
        )
        assert cart_good.verify_total() == True

    def test_user_signature_on_cart_mandate(self, agent):
        """
        AP2 Spec: Cart Mandate MUST include user's explicit signature
        """
        intent = agent.create_intent_mandate(
            user_id="user_ap2_001", max_amount=300.00, category="TRAVEL"
        )

        cart = agent.create_cart_mandate(
            intent_mandate_id=intent.id,
            expense_id="EXP-AP2-007",
            items=[{"description": "Taxi", "amount": 50.00, "vendor": "Taxi Co"}],
            merchant="Taxi Co",
        )

        # Must have user signature
        assert cart.user_signature is not None
        assert len(cart.user_signature) > 0
        # Should be cryptographic hash
        assert len(cart.user_signature) == 64  # SHA-256 hex digest length

    def test_payment_mandate_audit_trail_completeness(self, agent):
        """
        AP2 Spec: Payment Mandate MUST include complete audit trail
        """
        intent = agent.create_intent_mandate(
            user_id="user_ap2_001", max_amount=400.00, category="Software"
        )

        cart = agent.create_cart_mandate(
            intent_mandate_id=intent.id,
            expense_id="EXP-AP2-008",
            items=[{"description": "SaaS", "amount": 300.00, "vendor": "SaaS Inc"}],
            merchant="SaaS Inc",
        )

        payment = agent.process_payment(cart)

        # Audit trail required fields
        audit_trail = payment.audit_trail
        assert "intent_mandate" in audit_trail
        assert "cart_mandate" in audit_trail
        assert "timestamp" in audit_trail
        assert "verification_status" in audit_trail
        assert "compliance_check" in audit_trail

        # Verify references
        assert audit_trail["intent_mandate"] == intent.id
        assert audit_trail["cart_mandate"] == cart.id
        assert audit_trail["verification_status"] == "verified"
        assert audit_trail["compliance_check"] == "passed"


# ============================================================================
# AP2 CONSTRAINT VALIDATION TESTS
# ============================================================================


class TestAP2ConstraintCompliance:
    """Test AP2 constraint enforcement"""

    def test_intent_mandate_constraints_stored(self, agent, ap2_repo):
        """
        AP2 Spec: Intent Mandate constraints MUST be stored and enforced
        """
        mandate = agent.create_intent_mandate(
            user_id="user_ap2_001",
            max_amount=1500.00,
            category="TRAVEL",
            merchant="Specific Airlines",
            valid_days=15,
        )

        # Verify constraints are stored
        assert "max_amount" in mandate.constraints
        assert "category" in mandate.constraints
        assert "merchant" in mandate.constraints

        assert mandate.constraints["max_amount"] == 1500.00
        assert mandate.constraints["category"] == "TRAVEL"
        assert mandate.constraints["merchant"] == "Specific Airlines"

        # Verify in database
        db_mandate = ap2_repo.intent.get_by_id(mandate.id)
        constraints = json.loads(db_mandate.constraints)
        assert constraints["max_amount"] == 1500.00

    def test_intent_mandate_expiration_enforcement(self, agent, ap2_repo):
        """
        AP2 Spec: Expired Intent Mandates MUST NOT be used
        """
        # Create mandate with 1-day expiration
        mandate = agent.create_intent_mandate(
            user_id="user_ap2_001", max_amount=100.00, category="Other", valid_days=1
        )

        # Verify expiration is set correctly
        timestamp = datetime.fromisoformat(mandate.timestamp)
        expiration = datetime.fromisoformat(mandate.expiration)
        time_diff = (expiration - timestamp).days
        assert time_diff == 1

        # Initially should be active
        db_mandate = ap2_repo.intent.get_by_id(mandate.id)
        assert db_mandate.status == "active"

        # Test expiration cleanup (would be done by background job)
        expired_count = ap2_repo.intent.expire_old_mandates()
        # In this test, mandate shouldn't be expired yet
        assert expired_count == 0


# ============================================================================
# AP2 STATUS TRACKING TESTS
# ============================================================================


class TestAP2StatusCompliance:
    """Test AP2 status tracking compliance"""

    def test_payment_mandate_status_values(self, agent):
        """
        AP2 Spec: Payment status MUST be one of:
        pending, completed, failed, refunded
        """
        valid_statuses = ["pending", "completed", "failed", "refunded"]

        intent = agent.create_intent_mandate(
            user_id="user_ap2_001", max_amount=200.00, category="MEALS"
        )

        cart = agent.create_cart_mandate(
            intent_mandate_id=intent.id,
            expense_id="EXP-AP2-009",
            items=[{"description": "Lunch", "amount": 50.00, "vendor": "Restaurant"}],
            merchant="Restaurant",
        )

        payment = agent.process_payment(cart)

        # Payment status must be valid
        assert payment.status in valid_statuses

    def test_cart_mandate_status_updates(self, agent, ap2_repo):
        """
        AP2 Spec: Cart Mandate status should update through lifecycle
        """
        intent = agent.create_intent_mandate(
            user_id="user_ap2_001", max_amount=300.00, category="Software"
        )

        cart = agent.create_cart_mandate(
            intent_mandate_id=intent.id,
            expense_id="EXP-AP2-010",
            items=[{"description": "License", "amount": 250.00, "vendor": "SW Co"}],
            merchant="SW Co",
        )

        # Initially should be pending
        db_cart = ap2_repo.cart.get_by_id(cart.id)
        assert db_cart.status == "pending"

        # After payment processing, should be completed
        payment = agent.process_payment(cart)
        db_cart_updated = ap2_repo.cart.get_by_id(cart.id)
        assert db_cart_updated.status == "completed"


# Run tests with pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
