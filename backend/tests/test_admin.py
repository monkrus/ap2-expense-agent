"""
Tests for admin endpoints
"""

import pytest


class TestAdminEndpoints:
    """Test admin-only endpoints"""

    def test_get_database_stats_as_admin(self, client, admin_headers):
        """Test getting database statistics as admin"""
        response = client.get("/api/v1/admin/stats/database", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "sessions" in data
        assert "audit_logs" in data
        assert "tokens" in data

    def test_get_stats_as_employee_forbidden(self, client, auth_headers):
        """Test that employees cannot access admin stats"""
        response = client.get("/api/v1/admin/stats/database", headers=auth_headers)
        assert response.status_code == 403

    def test_run_maintenance_as_admin(self, client, admin_headers):
        """Test running maintenance tasks as admin"""
        response = client.post("/api/v1/admin/maintenance", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "statistics" in data

    def test_cleanup_audit_logs(self, client, admin_headers):
        """Test cleaning up audit logs"""
        response = client.post(
            "/api/v1/admin/maintenance/audit-logs", headers=admin_headers
        )
        assert response.status_code == 200
        assert "deleted_count" in response.json()

    def test_cleanup_sessions(self, client, admin_headers):
        """Test cleaning up sessions"""
        response = client.post(
            "/api/v1/admin/maintenance/sessions", headers=admin_headers
        )
        assert response.status_code == 200
        assert "deleted_count" in response.json()

    def test_cleanup_tokens(self, client, admin_headers):
        """Test cleaning up tokens"""
        response = client.post(
            "/api/v1/admin/maintenance/tokens", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_deleted" in data

    def test_unlock_user_account(self, client, admin_headers, test_user, db_session):
        """Test unlocking a user account"""
        from datetime import datetime, timedelta

        # Lock the user account
        test_user.failed_login_attempts = 5
        test_user.locked_until = datetime.utcnow() + timedelta(minutes=30)
        db_session.commit()

        # Unlock as admin
        response = client.post(
            f"/api/v1/admin/users/{test_user.id}/unlock", headers=admin_headers
        )
        assert response.status_code == 200
        assert "unlocked successfully" in response.json()["message"]

        # Verify user can now login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "TestPass123!"},
        )
        assert login_response.status_code == 200
