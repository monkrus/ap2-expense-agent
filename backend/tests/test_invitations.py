"""
Tests for organization invitation endpoints.
Covers create, list, accept, and revoke invitation flows.
"""

import secrets
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from src.models import (
    Organization,
    OrganizationInvitation,
    OrganizationMember,
    OrganizationRole,
    User,
    UserRole,
)
from src.auth import AuthService


@pytest.fixture
def admin_org_setup(db_session, test_admin):
    """Return (admin, org, org_id) with admin as OWNER."""
    membership = (
        db_session.query(OrganizationMember)
        .filter(OrganizationMember.user_id == test_admin.id)
        .first()
    )
    org = (
        db_session.query(Organization)
        .filter(Organization.id == membership.organization_id)
        .first()
    )
    return test_admin, org, org.id


@pytest.fixture
def member_user(db_session, admin_org_setup):
    """A regular member in the admin's org (cannot invite)."""
    _, org, org_id = admin_org_setup
    user = User(
        id=str(uuid.uuid4()),
        email="member@example.com",
        username="memberuser",
        full_name="Member User",
        hashed_password=AuthService.hash_password("MemberPass123!"),
        role=UserRole.EMPLOYEE,
        is_active=True,
        is_verified=True,
        failed_login_attempts=0,
    )
    db_session.add(user)
    db_session.flush()

    membership = OrganizationMember(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        user_id=user.id,
        role=OrganizationRole.MEMBER,
        is_active=True,
        joined_at=datetime.utcnow(),
    )
    db_session.add(membership)
    db_session.commit()
    return user


