"""
Tests for Recurring Expenses and Notifications API Routes
Tests CRUD operations for recurring expense templates, pause/resume, and notification endpoints.
"""

from datetime import datetime, timedelta

import pytest


class TestRecurringExpenses:
    """Test recurring expense template API endpoints"""

    def _create_recurring_expense(self, client, org_headers):
        """Helper to create a recurring expense and return the response data"""
        payload = {
            "vendor": "Netflix",
            "amount": 15.99,
            "category": "SOFTWARE",
            "description": "Monthly subscription",
            "frequency": "monthly",
            "start_date": datetime.utcnow().isoformat(),
            "auto_submit": True,
        }
        response = client.post(
            "/api/recurring-expenses", json=payload, headers=org_headers
        )
        return response

    def test_create_recurring_expense(self, client, org_headers):
        """Test creating a recurring expense template"""
        response = self._create_recurring_expense(client, org_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["vendor"] == "Netflix"
        assert data["amount"] == 15.99
        assert data["category"] == "SOFTWARE"
        assert data["frequency"] == "monthly"
        assert data["is_active"] is True
        assert data["is_paused"] is False
        assert "id" in data

    def test_create_recurring_expense_missing_fields(self, client, org_headers):
        """Test creating a recurring expense with missing required fields"""
        payload = {"vendor": "Netflix"}
        response = client.post(
            "/api/recurring-expenses", json=payload, headers=org_headers
        )
        assert response.status_code == 422

    def test_create_recurring_expense_invalid_amount(self, client, org_headers):
        """Test creating a recurring expense with invalid amount"""
        payload = {
            "vendor": "Netflix",
            "amount": -5.00,
            "category": "SOFTWARE",
            "description": "Monthly subscription",
            "frequency": "monthly",
            "start_date": datetime.utcnow().isoformat(),
        }
        response = client.post(
            "/api/recurring-expenses", json=payload, headers=org_headers
        )
        assert response.status_code == 422

    def test_list_recurring_expenses(self, client, org_headers):
        """Test listing recurring expense templates"""
        # Create one first
        self._create_recurring_expense(client, org_headers)

        response = client.get("/api/recurring-expenses", headers=org_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_list_recurring_expenses_empty(self, client, org_headers):
        """Test listing recurring expenses when none exist"""
        response = client.get("/api/recurring-expenses", headers=org_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_recurring_expense(self, client, org_headers):
        """Test getting a specific recurring expense template"""
        create_response = self._create_recurring_expense(client, org_headers)
        template_id = create_response.json()["id"]

        response = client.get(
            f"/api/recurring-expenses/{template_id}", headers=org_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == template_id
        assert data["vendor"] == "Netflix"

    def test_get_recurring_expense_not_found(self, client, org_headers):
        """Test getting a non-existent recurring expense template"""
        response = client.get(
            "/api/recurring-expenses/nonexistent_99999", headers=org_headers
        )
        assert response.status_code == 404

    def test_update_recurring_expense(self, client, org_headers):
        """Test updating a recurring expense template"""
        create_response = self._create_recurring_expense(client, org_headers)
        template_id = create_response.json()["id"]

        update_payload = {"amount": 19.99, "vendor": "Netflix Premium"}
        response = client.patch(
            f"/api/recurring-expenses/{template_id}",
            json=update_payload,
            headers=org_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["amount"] == 19.99
        assert data["vendor"] == "Netflix Premium"

    def test_update_recurring_expense_not_found(self, client, org_headers):
        """Test updating a non-existent recurring expense template"""
        response = client.patch(
            "/api/recurring-expenses/nonexistent_99999",
            json={"amount": 25.00},
            headers=org_headers,
        )
        assert response.status_code == 404

    def test_delete_recurring_expense(self, client, org_headers):
        """Test deleting a recurring expense template"""
        create_response = self._create_recurring_expense(client, org_headers)
        template_id = create_response.json()["id"]

        response = client.delete(
            f"/api/recurring-expenses/{template_id}", headers=org_headers
        )
        assert response.status_code == 204

        # Verify it's deleted
        get_response = client.get(
            f"/api/recurring-expenses/{template_id}", headers=org_headers
        )
        assert get_response.status_code == 404

    def test_delete_recurring_expense_not_found(self, client, org_headers):
        """Test deleting a non-existent recurring expense template"""
        response = client.delete(
            "/api/recurring-expenses/nonexistent_99999", headers=org_headers
        )
        assert response.status_code == 404

    def test_pause_recurring_expense(self, client, org_headers):
        """Test pausing a recurring expense template"""
        create_response = self._create_recurring_expense(client, org_headers)
        template_id = create_response.json()["id"]

        response = client.post(
            f"/api/recurring-expenses/{template_id}/pause", headers=org_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_paused"] is True

    def test_pause_recurring_expense_not_found(self, client, org_headers):
        """Test pausing a non-existent recurring expense template"""
        response = client.post(
            "/api/recurring-expenses/nonexistent_99999/pause", headers=org_headers
        )
        assert response.status_code == 404

    def test_resume_recurring_expense(self, client, org_headers):
        """Test resuming a paused recurring expense template"""
        create_response = self._create_recurring_expense(client, org_headers)
        template_id = create_response.json()["id"]

        # Pause first
        client.post(f"/api/recurring-expenses/{template_id}/pause", headers=org_headers)

        # Resume
        response = client.post(
            f"/api/recurring-expenses/{template_id}/resume", headers=org_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_paused"] is False

    def test_resume_recurring_expense_not_found(self, client, org_headers):
        """Test resuming a non-existent recurring expense template"""
        response = client.post(
            "/api/recurring-expenses/nonexistent_99999/resume", headers=org_headers
        )
        assert response.status_code == 404

    def test_recurring_expense_requires_auth(self, client):
        """Test that recurring expense endpoints require authentication"""
        response = client.get("/api/recurring-expenses")
        assert response.status_code in (401, 403)

    def test_create_with_all_frequencies(self, client, org_headers):
        """Test creating recurring expenses with different frequencies"""
        for freq in ["weekly", "biweekly", "monthly", "quarterly", "yearly"]:
            payload = {
                "vendor": f"Vendor {freq}",
                "amount": 10.00,
                "category": "SOFTWARE",
                "description": f"{freq} subscription",
                "frequency": freq,
                "start_date": datetime.utcnow().isoformat(),
            }
            response = client.post(
                "/api/recurring-expenses", json=payload, headers=org_headers
            )
            assert response.status_code == 201, f"Failed for frequency: {freq}"
            assert response.json()["frequency"] == freq


class TestNotifications:
    """Test notification API endpoints (from routes/notifications.py)"""

    def test_get_notifications(self, client, org_headers):
        """Test getting notifications for the current user"""
        response = client.get("/api/notifications", headers=org_headers)
        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data
        assert "unread_count" in data

    def test_get_notifications_requires_auth(self, client):
        """Test that notifications endpoint requires authentication"""
        response = client.get("/api/notifications")
        assert response.status_code in (401, 403)

    def test_unread_count(self, client, org_headers):
        """Test getting unread notification count"""
        response = client.get("/api/notifications/unread-count", headers=org_headers)
        assert response.status_code == 200
        data = response.json()
        assert "unread_count" in data
        assert isinstance(data["unread_count"], int)

    def test_unread_count_requires_auth(self, client):
        """Test that unread count endpoint requires authentication"""
        response = client.get("/api/notifications/unread-count")
        assert response.status_code in (401, 403)

    def test_mark_all_read(self, client, org_headers):
        """Test marking all notifications as read"""
        response = client.post("/api/notifications/mark-all-read", headers=org_headers)
        assert response.status_code == 200

    def test_mark_notification_read_not_found(self, client, org_headers):
        """Test marking a non-existent notification as read"""
        response = client.post(
            "/api/notifications/nonexistent_99999/read", headers=org_headers
        )
        assert response.status_code == 404

    def test_delete_notification_not_found(self, client, org_headers):
        """Test deleting a non-existent notification"""
        response = client.delete(
            "/api/notifications/nonexistent_99999", headers=org_headers
        )
        assert response.status_code == 404
