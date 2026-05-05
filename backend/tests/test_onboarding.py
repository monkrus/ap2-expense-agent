"""
Tests for onboarding API routes (/api/v1/onboarding/*).
The User model currently lacks onboarding_data/onboarding_completed columns,
so service-layer calls that set those fields will fail. Tests here focus on
what the route layer can deliver today: auth gates and the organization
creation sub-flow (which doesn't touch the missing columns before committing
the org).
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models import Organization, OrganizationMember, OrganizationRole


class TestOnboardingAuth:
    """Verify all onboarding endpoints require authentication."""

    def test_status_requires_auth(self, client):
        resp = client.get("/api/v1/onboarding/status")
        assert resp.status_code == 401

    def test_start_requires_auth(self, client):
        resp = client.post("/api/v1/onboarding/start")
        assert resp.status_code == 401

    def test_complete_step_requires_auth(self, client):
        resp = client.post("/api/v1/onboarding/steps/email_verified/complete")
        assert resp.status_code == 401

    def test_create_org_requires_auth(self, client):
        resp = client.post(
            "/api/v1/onboarding/organization",
            json={"name": "Acme", "slug": "acme"},
        )
        assert resp.status_code == 401

    def test_invite_team_requires_auth(self, client):
        resp = client.post(
            "/api/v1/onboarding/invite-team",
            json={"organization_id": "org_1", "emails": ["a@b.com"]},
        )
        assert resp.status_code == 401


class TestOnboardingCreateOrganization:
    """POST /api/v1/onboarding/organization — creates org + owner membership."""

    @patch("src.onboarding.service.OnboardingService.complete_step")
    def test_create_org_during_onboarding(
        self, mock_complete, client, auth_headers, test_user, db_session
    ):
        """Creating an org via onboarding returns org details and makes user owner."""
        # Stub complete_step so missing onboarding columns don't blow up
        mock_complete.return_value = {
            "completed_steps": ["account_created", "organization_created"],
            "remaining_steps": [],
            "current_step": "team_invited",
            "total_steps": 6,
            "percentage": 33,
        }

        resp = client.post(
            "/api/v1/onboarding/organization",
            headers=auth_headers,
            json={"name": "My Startup", "slug": "my-startup"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "My Startup"
        assert data["slug"] == "my-startup"
        assert "organization_id" in data

        # Verify org exists in DB
        org = (
            db_session.query(Organization).filter_by(id=data["organization_id"]).first()
        )
        assert org is not None
        assert org.name == "My Startup"

        # Verify user is OWNER
        mem = (
            db_session.query(OrganizationMember)
            .filter_by(organization_id=org.id, user_id=test_user.id)
            .first()
        )
        assert mem is not None
        assert mem.role == OrganizationRole.OWNER
