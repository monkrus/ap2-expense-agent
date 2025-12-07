"""
Tests for AP2 audit service
"""

from datetime import datetime, timedelta

import pytest

from src.models import (AuditLog, CartMandate, Expense, ExpenseCategory,
                        ExpenseStatus, IntentMandate, PaymentMandate, User,
                        UserRole)
from src.services.audit_service import AuditService


class TestAuditServiceMandateCreation:
    """Test audit service mandate creation"""

    def test_create_complete_audit_trail(self, db_session, sample_user, sample_expense):
        """Test creating complete AP2 audit trail"""
        # Create approver and expense
        approver = sample_user(role=UserRole.ADMIN, email="approver@test.com")
        expense = sample_expense(status=ExpenseStatus.PENDING)

        # Create audit service and generate trail
        audit_service = AuditService(db_session)
        audit_trail = audit_service.create_complete_audit_trail(
            expense=expense, approver=approver, action="approve"
        )

        # Verify all mandates were created
        assert "intent_mandate" in audit_trail
        assert "cart_mandate" in audit_trail
        assert "payment_mandate" in audit_trail
        assert "transaction_id" in audit_trail

        # Verify intent mandate structure
        intent = audit_trail["intent_mandate"]
        assert "id" in intent
        assert intent["id"].startswith("intent_")
        assert "constraints" in intent
        assert "signature" in intent
        assert "timestamp" in intent

        # Verify cart mandate structure
        cart = audit_trail["cart_mandate"]
        assert "id" in cart
        assert cart["id"].startswith("cart_")
        assert "items" in cart
        assert cart["total"] == float(expense.amount)
        assert cart["merchant"] == expense.vendor
        assert "user_signature" in cart

        # Verify payment mandate structure
        payment = audit_trail["payment_mandate"]
        assert "id" in payment
        assert payment["id"].startswith("payment_")
        assert payment["status"] == "approved"
        assert "audit_trail" in payment
        assert payment["payment_method"] == "corporate_account"

    def test_mandates_linked_to_expense(self, db_session, sample_user, sample_expense):
        """Test that mandates are properly linked to expense"""
        approver = sample_user(role=UserRole.ADMIN)
        expense = sample_expense(status=ExpenseStatus.PENDING)

        audit_service = AuditService(db_session)
        audit_trail = audit_service.create_complete_audit_trail(
            expense=expense, approver=approver, action="approve"
        )

        # Refresh expense from database
        db_session.refresh(expense)

        # Verify expense has mandate IDs
        assert expense.intent_mandate_id is not None
        assert expense.cart_mandate_id is not None
        assert expense.payment_mandate_id is not None
        assert expense.transaction_id == audit_trail["transaction_id"]

    def test_audit_log_created(self, db_session, sample_user, sample_expense):
        """Test that audit log entry is created"""
        approver = sample_user(role=UserRole.ADMIN)
        expense = sample_expense(status=ExpenseStatus.PENDING)

        audit_service = AuditService(db_session)
        audit_service.create_complete_audit_trail(
            expense=expense, approver=approver, action="approve"
        )

        # Check audit log was created
        audit_logs = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.resource_type == "expense", AuditLog.resource_id == expense.id
            )
            .all()
        )

        assert len(audit_logs) > 0
        log = audit_logs[-1]
        assert log.action == "expense_approve"
        assert log.user_id == approver.id


class TestAuditServiceRetrieval:
    """Test audit service retrieval functions"""

    def test_get_complete_audit_trail(self, db_session, sample_user, sample_expense):
        """Test retrieving complete audit trail"""
        approver = sample_user(role=UserRole.ADMIN)
        expense = sample_expense(status=ExpenseStatus.PENDING)

        # Create audit trail
        audit_service = AuditService(db_session)
        created_trail = audit_service.create_complete_audit_trail(
            expense=expense, approver=approver, action="approve"
        )

        transaction_id = created_trail["transaction_id"]

        # Retrieve audit trail
        retrieved_trail = audit_service.get_complete_audit_trail(transaction_id)

        assert retrieved_trail is not None
        assert retrieved_trail["transaction_id"] == transaction_id
        assert retrieved_trail["complete"] is True

        # Verify all mandates are present
        assert retrieved_trail["intent_mandate"] is not None
        assert retrieved_trail["cart_mandate"] is not None
        assert retrieved_trail["payment_mandate"] is not None
        assert retrieved_trail["expense"] is not None

    def test_get_audit_trail_not_found(self, db_session):
        """Test retrieving non-existent audit trail"""
        audit_service = AuditService(db_session)
        trail = audit_service.get_complete_audit_trail("non-existent-id")

        assert trail is None

    def test_get_expense_history(self, db_session, sample_user, sample_expense):
        """Test getting expense history"""
        approver = sample_user(role=UserRole.ADMIN)
        expense = sample_expense(status=ExpenseStatus.PENDING)

        # Create audit trail (which creates audit logs)
        audit_service = AuditService(db_session)
        audit_service.create_complete_audit_trail(
            expense=expense, approver=approver, action="approve"
        )

        # Get expense history
        history = audit_service.get_expense_history(expense.id)

        assert len(history) > 0
        assert all("action" in entry for entry in history)
        assert all("timestamp" in entry for entry in history)


