"""
Authentication tests - streamlined and focused
"""

import pytest
from datetime import datetime


class TestRegistration:
    """Test user registration endpoints"""

    def test_register_new_user(self, client):
        """Test successful registration of a new user"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@test.com",
                "username": "newuser",
                "password": "SecurePass123!",
                "full_name": "New User",
                "role": "employee",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@test.com"
        assert data["username"] == "newuser"
        assert "hashed_password" not in data

    def test_register_duplicate_email(self, client, test_user):
        """Test registration with duplicate email fails"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "username": "different",
                "password": "SecurePass123!",
                "full_name": "Different User",
                "role": "employee",
            },
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_register_weak_password(self, client):
        """Test registration with weak password fails"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak@test.com",
                "username": "weakuser",
                "password": "weak",
                "full_name": "Weak User",
                "role": "employee",
            },
        )
        assert response.status_code == 422  # Pydantic validation error


class TestLogin:
    """Test user login endpoints"""

    def test_login_success(self, client, test_user):
        """Test successful login"""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "TestPass123!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_user):
        """Test login with wrong password fails"""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "WrongPassword123!"},
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        """Test login with nonexistent user fails"""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "nonexistent", "password": "Password123!"},
        )
        assert response.status_code == 401


class TestGetCurrentUser:
    """Test getting current user information"""

    def test_get_current_user(self, client, auth_headers):
        """Test getting current authenticated user"""
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["username"] == "testuser"

    def test_get_current_user_unauthorized(self, client):
        """Test getting current user without auth fails"""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401


class TestAdminAccess:
    """Test admin-only endpoints"""

    def test_admin_can_access_admin_endpoint(self, client, admin_headers):
        """Test admin can access admin endpoints"""
        response = client.get("/api/v1/admin/users", headers=admin_headers)
        # Should not be 403 (forbidden)
        assert response.status_code in [200, 404]

    def test_regular_user_cannot_access_admin_endpoint(self, client, auth_headers):
        """Test regular user cannot access admin endpoints"""
        response = client.get("/api/v1/admin/users", headers=auth_headers)
        assert response.status_code == 403
