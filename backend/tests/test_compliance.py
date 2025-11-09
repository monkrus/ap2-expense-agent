"""
Compliance Validation Tests for AP2 Expense Management Agent
Tests business rules, security compliance, and data integrity
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import json

from src.models import Base, Expense, ExpenseStatus, ExpenseCategory, User, UserRole
from src.models import IntentMandate, CartMandate, PaymentMandate
from src.agent_db import ExpenseManagementAgent
from src.repository import ExpenseRepository, AP2Repository


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
        id="test_user_001",
        email="test@example.com",
        username="testuser",
        hashed_password="hashed_password",
        full_name="Test User",
        role=UserRole.EMPLOYEE.name.lower(),
        is_active=True,
        is_verified=True
    )
    db.add(test_user)
    db.commit()

    yield db
    db.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def test_organization(test_db):
    """Create a test organization in the same SQLite database"""
    from src.models import Organization
    from datetime import datetime

    org = Organization(
        id="org_compliance_001",
        name="Compliance Test Organization",
        slug="compliance-test-org",
        description="Test organization for compliance testing",
        currency="USD",
        timezone="UTC",
        max_members=25,
        is_active=True,
        created_at=datetime.utcnow()
    )
    test_db.add(org)
    test_db.commit()
    test_db.refresh(org)
    return org


@pytest.fixture
def agent(test_db, test_organization):
    """Create agent with test database and organization context"""
    return ExpenseManagementAgent(db=test_db, api_key="", project_id="", organization_id=test_organization.id)


@pytest.fixture
def expense_repo(test_db, test_organization):
    """Create expense repository with organization context"""
    return ExpenseRepository(test_db, organization_id=test_organization.id)


@pytest.fixture
def ap2_repo(test_db):
    """Create AP2 repository"""
    return AP2Repository(test_db)


# ============================================================================
# EXPENSE VALIDATION TESTS
# ============================================================================

class TestExpenseCompliance:
    """Test expense submission and validation compliance"""

    def test_expense_creation_with_valid_data(self, agent):
        """Test that valid expenses are created correctly"""
        expense = agent.submit_expense(
            user_id="test_user_001",
            amount=100.50,
            vendor="Acme Corp",
            category="Travel",
            description="Business trip to conference"
        )

        assert expense['amount'] == 100.50
        assert expense['vendor'] == "Acme Corp"
        assert expense['category'] == "Travel"
        assert expense['status'] == "pending"

    def test_expense_creation_requires_positive_amount(self, expense_repo):
        """Test that expenses must have positive amounts"""
        with pytest.raises(Exception):
            expense_repo.create({
                'id': 'EXP-001',
                'user_id': 'test_user_001',
                'amount': -50.00,  # Invalid: negative amount
                'vendor': 'Vendor',
                'category': ExpenseCategory.TRAVEL,
                'description': 'Test',
                'status': ExpenseStatus.PENDING,
                'date': datetime.utcnow()
            })

    def test_expense_requires_all_mandatory_fields(self, expense_repo):
        """Test that all required fields must be provided"""
        required_fields = {
            'id': 'EXP-002',
            'user_id': 'test_user_001',
            'amount': 100.00,
            'vendor': 'Test Vendor',
            'category': ExpenseCategory.MEALS,
            'description': 'Test expense',
            'status': ExpenseStatus.PENDING,
            'date': datetime.utcnow()
        }

        # Should succeed with all fields
        expense = expense_repo.create(required_fields)
        assert expense is not None

        # Test each required field
        for field in ['user_id', 'amount', 'vendor', 'category', 'description']:
            test_data = required_fields.copy()
            test_data['id'] = f'EXP-{field}'
            del test_data[field]

            with pytest.raises(Exception):
                expense_repo.create(test_data)

    def test_expense_status_workflow(self, expense_repo):
        """Test that expense status transitions follow proper workflow"""
        # Create pending expense
        expense = expense_repo.create({
            'id': 'EXP-003',
            'user_id': 'test_user_001',
            'amount': 75.00,
            'vendor': 'Office Depot',
            'category': ExpenseCategory.OFFICE_SUPPLIES,
            'description': 'Office supplies',
            'status': ExpenseStatus.PENDING,
            'date': datetime.utcnow()
        })

        assert expense.status == ExpenseStatus.PENDING

        # Approve expense
        approved = expense_repo.approve('EXP-003', 'approver_001')
        assert approved.status == ExpenseStatus.APPROVED
        assert approved.approved_by == 'approver_001'
        assert approved.approved_at is not None

    def test_expense_rejection_requires_reason(self, expense_repo):
        """Test that rejected expenses must have a rejection reason"""
        expense = expense_repo.create({
            'id': 'EXP-004',
            'user_id': 'test_user_001',
            'amount': 500.00,
            'vendor': 'Luxury Hotel',
            'category': ExpenseCategory.TRAVEL,
            'description': 'Hotel stay',
            'status': ExpenseStatus.PENDING,
            'date': datetime.utcnow()
        })

        rejected = expense_repo.reject(
            'EXP-004',
            'approver_001',
            'Exceeds travel budget limits'
        )

        assert rejected.status == ExpenseStatus.REJECTED
        assert rejected.rejection_reason == 'Exceeds travel budget limits'
        assert rejected.approved_by == 'approver_001'

    def test_expense_category_validation(self, agent):
        """Test that expense categories are validated"""
        valid_categories = ["Travel", "Meals", "Software", "Office Supplies", "Other"]

        for category in valid_categories:
            expense = agent.submit_expense(
                user_id="test_user_001",
                amount=50.00,
                vendor="Test Vendor",
                category=category,
                description=f"Test {category} expense"
            )
            assert expense['category'] == category


# ============================================================================
# AP2 MANDATE COMPLIANCE TESTS
# ============================================================================

class TestAP2Compliance:
    """Test AP2 protocol mandate compliance"""

    def test_intent_mandate_creation(self, agent, ap2_repo):
        """Test that intent mandates are created with proper structure"""
        mandate = agent.create_intent_mandate(
            user_id="test_user_001",
            max_amount=500.00,
            category="Travel",
            merchant="Airlines Co",
            valid_days=30
        )

        assert mandate.id.startswith("intent_")
        assert mandate.user_id == "test_user_001"
        assert mandate.constraints['max_amount'] == 500.00
        assert mandate.constraints['category'] == "Travel"
        assert mandate.signature is not None  # Must be signed

        # Verify it's in database
        db_mandate = ap2_repo.intent.get_by_id(mandate.id)
        assert db_mandate is not None
        assert db_mandate.status == "active"

    def test_intent_mandate_expiration(self, agent, ap2_repo):
        """Test that intent mandates have proper expiration"""
        mandate = agent.create_intent_mandate(
            user_id="test_user_001",
            max_amount=1000.00,
            category="Software",
            valid_days=7
        )

        expiration = datetime.fromisoformat(mandate.expiration)
        timestamp = datetime.fromisoformat(mandate.timestamp)

        # Should expire approximately 7 days from creation
        expected_expiration = timestamp + timedelta(days=7)
        time_diff = abs((expiration - expected_expiration).total_seconds())
        assert time_diff < 60  # Within 1 minute

    def test_cart_mandate_total_verification(self, agent):
        """Test that cart mandates verify item totals"""
        # First create intent mandate
        intent = agent.create_intent_mandate(
            user_id="test_user_001",
            max_amount=200.00,
            category="Meals"
        )

        # Create cart mandate with matching total
        cart = agent.create_cart_mandate(
            intent_mandate_id=intent.id,
            expense_id="EXP-005",
            items=[
                {'description': 'Lunch', 'amount': 50.00, 'vendor': 'Restaurant A'},
                {'description': 'Dinner', 'amount': 75.00, 'vendor': 'Restaurant B'}
            ],
            merchant="Restaurant Group"
        )

        assert cart.verify_total() == True
        assert cart.total == 125.00

    def test_cart_mandate_requires_user_signature(self, agent):
        """Test that cart mandates must have user signatures"""
        intent = agent.create_intent_mandate(
            user_id="test_user_001",
            max_amount=100.00,
            category="Other"
        )

        cart = agent.create_cart_mandate(
            intent_mandate_id=intent.id,
            expense_id="EXP-006",
            items=[{'description': 'Item', 'amount': 50.00, 'vendor': 'Vendor'}],
            merchant="Vendor"
        )

        assert cart.user_signature is not None
        assert len(cart.user_signature) > 0

    def test_payment_mandate_audit_trail(self, agent, ap2_repo):
        """Test that payment mandates include complete audit trail"""
        # Create full AP2 flow
        intent = agent.create_intent_mandate(
            user_id="test_user_001",
            max_amount=300.00,
            category="Travel"
        )

        cart = agent.create_cart_mandate(
            intent_mandate_id=intent.id,
            expense_id="EXP-007",
            items=[{'description': 'Flight', 'amount': 250.00, 'vendor': 'Airline'}],
            merchant="Airline"
        )

        payment = agent.process_payment(cart, payment_method="corporate_card")

        # Verify payment mandate structure
        assert payment.id.startswith("payment_")
        assert payment.cart_mandate_ref == cart.id
        assert payment.status == "completed"
        assert 'intent_mandate' in payment.audit_trail
        assert 'cart_mandate' in payment.audit_trail
        assert 'verification_status' in payment.audit_trail
        assert payment.audit_trail['verification_status'] == 'verified'

        # Verify full audit trail retrieval
        audit = ap2_repo.payment.get_audit_trail(payment.id)
        assert audit['audit_trail_complete'] == True
        assert audit['intent_mandate'] is not None
        assert audit['cart_mandate'] is not None
        assert audit['payment_mandate'] is not None

    def test_mandate_relationships(self, agent, test_db):
        """Test that AP2 mandates maintain proper relationships"""
        # Create expense and process through AP2
        expense = agent.submit_expense(
            user_id="test_user_001",
            amount=150.00,
            vendor="Test Vendor",
            category="Software",
            description="Software license"
        )

        result = agent.approve_and_process_expense(
            expense_id=expense['id'],
            approver_id="approver_001"
        )

        # Verify all relationships are established
        expense_db = test_db.query(Expense).filter(
            Expense.id == expense['id']
        ).first()

        assert expense_db.intent_mandate_id is not None
        assert expense_db.cart_mandate_id is not None
        assert expense_db.payment_mandate_id is not None
        assert expense_db.transaction_id is not None

        # Verify relationships can be traversed
        assert expense_db.intent_mandate is not None
        assert expense_db.cart_mandate is not None
        assert expense_db.payment_mandate is not None


# ============================================================================
# DATA INTEGRITY TESTS
# ============================================================================

class TestDataIntegrity:
    """Test data integrity and consistency"""

    def test_expense_amount_precision(self, expense_repo):
        """Test that amounts maintain proper decimal precision"""
        expense = expense_repo.create({
            'id': 'EXP-008',
            'user_id': 'test_user_001',
            'amount': Decimal('123.456'),  # 3 decimal places
            'vendor': 'Vendor',
            'category': ExpenseCategory.OTHER,
            'description': 'Test',
            'status': ExpenseStatus.PENDING,
            'date': datetime.utcnow()
        })

        # Should be rounded/stored with 2 decimal precision
        assert float(expense.amount) == 123.46  # Rounded

    def test_expense_timestamps_auto_populate(self, expense_repo):
        """Test that timestamps are automatically populated"""
        before = datetime.utcnow().replace(microsecond=0)  # Strip microseconds for comparison

        expense = expense_repo.create({
            'id': 'EXP-009',
            'user_id': 'test_user_001',
            'amount': 50.00,
            'vendor': 'Vendor',
            'category': ExpenseCategory.MEALS,
            'description': 'Test',
            'status': ExpenseStatus.PENDING,
            'date': datetime.utcnow()
        })

        after = datetime.utcnow().replace(microsecond=0) + timedelta(seconds=1)  # Add buffer

        assert expense.created_at is not None
        # Compare with microseconds stripped since SQLite doesn't store them
        created_at_no_micro = expense.created_at.replace(microsecond=0) if expense.created_at.microsecond else expense.created_at
        assert before <= created_at_no_micro <= after

    def test_json_fields_serialize_correctly(self, ap2_repo):
        """Test that JSON fields are properly serialized/deserialized"""
        # Create intent mandate with constraints
        mandate_data = {
            'id': 'intent_test_001',
            'user_id': 'test_user_001',
            'constraints': {
                'max_amount': 500.00,
                'category': 'Travel',
                'merchant': 'Airlines',
                'frequency': 'monthly'
            },
            'timestamp': datetime.utcnow(),
            'expiration': datetime.utcnow() + timedelta(days=30),
            'signature': 'test_signature',
            'status': 'active'
        }

        mandate = ap2_repo.intent.create(mandate_data)

        # Retrieve and verify
        retrieved = ap2_repo.intent.get_by_id('intent_test_001')
        constraints = json.loads(retrieved.constraints)

        assert constraints['max_amount'] == 500.00
        assert constraints['category'] == 'Travel'
        assert constraints['merchant'] == 'Airlines'
        assert constraints['frequency'] == 'monthly'

    def test_expense_user_relationship_integrity(self, test_db, expense_repo):
        """Test that expense-user relationships maintain referential integrity"""
        # Create expense
        expense = expense_repo.create({
            'id': 'EXP-010',
            'user_id': 'test_user_001',
            'amount': 100.00,
            'vendor': 'Vendor',
            'category': ExpenseCategory.OTHER,
            'description': 'Test',
            'status': ExpenseStatus.PENDING,
            'date': datetime.utcnow()
        })

        # Verify user relationship exists
        assert expense.user is not None
        assert expense.user.id == 'test_user_001'
        assert expense.user.username == 'testuser'


# ============================================================================
# AUTHORIZATION & SECURITY TESTS
# ============================================================================

class TestAuthorizationCompliance:
    """Test authorization and security compliance"""

    def test_expense_ownership_validation(self, expense_repo):
        """Test that expenses are owned by specific users"""
        expense = expense_repo.create({
            'id': 'EXP-011',
            'user_id': 'test_user_001',
            'amount': 100.00,
            'vendor': 'Vendor',
            'category': ExpenseCategory.TRAVEL,
            'description': 'Test',
            'status': ExpenseStatus.PENDING,
            'date': datetime.utcnow()
        })

        # Verify ownership
        user_expenses = expense_repo.get_by_user('test_user_001')
        assert len(user_expenses) > 0
        assert all(e.user_id == 'test_user_001' for e in user_expenses)

    def test_mandate_signature_requirement(self, agent):
        """Test that mandates are cryptographically signed"""
        intent = agent.create_intent_mandate(
            user_id="test_user_001",
            max_amount=200.00,
            category="Meals"
        )

        # Intent mandate must have signature
        assert intent.signature is not None
        assert len(intent.signature) > 0
        # Signature should be hex-encoded
        assert all(c in '0123456789abcdef' for c in intent.signature.lower())


# Run tests with pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
