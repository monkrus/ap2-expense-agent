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


class TestAuthService:
    """Test AuthService methods directly"""

    def test_hash_password(self):
        """Test password hashing"""
        from src.auth import AuthService

        password = "TestPassword123!"
        hashed = AuthService.hash_password(password)

        assert hashed != password
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_long(self):
        """Test hashing password longer than 72 bytes (bcrypt limit)"""
        from src.auth import AuthService

        # Create password longer than 72 bytes
        long_password = "a" * 100
        hashed = AuthService.hash_password(long_password)

        assert isinstance(hashed, str)

    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        from src.auth import AuthService

        password = "TestPassword123!"
        hashed = AuthService.hash_password(password)

        assert AuthService.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        from src.auth import AuthService

        password = "TestPassword123!"
        hashed = AuthService.hash_password(password)

        assert AuthService.verify_password("WrongPassword", hashed) is False

    def test_verify_password_long(self):
        """Test verifying long password (>72 bytes)"""
        from src.auth import AuthService

        long_password = "a" * 100
        hashed = AuthService.hash_password(long_password)

        # Should verify correctly even with long password
        assert AuthService.verify_password(long_password, hashed) is True

    def test_create_access_token(self):
        """Test creating JWT access token"""
        from src.auth import AuthService

        data = {"sub": "user123", "email": "test@example.com"}
        token = AuthService.create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_custom_expiry(self):
        """Test creating token with custom expiration"""
        from src.auth import AuthService
        from datetime import timedelta

        data = {"sub": "user123"}
        token = AuthService.create_access_token(
            data, expires_delta=timedelta(minutes=5)
        )

        assert isinstance(token, str)

    def test_verify_token_valid(self):
        """Test verifying valid JWT token"""
        from src.auth import AuthService

        data = {"sub": "user123", "email": "test@example.com"}
        token = AuthService.create_access_token(data)

        payload = AuthService.verify_token(token)
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
        assert "exp" in payload
        assert "iat" in payload

    def test_verify_token_invalid(self):
        """Test verifying invalid JWT token"""
        from src.auth import AuthService
        from fastapi import HTTPException
        import pytest

        with pytest.raises(HTTPException) as exc_info:
            AuthService.verify_token("invalid.token.here")

        assert exc_info.value.status_code == 401

    def test_create_refresh_token(self, db_session, test_user):
        """Test creating refresh token"""
        from src.auth import AuthService
        from src.models import RefreshToken

        token = AuthService.create_refresh_token(
            test_user.id, db_session, device_info="Test Device"
        )

        assert isinstance(token, str)
        assert len(token) > 0

        # Verify token was stored in database
        stored_token = db_session.query(RefreshToken).filter_by(
            user_id=test_user.id
        ).first()
        assert stored_token is not None
        assert stored_token.token == token
        assert stored_token.device_info == "Test Device"

    def test_verify_refresh_token_valid(self, db_session, test_user):
        """Test verifying valid refresh token"""
        from src.auth import AuthService

        token = AuthService.create_refresh_token(test_user.id, db_session)

        refresh_token = AuthService.verify_refresh_token(token, db_session)
        assert refresh_token is not None
        assert refresh_token.user_id == test_user.id

    def test_verify_refresh_token_invalid(self, db_session):
        """Test verifying invalid refresh token"""
        from src.auth import AuthService
        from fastapi import HTTPException
        import pytest

        with pytest.raises(HTTPException) as exc_info:
            AuthService.verify_refresh_token("invalid_token", db_session)

        assert exc_info.value.status_code == 401

    def test_verify_refresh_token_revoked(self, db_session, test_user):
        """Test verifying revoked refresh token"""
        from src.auth import AuthService
        from fastapi import HTTPException
        import pytest

        token = AuthService.create_refresh_token(test_user.id, db_session)
        AuthService.revoke_refresh_token(token, db_session)

        with pytest.raises(HTTPException) as exc_info:
            AuthService.verify_refresh_token(token, db_session)

        assert exc_info.value.status_code == 401

    def test_revoke_refresh_token(self, db_session, test_user):
        """Test revoking refresh token"""
        from src.auth import AuthService
        from src.models import RefreshToken

        token = AuthService.create_refresh_token(test_user.id, db_session)

        result = AuthService.revoke_refresh_token(token, db_session)
        assert result is True

        # Verify token is revoked in database
        stored_token = db_session.query(RefreshToken).filter_by(token=token).first()
        assert stored_token.revoked is True

    def test_revoke_refresh_token_nonexistent(self, db_session):
        """Test revoking non-existent refresh token"""
        from src.auth import AuthService

        result = AuthService.revoke_refresh_token("nonexistent_token", db_session)
        assert result is False

    def test_log_audit(self, db_session, test_user):
        """Test logging audit events"""
        from src.auth import AuthService
        from src.models import AuditLog

        AuthService.log_audit(
            db=db_session,
            user_id=test_user.id,
            action="test.action",
            resource_type="test_resource",
            resource_id="res_123",
            details={"key": "value"}
        )

        # Verify audit log was created
        log = db_session.query(AuditLog).filter_by(user_id=test_user.id).first()
        assert log is not None
        assert log.action == "test.action"
        assert log.resource_type == "test_resource"
        assert log.resource_id == "res_123"


class TestTOTPService:
    """Test two-factor authentication service"""

    def test_generate_secret(self):
        """Test generating TOTP secret"""
        from src.auth import TOTPService

        secret = TOTPService.generate_secret()
        assert isinstance(secret, str)
        assert len(secret) == 32  # Base32 encoded

    def test_generate_qr_code(self):
        """Test generating QR code for TOTP"""
        from src.auth import TOTPService

        secret = TOTPService.generate_secret()
        qr_code = TOTPService.generate_qr_code("testuser", secret)

        assert isinstance(qr_code, str)
        assert qr_code.startswith("data:image/png;base64,")

    def test_verify_totp_valid(self):
        """Test verifying valid TOTP code"""
        from src.auth import TOTPService
        import pyotp

        secret = TOTPService.generate_secret()
        totp = pyotp.TOTP(secret)
        code = totp.now()

        assert TOTPService.verify_totp(secret, code) is True

    def test_verify_totp_invalid(self):
        """Test verifying invalid TOTP code"""
        from src.auth import TOTPService

        secret = TOTPService.generate_secret()

        assert TOTPService.verify_totp(secret, "000000") is False

    def test_generate_backup_codes(self):
        """Test generating 2FA backup codes"""
        from src.auth import TOTPService

        codes = TOTPService.generate_backup_codes(count=10)

        assert len(codes) == 10
        assert all(isinstance(code, str) for code in codes)
        assert len(set(codes)) == 10  # All unique

    def test_generate_backup_codes_custom_count(self):
        """Test generating custom number of backup codes"""
        from src.auth import TOTPService

        codes = TOTPService.generate_backup_codes(count=5)
        assert len(codes) == 5
