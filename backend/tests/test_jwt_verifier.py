from unittest.mock import MagicMock, patch

from src.gcp.jwt_verifier import verify_google_signed_jwt


def test_verify_google_signed_jwt_success():
    with patch("src.gcp.jwt_verifier.id_token.verify_oauth2_token") as mock_verify:
        mock_verify.return_value = {"iss": "https://accounts.google.com"}
        assert verify_google_signed_jwt("token-abc", "audience-123") is True
        mock_verify.assert_called_once()


def test_verify_google_signed_jwt_invalid_issuer():
    with patch("src.gcp.jwt_verifier.id_token.verify_oauth2_token") as mock_verify:
        mock_verify.return_value = {"iss": "https://not-google.example.com"}
        assert verify_google_signed_jwt("token-abc", "audience-123") is False


def test_verify_google_signed_jwt_missing_token():
    assert verify_google_signed_jwt(None, "aud") is False
    assert verify_google_signed_jwt("", "aud") is False


def test_verify_google_signed_jwt_exception():
    with patch("src.gcp.jwt_verifier.id_token.verify_oauth2_token") as mock_verify:
        mock_verify.side_effect = Exception("boom")
        assert verify_google_signed_jwt("token-abc", "audience-123") is False
