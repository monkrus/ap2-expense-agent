"""
Tests for rate_limit_handler and AlertManager.alert_suspicious_activity.
Rate limiting is disabled during TESTING=true, so we test the handler
and alerting functions directly with mock Request objects.

NOTE: psutil and prometheus_client are not installed in the test environment,
so we mock them before importing src.monitoring.
"""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

# psutil and prometheus_client are installed in the test environment

from src.monitoring import AlertManager
from src.rate_limit import rate_limit_handler

pytestmark = pytest.mark.asyncio


def _make_request(path: str, client_host: str = "1.2.3.4") -> MagicMock:
    """Build a mock Request with .url.path and .client.host."""
    req = MagicMock()
    req.url.path = path
    req.client.host = client_host
    return req


def _make_exc(retry_after: int = 60) -> MagicMock:
    """Build a mock RateLimitExceeded with retry_after."""
    exc = MagicMock()
    exc.retry_after = retry_after
    return exc


class TestRateLimitHandler:
    """Tests for the rate_limit_handler function."""

    async def test_returns_429_with_correct_body(self):
        resp = await rate_limit_handler(_make_request("/api/v1/expenses"), _make_exc(30))
        assert resp.status_code == 429
        body = json.loads(resp.body)
        assert body["error"] == "rate_limit_exceeded"
        assert body["retry_after"] == 30
        assert "detail" in body

    async def test_fires_alert_for_login_path(self):
        with patch.object(AlertManager, "alert_suspicious_activity") as mock_alert:
            await rate_limit_handler(
                _make_request("/api/v1/auth/login"), _make_exc()
            )
            mock_alert.assert_called_once()
            kw = mock_alert.call_args[1]
            assert kw["endpoint"] == "/api/v1/auth/login"
            assert kw["activity_type"] == "rate_limit_exceeded"

    async def test_fires_alert_for_invitations_path(self):
        with patch.object(AlertManager, "alert_suspicious_activity") as mock_alert:
            await rate_limit_handler(
                _make_request("/api/v1/organizations/org_1/invitations"), _make_exc()
            )
            mock_alert.assert_called_once()

    async def test_no_alert_for_non_sensitive_path(self):
        with patch.object(AlertManager, "alert_suspicious_activity") as mock_alert:
            await rate_limit_handler(
                _make_request("/api/v1/expenses"), _make_exc()
            )
            mock_alert.assert_not_called()


class TestAlertSuspiciousActivity:
    """Tests for AlertManager.alert_suspicious_activity severity classification."""

    def test_login_classified_critical(self):
        with patch.object(AlertManager, "send_alert") as mock_send:
            AlertManager.alert_suspicious_activity(
                activity_type="rate_limit_exceeded",
                ip_address="10.0.0.1",
                endpoint="/api/v1/auth/login",
            )
            mock_send.assert_called_once()
            assert mock_send.call_args[1]["severity"] == "critical"

    def test_invitations_classified_warning(self):
        with patch.object(AlertManager, "send_alert") as mock_send:
            AlertManager.alert_suspicious_activity(
                activity_type="rate_limit_exceeded",
                ip_address="10.0.0.1",
                endpoint="/api/v1/organizations/org_1/invitations",
            )
            mock_send.assert_called_once()
            assert mock_send.call_args[1]["severity"] == "warning"
