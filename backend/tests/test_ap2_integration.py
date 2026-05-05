"""
Integration tests for AP2 Phase 2 & Phase 3 API endpoints.

Uses FastAPI TestClient with the shared conftest fixtures (client, auth_headers,
org_headers, db_session, test_user, etc.).
"""

import json
import uuid
from datetime import datetime, timedelta

import pytest

from src.models import (
    Expense,
    ExpenseStatus,
    IntentMandate,
    OrganizationMember,
)

# ── Helpers ────────────────────────────────────────────────────────


def _get_org_id(db_session, user_id):
    """Get user's organization ID from membership."""
    membership = (
        db_session.query(OrganizationMember)
        .filter(OrganizationMember.user_id == user_id)
        .first()
    )
    return membership.organization_id if membership else ""


def _seed_expenses(
    db_session,
    user_id,
    org_id,
    vendor,
    category,
    count,
    amount=50.0,
    auto_approved=False,
    auto_approved_via=None,
    status=ExpenseStatus.APPROVED,
):
    """Create a batch of expenses for testing."""
    expenses = []
    for i in range(count):
        exp = Expense(
            id=f"EXP-{uuid.uuid4().hex[:12].upper()}",
            user_id=user_id,
            organization_id=org_id,
            vendor=vendor,
            category=category,
            amount=amount + i,
            description=f"Test {vendor} expense #{i+1}",
            status=status,
            date=datetime.utcnow() - timedelta(days=i * 7),
            created_at=datetime.utcnow() - timedelta(days=i * 7),
            auto_approved=auto_approved,
            auto_approved_via=auto_approved_via,
        )
        db_session.add(exp)
        expenses.append(exp)
    db_session.commit()
    return expenses


def _seed_intent_mandate(db_session, user_id, constraints, status="active", hours=720):
    """Create an Intent Mandate for testing."""
    mandate = IntentMandate(
        id=str(uuid.uuid4()),
        user_id=user_id,
        constraints=json.dumps(constraints),
        timestamp=datetime.utcnow(),
        status=status,
        expiration=datetime.utcnow() + timedelta(hours=hours),
        created_at=datetime.utcnow(),
    )
    db_session.add(mandate)
    db_session.commit()
    return mandate


# ── Sample Mandates (Onboarding) ──────────────────────────────────


