"""
Tests for GCP Marketplace Procurement Handler
Critical integration module - targets 80%+ coverage
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

pytestmark = pytest.mark.asyncio

from src.gcp.procurement_handler import (
    generate_secure_password,
    generate_slug,
    get_tier_max_members,
    handle_procurement_webhook,
)
from src.models import Organization, OrganizationMember, OrganizationRole, User


class TestProcurementHelpers:
    """Test helper functions"""

    def test_generate_secure_password(self):
        """Test secure password generation"""
        password = generate_secure_password(16)

        assert len(password) == 16
        assert isinstance(password, str)

        # Generate multiple passwords to ensure randomness
        passwords = [generate_secure_password(16) for _ in range(10)]
        assert len(set(passwords)) == 10  # All unique

    def test_generate_secure_password_custom_length(self):
        """Test secure password generation with custom length"""
        password = generate_secure_password(32)
        assert len(password) == 32

    def test_generate_slug(self):
        """Test slug generation from company name"""
        slug = generate_slug("Acme Corporation")

        assert "acme-corporation" in slug
        assert isinstance(slug, str)
        assert len(slug) > len("acme-corporation")  # Has random suffix

    def test_generate_slug_special_characters(self):
        """Test slug generation with special characters"""
        slug = generate_slug("Company & Co., Inc.")

        assert "company" in slug
        assert "co" in slug
        assert "&" not in slug
        assert "," not in slug
        assert "." not in slug

    def test_generate_slug_uniqueness(self):
        """Test that slugs are unique even for same company name"""
        slug1 = generate_slug("Test Company")
        slug2 = generate_slug("Test Company")

        assert slug1 != slug2  # Should have different random suffixes

    def test_get_tier_max_members(self):
        """Test tier member limit lookup"""
        assert get_tier_max_members("free") == 5
        assert get_tier_max_members("starter") == 25
        assert get_tier_max_members("professional") == 100
        assert get_tier_max_members("enterprise") == 10000

    def test_get_tier_max_members_case_insensitive(self):
        """Test tier lookup is case insensitive"""
        assert get_tier_max_members("PROFESSIONAL") == 100
        assert get_tier_max_members("Starter") == 25

    def test_get_tier_max_members_unknown(self):
        """Test unknown tier returns default"""
        assert get_tier_max_members("unknown") == 25


class TestProcurementWebhook:
    """Test GCP procurement webhook handler"""

    @pytest.fixture
    def webhook_data(self):
        """Sample webhook data from GCP"""
        return {
            "entitlement_id": "ent_test_123",
            "account_id": "acct_test_456",
            "plan": "professional",
            "user_email": "admin@acme.com",
            "company_name": "Acme Corporation",
            "state": "ACTIVE",
        }

    @pytest.fixture
    def mock_email_service(self):
        """Mock email service"""
        with patch("src.gcp.procurement_handler.EmailService") as mock:
            mock_instance = Mock()
            mock_instance.send_email = AsyncMock()
            mock.return_value = mock_instance
            yield mock_instance

    async def test_handle_procurement_new_organization(
        self, db_session, webhook_data, mock_email_service
    ):
        """Test creating new organization from GCP webhook"""
        result = await handle_procurement_webhook(webhook_data, db_session)

        assert result["status"] == "created"
        assert result["organization_name"] == "Acme Corporation"
        assert result["admin_email"] == "admin@acme.com"
        assert result["tier"] == "professional"
        assert "organization_id" in result
        assert "admin_user_id" in result

        # Verify organization was created in DB
        org = (
            db_session.query(Organization)
            .filter_by(id=result["organization_id"])
            .first()
        )
        assert org is not None
        assert org.name == "Acme Corporation"
        assert org.is_active is True
        assert org.max_members == 100  # Professional tier

    async def test_handle_procurement_new_user_created(
        self, db_session, webhook_data, mock_email_service
    ):
        """Test that new admin user is created"""
        result = await handle_procurement_webhook(webhook_data, db_session)

        # Verify user was created
        user = db_session.query(User).filter_by(email="admin@acme.com").first()
        assert user is not None
        assert user.is_active is True
        assert user.is_verified is True  # Auto-verified for GCP users
        assert user.hashed_password is not None

        # Verify email was sent with temp password
        mock_email_service.send_email.assert_called_once()
        call_args = mock_email_service.send_email.call_args
        assert call_args[1]["to_email"] == "admin@acme.com"
        assert "password" in call_args[1]["body"].lower()

    async def test_handle_procurement_existing_user(
        self, db_session, webhook_data, sample_user, mock_email_service
    ):
        """Test webhook with existing user"""
        # Create existing user
        existing_user = sample_user(email="admin@acme.com")

        result = await handle_procurement_webhook(webhook_data, db_session)

        assert result["status"] == "created"
        assert result["admin_user_id"] == existing_user.id

        # Verify no duplicate user created
        users = db_session.query(User).filter_by(email="admin@acme.com").all()
        assert len(users) == 1

    async def test_handle_procurement_organization_membership(
        self, db_session, webhook_data, mock_email_service
    ):
        """Test that admin is added as organization owner"""
        result = await handle_procurement_webhook(webhook_data, db_session)

        # Verify membership was created
        membership = (
            db_session.query(OrganizationMember)
            .filter_by(
                organization_id=result["organization_id"],
                user_id=result["admin_user_id"],
            )
            .first()
        )

        assert membership is not None
        assert membership.role == OrganizationRole.OWNER
        assert membership.is_active is True

    async def test_handle_procurement_subscription_created(
        self, db_session, webhook_data, mock_email_service
    ):
        """Test that subscription is created and linked to GCP"""
        from src.models_billing import OrganizationSubscription

        result = await handle_procurement_webhook(webhook_data, db_session)

        # Verify subscription was created
        subscription = (
            db_session.query(OrganizationSubscription)
            .filter_by(id=result["subscription_id"])
            .first()
        )

        assert subscription is not None
        assert subscription.organization_id == result["organization_id"]
        assert subscription.gcp_entitlement_id == "ent_test_123"
        assert subscription.gcp_account_id == "acct_test_456"
        assert subscription.status == "active"
        assert subscription.is_trial is False
        assert subscription.additional_metadata["source"] == "gcp_marketplace"

    async def test_handle_procurement_billing_event_logged(
        self, db_session, webhook_data, mock_email_service
    ):
        """Test that billing event is logged"""
        from src.models_billing import BillingEvent

        result = await handle_procurement_webhook(webhook_data, db_session)

        # Verify billing event was created
        event = (
            db_session.query(BillingEvent)
            .filter_by(
                organization_id=result["organization_id"],
                event_type="gcp_procurement_created",
            )
            .first()
        )

        assert event is not None
        assert event.status == "success"
        assert event.event_data["entitlement_id"] == "ent_test_123"
        assert event.event_data["company_name"] == "Acme Corporation"

    async def test_handle_procurement_missing_entitlement_id(
        self, db_session, mock_email_service
    ):
        """Test webhook with missing entitlement_id raises error"""
        webhook_data = {"account_id": "acct_test_456", "user_email": "admin@acme.com"}

        with pytest.raises(ValueError, match="Missing required fields"):
            await handle_procurement_webhook(webhook_data, db_session)

    async def test_handle_procurement_missing_user_email(
        self, db_session, mock_email_service
    ):
        """Test webhook with missing user_email raises error"""
        webhook_data = {"entitlement_id": "ent_test_123", "account_id": "acct_test_456"}

        with pytest.raises(ValueError, match="Missing required fields"):
            await handle_procurement_webhook(webhook_data, db_session)

    async def test_handle_procurement_duplicate_entitlement(
        self, db_session, webhook_data, mock_email_service
    ):
        """Test webhook with duplicate entitlement returns existing org"""
        import uuid

        from src.models_billing import OrganizationSubscription

        # Create existing organization and subscription
        org_id = str(uuid.uuid4())
        org = Organization(
            id=org_id,
            name="Existing Org",
            slug="existing-org-abc123",
            currency="USD",
            timezone="UTC",
            max_members=100,
            is_active=True,
        )
        db_session.add(org)

        subscription = OrganizationSubscription(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            tier_id="professional",
            tier_name="professional",
            gcp_entitlement_id="ent_test_123",  # Same as webhook
            status="active",
        )
        db_session.add(subscription)
        db_session.commit()

        # Try to process webhook with same entitlement
        result = await handle_procurement_webhook(webhook_data, db_session)

        assert result["status"] == "already_exists"
        assert result["organization_id"] == org_id

    async def test_handle_procurement_default_plan(
        self, db_session, mock_email_service
    ):
        """Test webhook without plan uses default (professional)"""
        webhook_data = {
            "entitlement_id": "ent_test_123",
            "account_id": "acct_test_456",
            "user_email": "admin@acme.com",
            "company_name": "Acme Corporation",
        }

        result = await handle_procurement_webhook(webhook_data, db_session)

        assert result["tier"] == "professional"

        # Verify organization has professional tier limits
        org = (
            db_session.query(Organization)
            .filter_by(id=result["organization_id"])
            .first()
        )
        assert org.max_members == 100  # Professional tier

    async def test_handle_procurement_default_company_name(
        self, db_session, mock_email_service
    ):
        """Test webhook without company name uses default"""
        webhook_data = {
            "entitlement_id": "ent_test_123",
            "account_id": "acct_test_456",
            "user_email": "admin@acme.com",
        }

        result = await handle_procurement_webhook(webhook_data, db_session)

        assert result["organization_name"] == "New Organization"

    async def test_handle_procurement_email_failure_non_blocking(
        self, db_session, webhook_data
    ):
        """Test that email failure doesn't prevent org creation"""
        with patch("src.gcp.procurement_handler.EmailService") as mock_email:
            mock_email_instance = Mock()
            mock_email_instance.send_email = AsyncMock(
                side_effect=Exception("Email error")
            )
            mock_email.return_value = mock_email_instance

            # Should not raise exception
            result = await handle_procurement_webhook(webhook_data, db_session)

            assert result["status"] == "created"

            # Verify organization was still created
            org = (
                db_session.query(Organization)
                .filter_by(id=result["organization_id"])
                .first()
            )
            assert org is not None

    async def test_handle_procurement_database_error(
        self, db_session, webhook_data, mock_email_service
    ):
        """Test handling of database errors"""
        # Force IntegrityError by using invalid data
        with patch.object(db_session, "commit", side_effect=Exception("DB error")):
            with pytest.raises(Exception):
                await handle_procurement_webhook(webhook_data, db_session)

            # Verify rollback occurred
            # Organization should not exist
            orgs = (
                db_session.query(Organization).filter_by(name="Acme Corporation").all()
            )
            assert len(orgs) == 0

    async def test_handle_procurement_different_tiers(
        self, db_session, webhook_data, mock_email_service
    ):
        """Test provisioning with different tier plans"""
        tiers_to_test = [("starter", 25), ("professional", 100), ("enterprise", 10000)]

        for tier, expected_max_members in tiers_to_test:
            webhook_data["plan"] = tier
            webhook_data["entitlement_id"] = f"ent_{tier}_123"
            webhook_data["account_id"] = f"acct_{tier}_456"
            webhook_data["user_email"] = f"admin_{tier}@acme.com"

            result = await handle_procurement_webhook(webhook_data, db_session)

            org = (
                db_session.query(Organization)
                .filter_by(id=result["organization_id"])
                .first()
            )

            assert org.max_members == expected_max_members
            assert result["tier"] == tier
