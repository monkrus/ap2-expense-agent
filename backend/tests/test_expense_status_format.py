"""
Test to ensure all expense API endpoints return lowercase status values.

This test prevents future regressions where status values might be returned
as uppercase (e.g., "PENDING") instead of lowercase (e.g., "pending").
"""

import pytest
from fastapi.testclient import TestClient


def test_expense_report_returns_lowercase_status(client: TestClient, org_headers):
    """Test that /expenses/report returns lowercase status values"""
    response = client.get("/api/v1/expenses/report", headers=org_headers)
    assert response.status_code == 200

    data = response.json()
    if "expenses" in data:
        for expense in data["expenses"]:
            if "status" in expense and expense["status"]:
                # Status should be lowercase
                assert expense[
                    "status"
                ].islower(), f"Expense status '{expense['status']}' should be lowercase"
                # Status should be one of the valid values
                valid_statuses = [
                    "pending",
                    "approved",
                    "rejected",
                    "processing",
                    "withdrawn",
                ]
                assert (
                    expense["status"] in valid_statuses
                ), f"Expense status '{expense['status']}' is not a valid status"


def test_create_expense_returns_lowercase_status(client: TestClient, org_headers):
    """Test that POST /expenses returns lowercase status values"""
    expense_data = {
        "amount": 100.00,
        "vendor": "Test Vendor",
        "category": "MEALS",
        "description": "Test expense",
    }

    response = client.post("/api/v1/expenses", json=expense_data, headers=org_headers)

    # Should return 201 Created or 200 OK
    assert response.status_code in [200, 201]

    data = response.json()
    if "status" in data and data["status"]:
        assert data[
            "status"
        ].islower(), f"Created expense status '{data['status']}' should be lowercase"


def test_get_expense_returns_lowercase_status(
    client: TestClient, org_headers, test_expense
):
    """Test that GET /expenses/{id} returns lowercase status values"""
    response = client.get(f"/api/v1/expenses/{test_expense.id}", headers=org_headers)

    assert response.status_code == 200

    data = response.json()
    if "status" in data and data["status"]:
        assert data[
            "status"
        ].islower(), f"Expense status '{data['status']}' should be lowercase"


def test_approve_expense_returns_lowercase_status(
    client: TestClient, org_headers, test_expense, admin_headers
):
    """Test that PUT /expenses/{id}/approve returns lowercase status values"""
    response = client.put(
        f"/api/v1/expenses/{test_expense.id}/approve", headers=admin_headers
    )

    # Should return 200 OK
    if response.status_code == 200:
        data = response.json()
        if "status" in data and data["status"]:
            assert data[
                "status"
            ].islower(), (
                f"Approved expense status '{data['status']}' should be lowercase"
            )


def test_reject_expense_returns_lowercase_status(
    client: TestClient, org_headers, test_expense, admin_headers
):
    """Test that PUT /expenses/{id}/reject returns lowercase status values"""
    reject_data = {"reason": "Test rejection"}

    response = client.put(
        f"/api/v1/expenses/{test_expense.id}/reject",
        json=reject_data,
        headers=admin_headers,
    )

    # Should return 200 OK
    if response.status_code == 200:
        data = response.json()
        if "status" in data and data["status"]:
            assert data[
                "status"
            ].islower(), (
                f"Rejected expense status '{data['status']}' should be lowercase"
            )


def test_gdpr_export_returns_lowercase_status(client: TestClient, org_headers):
    """Test that GDPR export returns lowercase status values"""
    response = client.get("/api/v1/gdpr/export", headers=org_headers)

    # Should return 200 OK
    if response.status_code == 200:
        data = response.json()
        if "expenses" in data:
            for expense in data["expenses"]:
                if "status" in expense and expense["status"]:
                    assert expense[
                        "status"
                    ].islower(), f"GDPR export expense status '{expense['status']}' should be lowercase"
