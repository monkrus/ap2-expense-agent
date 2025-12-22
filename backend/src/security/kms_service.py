"""
Google Cloud KMS Integration for Cryptographic Signing
Provides secure key management and signing for AP2 mandates
"""

import base64
import hashlib
import hmac
import os
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from google.cloud import kms
    from google.cloud.kms_v1 import KeyManagementServiceClient

from ..config import settings


class KMSSigningService:
    """
    Service for cryptographic signing using Google Cloud KMS

    Uses asymmetric RSA keys stored in Cloud KMS for secure mandate signing.
    Keys never leave Google's Hardware Security Modules (HSMs).
    """

    def __init__(self):
        """Initialize KMS client and key configuration"""
        self.project_id = settings.gcp_project_id or os.getenv("GCP_PROJECT_ID")
        self.location = os.getenv("GCP_KMS_LOCATION", "us-central1")
        self.keyring_name = os.getenv("GCP_KMS_KEYRING", "ap2-expense-keyring")
        self.key_name = os.getenv("GCP_KMS_SIGNING_KEY", "ap2-mandate-signing-key")

        # Initialize KMS client
        self.client: Optional["KeyManagementServiceClient"] = None
        self.key_path: Optional[str] = None

        # Only initialize if GCP credentials are available
        if self.project_id and os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            try:
                # Lazy import to avoid import errors in test environments
                from google.cloud.kms_v1 import KeyManagementServiceClient

                self.client = KeyManagementServiceClient()
                self.key_path = self.client.crypto_key_path(
                    self.project_id, self.location, self.keyring_name, self.key_name
                )
            except Exception as e:
                print(f"Warning: Cloud KMS not available: {e}")
                print("Falling back to local signing (dev mode only)")

    def sign_mandate(self, data: str) -> str:
        """
        Sign mandate data using Cloud KMS asymmetric key

        Args:
            data: String data to sign (JSON serialized mandate)

        Returns:
            Base64-encoded signature

        Raises:
            ValueError: If KMS is not configured
        """
        # Determine if we are in a non-prod/test context
        in_test_mode = (
            os.getenv("TESTING") in ("true", "True", "1")
            or os.getenv("PYTEST_CURRENT_TEST") is not None
            or settings.environment not in ("production", "staging")
        )
        allow_dev_fallback = in_test_mode or settings.allow_dev_kms_fallback

        if not self.client or not self.key_path:
            # Development/testing fallback (INSECURE - only for non-prod)
            if allow_dev_fallback:
                return self._dev_sign(data)
            raise ValueError(
                "Cloud KMS not configured. Set GCP_PROJECT_ID and "
                "GOOGLE_APPLICATION_CREDENTIALS environment variables."
            )

        # Create SHA-256 digest of the data
        digest = hashlib.sha256(data.encode("utf-8")).digest()

        # Build the digest object for KMS
        digest_obj = {"sha256": digest}

        # Request asymmetric signature from KMS
        request = {
            "name": self.key_path,
            "digest": digest_obj,
        }

        response = self.client.asymmetric_sign(request)

        # Return base64-encoded signature
        signature = base64.b64encode(response.signature).decode("utf-8")
        return signature

    def verify_signature(self, data: str, signature: str) -> bool:
        """
        Verify a signature using the public key from Cloud KMS

        Args:
            data: Original data that was signed
            signature: Base64-encoded signature to verify

        Returns:
            True if signature is valid, False otherwise
        """
        in_test_mode = (
            os.getenv("TESTING") in ("true", "True", "1")
            or os.getenv("PYTEST_CURRENT_TEST") is not None
            or settings.environment not in ("production", "staging")
        )
        allow_dev_fallback = in_test_mode or settings.allow_dev_kms_fallback

        if not self.client or not self.key_path:
            # Development/testing fallback
            if allow_dev_fallback:
                return self._dev_verify(data, signature)
            return False

        try:
            # Get the public key from KMS
            public_key = self.client.get_public_key(name=self.key_path)

            # Create digest
            digest = hashlib.sha256(data.encode("utf-8")).digest()

            # Decode signature
            signature_bytes = base64.b64decode(signature)

            # Verify using cryptography library
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding, rsa

            # Load public key
            public_key_pem = public_key.pem.encode("utf-8")
            pub_key = serialization.load_pem_public_key(
                public_key_pem, backend=default_backend()
            )

            # Verify signature
            pub_key.verify(
                signature_bytes,
                data.encode("utf-8"),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            return True

        except Exception as e:
            print(f"Signature verification failed: {e}")
            return False

    def _dev_sign(self, data: str) -> str:
        """
        Development-only signing using deterministic HMAC

        Produces a 256-byte signature (base64 ~344 chars) to mirror RSA-2048
        output length for tests that validate signature size.

        WARNING: This is INSECURE and should NEVER be used in production!
        Uses a static secret to keep signatures stable for tests.
        """
        secret = (settings.jwt_secret or "dev-signing-secret").encode("utf-8")
        seed = hmac.new(secret, data.encode("utf-8"), hashlib.sha256).digest()

        # Expand to 256 bytes deterministically (RSA-2048 signature size)
        output = bytearray()
        counter = 0
        while len(output) < 256:
            counter_bytes = counter.to_bytes(4, "big")
            block = hmac.new(secret, seed + counter_bytes, hashlib.sha256).digest()
            output.extend(block)
            counter += 1

        return base64.b64encode(bytes(output[:256])).decode("utf-8")

    def _dev_verify(self, data: str, signature: str) -> bool:
        """
        Development-only signature verification

        WARNING: This is INSECURE and should NEVER be used in production!
        Use only for testing, never in production.
        """
        expected = self._dev_sign(data)
        return hmac.compare_digest(expected, signature)

    def get_public_key_pem(self) -> str:
        """
        Get the public key in PEM format for external verification

        Returns:
            PEM-encoded public key string
        """
        if not self.client or not self.key_path:
            raise ValueError("Cloud KMS not configured")

        public_key = self.client.get_public_key(name=self.key_path)
        return public_key.pem


# Singleton instance
_kms_service: Optional[KMSSigningService] = None


def get_kms_service() -> KMSSigningService:
    """
    Get singleton KMS service instance

    Returns:
        KMSSigningService instance
    """
    global _kms_service
    if _kms_service is None:
        _kms_service = KMSSigningService()
    return _kms_service
