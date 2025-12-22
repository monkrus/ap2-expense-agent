"""
Tests for GCP Marketplace Client
Critical integration module - targets 80%+ coverage
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.gcp.marketplace_client import GCPMarketplaceClient


class TestGCPMarketplaceClient:
    """Test GCP Marketplace API client"""

    @patch("src.gcp.marketplace_client.settings")
    def test_init_without_credentials(self, mock_settings):
        """Test client initialization without service account"""
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_service_account_path = None

        client = GCPMarketplaceClient()

        assert client.project_id == "test-project"
        assert client.credentials is None

    @patch(
        "src.gcp.marketplace_client.service_account.Credentials.from_service_account_file"
    )
    @patch("src.gcp.marketplace_client.settings")
    def test_init_with_credentials(self, mock_settings, mock_creds):
        """Test client initialization with service account"""
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_service_account_path = "/path/to/service-account.json"

        mock_credentials = Mock()
        mock_creds.return_value = mock_credentials

        client = GCPMarketplaceClient()

        assert client.credentials == mock_credentials
        mock_creds.assert_called_once()

    @patch("src.gcp.marketplace_client.settings")
    def test_get_access_token_no_credentials(self, mock_settings):
        """Test getting access token without credentials raises error"""
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_service_account_path = None

        client = GCPMarketplaceClient()

        with pytest.raises(ValueError, match="not configured"):
            client._get_access_token()

    @patch(
        "src.gcp.marketplace_client.service_account.Credentials.from_service_account_file"
    )
    @patch("src.gcp.marketplace_client.settings")
    def test_get_access_token_valid(self, mock_settings, mock_creds):
        """Test getting valid access token"""
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_service_account_path = "/path/to/service-account.json"

        mock_credentials = Mock()
        mock_credentials.valid = True
        mock_credentials.token = "test-token-123"
        mock_creds.return_value = mock_credentials

        client = GCPMarketplaceClient()
        token = client._get_access_token()

        assert token == "test-token-123"

    @patch(
        "src.gcp.marketplace_client.service_account.Credentials.from_service_account_file"
    )
    @patch("src.gcp.marketplace_client.settings")
    def test_get_access_token_expired(self, mock_settings, mock_creds):
        """Test getting access token when expired (should refresh)"""
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_service_account_path = "/path/to/service-account.json"

        mock_credentials = Mock()
        mock_credentials.valid = False
        mock_credentials.token = "refreshed-token-456"
        mock_creds.return_value = mock_credentials

        client = GCPMarketplaceClient()
        token = client._get_access_token()

        mock_credentials.refresh.assert_called_once()
        assert token == "refreshed-token-456"

    @patch("src.gcp.marketplace_client.settings")
    async def test_report_usage_no_credentials(self, mock_settings):
        """Test usage reporting without credentials (should skip gracefully)"""
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_service_account_path = None

        client = GCPMarketplaceClient()
        result = await client.report_usage(
            "ent_test_123", {"ai_categorization": 100, "ap2_transaction": 50}
        )

        assert result["status"] == "skipped"
        assert result["reason"] == "no_credentials"

    @patch("src.gcp.marketplace_client.requests.post")
    @patch(
        "src.gcp.marketplace_client.service_account.Credentials.from_service_account_file"
    )
    @patch("src.gcp.marketplace_client.settings")
    async def test_report_usage_success(self, mock_settings, mock_creds, mock_post):
        """Test successful usage reporting"""
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_service_account_path = "/path/to/service-account.json"

        mock_credentials = Mock()
        mock_credentials.valid = True
        mock_credentials.token = "test-token"
        mock_creds.return_value = mock_credentials

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"operationId": "op_123"}
        mock_post.return_value = mock_response

        client = GCPMarketplaceClient()
        result = await client.report_usage(
            "ent_test_123", {"ai_categorization": 100, "ap2_transaction": 50}
        )

        assert result["status"] == "success"
        assert result["entitlement_id"] == "ent_test_123"
        assert result["metrics_reported"] == 2

        # Verify API was called correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "reportUsage" in call_args[0][0]
        assert call_args[1]["headers"]["Authorization"] == "Bearer test-token"

    @patch("src.gcp.marketplace_client.requests.post")
    @patch(
        "src.gcp.marketplace_client.service_account.Credentials.from_service_account_file"
    )
    @patch("src.gcp.marketplace_client.settings")
    async def test_report_usage_api_error(self, mock_settings, mock_creds, mock_post):
        """Test usage reporting with API error"""
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_service_account_path = "/path/to/service-account.json"

        mock_credentials = Mock()
        mock_credentials.valid = True
        mock_credentials.token = "test-token"
        mock_creds.return_value = mock_credentials

        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Invalid request"
        mock_post.return_value = mock_response

        client = GCPMarketplaceClient()
        result = await client.report_usage("ent_test_123", {"ai_categorization": 100})

        assert result["status"] == "error"
        assert result["status_code"] == 400

    @patch("src.gcp.marketplace_client.requests.post")
    @patch(
        "src.gcp.marketplace_client.service_account.Credentials.from_service_account_file"
    )
    @patch("src.gcp.marketplace_client.settings")
    async def test_report_usage_exception(self, mock_settings, mock_creds, mock_post):
        """Test usage reporting with exception"""
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_service_account_path = "/path/to/service-account.json"

        mock_credentials = Mock()
        mock_credentials.valid = True
        mock_credentials.token = "test-token"
        mock_creds.return_value = mock_credentials

        # Mock exception
        mock_post.side_effect = Exception("Network error")

        client = GCPMarketplaceClient()
        result = await client.report_usage("ent_test_123", {"ai_categorization": 100})

        assert result["status"] == "error"
        assert "Network error" in result["error"]

    @patch("src.gcp.marketplace_client.requests.get")
    @patch(
        "src.gcp.marketplace_client.service_account.Credentials.from_service_account_file"
    )
    @patch("src.gcp.marketplace_client.settings")
    async def test_get_entitlement_success(self, mock_settings, mock_creds, mock_get):
        """Test getting entitlement details successfully"""
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_service_account_path = "/path/to/service-account.json"

        mock_credentials = Mock()
        mock_credentials.valid = True
        mock_credentials.token = "test-token"
        mock_creds.return_value = mock_credentials

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "ent_test_123",
            "state": "ACTIVE",
            "plan": "professional",
        }
        mock_get.return_value = mock_response

        client = GCPMarketplaceClient()
        result = await client.get_entitlement("ent_test_123")

        assert result["state"] == "ACTIVE"
        assert result["plan"] == "professional"

    @patch(
        "src.gcp.marketplace_client.service_account.Credentials.from_service_account_file"
    )
    @patch("src.gcp.marketplace_client.settings")
    async def test_get_entitlement_no_credentials(self, mock_settings, mock_creds):
        """Test getting entitlement without credentials raises error"""
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_service_account_path = None

        client = GCPMarketplaceClient()

        with pytest.raises(ValueError, match="not configured"):
            await client.get_entitlement("ent_test_123")

    @patch("src.gcp.marketplace_client.GCPMarketplaceClient.get_entitlement")
    @patch(
        "src.gcp.marketplace_client.service_account.Credentials.from_service_account_file"
    )
    @patch("src.gcp.marketplace_client.settings")
    async def test_validate_entitlement_active(
        self, mock_settings, mock_creds, mock_get_ent
    ):
        """Test validating active entitlement"""
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_service_account_path = "/path/to/service-account.json"

        mock_credentials = Mock()
        mock_creds.return_value = mock_credentials

        mock_get_ent.return_value = {"state": "ACTIVE"}

        client = GCPMarketplaceClient()
        is_valid = await client.validate_entitlement("ent_test_123")

        assert is_valid is True

    @patch("src.gcp.marketplace_client.GCPMarketplaceClient.get_entitlement")
    @patch(
        "src.gcp.marketplace_client.service_account.Credentials.from_service_account_file"
    )
    @patch("src.gcp.marketplace_client.settings")
    async def test_validate_entitlement_inactive(
        self, mock_settings, mock_creds, mock_get_ent
    ):
        """Test validating inactive entitlement"""
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_service_account_path = "/path/to/service-account.json"

        mock_credentials = Mock()
        mock_creds.return_value = mock_credentials

        mock_get_ent.return_value = {"state": "CANCELLED"}

        client = GCPMarketplaceClient()
        is_valid = await client.validate_entitlement("ent_test_123")

        assert is_valid is False

    @patch("src.gcp.marketplace_client.GCPMarketplaceClient.get_entitlement")
    @patch(
        "src.gcp.marketplace_client.service_account.Credentials.from_service_account_file"
    )
    @patch("src.gcp.marketplace_client.settings")
    async def test_validate_entitlement_error(
        self, mock_settings, mock_creds, mock_get_ent
    ):
        """Test validating entitlement with error returns False"""
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_service_account_path = "/path/to/service-account.json"

        mock_credentials = Mock()
        mock_creds.return_value = mock_credentials

        mock_get_ent.side_effect = Exception("API error")

        client = GCPMarketplaceClient()
        is_valid = await client.validate_entitlement("ent_test_123")

        assert is_valid is False

    def test_verify_webhook_signature_valid(self):
        """Test webhook signature verification with valid signature"""
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
        """Test webhook signature verification with invalid signature"""
        request_body = b'{"test": "data"}'
        webhook_secret = "test-secret-key"
        invalid_signature = "invalid-signature-123"

        is_valid = GCPMarketplaceClient.verify_webhook_signature(
            request_body, invalid_signature, webhook_secret
        )

        assert is_valid is False

    def test_verify_webhook_signature_no_secret(self):
        """Test webhook signature verification without secret (dev mode)"""
        request_body = b'{"test": "data"}'

        is_valid = GCPMarketplaceClient.verify_webhook_signature(
            request_body, "any-signature", None
        )

        assert is_valid is True  # Should skip verification in dev mode

    @patch("src.gcp.marketplace_client.requests.get")
    @patch(
        "src.gcp.marketplace_client.service_account.Credentials.from_service_account_file"
    )
    @patch("src.gcp.marketplace_client.settings")
    async def test_get_account_info_success(self, mock_settings, mock_creds, mock_get):
        """Test getting account info successfully"""
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_service_account_path = "/path/to/service-account.json"

        mock_credentials = Mock()
        mock_credentials.valid = True
        mock_credentials.token = "test-token"
        mock_creds.return_value = mock_credentials

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "acct_test_456",
            "company": "Acme Corp",
            "email": "admin@acme.com",
        }
        mock_get.return_value = mock_response

        client = GCPMarketplaceClient()
        result = await client.get_account_info("acct_test_456")

        assert result["company"] == "Acme Corp"
        assert result["email"] == "admin@acme.com"

    @patch("src.gcp.marketplace_client.requests.get")
    @patch(
        "src.gcp.marketplace_client.service_account.Credentials.from_service_account_file"
    )
    @patch("src.gcp.marketplace_client.settings")
    async def test_get_account_info_error(self, mock_settings, mock_creds, mock_get):
        """Test getting account info with error"""
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_service_account_path = "/path/to/service-account.json"

        mock_credentials = Mock()
        mock_credentials.valid = True
        mock_credentials.token = "test-token"
        mock_creds.return_value = mock_credentials

        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Account not found"
        mock_get.return_value = mock_response

        client = GCPMarketplaceClient()

        with pytest.raises(Exception, match="Failed to get account info"):
            await client.get_account_info("invalid_account")
