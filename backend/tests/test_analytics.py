"""
Tests for Analytics API Routes
Tests dashboard, summary, variance, category reconciliation, user spending, and budget forecast endpoints.
"""

import uuid
from datetime import datetime

import pytest


class TestAnalyticsRoutes:
    """Test analytics-related API endpoints"""

    def test_dashboard(self, client, org_headers):
        """Test getting dashboard analytics"""
        response = client.get("/api/v1/analytics/dashboard", headers=org_headers)
        assert response.status_code == 200
        data = response.json()
        assert "spending_over_time" in data
        assert "category_breakdown" in data
        assert "status_distribution" in data
        assert "top_spenders" in data
        assert "monthly_comparison" in data
        assert "top_vendors" in data
        assert "period" in data

    def test_dashboard_with_days_param(self, client, org_headers):
        """Test dashboard analytics with custom days parameter"""
        response = client.get(
            "/api/v1/analytics/dashboard?days=90", headers=org_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["period"]["days"] == 90

    def test_dashboard_invalid_days(self, client, org_headers):
        """Test dashboard with out-of-range days parameter"""
        response = client.get("/api/v1/analytics/dashboard?days=1", headers=org_headers)
        assert response.status_code == 422

    def test_dashboard_requires_auth(self, client):
        """Test that dashboard requires authentication"""
        response = client.get("/api/v1/analytics/dashboard")
        assert response.status_code in (401, 403)

    def test_summary(self, client, org_headers):
        """Test getting analytics summary"""
        response = client.get("/api/v1/analytics/summary", headers=org_headers)
        assert response.status_code == 200
        data = response.json()
        assert "all_time" in data
        assert "this_month" in data
        assert "pending_approvals" in data
        assert "active_users" in data

    def test_summary_requires_auth(self, client):
        """Test that summary requires authentication"""
        response = client.get("/api/v1/analytics/summary")
        assert response.status_code in (401, 403)

    def test_variance_report(self, client, org_headers):
        """Test getting variance report"""
        response = client.get("/api/v1/analytics/variance-report", headers=org_headers)
        assert response.status_code == 200
        data = response.json()
        assert "budgets" in data
        assert "total_budgeted" in data
        assert "total_actual" in data

    def test_variance_report_with_period(self, client, org_headers):
        """Test variance report with period parameter"""
        response = client.get(
            "/api/v1/analytics/variance-report?period=quarterly",
            headers=org_headers,
        )
        assert response.status_code == 200

    def test_category_reconciliation(self, client, org_headers):
        """Test getting category reconciliation report"""
        response = client.get(
            "/api/v1/analytics/category-reconciliation", headers=org_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert "total_budgeted" in data
        assert "total_actual" in data

    def test_category_reconciliation_with_dates(self, client, org_headers):
        """Test category reconciliation with date filters"""
        response = client.get(
            "/api/v1/analytics/category-reconciliation"
            "?start_date=2026-01-01&end_date=2026-02-28",
            headers=org_headers,
        )
        assert response.status_code == 200

    def test_category_reconciliation_invalid_dates(self, client, org_headers):
        """Test category reconciliation with invalid date format"""
        response = client.get(
            "/api/v1/analytics/category-reconciliation?start_date=bad-date",
            headers=org_headers,
        )
        assert response.status_code == 400

    def test_user_spending(self, client, org_headers):
        """Test getting user spending report"""
        response = client.get("/api/v1/analytics/user-spending", headers=org_headers)
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "total_users" in data
        assert "total_spending" in data

    def test_user_spending_with_period(self, client, org_headers):
        """Test user spending report with period parameter"""
        response = client.get(
            "/api/v1/analytics/user-spending?period=yearly",
            headers=org_headers,
        )
        assert response.status_code == 200

    def test_budget_forecast_not_found(self, client, org_headers):
        """Test budget forecast with non-existent budget ID"""
        response = client.get(
            "/api/v1/analytics/budget-forecast/nonexistent_budget_99999",
            headers=org_headers,
        )
        assert response.status_code == 404

    def test_budget_forecast_requires_auth(self, client):
        """Test that budget forecast requires authentication"""
        response = client.get("/api/v1/analytics/budget-forecast/some_id")
        assert response.status_code in (401, 403)

    def test_dashboard_with_expenses(self, client, org_headers, test_expense):
        """Test dashboard returns data when expenses exist"""
        response = client.get("/api/v1/analytics/dashboard", headers=org_headers)
        assert response.status_code == 200
        data = response.json()
        # With at least one expense, we should have some data
        assert isinstance(data["spending_over_time"], list)
        assert isinstance(data["category_breakdown"], list)

    def test_summary_with_expenses(self, client, org_headers, test_expense):
        """Test summary returns correct counts when expenses exist"""
        response = client.get("/api/v1/analytics/summary", headers=org_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["all_time"]["total_expenses"] >= 1
        assert data["all_time"]["total_amount"] > 0
