"""
Tests for GCP Marketplace Client
Critical integration module - targets 80%+ coverage
"""

from unittest.mock import Mock, patch

import pytest

from src.gcp.marketplace_client import GCPMarketplaceClient


class TestGCPMarketplaceClient:
    """Test GCP Marketplace API client"""

    @patch("src.gcp.marketplace_client.settings")
    def test_init_without_credentials(self, mock_settings):
        """Client initializes without session when no credentials configured"""
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_service_account_path = None

        client = GCPMarketplaceClient()

        assert client.project_id == "test-project"
        assert client.credentials is None
        assert client.session is None

    @patch("src.gcp.marketplace_client.AuthorizedSession")
    @patch("src.gcp.marketplace_client.service_account.Credentials.from_service_account_file")
    @patch("src.gcp.marketplace_client.settings")
    def test_init_with_credentials(self, mock_settings, mock_creds, mock_session_cls):
        """Client initializes authorized session when credentials present"""
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_service_account_path = "/path/to/service-account.json"

        mock_credentials = Mock()
        mock_creds.return_value = mock_credentials
        mock_session = Mock()
        mock_session_cls.return_value = mock_session

        client = GCPMarketplaceClient()

        assert client.credentials == mock_credentials
        assert client.session == mock_session
        mock_creds.assert_called_once()
        mock_session_cls.assert_called_once_with(mock_credentials)

    @patch("src.gcp.marketplace_client.settings")
    async def test_report_usage_no_credentials(self, mock_settings):
        """Usage reporting skips gracefully when not configured"""
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_service_account_path = None

        client = GCPMarketplaceClient()
        result = await client.report_usage(
            "ent_test_123", {"ai_categorization": 100, "ap2_transaction": 50}
        )

        assert result["status"] == "skipped"
        assert result["reason"] == "no_credentials"

    @patch("src.gcp.marketplace_client.AuthorizedSession")
    @patch("src.gcp.marketplace_client.service_account.Credentials.from_service_account_file")
    @patch("src.gcp.marketplace_client.settings")
    async def test_report_usage_success(self, mock_settings, mock_creds, mock_session_cls):
        """Successful usage reporting via authorized session"""
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_service_account_path = "/path/to/service-account.json"

        mock_credentials = Mock()
        mock_creds.return_value = mock_credentials

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"operationId": "op_123"}
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_cls.return_value = mock_session

        client = GCPMarketplaceClient()
        result = await client.report_usage(
            "ent_test_123", {"ai_categorization": 100, "ap2_transaction": 50}
        )

        assert result["status"] == "success"
        assert result["entitlement_id"] == "ent_test_123"
        assert result["metrics_reported"] == 2
        mock_session.post.assert_called_once()

    @patch("src.gcp.marketplace_client.AuthorizedSession")
    @patch("src.gcp.marketplace_client.service_account.Credentials.from_service_account_file")
    @patch("src.gcp.marketplace_client.settings")
    async def test_report_usage_api_error(self, mock_settings, mock_creds, mock_session_cls):
        """Usage reporting returns error details on non-200"""
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_service_account_path = "/path/to/service-account.json"

        mock_credentials = Mock()
        mock_creds.return_value = mock_credentials

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Invalid request"
        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session_cls.return_value = mock_session

        client = GCPMarketplaceClient()
        result = await client.report_usage("ent_test_123", {"ai_categorization": 100})

        assert result["status"] == "error"
        assert result["status_code"] == 400

    @patch("src.gcp.marketplace_client.AuthorizedSession")
    @patch("src.gcp.marketplace_client.service_account.Credentials.from_service_account_file")
    @patch("src.gcp.marketplace_client.settings")
    async def test_report_usage_exception(self, mock_settings, mock_creds, mock_session_cls):
        """Usage reporting surfaces exceptions"""
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_service_account_path = "/path/to/service-account.json"

        mock_credentials = Mock()
        mock_creds.return_value = mock_credentials

        mock_session = Mock()
        mock_session.post.side_effect = Exception("Network error")
        mock_session_cls.return_value = mock_session

        client = GCPMarketplaceClient()
        result = await client.report_usage("ent_test_123", {"ai_categorization": 100})

        assert result["status"] == "error"
        assert "Network error" in result["error"]

    @patch("src.gcp.marketplace_client.AuthorizedSession")
    @patch("src.gcp.marketplace_client.service_account.Credentials.from_service_account_file")
    @patch("src.gcp.marketplace_client.settings")
    async def test_get_entitlement_success(self, mock_settings, mock_creds, mock_session_cls):
        """Get entitlement returns JSON on success"""
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_service_account_path = "/path/to/service-account.json"

        mock_credentials = Mock()
        mock_creds.return_value = mock_credentials

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "ent_test_123",
            "state": "ACTIVE",
            "plan": "professional",
        }
        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_cls.return_value = mock_session

        client = GCPMarketplaceClient()
        result = await client.get_entitlement("ent_test_123")

        assert result["state"] == "ACTIVE"
        assert result["plan"] == "professional"

    @patch("src.gcp.marketplace_client.service_account.Credentials.from_service_account_file")
    @patch("src.gcp.marketplace_client.settings")
    async def test_get_entitlement_no_credentials(self, mock_settings, mock_creds):
        """Get entitlement raises when no credentials configured"""
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_service_account_path = None

        client = GCPMarketplaceClient()

        with pytest.raises(ValueError, match="not configured"):
            await client.get_entitlement("ent_test_123")

    @patch("src.gcp.marketplace_client.GCPMarketplaceClient.get_entitlement")
    @patch("src.gcp.marketplace_client.service_account.Credentials.from_service_account_file")
    @patch("src.gcp.marketplace_client.settings")
    async def test_validate_entitlement_active(
        self, mock_settings, mock_creds, mock_get_ent
    ):
        """Validate entitlement returns True for ACTIVE"""
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_service_account_path = "/path/to/service-account.json"

        mock_credentials = Mock()
        mock_creds.return_value = mock_credentials

        mock_get_ent.return_value = {"state": "ACTIVE"}

        client = GCPMarketplaceClient()
        is_valid = await client.validate_entitlement("ent_test_123")

        assert is_valid is True

    @patch("src.gcp.marketplace_client.GCPMarketplaceClient.get_entitlement")
    @patch("src.gcp.marketplace_client.service_account.Credentials.from_service_account_file")
    @patch("src.gcp.marketplace_client.settings")
    async def test_validate_entitlement_inactive(
        self, mock_settings, mock_creds, mock_get_ent
    ):
        """Validate entitlement returns False for cancelled"""
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_service_account_path = "/path/to/service-account.json"

        mock_credentials = Mock()
        mock_creds.return_value = mock_credentials

        mock_get_ent.return_value = {"state": "CANCELLED"}

        client = GCPMarketplaceClient()
        is_valid = await client.validate_entitlement("ent_test_123")

        assert is_valid is False

    @patch("src.gcp.marketplace_client.GCPMarketplaceClient.get_entitlement")
    @patch("src.gcp.marketplace_client.service_account.Credentials.from_service_account_file")
    @patch("src.gcp.marketplace_client.settings")
    async def test_validate_entitlement_error(
        self, mock_settings, mock_creds, mock_get_ent
    ):
        """Validate entitlement returns False on error"""
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_service_account_path = "/path/to/service-account.json"

        mock_credentials = Mock()
        mock_creds.return_value = mock_credentials

        mock_get_ent.side_effect = Exception("API error")

        client = GCPMarketplaceClient()
        is_valid = await client.validate_entitlement("ent_test_123")

        assert is_valid is False

    def test_verify_webhook_signature_valid(self):
        """Webhook signature verification with valid signature"""
        request_body = b'{"test": "data"}'
        webhook_secret = "test-secret-key"

        import hashlib
        import hmac

        expected_signature = hmac.new(
            webhook_secret.encode(), request_body, hashlib.sha256
        ).hexdigest()

        is_valid = GCPMarketplaceClient.verify_webhook_signature(
            request_body, expected_signature, webhook_secret
        )

        assert is_valid is True

    def test_verify_webhook_signature_invalid(self):
        """Webhook signature verification with invalid signature"""
        request_body = b'{"test": "data"}'
        webhook_secret = "test-secret-key"
        invalid_signature = "invalid-signature-123"

        is_valid = GCPMarketplaceClient.verify_webhook_signature(
            request_body, invalid_signature, webhook_secret
        )

        assert is_valid is False

    def test_verify_webhook_signature_no_secret(self):
        """Webhook signature verification without secret fails closed"""
        request_body = b'{"test": "data"}'

        is_valid = GCPMarketplaceClient.verify_webhook_signature(
            request_body, "any-signature", None
        )

        assert is_valid is False

    @patch("src.gcp.marketplace_client.AuthorizedSession")
    @patch("src.gcp.marketplace_client.service_account.Credentials.from_service_account_file")
    @patch("src.gcp.marketplace_client.settings")
    async def test_get_account_info_success(self, mock_settings, mock_creds, mock_session_cls):
        """Get account info returns JSON on success"""
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_service_account_path = "/path/to/service-account.json"

        mock_credentials = Mock()
        mock_credentials.valid = True
        mock_credentials.token = "test-token"
        mock_creds.return_value = mock_credentials

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "acct_test_456",
            "company": "Acme Corp",
            "email": "admin@acme.com",
        }
        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_cls.return_value = mock_session

        client = GCPMarketplaceClient()
        result = await client.get_account_info("acct_test_456")

        assert result["company"] == "Acme Corp"
        assert result["email"] == "admin@acme.com"

    @patch("src.gcp.marketplace_client.AuthorizedSession")
    @patch("src.gcp.marketplace_client.service_account.Credentials.from_service_account_file")
    @patch("src.gcp.marketplace_client.settings")
    async def test_get_account_info_error(self, mock_settings, mock_creds, mock_session_cls):
        """Get account info raises on non-200"""
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_service_account_path = "/path/to/service-account.json"

        mock_credentials = Mock()
        mock_credentials.valid = True
        mock_credentials.token = "test-token"
        mock_creds.return_value = mock_credentials

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Account not found"
        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_cls.return_value = mock_session

        client = GCPMarketplaceClient()

        with pytest.raises(Exception, match="Failed to get account info"):
            await client.get_account_info("invalid_account")
