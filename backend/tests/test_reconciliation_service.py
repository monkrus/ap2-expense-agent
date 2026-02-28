"""
Tests for ReconciliationService - variance analysis and reporting.
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from src.models import (
    Budget,
    BudgetPeriod,
    Expense,
    ExpenseCategory,
    Organization,
    OrganizationMember,
    OrganizationRole,
    User,
    UserRole,
)
from src.auth import AuthService
from src.services.reconciliation_service import ReconciliationService


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def org(db_session):
    """Create a test organization."""
    org = Organization(
        id=f"org_{uuid.uuid4().hex[:8]}",
        name="Recon Test Org",
        slug=f"recon-test-{uuid.uuid4().hex[:6]}",
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


@pytest.fixture
def user(db_session, org):
    """Create a test user in the org."""
    u = User(
        id=str(uuid.uuid4()),
        email="recon_test@example.com",
        username="recon_tester",
        full_name="Recon Tester",
        hashed_password=AuthService.hash_password("TestPass123!"),
        role=UserRole.USER,
        is_active=True,
        is_verified=True,
        failed_login_attempts=0,
    )
    db_session.add(u)
    db_session.flush()

    member = OrganizationMember(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        user_id=u.id,
        role=OrganizationRole.MEMBER,
        is_active=True,
        joined_at=datetime.utcnow(),
    )
    db_session.add(member)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def user2(db_session, org):
    """Create a second test user in the org."""
    u = User(
        id=str(uuid.uuid4()),
        email="recon_test2@example.com",
        username="recon_tester2",
        full_name="Recon Tester 2",
        hashed_password=AuthService.hash_password("TestPass123!"),
        role=UserRole.USER,
        is_active=True,
        is_verified=True,
        failed_login_attempts=0,
    )
    db_session.add(u)
    db_session.flush()

    member = OrganizationMember(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        user_id=u.id,
        role=OrganizationRole.MEMBER,
        is_active=True,
        joined_at=datetime.utcnow(),
    )
    db_session.add(member)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def service(db_session):
    """Create a ReconciliationService instance."""
    return ReconciliationService(db_session)


def _make_budget(db_session, org, **kwargs):
    """Helper to create a budget with sensible defaults."""
    now = datetime.utcnow()
    budget = Budget(
        id=f"bud_{uuid.uuid4().hex[:8]}",
        organization_id=org.id,
        name=kwargs.get("name", "Test Budget"),
        amount=kwargs.get("amount", 1000),
        period=kwargs.get("period", BudgetPeriod.MONTHLY),
        category=kwargs.get("category", None),
        user_id=kwargs.get("user_id", None),
        warning_threshold=kwargs.get("warning_threshold", 75),
        critical_threshold=kwargs.get("critical_threshold", 90),
        is_active=kwargs.get("is_active", True),
        start_date=kwargs.get("start_date", datetime(now.year, now.month, 1)),
        end_date=kwargs.get("end_date", None),
    )
    db_session.add(budget)
    db_session.commit()
    db_session.refresh(budget)
    return budget


def _make_expense(db_session, org, user, **kwargs):
    """Helper to create an expense."""
    expense = Expense(
        id=f"exp_{uuid.uuid4().hex[:8]}",
        organization_id=org.id,
        user_id=user.id,
        amount=kwargs.get("amount", 100),
        description=kwargs.get("description", "Test expense"),
        category=kwargs.get("category", "TRAVEL"),
        status=kwargs.get("status", "approved"),
        vendor=kwargs.get("vendor", "Test Vendor"),
        date=kwargs.get("date", datetime.utcnow()),
        created_at=kwargs.get("created_at", datetime.utcnow()),
    )
    db_session.add(expense)
    db_session.commit()
    db_session.refresh(expense)
    return expense


# ============================================================================
# Tests: generate_variance_report
# ============================================================================


class TestVarianceReport:
    def test_variance_report_over_budget(self, db_session, org, user, service):
        """Budget with spending exceeding amount should show over_budget."""
        _make_budget(db_session, org, amount=500)
        _make_expense(db_session, org, user, amount=300)
        _make_expense(db_session, org, user, amount=300)

        report = service.generate_variance_report(organization_id=org.id)

        assert len(report.budgets) >= 1
        budget_entry = report.budgets[0]
        assert budget_entry.status == "over_budget"
        assert budget_entry.variance_amount < 0

    def test_variance_report_under_budget(self, db_session, org, user, service):
        """Budget with low spending should show under_budget."""
        _make_budget(db_session, org, amount=1000)
        _make_expense(db_session, org, user, amount=200)

        report = service.generate_variance_report(organization_id=org.id)

        assert len(report.budgets) >= 1
        budget_entry = report.budgets[0]
        assert budget_entry.status == "under_budget"
        assert budget_entry.variance_amount > 0

    def test_variance_report_totals(self, db_session, org, user, service):
        """Report totals should aggregate across budgets."""
        _make_budget(db_session, org, amount=1000, name="Budget A",
                     category=ExpenseCategory.TRAVEL)
        _make_expense(db_session, org, user, amount=200, category="TRAVEL")

        report = service.generate_variance_report(organization_id=org.id)

        assert report.total_budgeted > 0
        assert report.total_actual >= 0


# ============================================================================
# Tests: generate_category_reconciliation
# ============================================================================


class TestCategoryReconciliation:
    def test_category_reconciliation_basic(self, db_session, org, user, service):
        """Should return categories with spending data."""
        _make_expense(db_session, org, user, amount=100, category="TRAVEL")
        _make_expense(db_session, org, user, amount=200, category="MEALS")

        report = service.generate_category_reconciliation(
            organization_id=org.id,
        )

        assert len(report.categories) >= 2
        category_names = [c.category for c in report.categories]
        assert "TRAVEL" in category_names
        assert "MEALS" in category_names

    def test_category_reconciliation_with_date_range(self, db_session, org, user, service):
        """Only expenses in the date range should be included."""
        now = datetime.utcnow()
        _make_expense(
            db_session, org, user, amount=100, category="TRAVEL",
            created_at=now - timedelta(days=5),
        )
        _make_expense(
            db_session, org, user, amount=200, category="TRAVEL",
            created_at=now - timedelta(days=30),
        )

        start = now - timedelta(days=10)
        end = now

        report = service.generate_category_reconciliation(
            organization_id=org.id,
            start_date=start,
            end_date=end,
        )

        # Only the recent expense (100) should be included
        travel_cats = [c for c in report.categories if c.category == "TRAVEL"]
        assert len(travel_cats) == 1
        assert travel_cats[0].actual_spending == 100.0

    def test_category_reconciliation_unbudgeted(self, db_session, org, user, service):
        """Spending in categories without budgets should be tracked as unbudgeted."""
        _make_expense(db_session, org, user, amount=150, category="MEALS")

        report = service.generate_category_reconciliation(
            organization_id=org.id,
        )

        assert report.unbudgeted_spending >= 150.0


# ============================================================================
# Tests: generate_user_spending_report
# ============================================================================


class TestUserSpendingReport:
    def test_user_spending_report(self, db_session, org, user, user2, service):
        """Should return per-user data with totals and avg_expense."""
        _make_expense(db_session, org, user, amount=100)
        _make_expense(db_session, org, user, amount=200)
        _make_expense(db_session, org, user2, amount=300)

        report = service.generate_user_spending_report(organization_id=org.id)

        assert report.total_users == 2
        assert report.total_spending == 600.0

        # Check per-user data
        user_ids = [u.user_id for u in report.users]
        assert user.id in user_ids
        assert user2.id in user_ids

        user1_data = next(u for u in report.users if u.user_id == user.id)
        assert user1_data.total_spending == 300.0
        assert user1_data.expense_count == 2
        assert user1_data.avg_expense == 150.0

    def test_user_spending_report_empty(self, db_session, org, service):
        """No expenses should return empty user list."""
        report = service.generate_user_spending_report(organization_id=org.id)
        assert report.total_users == 0
        assert report.total_spending == 0.0


# ============================================================================
# Tests: get_budget_forecast
# ============================================================================


class TestBudgetForecast:
    def test_budget_forecast(self, db_session, org, user, service):
        """Forecast should return projected_end_spending."""
        budget = _make_budget(db_session, org, amount=1000)
        _make_expense(db_session, org, user, amount=200)

        result = service.get_budget_forecast(budget_id=budget.id)

        assert result is not None
        assert hasattr(result, "projected_end_spending")
        assert result.budget_amount == 1000.0
        assert result.current_spending >= 0

    def test_budget_forecast_not_found(self, db_session, service):
        """Non-existent budget should return None."""
        result = service.get_budget_forecast(budget_id="nonexistent_id")
        assert result is None
