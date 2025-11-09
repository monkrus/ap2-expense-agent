"""
Tests for authentication endpoints
"""
import pytest
from datetime import datetime, timedelta


class TestRegistration:
    """Test user registration"""

    def test_register_success(self, client):
        """Test successful user registration"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "NewPassword123!",
                "full_name": "New User",
                "role": "employee"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"
        assert "hashed_password" not in data

    def test_register_duplicate_email(self, client, test_user):
        """Test registration with duplicate email"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "username": "differentuser",
                "password": "Password123!",
                "full_name": "Different User",
                "role": "employee"
            }
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_register_weak_password(self, client):
        """Test registration with weak password"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak@example.com",
                "username": "weakuser",
                "password": "weak",
                "full_name": "Weak User",
                "role": "employee"
            }
        )
        assert response.status_code == 422  # Validation error


class TestLogin:
    """Test user login"""

    def test_login_success(self, client, test_user):
        """Test successful login"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "TestPass123!"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["username"] == "testuser"

    def test_login_wrong_password(self, client, test_user):
        """Test login with wrong password"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "WrongPassword123!"
            }
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        """Test login with nonexistent user"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "nonexistent",
                "password": "Password123!"
            }
        )
        assert response.status_code == 401

    def test_account_lockout(self, client, test_user):
        """Test account lockout after failed attempts"""
        # Attempt 5 failed logins
        for i in range(5):
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "username": "testuser",
                    "password": "WrongPassword!"
                }
            )
            if i < 4:
                assert response.status_code == 401
                assert "attempts remaining" in response.json()["detail"]

        # 5th attempt should lock the account
        assert response.status_code == 423
        assert "locked" in response.json()["detail"].lower()

    def test_login_after_lockout_expiry(self, client, test_user, db_session):
        """Test login after lockout period expires"""
        # Lock the account manually
        test_user.failed_login_attempts = 5
        test_user.locked_until = datetime.utcnow() - timedelta(minutes=1)  # Expired
        db_session.commit()

        # Should be able to login
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "TestPass123!"
            }
        )
        assert response.status_code == 200


class TestTokenRefresh:
    """Test token refresh"""

    def test_refresh_token_success(self, client, test_user):
        """Test successful token refresh"""
        # Login to get refresh token
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "TestPass123!"
            }
        )
        refresh_token = login_response.json()["refresh_token"]

        # Refresh token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_refresh_invalid_token(self, client):
        """Test refresh with invalid token"""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token"}
        )
        assert response.status_code == 401


class TestPasswordReset:
    """Test password reset flow"""

    def test_request_password_reset(self, client, test_user):
        """Test password reset request"""
        response = client.post(
            "/api/v1/auth/password/reset-request",
            json={"email": "test@example.com"}
        )
        assert response.status_code == 200
        assert "reset_token" in response.json()  # Dev mode only

    def test_confirm_password_reset(self, client, test_user):
        """Test password reset confirmation"""
        # Request reset
        reset_response = client.post(
            "/api/v1/auth/password/reset-request",
            json={"email": "test@example.com"}
        )
        reset_token = reset_response.json()["reset_token"]

        # Confirm reset
        response = client.post(
            "/api/v1/auth/password/reset-confirm",
            json={
                "token": reset_token,
                "new_password": "NewPassword123!"
            }
        )
        assert response.status_code == 200

        # Login with new password
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "NewPassword123!"
            }
        )
        assert login_response.status_code == 200


class Test2FA:
    """Test two-factor authentication"""

    def test_2fa_setup(self, client, auth_headers):
        """Test 2FA setup"""
        response = client.post(
            "/api/v1/auth/2fa/setup",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "secret" in data
        assert "qr_code_url" in data
        assert "backup_codes" in data

    def test_2fa_enable(self, client, auth_headers, test_user, db_session):
        """Test 2FA enable"""
        # Setup 2FA
        setup_response = client.post(
            "/api/v1/auth/2fa/setup",
            headers=auth_headers
        )
        secret = setup_response.json()["secret"]

        # Generate TOTP code
        import pyotp
        totp = pyotp.TOTP(secret)
        code = totp.now()

        # Enable 2FA
        response = client.post(
            "/api/v1/auth/2fa/enable",
            headers=auth_headers,
            json={"totp_code": code}
        )
        assert response.status_code == 200


class TestRateLimiting:
    """Test rate limiting"""

    def test_login_rate_limit(self, client, test_user):
        """Test rate limit on login endpoint (SKIPPED - rate limiting disabled in tests)"""
        import os
        # Skip this test since rate limiting is disabled during testing
        if os.getenv("TESTING", "false").lower() == "true":
            pytest.skip("Rate limiting disabled during tests")

        # Make 6 requests (limit is 5/minute)
        for i in range(6):
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "username": "testuser",
                    "password": "TestPass123!"
                }
            )
            if i < 5:
                assert response.status_code in [200, 401]
            else:
                # 6th request should be rate limited
                assert response.status_code == 429
                assert "retry_after" in response.json()