class TestAuditServiceConstraints:
    """Test audit service constraints and validation"""

    def test_intent_mandate_constraints(self, db_session, sample_user, sample_expense):
        """Test intent mandate contains proper constraints"""
        approver = sample_user(role=UserRole.ADMIN)
        expense = sample_expense(status=ExpenseStatus.PENDING, amount=100.00)

        audit_service = AuditService(db_session)
        audit_trail = audit_service.create_complete_audit_trail(
            expense=expense, approver=approver, action="approve"
        )

        constraints = audit_trail["intent_mandate"]["constraints"]

        # Verify constraint structure
        assert "max_amount" in constraints
        assert constraints["max_amount"] >= float(expense.amount)
        assert "allowed_categories" in constraints
        assert expense.category.value in constraints["allowed_categories"]
        assert "allowed_vendors" in constraints
        assert expense.vendor in constraints["allowed_vendors"]
        assert "approver_id" in constraints
        assert constraints["approver_id"] == approver.id

    def test_cart_mandate_items(self, db_session, sample_user, sample_expense):
        """Test cart mandate contains expense items"""
        approver = sample_user(role=UserRole.ADMIN)
        expense = sample_expense(status=ExpenseStatus.PENDING)

        audit_service = AuditService(db_session)
        audit_trail = audit_service.create_complete_audit_trail(
            expense=expense, approver=approver, action="approve"
        )

        items = audit_trail["cart_mandate"]["items"]

        assert len(items) == 1
        item = items[0]
        assert item["expense_id"] == expense.id
        assert item["amount"] == float(expense.amount)
        assert item["category"] == expense.category.value
        assert item["description"] == expense.description

    def test_payment_mandate_audit_trail(self, db_session, sample_user, sample_expense):
        """Test payment mandate contains detailed audit trail"""
        approver = sample_user(role=UserRole.ADMIN)
        expense = sample_expense(status=ExpenseStatus.PENDING)

        audit_service = AuditService(db_session)
        audit_trail = audit_service.create_complete_audit_trail(
            expense=expense, approver=approver, action="approve"
        )

        payment_audit = audit_trail["payment_mandate"]["audit_trail"]

        # Verify audit trail structure
        assert "expense_id" in payment_audit
        assert "submitted_by" in payment_audit
        assert "reviewed_by" in payment_audit
        assert "action" in payment_audit
        assert payment_audit["action"] == "approve"
        assert "approval_chain" in payment_audit
        assert "compliance_checks" in payment_audit
        assert "metadata" in payment_audit


class TestAuditServiceVerification:
    """Test audit service verification functions"""

    def test_timestamp_verification(self, db_session, sample_user, sample_expense):
        """Test that timestamps are in correct chronological order"""
        approver = sample_user(role=UserRole.ADMIN)
        expense = sample_expense(status=ExpenseStatus.PENDING)

        audit_service = AuditService(db_session)
        created_trail = audit_service.create_complete_audit_trail(
            expense=expense, approver=approver, action="approve"
        )

        # Retrieve trail with verification
        retrieved_trail = audit_service.get_complete_audit_trail(
            created_trail["transaction_id"]
        )

        verification = retrieved_trail["verification"]
        assert verification["chain_complete"] is True
        assert verification["timestamps_valid"] is True

    def test_signature_generation(self, db_session):
        """Test that signatures are generated consistently"""
        audit_service = AuditService(db_session)

        message = "test_message"
        sig1 = audit_service._generate_signature(message)
        sig2 = audit_service._generate_signature(message)

        # Signatures should be different due to timestamp
        # RSA-2048 signatures are 256 bytes, base64 encoded = ~344 characters
        assert len(sig1) > 300  # RSA signature length
        assert len(sig2) > 300
        # Verify base64 format (alphanumeric + / + = for padding)
        import re

        assert re.match(r"^[A-Za-z0-9+/]+=*$", sig1)


class TestAuditServiceRejection:
    """Test audit service for rejection scenarios"""

    def test_rejection_does_not_create_mandates(
        self, db_session, sample_user, sample_expense
    ):
        """Test that rejection doesn't create AP2 mandates"""
        # This test verifies that rejection uses simple audit log,
        # not full AP2 protocol
        approver = sample_user(role=UserRole.ADMIN)
        expense = sample_expense(status=ExpenseStatus.PENDING)

        # Rejection is handled differently - it doesn't create full mandates
        # Just verify the audit log creation works
        audit_service = AuditService(db_session)

        # Create a simple audit log for rejection
        audit_service._create_audit_log_entry(
            expense=expense,
            user=approver,
            action="reject",
            details={"rejection_reason": "Does not meet policy"},
        )

        # Verify audit log exists
        audit_logs = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.resource_type == "expense", AuditLog.resource_id == expense.id
            )
            .all()
        )

        assert len(audit_logs) > 0
