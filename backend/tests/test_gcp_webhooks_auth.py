from unittest.mock import patch, Mock

import pytest

from src.routes.gcp_webhooks import verify_google_oidc_token


@patch("google.oauth2.id_token.verify_oauth2_token")
@patch("google.auth.transport.requests.Request")
def test_verify_google_oidc_token_valid(mock_request, mock_verify):
    mock_verify.return_value = {"iss": "https://accounts.google.com", "aud": "aud"}
    assert verify_google_oidc_token("Bearer token123", "aud") is True


@patch("google.oauth2.id_token.verify_oauth2_token")
@patch("google.auth.transport.requests.Request")
def test_verify_google_oidc_token_invalid_issuer(mock_request, mock_verify):
    mock_verify.return_value = {"iss": "https://example.com", "aud": "aud"}
    assert verify_google_oidc_token("Bearer token123", "aud") is False


def test_verify_google_oidc_token_missing_header():
    assert verify_google_oidc_token(None, "aud") is False
    assert verify_google_oidc_token("", "aud") is False
    assert verify_google_oidc_token("Token abc", "aud") is False
