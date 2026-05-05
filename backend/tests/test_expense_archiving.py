"""
Comprehensive tests for expense archiving functionality
Tests archive endpoints, permissions, database updates, and archive state transitions
"""

import uuid
from datetime import datetime

import pytest

from src.models import AuditLog, Expense, ExpenseStatus, OrganizationMember


class TestArchiveSingleExpense:
    """Test archiving individual expense records"""

    def _get_admin_org_and_headers(self, client, db_session, test_admin):
        """Helper to get admin's organization and headers"""
        membership = (
            db_session.query(OrganizationMember)
            .filter(OrganizationMember.user_id == test_admin.id)
            .first()
        )
        org_id = membership.organization_id

        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "AdminPass123!"},
        )
        admin_token = response.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {admin_token}",
            "X-Organization-Id": org_id,
        }
        return org_id, headers

    def test_archive_approved_expense_as_admin(self, client, db_session, test_admin):
        """Test archiving a single approved expense as admin"""
        org_id, headers = self._get_admin_org_and_headers(
            client, db_session, test_admin
        )

        # Setup: Create approved expense
        expense = Expense(
            id="exp_1",
            organization_id=org_id,
            user_id=test_admin.id,
            amount=100.00,
            vendor="Test Vendor",
            category="travel",
            description="Test expense",
            status=ExpenseStatus.APPROVED,
            is_archived=False,
            approved_by=test_admin.id,
        )
        db_session.add(expense)
        db_session.commit()

        # Verify expense is not archived before
        expense_before = db_session.query(Expense).filter(Expense.id == "exp_1").first()
        assert expense_before.is_archived is False
        assert expense_before.archived_at is None
        assert expense_before.archived_by is None

        # Archive expense
        response = client.post("/api/v1/admin/expenses/exp_1/archive", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "successfully" in data["message"].lower()

        # Verify expense is archived in database
        expense_after = db_session.query(Expense).filter(Expense.id == "exp_1").first()
        assert expense_after.is_archived is True
        assert expense_after.archived_at is not None
        assert expense_after.archived_by == test_admin.id
        assert isinstance(expense_after.archived_at, datetime)

    def test_archive_rejected_expense_as_admin(self, client, db_session, test_admin):
        """Test archiving a rejected expense as admin"""
        org_id, headers = self._get_admin_org_and_headers(
            client, db_session, test_admin
        )

        expense = Expense(
            id="exp_rejected",
            organization_id=org_id,
            user_id=test_admin.id,
            amount=50.00,
            vendor="Test Vendor",
            category="meals",
            description="Test rejected expense",
            status=ExpenseStatus.REJECTED,
            is_archived=False,
            rejection_reason="Invalid receipt",
        )
        db_session.add(expense)
        db_session.commit()

        response = client.post(
            "/api/v1/admin/expenses/exp_rejected/archive", headers=headers
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify in database
        expense_after = (
            db_session.query(Expense).filter(Expense.id == "exp_rejected").first()
        )
        assert expense_after.is_archived is True

    def test_cannot_archive_pending_expense(self, client, db_session, test_admin):
        """Test that pending expenses cannot be archived"""
        org_id, headers = self._get_admin_org_and_headers(
            client, db_session, test_admin
        )

        expense = Expense(
            id="exp_pending",
            organization_id=org_id,
            user_id=test_admin.id,
            amount=75.00,
            vendor="Test Vendor",
            category="office_supplies",
            description="Test pending expense",
            status=ExpenseStatus.PENDING,
            is_archived=False,
        )
        db_session.add(expense)
        db_session.commit()

        response = client.post(
            "/api/v1/admin/expenses/exp_pending/archive", headers=headers
        )

        assert response.status_code == 400
        assert "Cannot archive pending" in response.json()["detail"]

        # Verify NOT archived in database
        expense_after = (
            db_session.query(Expense).filter(Expense.id == "exp_pending").first()
        )
        assert expense_after.is_archived is False

    def test_cannot_archive_already_archived_expense(
        self, client, db_session, test_admin
    ):
        """Test that already archived expenses cannot be archived again"""
        org_id, headers = self._get_admin_org_and_headers(
            client, db_session, test_admin
        )

        expense = Expense(
            id="exp_archived",
            organization_id=org_id,
            user_id=test_admin.id,
            amount=100.00,
            vendor="Test Vendor",
            category="travel",
            description="Test expense",
            status=ExpenseStatus.APPROVED,
            is_archived=True,
            archived_at=datetime.utcnow(),
            archived_by=test_admin.id,
        )
        db_session.add(expense)
        db_session.commit()

        response = client.post(
            "/api/v1/admin/expenses/exp_archived/archive", headers=headers
        )

        assert response.status_code == 400
        assert "already archived" in response.json()["detail"]

    def test_archive_nonexistent_expense_returns_404(
        self, client, db_session, test_admin
    ):
        """Test archiving nonexistent expense returns 404"""
        org_id, headers = self._get_admin_org_and_headers(
            client, db_session, test_admin
        )

        response = client.post(
            "/api/v1/admin/expenses/nonexistent/archive", headers=headers
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_non_admin_cannot_archive_expense(self, client, db_session, test_user):
        """Test that non-admin users cannot archive expenses"""
        # Get user's organization
        membership = (
            db_session.query(OrganizationMember)
            .filter(OrganizationMember.user_id == test_user.id)
            .first()
        )
        org_id = membership.organization_id

        expense = Expense(
            id="exp_user",
            organization_id=org_id,
            user_id=test_user.id,
            amount=100.00,
            vendor="Test Vendor",
            category="travel",
            description="Test expense",
            status=ExpenseStatus.APPROVED,
            is_archived=False,
            approved_by=test_user.id,
        )
        db_session.add(expense)
        db_session.commit()

        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "TestPass123!"},
        )
        user_token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {user_token}", "X-Organization-Id": org_id}

        response = client.post(
            "/api/v1/admin/expenses/exp_user/archive", headers=headers
        )

        assert response.status_code == 403  # Forbidden

    def test_archive_requires_organization_header(self, client, db_session, test_admin):
        """Test that archive endpoint requires X-Organization-Id header"""
        org_id, _ = self._get_admin_org_and_headers(client, db_session, test_admin)

        expense = Expense(
            id="exp_header_test",
            organization_id=org_id,
            user_id=test_admin.id,
            amount=100.00,
            vendor="Test Vendor",
            category="travel",
            description="Test expense",
            status=ExpenseStatus.APPROVED,
            is_archived=False,
        )
        db_session.add(expense)
        db_session.commit()

        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "AdminPass123!"},
        )
        admin_token = response.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {admin_token}"
            # Missing X-Organization-Id
        }

        response = client.post(
            "/api/v1/admin/expenses/exp_header_test/archive", headers=headers
        )

        assert response.status_code == 400
        assert "Organization context required" in response.json()["detail"]


