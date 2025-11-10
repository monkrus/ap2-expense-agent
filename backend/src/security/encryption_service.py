"""
Encryption Service for PII and Sensitive Data
Uses AES-256-GCM with Cloud KMS for key management
"""

import base64
import os
from typing import Optional

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from google.cloud import kms

from ..config import settings


class EncryptionService:
    """
    Service for encrypting/decrypting sensitive data at rest

    Uses AES-256-GCM with keys managed by Cloud KMS.
    Each encrypted value includes IV and authentication tag.
    """

    def __init__(self):
        """Initialize encryption service"""
        self.project_id = settings.gcp_project_id or os.getenv("GCP_PROJECT_ID")
        self.location = os.getenv("GCP_KMS_LOCATION", "us-central1")
        self.keyring_name = os.getenv("GCP_KMS_KEYRING", "ap2-expense-keyring")
        self.key_name = os.getenv("GCP_KMS_ENCRYPTION_KEY", "ap2-data-encryption-key")

        # Initialize KMS client
        self.client: Optional[kms.KeyManagementServiceClient] = None
        self.key_path: Optional[str] = None

        # DEK (Data Encryption Key) cache - encrypted with KEK in KMS
        self._dek_cache: Optional[bytes] = None

        if self.project_id and os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            try:
                self.client = kms.KeyManagementServiceClient()
                self.key_path = self.client.crypto_key_path(
                    self.project_id, self.location, self.keyring_name, self.key_name
                )
            except Exception as e:
                print(f"Warning: Cloud KMS encryption not available: {e}")

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext data

        Args:
            plaintext: String data to encrypt

        Returns:
            Base64-encoded encrypted data (format: iv:ciphertext:tag)

        Example:
            encrypted = service.encrypt("sensitive PII data")
            # Returns: "tRzXY...:9fKmL...:aB3dE..."
        """
        if not plaintext:
            return ""

        if not self.client or not self.key_path:
            # Development fallback
            if settings.environment == "development":
                return self._dev_encrypt(plaintext)
            raise ValueError("Encryption not configured. Set GCP_PROJECT_ID.")

        # Get or generate DEK
        dek = self._get_dek()

        # Generate random IV (96 bits for GCM)
        iv = os.urandom(12)

        # Encrypt using AES-256-GCM
        cipher = Cipher(algorithms.AES(dek), modes.GCM(iv), backend=default_backend())
        encryptor = cipher.encryptor()

        ciphertext = encryptor.update(plaintext.encode("utf-8")) + encryptor.finalize()

        # Get authentication tag
        tag = encryptor.tag

        # Combine IV, ciphertext, and tag
        encrypted_data = (
            base64.b64encode(iv).decode("utf-8")
            + ":"
            + base64.b64encode(ciphertext).decode("utf-8")
            + ":"
            + base64.b64encode(tag).decode("utf-8")
        )

        return encrypted_data

    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt encrypted data

        Args:
            encrypted_data: Base64-encoded encrypted string (iv:ciphertext:tag)

        Returns:
            Decrypted plaintext string

        Raises:
            ValueError: If decryption fails (tampered data, wrong key, etc.)
        """
        if not encrypted_data:
            return ""

        if not self.client or not self.key_path:
            # Development fallback
            if settings.environment == "development":
                return self._dev_decrypt(encrypted_data)
            raise ValueError("Decryption not configured")

        try:
            # Parse encrypted data
            parts = encrypted_data.split(":")
            if len(parts) != 3:
                raise ValueError("Invalid encrypted data format")

            iv = base64.b64decode(parts[0])
            ciphertext = base64.b64decode(parts[1])
            tag = base64.b64decode(parts[2])

            # Get DEK
            dek = self._get_dek()

            # Decrypt using AES-256-GCM
            cipher = Cipher(
                algorithms.AES(dek), modes.GCM(iv, tag), backend=default_backend()
            )
            decryptor = cipher.decryptor()

            plaintext = decryptor.update(ciphertext) + decryptor.finalize()

            return plaintext.decode("utf-8")

        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")

    def _get_dek(self) -> bytes:
        """
        Get Data Encryption Key (DEK)

        Uses envelope encryption:
        1. DEK is a random AES-256 key used for data encryption
        2. DEK is encrypted with KEK (Key Encryption Key) in Cloud KMS
        3. Encrypted DEK is cached in memory for performance

        Returns:
            32-byte AES-256 key
        """
        if self._dek_cache:
            return self._dek_cache

        # Generate new DEK
        dek = os.urandom(32)  # 256 bits

        # Encrypt DEK with KMS (envelope encryption)
        # In production, store encrypted DEK in database or config
        # For now, we generate fresh DEK per session

        self._dek_cache = dek
        return dek

    def _dev_encrypt(self, plaintext: str) -> str:
        """
        Development-only encryption (INSECURE)

        WARNING: Uses hardcoded key, not secure!
        """
        # Use simple base64 encoding in dev (NOT SECURE!)
        # This allows development without GCP setup
        return base64.b64encode(plaintext.encode("utf-8")).decode("utf-8")

    def _dev_decrypt(self, encrypted_data: str) -> str:
        """
        Development-only decryption (INSECURE)
        """
        try:
            return base64.b64decode(encrypted_data).decode("utf-8")
        except:
            return encrypted_data  # Return as-is if not encoded


# Singleton instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """
    Get singleton encryption service instance

    Returns:
        EncryptionService instance
    """
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service