class TestSampleMandatesEndpoint:
    def test_returns_templates(self, client, auth_headers):
        response = client.get("/api/ap2/sample-mandates", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert len(data["templates"]) == 4
        names = [t["name"] for t in data["templates"]]
        assert "Office Supplies" in names
        assert "Travel Expenses" in names

    def test_requires_auth(self, client):
        response = client.get("/api/ap2/sample-mandates")
        assert response.status_code == 401


# ── Suggest Mandate Endpoint ──────────────────────────────────────


class TestSuggestMandateEndpoint:
    def test_suggests_constraints(self, client, auth_headers):
        response = client.post(
            "/api/ap2/suggest-mandate",
            headers=auth_headers,
            json={"amount": 45.0, "category": "OFFICE_SUPPLIES", "vendor": "Amazon"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "suggested_constraints" in data
        sc = data["suggested_constraints"]
        assert sc["max_amount"] >= 45.0
        assert sc["monthly_limit"] > sc["max_amount"]
        assert sc["category"] == "OFFICE_SUPPLIES"
        assert sc["merchant"] == "Amazon"
        assert "explanation" in data

    def test_small_amount(self, client, auth_headers):
        response = client.post(
            "/api/ap2/suggest-mandate",
            headers=auth_headers,
            json={"amount": 5.0, "category": "OTHER", "vendor": "Corner Store"},
        )
        assert response.status_code == 200
        assert response.json()["suggested_constraints"]["max_amount"] == 25

    def test_requires_auth(self, client):
        response = client.post(
            "/api/ap2/suggest-mandate",
            json={"amount": 10.0, "category": "OTHER", "vendor": "X"},
        )
        assert response.status_code == 401


# ── Check Auto-Approval Endpoint ─────────────────────────────────


class TestCheckAutoApprovalEndpoint:
    def test_no_mandates_returns_false(self, client, auth_headers):
        response = client.post(
            "/api/ap2/check-auto-approval",
            headers=auth_headers,
            json={"amount": 50.0, "category": "OFFICE_SUPPLIES", "vendor": "Amazon"},
        )
        assert response.status_code == 200
        assert response.json()["will_auto_approve"] is False

    def test_matching_mandate_returns_true(
        self, client, auth_headers, db_session, test_user
    ):
        org_id = _get_org_id(db_session, test_user.id)
        _seed_intent_mandate(
            db_session,
            test_user.id,
            {
                "max_amount": 100,
                "monthly_limit": 500,
                "category": "office_supplies",
                "merchant": "Amazon",
            },
        )

        response = client.post(
            "/api/ap2/check-auto-approval",
            headers=auth_headers,
            json={"amount": 50.0, "category": "OFFICE_SUPPLIES", "vendor": "Amazon"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["will_auto_approve"] is True
        assert data["via"] == "intent_mandate"

    def test_requires_auth(self, client):
        response = client.post(
            "/api/ap2/check-auto-approval",
            json={"amount": 10.0, "category": "OTHER", "vendor": "X"},
        )
        assert response.status_code == 401


# ── Mandate Suggestions (AI Pattern Detection) ───────────────────


class TestMandateSuggestionsEndpoint:
    def test_returns_suggestions_for_recurring_vendor(
        self, client, auth_headers, db_session, test_user
    ):
        org_id = _get_org_id(db_session, test_user.id)
        _seed_expenses(
            db_session,
            test_user.id,
            org_id,
            vendor="Amazon",
            category="OFFICE_SUPPLIES",
            count=5,
            amount=40.0,
            auto_approved=False,
        )

        response = client.get("/api/ap2/mandate-suggestions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert data["count"] >= 1
        amazon = next((s for s in data["suggestions"] if s["vendor"] == "Amazon"), None)
        assert amazon is not None
        assert amazon["expense_count"] == 5

    def test_no_suggestions_when_below_minimum(
        self, client, auth_headers, db_session, test_user
    ):
        org_id = _get_org_id(db_session, test_user.id)
        _seed_expenses(
            db_session,
            test_user.id,
            org_id,
            vendor="RareVendor",
            category="OTHER",
            count=2,
        )

        response = client.get("/api/ap2/mandate-suggestions", headers=auth_headers)
        assert response.status_code == 200
        rare = next(
            (s for s in response.json()["suggestions"] if s["vendor"] == "RareVendor"),
            None,
        )
        assert rare is None

    def test_requires_auth(self, client):
        response = client.get("/api/ap2/mandate-suggestions")
        assert response.status_code == 401


# ── Analytics: Trends ─────────────────────────────────────────────


class TestAnalyticsTrendsEndpoint:
    def test_returns_trend_data(self, client, auth_headers, db_session, test_user):
        org_id = _get_org_id(db_session, test_user.id)
        _seed_expenses(
            db_session,
            test_user.id,
            org_id,
            vendor="Amazon",
            category="OFFICE_SUPPLIES",
            count=3,
            auto_approved=True,
            auto_approved_via="intent_mandate",
        )
        _seed_expenses(
            db_session,
            test_user.id,
            org_id,
            vendor="Uber",
            category="TRAVEL",
            count=2,
            auto_approved=False,
        )

        response = client.get("/api/ap2/analytics/trends?days=30", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "trend" in data
        assert data["total_expenses"] == 5
        assert data["total_auto_approved"] == 3
        assert data["overall_auto_approval_rate"] == 60.0

    def test_empty_org_returns_zero(self, client, auth_headers):
        response = client.get("/api/ap2/analytics/trends?days=7", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_expenses"] == 0
        assert data["overall_auto_approval_rate"] == 0

    def test_requires_auth(self, client):
        response = client.get("/api/ap2/analytics/trends")
        assert response.status_code == 401


# ── Analytics: Cost Savings ───────────────────────────────────────


class TestAnalyticsCostSavingsEndpoint:
    def test_calculates_savings(self, client, auth_headers, db_session, test_user):
        org_id = _get_org_id(db_session, test_user.id)
        _seed_expenses(
            db_session,
            test_user.id,
            org_id,
            vendor="Staples",
            category="OFFICE_SUPPLIES",
            count=10,
            auto_approved=True,
            auto_approved_via="intent_mandate",
        )
        _seed_expenses(
            db_session,
            test_user.id,
            org_id,
            vendor="Uber",
            category="TRAVEL",
            count=5,
            auto_approved=False,
        )

        response = client.get(
            "/api/ap2/analytics/cost-savings?days=90", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["auto_approved_count"] == 10
        assert data["total_count"] == 15
        assert data["minutes_saved"] == 30  # 10 * 3
        assert data["hours_saved"] == 0.5
        assert data["estimated_dollar_savings"] == 25.0
        assert data["rate"] > 0

    def test_empty_returns_zeros(self, client, auth_headers):
        response = client.get(
            "/api/ap2/analytics/cost-savings?days=7", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["auto_approved_count"] == 0
        assert data["rate"] == 0

    def test_requires_auth(self, client):
        response = client.get("/api/ap2/analytics/cost-savings")
        assert response.status_code == 401


# ── Analytics: Bottlenecks ────────────────────────────────────────


class TestAnalyticsBottlenecksEndpoint:
    def test_identifies_bottleneck_categories(
        self, client, auth_headers, db_session, test_user
    ):
        org_id = _get_org_id(db_session, test_user.id)
        # Office supplies: all auto-approved (high rate)
        _seed_expenses(
            db_session,
            test_user.id,
            org_id,
            vendor="Staples",
            category="OFFICE_SUPPLIES",
            count=5,
            auto_approved=True,
            auto_approved_via="intent_mandate",
        )

        # Travel: none auto-approved (bottleneck)
        _seed_expenses(
            db_session,
            test_user.id,
            org_id,
            vendor="Uber",
            category="TRAVEL",
            count=4,
            auto_approved=False,
        )

        response = client.get(
            "/api/ap2/analytics/bottlenecks?days=90", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "category_bottlenecks" in data
        assert "vendor_bottlenecks" in data

        # TRAVEL should be the biggest bottleneck (0% auto-approval)
        cats = data["category_bottlenecks"]
        if cats:
            # Sorted ascending by auto_approval_rate, so worst first
            assert cats[0]["auto_approval_rate"] <= cats[-1]["auto_approval_rate"]

    def test_requires_auth(self, client):
        response = client.get("/api/ap2/analytics/bottlenecks")
        assert response.status_code == 401


# ── Monthly Summary Endpoint ─────────────────────────────────────


class TestMonthlySummaryEndpoint:
    def test_returns_summary(self, client, auth_headers, db_session, test_user):
        org_id = _get_org_id(db_session, test_user.id)
        now = datetime.utcnow()

        # Seed expenses all on today (same month guaranteed)
        for i in range(3):
            exp = Expense(
                id=f"EXP-SUMMARY-{uuid.uuid4().hex[:8].upper()}",
                user_id=test_user.id,
                organization_id=org_id,
                vendor="Amazon",
                category="OFFICE_SUPPLIES",
                amount=50.0 + i,
                description=f"Summary test #{i+1}",
                status=ExpenseStatus.APPROVED,
                date=now,
                created_at=now,
                auto_approved=True,
                auto_approved_via="intent_mandate",
            )
            db_session.add(exp)
        db_session.commit()

        response = client.post(
            "/api/ap2/send-monthly-summary",
            headers=auth_headers,
            json={"year": now.year, "month": now.month},
        )
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert data["summary"] is not None
        assert data["summary"]["total_expenses"] >= 3
        assert data["summary"]["auto_approved_count"] >= 3

    def test_no_expenses_returns_not_sent(self, client, auth_headers):
        response = client.post(
            "/api/ap2/send-monthly-summary",
            headers=auth_headers,
            json={"year": 2020, "month": 1},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["sent"] is False

    def test_requires_auth(self, client):
        response = client.post("/api/ap2/send-monthly-summary", json={})
        assert response.status_code == 401


# ── Admin-only: Send All Summaries ────────────────────────────────


class TestSendAllSummariesEndpoint:
    def test_forbidden_for_employee(self, client, auth_headers):
        response = client.post(
            "/api/ap2/send-monthly-summary/all",
            headers=auth_headers,
            json={},
        )
        assert response.status_code == 403

    def test_requires_auth(self, client):
        response = client.post("/api/ap2/send-monthly-summary/all", json={})
        assert response.status_code == 401


# ── Protocol Info (public-ish) ────────────────────────────────────


class TestProtocolInfoEndpoint:
    def test_returns_protocol_info(self, client):
        response = client.get("/api/ap2/protocol-info")
        assert response.status_code == 200
        data = response.json()
        assert "@context" in data
        assert data["@type"] == "ProtocolInfo"
        assert "ap2_protocol_version" in data
        assert data["features"]["mandate_revocation"] is True

    def test_agent_card(self, client):
        response = client.get("/api/ap2/.well-known/agent.json")
        assert response.status_code == 200
        data = response.json()
        assert data["@type"] == "AgentCard"
        assert "capabilities" in data
        assert "intent_mandates" in data["capabilities"]
