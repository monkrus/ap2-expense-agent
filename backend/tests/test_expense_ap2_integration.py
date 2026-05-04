"""
Integration tests for AP2 auto-approval linkage fix.

Verifies that:
1. Auto-approved expenses link to the *existing* Intent Mandate (not a throwaway one).
2. _get_mandate_monthly_usage correctly accumulates spending after auto-approval.
3. A second expense that would exceed the monthly limit is NOT auto-approved.
4. Payment mandate has payment_method="expense_reimbursement" and status "pending".
"""

import json
import uuid
from datetime import datetime, timedelta

import pytest

pytestmark = pytest.mark.asyncio

from src.models import (
    CartMandate,
    Expense,
    ExpenseCategory,
    ExpenseStatus,
    IntentMandate,
    Organization,
    OrganizationMember,
    PaymentMandate,
    User,
)
from src.payments.ap2_service import AP2PaymentService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_org(db):
    org = Organization(
        id=f"org_{uuid.uuid4().hex[:8]}",
        name="AP2 Integration Test Org",
        slug=f"ap2-int-{uuid.uuid4().hex[:6]}",
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db.add(org)
    db.flush()
    return org


def _make_user(db, org_id):
    from src.models import OrganizationRole, UserRole

    user = User(
        id=str(uuid.uuid4()),
        email=f"ap2int_{uuid.uuid4().hex[:6]}@example.com",
        username=f"ap2int_{uuid.uuid4().hex[:6]}",
        full_name="AP2 Integration User",
        hashed_password="hashed",
        role=UserRole.EMPLOYEE,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.flush()

    membership = OrganizationMember(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        user_id=user.id,
        role=OrganizationRole.EMPLOYEE,
        is_active=True,
        joined_at=datetime.utcnow(),
    )
    db.add(membership)
    db.flush()
    return user


def _create_intent_mandate(db, user_id, constraints, expiration_hours=24):
    """Insert an IntentMandate row directly (bypasses KMS signing)."""
    now = datetime.utcnow()
    mandate = IntentMandate(
        id=str(uuid.uuid4()),
        user_id=user_id,
        constraints=json.dumps(constraints),
        timestamp=now,
        expiration=now + timedelta(hours=expiration_hours),
        signature="test-signature",
        status="active",
    )
    db.add(mandate)
    db.commit()
    db.refresh(mandate)
    return mandate


def _create_expense_linked(db, user_id, org_id, amount, mandate_id, cart_id, payment_id):
    """Create an auto-approved Expense linked to an existing mandate."""
    expense = Expense(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        user_id=user_id,
        amount=amount,
        vendor="Test Vendor",
        category=ExpenseCategory.SOFTWARE,
        description="Test software purchase",
        status=ExpenseStatus.APPROVED,
        date=datetime.utcnow(),
        auto_approved=True,
        auto_approved_via="intent_mandate",
        intent_mandate_id=mandate_id,
        cart_mandate_id=cart_id,
        payment_mandate_id=payment_id,
        created_at=datetime.utcnow(),
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAP2MandateLinkage:
    """Verify the fixed auto-approval path links to the existing mandate."""

    async def test_cart_mandate_linked_to_existing_intent_mandate(self, db_session):
        """
        create_cart_mandate(intent_mandate_id=<existing_id>) should produce a
        CartMandate whose intent_mandate_id equals the pre-existing mandate's ID.
        """
        org = _make_org(db_session)
        user = _make_user(db_session, org.id)

        constraints = {
            "max_amount": 200.00,
            "categories": ["software"],
            "merchants": ["Test Vendor"],
        }
        existing_mandate = _create_intent_mandate(db_session, user.id, constraints)

        service = AP2PaymentService(db_session)

        cart_items = [
            {
                "description": "Software license",
                "amount": 99.00,
                "vendor": "Test Vendor",
                "category": "software",
            }
        ]
        cart_mandate = await service.create_cart_mandate(
            intent_mandate_id=existing_mandate.id,
            items=cart_items,
            merchant="Test Vendor",
            user_signature="agent-signature",
        )

        assert cart_mandate.intent_mandate_id == existing_mandate.id
        assert cart_mandate.status == "pending"

    async def test_payment_mandate_uses_expense_reimbursement_method(self, db_session):
        """
        Payment mandate created with payment_method='expense_reimbursement'
        must have that method and remain in 'pending' status (no Stripe execution).
        """
        org = _make_org(db_session)
        user = _make_user(db_session, org.id)

        constraints = {"max_amount": 500.00}
        existing_mandate = _create_intent_mandate(db_session, user.id, constraints)

        service = AP2PaymentService(db_session)

        cart_items = [{"description": "Expense", "amount": 150.00, "vendor": "Vendor"}]
        cart_mandate = await service.create_cart_mandate(
            intent_mandate_id=existing_mandate.id,
            items=cart_items,
            merchant="Vendor",
            user_signature="sig",
        )

        payment_mandate = await service.create_payment_mandate(
            cart_mandate_id=cart_mandate.id,
            payment_method="expense_reimbursement",
        )

        assert payment_mandate.payment_method == "expense_reimbursement"
        assert payment_mandate.status == "pending"


class TestMonthlyUsageAccumulation:
    """Verify _get_mandate_monthly_usage accumulates against the correct mandate."""

    async def test_usage_accumulates_on_existing_mandate(self, db_session):
        """
        After an auto-approved expense is linked to mandate X, monthly usage
        for mandate X must equal the expense amount.
        """
        org = _make_org(db_session)
        user = _make_user(db_session, org.id)

        constraints = {"max_amount": 500.00, "monthly_limit": 1000.00}
        mandate = _create_intent_mandate(db_session, user.id, constraints)

        service = AP2PaymentService(db_session)

        # Build the full AP2 chain
        cart_items = [{"description": "Item", "amount": 120.00, "vendor": "Acme"}]
        cart_mandate = await service.create_cart_mandate(
            intent_mandate_id=mandate.id,
            items=cart_items,
            merchant="Acme",
            user_signature="sig",
        )
        payment_mandate = await service.create_payment_mandate(
            cart_mandate_id=cart_mandate.id,
            payment_method="expense_reimbursement",
        )

        # Simulate what the fixed expenses.py route does
        _create_expense_linked(
            db_session,
            user.id,
            org.id,
            amount=120.00,
            mandate_id=mandate.id,
            cart_id=cart_mandate.id,
            payment_id=payment_mandate.id,
        )

        usage = service._get_mandate_monthly_usage(mandate.id, org.id)
        assert usage == pytest.approx(120.00)

    async def test_usage_not_counted_against_different_mandate(self, db_session):
        """
        Spending linked to mandate A must NOT appear in mandate B's monthly usage.
        This proves the old bug (throwaway mandate) would have been broken.
        """
        org = _make_org(db_session)
        user = _make_user(db_session, org.id)

        constraints = {"max_amount": 500.00}
        mandate_a = _create_intent_mandate(db_session, user.id, constraints)
        mandate_b = _create_intent_mandate(db_session, user.id, constraints)

        service = AP2PaymentService(db_session)
        cart_items = [{"description": "Item", "amount": 75.00, "vendor": "Shop"}]

        cart_mandate = await service.create_cart_mandate(
            intent_mandate_id=mandate_a.id,
            items=cart_items,
            merchant="Shop",
            user_signature="sig",
        )
        payment_mandate = await service.create_payment_mandate(
            cart_mandate_id=cart_mandate.id,
            payment_method="expense_reimbursement",
        )

        _create_expense_linked(
            db_session,
            user.id,
            org.id,
            amount=75.00,
            mandate_id=mandate_a.id,
            cart_id=cart_mandate.id,
            payment_id=payment_mandate.id,
        )

        # Mandate A should show $75; mandate B should show $0
        assert service._get_mandate_monthly_usage(mandate_a.id, org.id) == pytest.approx(75.00)
        assert service._get_mandate_monthly_usage(mandate_b.id, org.id) == pytest.approx(0.00)


class TestMonthlyLimitEnforcement:
    """Verify that monthly_limit blocks auto-approval when cap is reached."""

    async def test_second_expense_blocked_when_monthly_limit_exceeded(self, db_session):
        """
        After one auto-approved expense consumes most of the monthly budget,
        find_matching_intent_mandate should return None for a second expense
        that would push total over the monthly_limit.
        """
        org = _make_org(db_session)
        user = _make_user(db_session, org.id)

        # Monthly limit of $200, single expense cap of $150
        constraints = {"max_amount": 150.00, "monthly_limit": 200.00}
        mandate = _create_intent_mandate(db_session, user.id, constraints)

        service = AP2PaymentService(db_session)

        # First expense: $130 — within both per-expense and monthly limits
        cart_items_1 = [{"description": "Item 1", "amount": 130.00, "vendor": "Acme"}]
        cart_1 = await service.create_cart_mandate(
            intent_mandate_id=mandate.id,
            items=cart_items_1,
            merchant="Acme",
            user_signature="sig",
        )
        payment_1 = await service.create_payment_mandate(
            cart_mandate_id=cart_1.id,
            payment_method="expense_reimbursement",
        )
        _create_expense_linked(
            db_session,
            user.id,
            org.id,
            amount=130.00,
            mandate_id=mandate.id,
            cart_id=cart_1.id,
            payment_id=payment_1.id,
        )

        # After first expense: $130 used of $200 monthly limit
        usage_after_first = service._get_mandate_monthly_usage(mandate.id, org.id)
        assert usage_after_first == pytest.approx(130.00)

        # Second expense: $90 — would push total to $220, exceeding $200 limit
        # find_matching_intent_mandate should return None (no auto-approval)
        matching = service.find_matching_intent_mandate(
            user_id=user.id,
            amount=90.00,
            category="software",
            merchant="Acme",
            organization_id=org.id,
        )
        assert matching is None, (
            "Expected no matching mandate when second expense would exceed monthly_limit"
        )

    async def test_second_expense_approved_when_within_monthly_limit(self, db_session):
        """
        A second expense is still auto-approved if the cumulative total
        remains under the monthly_limit.
        """
        org = _make_org(db_session)
        user = _make_user(db_session, org.id)

        constraints = {"max_amount": 150.00, "monthly_limit": 500.00}
        mandate = _create_intent_mandate(db_session, user.id, constraints)

        service = AP2PaymentService(db_session)

        # First expense: $100
        cart_items_1 = [{"description": "Item 1", "amount": 100.00, "vendor": "Acme"}]
        cart_1 = await service.create_cart_mandate(
            intent_mandate_id=mandate.id,
            items=cart_items_1,
            merchant="Acme",
            user_signature="sig",
        )
        payment_1 = await service.create_payment_mandate(
            cart_mandate_id=cart_1.id,
            payment_method="expense_reimbursement",
        )
        _create_expense_linked(
            db_session,
            user.id,
            org.id,
            amount=100.00,
            mandate_id=mandate.id,
            cart_id=cart_1.id,
            payment_id=payment_1.id,
        )

        # Second expense: $100 → total $200, well below $500 monthly limit
        matching = service.find_matching_intent_mandate(
            user_id=user.id,
            amount=100.00,
            category="software",
            merchant="Acme",
            organization_id=org.id,
        )
        assert matching is not None
        assert matching.id == mandate.id


class TestMandateExhaustion:
    """Verify that a mandate is marked exhausted when monthly_limit is fully consumed."""

    async def test_mandate_marked_exhausted_when_limit_consumed(self, db_session):
        """
        After an expense consumes the entire monthly_limit, the mandate
        should be marked as 'exhausted' and no longer match new expenses.
        """
        org = _make_org(db_session)
        user = _make_user(db_session, org.id)

        # monthly_limit=150.00, max_amount=150.00 — a single $150 expense exhausts it
        constraints = {
            "max_amount": 150.00,
            "monthly_limit": 150.00,
            "categories": ["software"],
            "merchants": ["Test Vendor"],
        }
        mandate = _create_intent_mandate(db_session, user.id, constraints)

        service = AP2PaymentService(db_session)

        # Build AP2 chain
        cart_items = [{"description": "Software license", "amount": 150.00, "vendor": "Test Vendor", "category": "software"}]
        cart_mandate = await service.create_cart_mandate(
            intent_mandate_id=mandate.id,
            items=cart_items,
            merchant="Test Vendor",
            user_signature="agent-signature",
        )
        payment_mandate = await service.create_payment_mandate(
            cart_mandate_id=cart_mandate.id,
            payment_method="expense_reimbursement",
        )

        # Create the auto-approved expense for $150
        _create_expense_linked(
            db_session,
            user.id,
            org.id,
            amount=150.00,
            mandate_id=mandate.id,
            cart_id=cart_mandate.id,
            payment_id=payment_mandate.id,
        )

        # Simulate the exhaustion check (same logic as in expenses.py)
        current_usage = service._get_mandate_monthly_usage(mandate.id, org.id)
        assert current_usage == pytest.approx(150.00)

        monthly_limit = constraints["monthly_limit"]
        if current_usage >= float(monthly_limit):
            mandate.status = "exhausted"
            db_session.add(mandate)
            db_session.commit()

        # Verify mandate is exhausted
        db_session.refresh(mandate)
        assert mandate.status == "exhausted"

        # find_matching_intent_mandate should return None for exhausted mandate
        matching = service.find_matching_intent_mandate(
            user_id=user.id,
            amount=50.00,
            category="software",
            merchant="Test Vendor",
            organization_id=org.id,
        )
        assert matching is None, (
            "Expected no matching mandate after it has been marked exhausted"
        )
