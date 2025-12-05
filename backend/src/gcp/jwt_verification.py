"""
Google JWT Verification for GCP Marketplace Webhooks
Verifies JWT tokens signed by Google for webhook security
"""

import jwt
import requests
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class GoogleJWTVerifier:
    """Verify JWT tokens from Google"""

    def __init__(self):
        self.certs_url = "https://www.googleapis.com/oauth2/v3/certs"
        self._certs_cache = None
        self._certs_cache_time = None
        self._cache_duration = timedelta(hours=6)

    def _get_google_public_keys(self) -> Dict:
        """
        Fetch Google's public keys for JWT verification
        Cached for 6 hours to reduce API calls

        Returns:
            Dict of public keys
        """
        # Check cache
        if self._certs_cache and self._certs_cache_time:
            age = datetime.utcnow() - self._certs_cache_time
            if age < self._cache_duration:
                logger.debug("Using cached Google public keys")
                return self._certs_cache

        try:
            logger.info("Fetching Google public keys")
            response = requests.get(self.certs_url, timeout=10)
            response.raise_for_status()

            self._certs_cache = response.json()
            self._certs_cache_time = datetime.utcnow()

            logger.info("Google public keys fetched successfully")
            return self._certs_cache

        except Exception as e:
            logger.error(f"Failed to fetch Google public keys: {e}")
            raise HTTPException(500, "Cannot verify webhook signature")

    def verify_token(self, token: str, audience: Optional[str] = None) -> Dict:
        """
        Verify JWT token from Google

        Args:
            token: JWT token string from Authorization header
            audience: Expected audience (your GCP project ID or service URL)
                     If None, audience check is skipped (for local testing)

        Returns:
            Decoded claims dictionary with user info

        Raises:
            HTTPException(401): If token is invalid or expired
            HTTPException(500): If verification process fails
        """
        try:
            # Check for test mode (for local development only!)
            if os.getenv("GCP_JWT_TEST_MODE") == "true":
                logger.warning("JWT_TEST_MODE enabled - skipping signature verification (DEVELOPMENT ONLY)")
                # Decode without verification for testing
                claims = jwt.decode(token, options={"verify_signature": False})
                logger.info(f"Test token decoded: email={claims.get('email')}")
                return claims

            # Get public keys
            keys_data = self._get_google_public_keys()

            # Decode header to get key ID (without verification)
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")

            if not kid:
                logger.warning("JWT token missing 'kid' header")
                raise HTTPException(401, "Invalid token format")

            # Find matching public key
            public_key = None
            for key in keys_data.get("keys", []):
                if key.get("kid") == kid:
                    # Convert JWK to PEM format for PyJWT
                    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                    break

            if not public_key:
                logger.warning(f"Public key not found for kid: {kid}")
                raise HTTPException(401, f"Unknown signing key: {kid}")

            # Configure verification options
            options = {
                "verify_signature": True,
                "verify_exp": True,
                "verify_aud": audience is not None,
                "verify_iss": True,
            }

            # Verify and decode token
            claims = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=audience,
                issuer="https://accounts.google.com",
                options=options
            )

            logger.info(
                "JWT verified successfully",
                extra={
                    "email": claims.get("email", "unknown"),
                    "sub": claims.get("sub"),
                }
            )

            return claims

        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
            raise HTTPException(401, "Token has expired")

        except jwt.InvalidAudienceError:
            logger.warning("JWT token has invalid audience")
            raise HTTPException(401, "Invalid token audience")

        except jwt.InvalidIssuerError:
            logger.warning("JWT token has invalid issuer")
            raise HTTPException(401, "Invalid token issuer")

        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            raise HTTPException(401, f"Invalid token: {str(e)}")

        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise

        except Exception as e:
            logger.error(f"Unexpected error verifying JWT: {e}")
            raise HTTPException(500, "Token verification failed")


# Singleton instance
_verifier_instance = None


def get_jwt_verifier() -> GoogleJWTVerifier:
    """
    Get singleton instance of JWT verifier

    Returns:
        GoogleJWTVerifier instance
    """
    global _verifier_instance
    if _verifier_instance is None:
        _verifier_instance = GoogleJWTVerifier()
    return _verifier_instance


def verify_gcp_jwt(token: str, audience: Optional[str] = None) -> Dict:
    """
    Convenience function to verify a GCP JWT token

    Args:
        token: JWT token string
        audience: Expected audience (optional for local dev)

    Returns:
        Decoded claims

    Example:
        claims = verify_gcp_jwt(token, audience="my-gcp-project")
        email = claims.get("email")
        user_id = claims.get("sub")
    """
    verifier = get_jwt_verifier()
    return verifier.verify_token(token, audience)
