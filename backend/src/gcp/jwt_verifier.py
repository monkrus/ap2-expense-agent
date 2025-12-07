"""
Google-signed JWT verifier utilities.

Used to validate Pub/Sub push tokens and Marketplace webhook JWTs with audience checks.
"""

from functools import lru_cache
from typing import Optional

from google.oauth2 import id_token
from google.auth.transport import requests as grequests


@lru_cache(maxsize=1)
def _google_request() -> grequests.Request:
    """Cached HTTP request helper so JWKS fetch is reused across invocations."""
    return grequests.Request()


def verify_google_signed_jwt(token: Optional[str], audience: str) -> bool:
    """
    Verify a Google-signed JWT (e.g., Pub/Sub push) with audience check.

    Args:
        token: Authorization bearer token value (without the "Bearer " prefix)
        audience: Expected audience (webhook URL or configured override)

    Returns:
        True if token is valid and issued by Google, else False.
    """
    if not token:
        return False

    try:
        claims = id_token.verify_oauth2_token(
            token,
            _google_request(),
            audience=audience,
        )
        issuer = claims.get("iss")
        if issuer not in ("https://accounts.google.com", "accounts.google.com"):
            return False
        return True
    except Exception as exc:  # pragma: no cover - logged via print to keep dependency light
        print(f"OIDC token verification failed: {exc}")
        return False
