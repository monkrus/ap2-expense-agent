"""
Tests for AP2 Phase 2 & Phase 3 features:
- Pattern detection / mandate suggestions
- Monthly summary service
- Auto-approval email templates
- AP2 analytics endpoints
- Onboarding sample mandates
- Check auto-approval preview
"""

import json
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import (
    Base,
    Expense,
    ExpenseCategory,
    ExpenseStatus,
    IntentMandate,
    Organization,
    User,
    UserRole,
)

# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture(scope="function")
def test_db():
    """Create an in-memory test database for each test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    # Create test user
    user = User(
        id="user_phase23_001",
        email="phase23@example.com",
        username="phase23user",
        hashed_password="hashed",
        full_name="Phase 23 Test User",
        role=UserRole.EMPLOYEE.name.lower(),
        is_active=True,
        is_verified=True,
    )
    db.add(user)

    # Create test organization
    org = Organization(
        id="org_phase23_001",
        name="Test Org Phase23",
        slug="test-org-phase23",
        is_active=True,
    )
    db.add(org)
    db.commit()

    yield db
    db.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def user(test_db):
    return test_db.query(User).filter_by(id="user_phase23_001").first()


@pytest.fixture
def org_id():
    return "org_phase23_001"


def _create_expense(
    db,
    user_id,
    org_id,
    vendor,
    category,
    amount,
    auto_approved=False,
    auto_approved_via=None,
    status=ExpenseStatus.APPROVED,
    days_ago=0,
):
    """Helper to create an expense."""
    import uuid

    exp = Expense(
        id=f"EXP-{uuid.uuid4().hex[:12].upper()}",
        user_id=user_id,
        organization_id=org_id,
        vendor=vendor,
        category=category,
        amount=amount,
        description=f"Test expense at {vendor}",
        status=status,
        date=datetime.utcnow() - timedelta(days=days_ago),
        created_at=datetime.utcnow() - timedelta(days=days_ago),
        auto_approved=auto_approved,
        auto_approved_via=auto_approved_via,
    )
    db.add(exp)
    db.commit()
    return exp


def _create_intent_mandate(db, user_id, constraints, status="active", hours=720):
    """Helper to create an Intent Mandate."""
    import uuid

    mandate = IntentMandate(
        id=str(uuid.uuid4()),
        user_id=user_id,
        constraints=json.dumps(constraints),
        timestamp=datetime.utcnow(),
        status=status,
        expiration=datetime.utcnow() + timedelta(hours=hours),
        created_at=datetime.utcnow(),
    )
    db.add(mandate)
    db.commit()
    return mandate


# ── Email Template Tests ────────────────────────────────────────────


class TestAutoApprovalEmailTemplate:
    def test_renders_intent_mandate_email(self):
        from src.email_templates import get_auto_approved_email

        expense_data = {
            "amount": 45.00,
            "vendor": "Amazon",
            "category": "OFFICE_SUPPLIES",
            "description": "USB cables",
            "date": "2026-05-01",
        }
        mandate_details = {
            "name": "Office Supplies Rule",
            "constraints": {"max_amount": 100, "monthly_limit": 300},
        }

        subject, html, text = get_auto_approved_email(
            expense_data, "intent_mandate", mandate_details
        )

        assert "Auto-Approved" in subject
        assert "$45.00" in subject
        assert "Amazon" in subject
        assert "AI Agent" in html
        assert "USB cables" in html
        assert "Office Supplies Rule" in html
        assert "$45.00" in text
        assert "Amazon" in text

    def test_renders_policy_email(self):
        from src.email_templates import get_auto_approved_email

        expense_data = {
            "amount": 20.00,
            "vendor": "Staples",
            "category": "OFFICE_SUPPLIES",
            "description": "Paper",
            "date": "2026-05-01",
        }

        subject, html, text = get_auto_approved_email(expense_data, "approval_policy")

        assert "Auto-Approved" in subject
        assert "Approval Policy" in html
        assert "Staples" in text


class TestMonthlySummaryEmailTemplate:
    def test_renders_monthly_summary(self):
        from src.email_templates import get_monthly_auto_approval_summary_email

        summary = {
            "user_name": "Alice",
            "month_label": "April 2026",
            "total_expenses": 25,
            "auto_approved_count": 18,
            "manual_count": 7,
            "auto_approval_rate": 72.0,
            "total_amount": 3450.00,
            "auto_approved_amount": 2100.00,
            "time_saved_minutes": 54,
            "by_mandate_count": 12,
            "by_policy_count": 6,
            "top_vendors": [
                {"vendor": "Amazon", "count": 8, "amount": 950.00},
                {"vendor": "Staples", "count": 5, "amount": 420.00},
            ],
        }

        subject, html, text = get_monthly_auto_approval_summary_email(summary)

        assert "18 expenses auto-approved" in subject
        assert "April 2026" in subject
        assert "Alice" in html
        assert "72%" in html
        assert "54" in html  # minutes saved
        assert "Amazon" in html
        assert "Staples" in html
        assert "$3,450.00" in html
        assert "Excellent" in html  # rate >= 60%
        assert "Alice" in text

    def test_low_rate_shows_tip(self):
        from src.email_templates import get_monthly_auto_approval_summary_email

        summary = {
            "user_name": "Bob",
            "month_label": "April 2026",
            "total_expenses": 10,
            "auto_approved_count": 3,
            "manual_count": 7,
            "auto_approval_rate": 30.0,
            "total_amount": 500.00,
            "auto_approved_amount": 150.00,
            "time_saved_minutes": 9,
            "by_mandate_count": 2,
            "by_policy_count": 1,
            "top_vendors": [],
        }

        subject, html, text = get_monthly_auto_approval_summary_email(summary)

        assert "Tip" in html  # should show improvement tip
        assert "Getting started" in html  # rate < 40%


# ── Pattern Service Tests ───────────────────────────────────────────


class TestPatternService:
    def test_detects_recurring_vendor_pattern(self, test_db, user, org_id):
        from src.services.pattern_service import detect_patterns

        # Create 5 expenses at Amazon (non-auto-approved)
        for i in range(5):
            _create_expense(
                test_db,
                user.id,
                org_id,
                "Amazon",
                "OFFICE_SUPPLIES",
                45.00 + i * 5,
                days_ago=i * 7,
            )

        suggestions = detect_patterns(test_db, user.id, org_id)

        assert len(suggestions) >= 1
        amazon_suggestion = next(
            (s for s in suggestions if s["vendor"] == "Amazon"), None
        )
        assert amazon_suggestion is not None
        assert amazon_suggestion["expense_count"] == 5
        assert (
            amazon_suggestion["suggested_constraints"]["category"] == "OFFICE_SUPPLIES"
        )
        assert (
            amazon_suggestion["suggested_constraints"]["max_amount"] > 65
        )  # max was 65
        assert amazon_suggestion["suggested_constraints"]["monthly_limit"] > 0
        assert amazon_suggestion["estimated_time_saved_minutes_per_month"] > 0

    def test_ignores_auto_approved_expenses(self, test_db, user, org_id):
        from src.services.pattern_service import detect_patterns

        # Create 5 already auto-approved expenses (should be ignored)
        for i in range(5):
            _create_expense(
                test_db,
                user.id,
                org_id,
                "Staples",
                "OFFICE_SUPPLIES",
                30.00,
                auto_approved=True,
                auto_approved_via="intent_mandate",
                days_ago=i * 7,
            )

        suggestions = detect_patterns(test_db, user.id, org_id)

        staples_suggestion = next(
            (s for s in suggestions if s["vendor"] == "Staples"), None
        )
        assert staples_suggestion is None

    def test_requires_minimum_expenses(self, test_db, user, org_id):
        from src.services.pattern_service import detect_patterns

        # Only 2 expenses (below minimum of 3)
        for i in range(2):
            _create_expense(
                test_db,
                user.id,
                org_id,
                "Uber",
                "TRAVEL",
                25.00,
                days_ago=i * 7,
            )

        suggestions = detect_patterns(test_db, user.id, org_id)

        uber_suggestion = next((s for s in suggestions if s["vendor"] == "Uber"), None)
        assert uber_suggestion is None

    def test_skips_already_covered_patterns(self, test_db, user, org_id):
        from src.services.pattern_service import detect_patterns

        # Create expenses
        for i in range(4):
            _create_expense(
                test_db,
                user.id,
                org_id,
                "Amazon",
                "OFFICE_SUPPLIES",
                50.00,
                days_ago=i * 7,
            )

        # Create existing mandate covering Amazon + OFFICE_SUPPLIES
        _create_intent_mandate(
            test_db,
            user.id,
            {
                "max_amount": 100,
                "monthly_limit": 500,
                "merchant": "Amazon",
                "category": "office_supplies",
            },
        )

        suggestions = detect_patterns(test_db, user.id, org_id)

        amazon_suggestion = next(
            (s for s in suggestions if s["vendor"] == "Amazon"), None
        )
        assert amazon_suggestion is None


# ── Monthly Summary Service Tests ───────────────────────────────────


class TestMonthlySummaryService:
    def test_gathers_monthly_stats(self, test_db, user, org_id):
        from src.services.monthly_summary_service import gather_user_monthly_stats

        now = datetime.utcnow()

        # Create expenses this month
        for i in range(3):
            _create_expense(
                test_db,
                user.id,
                org_id,
                "Amazon",
                "OFFICE_SUPPLIES",
                50.00,
                auto_approved=True,
                auto_approved_via="intent_mandate",
                days_ago=i,
            )
        for i in range(2):
            _create_expense(
                test_db,
                user.id,
                org_id,
                "Uber",
                "TRAVEL",
                30.00,
                days_ago=i,
            )

        stats = gather_user_monthly_stats(test_db, user.id, now.year, now.month)

        assert stats is not None
        assert stats["total_expenses"] == 5
        assert stats["auto_approved_count"] == 3
        assert stats["manual_count"] == 2
        assert stats["by_mandate_count"] == 3
        assert stats["by_policy_count"] == 0
        assert stats["auto_approval_rate"] == 60.0
        assert stats["time_saved_minutes"] == 9  # 3 * 3 min
        assert stats["auto_approved_amount"] == 150.00
        assert stats["total_amount"] == 210.00
        assert len(stats["top_vendors"]) >= 1
        assert stats["top_vendors"][0]["vendor"] == "Amazon"
        assert stats["user_name"] == "Phase 23 Test User"

    def test_returns_none_for_no_expenses(self, test_db, user, org_id):
        from src.services.monthly_summary_service import gather_user_monthly_stats

        stats = gather_user_monthly_stats(test_db, user.id, 2020, 1)
        assert stats is None


# ── Suggest Mandate Endpoint Logic Tests ────────────────────────────


class TestSuggestMandate:
    def test_suggest_mandate_rounds_up(self):
        """Test the suggestion math from the ap2 route."""
        import math

        amount = 45.00
        suggested_max = math.ceil(amount / 25) * 25
        if suggested_max < amount * 1.2:
            suggested_max = math.ceil(amount * 1.2 / 25) * 25

        assert (
            suggested_max == 75
        )  # ceil(45/25)*25 = 50, 50 < 54 -> ceil(54/25)*25 = 75

        suggested_monthly = suggested_max * 5
        assert suggested_monthly == 375

    def test_suggest_mandate_small_amount(self):
        import math

        amount = 5.00
        suggested_max = math.ceil(amount / 25) * 25
        if suggested_max < amount * 1.2:
            suggested_max = math.ceil(amount * 1.2 / 25) * 25

        assert suggested_max == 25  # ceil(5/25)*25 = 25, 25 >= 6 -> 25


# ── Sample Mandates Tests ──────────────────────────────────────────


class TestSampleMandates:
    def test_sample_mandates_structure(self):
        """Verify sample mandate templates have required fields."""
        # Simulate what the endpoint returns
        templates = [
            {
                "name": "Office Supplies",
                "constraints": {
                    "max_amount": 100.00,
                    "monthly_limit": 300.00,
                    "category": "OFFICE_SUPPLIES",
                },
                "expiration_hours": 720,
            },
            {
                "name": "Software Subscriptions",
                "constraints": {
                    "max_amount": 50.00,
                    "monthly_limit": 200.00,
                    "category": "SOFTWARE",
                },
                "expiration_hours": 720,
            },
        ]

        for t in templates:
            assert "name" in t
            assert "constraints" in t
            assert "max_amount" in t["constraints"]
            assert "monthly_limit" in t["constraints"]
            assert "category" in t["constraints"]
            assert t["constraints"]["max_amount"] > 0
            assert t["constraints"]["monthly_limit"] >= t["constraints"]["max_amount"]
            assert t["expiration_hours"] > 0


# ── Analytics Logic Tests ──────────────────────────────────────────


class TestAnalyticsLogic:
    def test_cost_savings_calculation(self):
        """Test cost savings math."""
        auto_count = 20
        minutes_saved = auto_count * 3
        hours_saved = round(minutes_saved / 60, 1)
        dollar_savings = round(hours_saved * 50, 2)

        assert minutes_saved == 60
        assert hours_saved == 1.0
        assert dollar_savings == 50.0

    def test_bottleneck_rate_calculation(self):
        """Test bottleneck auto-approval rate math."""
        total = 10
        auto = 3
        rejected = 2

        auto_rate = (auto / total * 100) if total > 0 else 0
        rejection_rate = (rejected / total * 100) if total > 0 else 0

        assert auto_rate == 30.0
        assert rejection_rate == 20.0

    def test_trend_aggregation(self, test_db, user, org_id):
        """Test that expenses aggregate into daily trend buckets."""
        # Create a mix of auto and manual expenses
        _create_expense(
            test_db,
            user.id,
            org_id,
            "Amazon",
            "OFFICE_SUPPLIES",
            50.00,
            auto_approved=True,
            auto_approved_via="intent_mandate",
            days_ago=0,
        )
        _create_expense(
            test_db,
            user.id,
            org_id,
            "Uber",
            "TRAVEL",
            30.00,
            days_ago=0,
        )
        _create_expense(
            test_db,
            user.id,
            org_id,
            "Amazon",
            "OFFICE_SUPPLIES",
            60.00,
            auto_approved=True,
            auto_approved_via="approval_policy",
            days_ago=1,
        )

        # Query like the analytics endpoint does
        from collections import defaultdict

        from sqlalchemy import func as sqlfunc

        cutoff = datetime.utcnow() - timedelta(days=7)
        rows = (
            test_db.query(
                sqlfunc.date(Expense.created_at).label("day"),
                Expense.auto_approved,
                Expense.auto_approved_via,
                sqlfunc.count().label("cnt"),
            )
            .filter(
                Expense.organization_id == org_id,
                Expense.created_at >= cutoff,
            )
            .group_by(
                sqlfunc.date(Expense.created_at),
                Expense.auto_approved,
                Expense.auto_approved_via,
            )
            .all()
        )

        assert len(rows) >= 2  # at least 2 groups (auto + manual)

        total_auto = sum(r.cnt for r in rows if r.auto_approved)
        total_manual = sum(r.cnt for r in rows if not r.auto_approved)
        assert total_auto == 2
        assert total_manual == 1