@pytest.fixture
def member_headers(client, member_user):
    """Auth headers for the regular member."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "memberuser", "password": "MemberPass123!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


class TestCreateInvitation:
    """POST /{org_id}/invitations"""

    @patch(
        "src.routes.organizations.EmailService.send_organization_invitation_email",
        new_callable=AsyncMock,
    )
    def test_admin_creates_invitation(
        self, mock_email, client, admin_org_headers, admin_org_setup
    ):
        _, org, org_id = admin_org_setup
        resp = client.post(
            f"/api/v1/organizations/{org_id}/invitations",
            headers=admin_org_headers,
            json={"email": "invitee@example.com"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "invitee@example.com"
        assert data["status"] == "pending"
        assert data["organization_id"] == org_id
        mock_email.assert_called_once()

    @patch(
        "src.routes.organizations.EmailService.send_organization_invitation_email",
        new_callable=AsyncMock,
    )
    def test_non_admin_cannot_create_invitation(
        self, mock_email, client, member_headers, admin_org_setup
    ):
        _, _, org_id = admin_org_setup
        resp = client.post(
            f"/api/v1/organizations/{org_id}/invitations",
            headers={**member_headers, "X-Organization-Id": org_id},
            json={"email": "anyone@example.com"},
        )
        assert resp.status_code == 403
        mock_email.assert_not_called()

    @patch(
        "src.routes.organizations.EmailService.send_organization_invitation_email",
        new_callable=AsyncMock,
    )
    def test_duplicate_pending_invitation(
        self, mock_email, client, admin_org_headers, admin_org_setup, db_session
    ):
        _, org, org_id = admin_org_setup

        # Create an existing pending invitation directly
        inv = OrganizationInvitation(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            email="dup@example.com",
            role=OrganizationRole.MEMBER,
            invited_by=admin_org_setup[0].id,
            token=secrets.token_urlsafe(32),
            status="pending",
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        db_session.add(inv)
        db_session.commit()

        resp = client.post(
            f"/api/v1/organizations/{org_id}/invitations",
            headers=admin_org_headers,
            json={"email": "dup@example.com"},
        )
        assert resp.status_code == 400
        assert "already sent" in resp.json()["detail"].lower()


class TestListInvitations:
    """GET /{org_id}/invitations"""

    def test_list_pending_invitations(
        self, client, admin_org_headers, admin_org_setup, db_session
    ):
        _, _, org_id = admin_org_setup
        admin = admin_org_setup[0]

        # Seed two invitations
        for email in ["a@test.com", "b@test.com"]:
            db_session.add(
                OrganizationInvitation(
                    id=str(uuid.uuid4()),
                    organization_id=org_id,
                    email=email,
                    role=OrganizationRole.MEMBER,
                    invited_by=admin.id,
                    token=secrets.token_urlsafe(32),
                    status="pending",
                    expires_at=datetime.utcnow() + timedelta(days=7),
                )
            )
        db_session.commit()

        resp = client.get(
            f"/api/v1/organizations/{org_id}/invitations",
            headers=admin_org_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2
        emails = {inv["email"] for inv in data}
        assert "a@test.com" in emails
        assert "b@test.com" in emails


class TestAcceptInvitation:
    """POST /invitations/{token}/accept"""

    def test_accept_valid_invitation(
        self, client, auth_headers, test_user, admin_org_setup, db_session
    ):
        _, _, org_id = admin_org_setup
        token = secrets.token_urlsafe(32)

        inv = OrganizationInvitation(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            email=test_user.email,  # must match current user's email
            role=OrganizationRole.MEMBER,
            invited_by=admin_org_setup[0].id,
            token=token,
            status="pending",
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        db_session.add(inv)
        db_session.commit()

        resp = client.post(
            f"/api/v1/organizations/invitations/{token}/accept",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert "accepted" in resp.json()["message"].lower()

        # Verify membership was created
        mem = (
            db_session.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == test_user.id,
            )
            .first()
        )
        assert mem is not None

    def test_accept_expired_invitation(
        self, client, auth_headers, test_user, admin_org_setup, db_session
    ):
        _, _, org_id = admin_org_setup
        token = secrets.token_urlsafe(32)

        inv = OrganizationInvitation(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            email=test_user.email,
            role=OrganizationRole.MEMBER,
            invited_by=admin_org_setup[0].id,
            token=token,
            status="pending",
            expires_at=datetime.utcnow() - timedelta(days=1),  # expired
        )
        db_session.add(inv)
        db_session.commit()

        resp = client.post(
            f"/api/v1/organizations/invitations/{token}/accept",
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "expired" in resp.json()["detail"].lower()

    def test_accept_wrong_email(
        self, client, auth_headers, admin_org_setup, db_session
    ):
        """Current user's email doesn't match invitation email → 403"""
        _, _, org_id = admin_org_setup
        token = secrets.token_urlsafe(32)

        inv = OrganizationInvitation(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            email="someone_else@example.com",
            role=OrganizationRole.MEMBER,
            invited_by=admin_org_setup[0].id,
            token=token,
            status="pending",
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        db_session.add(inv)
        db_session.commit()

        resp = client.post(
            f"/api/v1/organizations/invitations/{token}/accept",
            headers=auth_headers,
        )
        assert resp.status_code == 403
        assert "different email" in resp.json()["detail"].lower()

    def test_accept_nonexistent_token(self, client, auth_headers):
        """Invalid token → 404"""
        resp = client.post(
            "/api/v1/organizations/invitations/nonexistent_token/accept",
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestRevokeInvitation:
    """DELETE /{org_id}/invitations/{invitation_id}"""

    def test_admin_revokes_invitation(
        self, client, admin_org_headers, admin_org_setup, db_session
    ):
        _, _, org_id = admin_org_setup
        inv = OrganizationInvitation(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            email="revoke_me@example.com",
            role=OrganizationRole.MEMBER,
            invited_by=admin_org_setup[0].id,
            token=secrets.token_urlsafe(32),
            status="pending",
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        db_session.add(inv)
        db_session.commit()

        resp = client.delete(
            f"/api/v1/organizations/{org_id}/invitations/{inv.id}",
            headers=admin_org_headers,
        )
        assert resp.status_code == 204

        # Verify status updated
        db_session.refresh(inv)
        assert inv.status == "revoked"

    def test_non_admin_cannot_revoke(
        self, client, member_headers, admin_org_setup, db_session
    ):
        _, _, org_id = admin_org_setup
        inv = OrganizationInvitation(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            email="norights@example.com",
            role=OrganizationRole.MEMBER,
            invited_by=admin_org_setup[0].id,
            token=secrets.token_urlsafe(32),
            status="pending",
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        db_session.add(inv)
        db_session.commit()

        resp = client.delete(
            f"/api/v1/organizations/{org_id}/invitations/{inv.id}",
            headers={**member_headers, "X-Organization-Id": org_id},
        )
        assert resp.status_code == 403
