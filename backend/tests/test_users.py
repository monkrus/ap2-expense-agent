"""
Tests for user management endpoints
"""

import pytest


class TestUserManagement:
    """Test user CRUD operations"""

    def test_get_current_user(self, client, auth_headers):
        """Test getting current user info"""
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"

    def test_list_users_as_manager(self, client, manager_headers):
        """Test listing users as manager"""
        response = client.get("/api/v1/users/", headers=manager_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_users_as_employee_forbidden(self, client, auth_headers):
        """Test that employees cannot list all users"""
        response = client.get("/api/v1/users/", headers=auth_headers)
        assert response.status_code == 403

    def test_create_user_as_admin(self, client, admin_headers):
        """Test creating user as admin"""
        response = client.post(
            "/api/v1/users/",
            headers=admin_headers,
            json={
                "email": "created@example.com",
                "username": "createduser",
                "password": "CreatedPassword123!",
                "full_name": "Created User",
                "role": "employee",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "createduser"
        assert data["is_verified"] == True  # Admin-created users are pre-verified

    def test_create_user_as_employee_forbidden(self, client, auth_headers):
        """Test that employees cannot create users"""
        response = client.post(
            "/api/v1/users/",
            headers=auth_headers,
            json={
                "email": "attempt@example.com",
                "username": "attemptuser",
                "password": "Password123!",
                "full_name": "Attempt User",
                "role": "employee",
            },
        )
        assert response.status_code == 403

    def test_update_own_profile(self, client, auth_headers, test_user):
        """Test user updating their own profile"""
        response = client.patch(
            f"/api/v1/users/{test_user.id}",
            headers=auth_headers,
            json={"full_name": "Updated Test User"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Test User"

    def test_update_other_user_as_employee_forbidden(
        self, client, auth_headers, test_admin
    ):
        """Test that employees cannot update other users"""
        response = client.patch(
            f"/api/v1/users/{test_admin.id}",
            headers=auth_headers,
            json={"full_name": "Hacked Admin"},
        )
        assert response.status_code == 403

    def test_update_user_role_as_admin(self, client, admin_headers, test_user):
        """Test admin updating user role"""
        response = client.patch(
            f"/api/v1/users/{test_user.id}",
            headers=admin_headers,
            json={"role": "manager"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "manager"

    def test_employee_cannot_change_own_role(self, client, auth_headers, test_user):
        """Test that employees cannot change their own role"""
        response = client.patch(
            f"/api/v1/users/{test_user.id}",
            headers=auth_headers,
            json={"role": "admin"},
        )
        assert response.status_code == 403

    def test_delete_user_as_admin(self, client, admin_headers, test_user):
        """Test deleting user as admin"""
        response = client.delete(f"/api/v1/users/{test_user.id}", headers=admin_headers)
        assert response.status_code == 204

    def test_admin_cannot_delete_self(self, client, admin_headers, test_admin):
        """Test that admin cannot delete their own account"""
        response = client.delete(
            f"/api/v1/users/{test_admin.id}", headers=admin_headers
        )
        assert response.status_code == 400
        assert "Cannot delete your own account" in response.json()["detail"]


class TestSessionManagement:
    """Test session management"""

    def test_get_user_sessions(self, client, auth_headers, test_user):
        """Test getting user sessions"""
        response = client.get(
            f"/api/v1/users/{test_user.id}/sessions", headers=auth_headers
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_revoke_session(self, client, auth_headers, test_user, db_session):
        """Test revoking a session"""
        # Get sessions
        sessions_response = client.get(
            f"/api/v1/users/{test_user.id}/sessions", headers=auth_headers
        )
        sessions = sessions_response.json()

        if len(sessions) > 0:
            session_id = sessions[0]["id"]

            # Revoke session
            response = client.delete(
                f"/api/v1/users/{test_user.id}/sessions/{session_id}",
                headers=auth_headers,
            )
            assert response.status_code == 200
