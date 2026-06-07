"""
Encrypt/decrypt QuickBooks OAuth tokens at rest.

Uses Fernet symmetric encryption derived from the app's JWT secret.
Tokens are encrypted before storage and decrypted on read.
"""

import base64
import hashlib

from cryptography.fernet import Fernet

from ..config import settings


def _get_fernet() -> Fernet:
    """Derive a Fernet key from the JWT secret."""
    # Derive a 32-byte key from JWT secret using SHA-256
    key_bytes = hashlib.sha256(settings.jwt_secret.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_token(plaintext: str) -> str:
    """Encrypt a token string. Returns base64-encoded ciphertext."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    """Decrypt a token string."""
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()