class TestArchiveAllExpenses:
    """Test bulk archiving of all non-pending expenses"""

    def _get_admin_org_and_headers(self, client, db_session, test_admin):
        """Helper to get admin's organization and headers"""
        membership = (
            db_session.query(OrganizationMember)
            .filter(OrganizationMember.user_id == test_admin.id)
            .first()
        )
        org_id = membership.organization_id

        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "AdminPass123!"},
        )
        admin_token = response.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {admin_token}",
            "X-Organization-Id": org_id,
        }
        return org_id, headers

    def test_archive_all_expenses_as_admin(self, client, db_session, test_admin):
        """Test archiving all non-pending expenses at once"""
        org_id, headers = self._get_admin_org_and_headers(
            client, db_session, test_admin
        )

        # Create multiple expenses in various states
        approved_exp = Expense(
            id="exp_approved",
            organization_id=org_id,
            user_id=test_admin.id,
            amount=100.00,
            vendor="Vendor A",
            category="travel",
            description="Approved",
            status=ExpenseStatus.APPROVED,
            is_archived=False,
        )

        rejected_exp = Expense(
            id="exp_rejected",
            organization_id=org_id,
            user_id=test_admin.id,
            amount=50.00,
            vendor="Vendor B",
            category="meals",
            description="Rejected",
            status=ExpenseStatus.REJECTED,
            is_archived=False,
            rejection_reason="Invalid",
        )

        pending_exp = Expense(
            id="exp_pending",
            organization_id=org_id,
            user_id=test_admin.id,
            amount=75.00,
            vendor="Vendor C",
            category="office_supplies",
            description="Pending",
            status=ExpenseStatus.PENDING,
            is_archived=False,
        )

        db_session.add_all([approved_exp, rejected_exp, pending_exp])
        db_session.commit()

        # Archive all
        response = client.post("/api/v1/admin/expenses/archive-all", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert (
            data["statistics"]["expenses_archived"] == 2
        )  # Approved and rejected only

        # Verify database state
        approved = (
            db_session.query(Expense).filter(Expense.id == "exp_approved").first()
        )
        rejected = (
            db_session.query(Expense).filter(Expense.id == "exp_rejected").first()
        )
        pending = db_session.query(Expense).filter(Expense.id == "exp_pending").first()

        assert approved.is_archived is True
        assert approved.archived_by == test_admin.id
        assert rejected.is_archived is True
        assert rejected.archived_by == test_admin.id
        assert pending.is_archived is False  # Should NOT be archived

    def test_archive_all_with_no_expenses_to_archive(
        self, client, db_session, test_admin
    ):
        """Test archive-all when there are no archivable expenses"""
        org_id, headers = self._get_admin_org_and_headers(
            client, db_session, test_admin
        )

        # Create only pending expenses
        pending_exp = Expense(
            id="exp_only_pending",
            organization_id=org_id,
            user_id=test_admin.id,
            amount=100.00,
            vendor="Vendor",
            category="travel",
            description="Pending",
            status=ExpenseStatus.PENDING,
            is_archived=False,
        )
        db_session.add(pending_exp)
        db_session.commit()

        response = client.post("/api/v1/admin/expenses/archive-all", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["statistics"]["expenses_archived"] == 0

    def test_archive_all_does_not_archive_already_archived(
        self, client, db_session, test_admin
    ):
        """Test that archive-all doesn't re-archive already archived expenses"""
        org_id, headers = self._get_admin_org_and_headers(
            client, db_session, test_admin
        )

        # Create mix of archived and non-archived
        approved_exp = Expense(
            id="exp_new_approved",
            organization_id=org_id,
            user_id=test_admin.id,
            amount=100.00,
            vendor="Vendor",
            category="travel",
            description="New approved",
            status=ExpenseStatus.APPROVED,
            is_archived=False,
        )

        already_archived = Expense(
            id="exp_already_archived",
            organization_id=org_id,
            user_id=test_admin.id,
            amount=50.00,
            vendor="Vendor",
            category="meals",
            description="Already archived",
            status=ExpenseStatus.APPROVED,
            is_archived=True,
            archived_at=datetime.utcnow(),
            archived_by=test_admin.id,
        )

        db_session.add_all([approved_exp, already_archived])
        db_session.commit()

        response = client.post("/api/v1/admin/expenses/archive-all", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["statistics"]["expenses_archived"] == 1  # Only the new one

    def test_archive_all_requires_admin(self, client, db_session, test_user):
        """Test that archive-all requires admin permissions"""
        # Get user's organization
        membership = (
            db_session.query(OrganizationMember)
            .filter(OrganizationMember.user_id == test_user.id)
            .first()
        )
        org_id = membership.organization_id

        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "TestPass123!"},
        )
        user_token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {user_token}", "X-Organization-Id": org_id}

        response = client.post("/api/v1/admin/expenses/archive-all", headers=headers)

        assert response.status_code == 403


class TestGetArchivedExpenses:
    """Test retrieving archived expenses"""

    def _get_admin_org_and_headers(self, client, db_session, test_admin):
        """Helper to get admin's organization and headers"""
        membership = (
            db_session.query(OrganizationMember)
            .filter(OrganizationMember.user_id == test_admin.id)
            .first()
        )
        org_id = membership.organization_id

        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "AdminPass123!"},
        )
        admin_token = response.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {admin_token}",
            "X-Organization-Id": org_id,
        }
        return org_id, headers

    def test_get_archived_expenses_as_admin(self, client, db_session, test_admin):
        """Test retrieving archived expenses as admin"""
        org_id, headers = self._get_admin_org_and_headers(
            client, db_session, test_admin
        )

        # Create archived and non-archived expenses
        archived_exp = Expense(
            id="exp_archived1",
            organization_id=org_id,
            user_id=test_admin.id,
            amount=100.00,
            vendor="Vendor A",
            category="travel",
            description="Archived",
            status=ExpenseStatus.APPROVED,
            is_archived=True,
            archived_at=datetime.utcnow(),
            archived_by=test_admin.id,
        )

        non_archived_exp = Expense(
            id="exp_active",
            organization_id=org_id,
            user_id=test_admin.id,
            amount=50.00,
            vendor="Vendor B",
            category="meals",
            description="Active",
            status=ExpenseStatus.APPROVED,
            is_archived=False,
        )

        db_session.add_all([archived_exp, non_archived_exp])
        db_session.commit()

        response = client.get("/api/v1/admin/expenses/archived", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert len(data["expenses"]) == 1
        assert data["expenses"][0]["id"] == "exp_archived1"
        assert data["expenses"][0]["archived_by_name"] == "Admin User"


class TestUnarchiveExpenses:
    """Test unarchiving expenses"""

    def _get_admin_org_and_headers(self, client, db_session, test_admin):
        """Helper to get admin's organization and headers"""
        membership = (
            db_session.query(OrganizationMember)
            .filter(OrganizationMember.user_id == test_admin.id)
            .first()
        )
        org_id = membership.organization_id

        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "AdminPass123!"},
        )
        admin_token = response.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {admin_token}",
            "X-Organization-Id": org_id,
        }
        return org_id, headers

    def test_unarchive_single_expense(self, client, db_session, test_admin):
        """Test unarchiving a single archived expense"""
        org_id, headers = self._get_admin_org_and_headers(
            client, db_session, test_admin
        )

        archived_exp = Expense(
            id="exp_to_unarchive",
            organization_id=org_id,
            user_id=test_admin.id,
            amount=100.00,
            vendor="Vendor",
            category="travel",
            description="Archived",
            status=ExpenseStatus.APPROVED,
            is_archived=True,
            archived_at=datetime.utcnow(),
            archived_by=test_admin.id,
        )
        db_session.add(archived_exp)
        db_session.commit()

        response = client.post(
            "/api/v1/admin/expenses/exp_to_unarchive/unarchive", headers=headers
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify in database
        expense = (
            db_session.query(Expense).filter(Expense.id == "exp_to_unarchive").first()
        )
        assert expense.is_archived is False
        assert expense.archived_at is None
        assert expense.archived_by is None

    def test_unarchive_all_expenses(self, client, db_session, test_admin):
        """Test unarchiving all archived expenses at once"""
        org_id, headers = self._get_admin_org_and_headers(
            client, db_session, test_admin
        )

        archived_exp1 = Expense(
            id="exp_archived1",
            organization_id=org_id,
            user_id=test_admin.id,
            amount=100.00,
            vendor="Vendor",
            category="travel",
            description="Archived 1",
            status=ExpenseStatus.APPROVED,
            is_archived=True,
            archived_at=datetime.utcnow(),
            archived_by=test_admin.id,
        )

        archived_exp2 = Expense(
            id="exp_archived2",
            organization_id=org_id,
            user_id=test_admin.id,
            amount=50.00,
            vendor="Vendor",
            category="meals",
            description="Archived 2",
            status=ExpenseStatus.APPROVED,
            is_archived=True,
            archived_at=datetime.utcnow(),
            archived_by=test_admin.id,
        )

        db_session.add_all([archived_exp1, archived_exp2])
        db_session.commit()

        response = client.post("/api/v1/admin/expenses/unarchive-all", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["statistics"]["expenses_unarchived"] == 2

        # Verify in database
        exp1 = db_session.query(Expense).filter(Expense.id == "exp_archived1").first()
        exp2 = db_session.query(Expense).filter(Expense.id == "exp_archived2").first()

        assert exp1.is_archived is False
        assert exp2.is_archived is False


class TestArchiveAuditTrail:
    """Test audit logging for archive operations"""

    def _get_admin_org_and_headers(self, client, db_session, test_admin):
        """Helper to get admin's organization and headers"""
        membership = (
            db_session.query(OrganizationMember)
            .filter(OrganizationMember.user_id == test_admin.id)
            .first()
        )
        org_id = membership.organization_id

        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "AdminPass123!"},
        )
        admin_token = response.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {admin_token}",
            "X-Organization-Id": org_id,
        }
        return org_id, headers

    def test_archive_creates_audit_log(self, client, db_session, test_admin):
        """Test that archiving creates proper audit log entries"""
        org_id, headers = self._get_admin_org_and_headers(
            client, db_session, test_admin
        )

        expense = Expense(
            id="exp_audit_test",
            organization_id=org_id,
            user_id=test_admin.id,
            amount=100.00,
            vendor="Vendor",
            category="travel",
            description="Test",
            status=ExpenseStatus.APPROVED,
            is_archived=False,
        )
        db_session.add(expense)
        db_session.commit()

        response = client.post(
            "/api/v1/admin/expenses/exp_audit_test/archive", headers=headers
        )

        assert response.status_code == 200

        # Check audit log
        audit_log = (
            db_session.query(AuditLog)
            .filter(
                AuditLog.action == "admin.archive_expense",
                AuditLog.resource_id == "exp_audit_test",
            )
            .first()
        )

        assert audit_log is not None
        assert audit_log.user_id == test_admin.id
        assert audit_log.resource_type == "expense"
        assert audit_log.action == "admin.archive_expense"
