"""
Tests for BudgetGuardianService - proactive budget enforcement.
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from src.auth import AuthService
from src.models import (
    Budget,
    BudgetAlert,
    BudgetPeriod,
    Expense,
    ExpenseCategory,
    Organization,
    OrganizationMember,
    OrganizationRole,
    User,
    UserRole,
)
from src.services.budget_guardian_service import BudgetGuardianService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def org(db_session):
    """Create a test organization."""
    org = Organization(
        id=f"org_{uuid.uuid4().hex[:8]}",
        name="Guardian Test Org",
        slug=f"guardian-test-{uuid.uuid4().hex[:6]}",
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
        email="guardian_test@example.com",
        username="guardian_tester",
        full_name="Guardian Tester",
        hashed_password=AuthService.hash_password("TestPass123!"),
        role=UserRole.EMPLOYEE,
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
        role=OrganizationRole.EMPLOYEE,
        is_active=True,
        joined_at=datetime.utcnow(),
    )
    db_session.add(member)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def service(db_session):
    """Create a BudgetGuardianService instance."""
    return BudgetGuardianService(db_session)


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
# Tests: evaluate_expense
# ============================================================================


class TestEvaluateExpense:
    def test_evaluate_expense_allowed(self, db_session, org, user, service):
        """Expense under budget should be allowed with no warnings."""
        _make_budget(db_session, org, amount=1000)
        # Create existing spending of 500
        _make_expense(db_session, org, user, amount=500)

        result = service.evaluate_expense(
            expense_amount=100,
            organization_id=org.id,
        )

        assert result.allowed is True
        assert len(result.blocks) == 0

    def test_evaluate_expense_blocked_over_budget(self, db_session, org, user, service):
        """Expense exceeding budget should be blocked when hard_block=True."""
        _make_budget(db_session, org, amount=500)
        _make_expense(db_session, org, user, amount=450)

        result = service.evaluate_expense(
            expense_amount=100,
            organization_id=org.id,
            hard_block=True,
        )

        assert result.allowed is False
        assert len(result.blocks) > 0

    def test_evaluate_expense_warning_threshold(self, db_session, org, user, service):
        """Expense crossing warning threshold should generate a warning."""
        _make_budget(db_session, org, amount=1000, warning_threshold=75)
        # Spend 700 so we're at 70%, then adding 100 pushes to 80%
        _make_expense(db_session, org, user, amount=700)

        result = service.evaluate_expense(
            expense_amount=100,
            organization_id=org.id,
        )

        assert result.allowed is True
        assert len(result.warnings) > 0

    def test_evaluate_expense_over_budget_soft(self, db_session, org, user, service):
        """Without hard_block, exceeding budget produces warning not block."""
        _make_budget(db_session, org, amount=500)
        _make_expense(db_session, org, user, amount=450)

        result = service.evaluate_expense(
            expense_amount=100,
            organization_id=org.id,
            hard_block=False,
        )

        assert result.allowed is True
        assert len(result.warnings) > 0

    def test_evaluate_expense_returns_budget_impacts(
        self, db_session, org, user, service
    ):
        """Result should contain budget impact details."""
        _make_budget(db_session, org, amount=1000)
        _make_expense(db_session, org, user, amount=200)

        result = service.evaluate_expense(
            expense_amount=100,
            organization_id=org.id,
        )

        assert len(result.budget_impacts) == 1
        impact = result.budget_impacts[0]
        assert impact.budget_amount == 1000.0
        assert impact.current_spending == 200.0
        assert impact.proposed_total == 300.0


# ============================================================================
# Tests: check_all_budgets
# ============================================================================


class TestCheckAllBudgets:
    def test_check_all_budgets_returns_health(self, db_session, org, user, service):
        """check_all_budgets should return a list with percentage_used."""
        _make_budget(db_session, org, amount=1000, name="Monthly Travel")
        _make_expense(db_session, org, user, amount=250)

        reports = service.check_all_budgets(organization_id=org.id)

        assert isinstance(reports, list)
        assert len(reports) >= 1
        report = reports[0]
        assert hasattr(report, "percentage_used")
        assert report.percentage_used >= 0

    def test_check_all_budgets_empty(self, db_session, org, service):
        """No budgets should return an empty list."""
        reports = service.check_all_budgets(organization_id=org.id)
        assert reports == []


# ============================================================================
# Tests: create_alerts_if_needed
# ============================================================================


class TestCreateAlerts:
    def test_create_alerts_at_thresholds(self, db_session, org, service):
        """Alerts should be created when spending crosses thresholds."""
        budget = _make_budget(
            db_session, org, amount=1000, warning_threshold=75, critical_threshold=90
        )

        # Spending at 80% should trigger warning alert
        alerts = service.create_alerts_if_needed(budget, Decimal("800"))
        db_session.commit()

        assert len(alerts) >= 1
        alert_types = [a.alert_type for a in alerts]
        assert "warning" in alert_types

    def test_create_alerts_exceeded(self, db_session, org, service):
        """Spending at 100%+ should trigger exceeded alert."""
        budget = _make_budget(
            db_session, org, amount=1000, warning_threshold=75, critical_threshold=90
        )

        alerts = service.create_alerts_if_needed(budget, Decimal("1100"))
        db_session.commit()

        alert_types = [a.alert_type for a in alerts]
        assert "exceeded" in alert_types

    def test_create_alerts_deduplicates(self, db_session, org, service):
        """Calling create_alerts_if_needed twice should not create duplicates."""
        budget = _make_budget(
            db_session, org, amount=1000, warning_threshold=75, critical_threshold=90
        )

        alerts1 = service.create_alerts_if_needed(budget, Decimal("800"))
        db_session.commit()
        alerts2 = service.create_alerts_if_needed(budget, Decimal("800"))
        db_session.commit()

        assert len(alerts1) >= 1
        assert len(alerts2) == 0

        # Verify only one set of alerts in DB
        all_alerts = (
            db_session.query(BudgetAlert)
            .filter(BudgetAlert.budget_id == budget.id)
            .all()
        )
        warning_alerts = [a for a in all_alerts if a.alert_type == "warning"]
        assert len(warning_alerts) == 1
