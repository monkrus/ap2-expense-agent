"""
Tests for GET /api/v1/auth/setup-status endpoint
First-run detection for new deployments / GCP Marketplace purchases.
"""


class TestSetupStatus:
    """Test the setup-status endpoint that drives the first-run wizard."""

    def test_empty_db_needs_setup(self, client):
        """Empty database → needs_setup: true (no users exist)"""
        response = client.get("/api/v1/auth/setup-status")
        assert response.status_code == 200
        data = response.json()
        assert data["needs_setup"] is True

    def test_with_users_no_setup_needed(self, client, test_user):
        """Database with users → needs_setup: false"""
        response = client.get("/api/v1/auth/setup-status")
        assert response.status_code == 200
        data = response.json()
        assert data["needs_setup"] is False
