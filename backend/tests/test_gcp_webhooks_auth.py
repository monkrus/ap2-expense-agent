from unittest.mock import patch

from src.routes.gcp_webhooks import verify_google_oidc_token


def test_verify_google_oidc_token_valid():
    with patch("src.routes.gcp_webhooks.verify_google_signed_jwt", return_value=True):
        assert verify_google_oidc_token("Bearer token123", "aud") is True


def test_verify_google_oidc_token_invalid():
    with patch("src.routes.gcp_webhooks.verify_google_signed_jwt", return_value=False):
        assert verify_google_oidc_token("Bearer token123", "aud") is False


def test_verify_google_oidc_token_missing_header():
    assert verify_google_oidc_token(None, "aud") is False
    assert verify_google_oidc_token("", "aud") is False
    assert verify_google_oidc_token("Token abc", "aud") is False
