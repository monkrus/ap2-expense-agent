"""
Nonce Service for Replay Attack Protection
Prevents duplicate execution of payment requests
"""

import hashlib
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional

import redis
from sqlalchemy.orm import Session

from ..config import settings


class NonceService:
    """
    Service for managing request nonces to prevent replay attacks

    Uses Redis for fast nonce validation with automatic expiration.
    Fallback to database for environments without Redis.

    Replay Attack Protection:
    1. Client includes unique nonce in each request
    2. Server validates nonce hasn't been used before
    3. Nonce is stored with 5-minute TTL
    4. After 5 minutes, nonce expires and request would be invalid anyway
    """

    def __init__(self, db: Session):
        """Initialize nonce service with Redis or database fallback"""
        self.db = db
        self.redis_client: Optional[redis.Redis] = None
        self.nonce_ttl = 300  # 5 minutes in seconds

        # Try to connect to Redis
        if settings.redis_url:
            try:
                self.redis_client = redis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2
                )
                # Test connection
                self.redis_client.ping()
                print("✓ Redis connected for nonce storage")
            except Exception as e:
                print(f"Warning: Redis not available, using database fallback: {e}")
                self.redis_client = None

    def generate_nonce(self) -> str:
        """
        Generate a new cryptographically secure nonce

        Returns:
            128-bit hex nonce (32 characters)

        Example:
            "a3f5b2c8d1e9f0a1b2c3d4e5f6a7b8c9"
        """
        return uuid.uuid4().hex

    def validate_and_store_nonce(
        self,
        nonce: str,
        request_timestamp: datetime,
        endpoint: str,
        user_id: str
    ) -> bool:
        """
        Validate nonce and store it to prevent reuse

        Args:
            nonce: Nonce from client request
            request_timestamp: Timestamp from client request
            endpoint: API endpoint (for namespace isolation)
            user_id: User making the request

        Returns:
            True if nonce is valid and stored successfully
            False if nonce has been used before or is invalid

        Raises:
            ValueError: If nonce is malformed or timestamp is too old/new
        """
        # Validate nonce format
        if not nonce or len(nonce) != 32:
            raise ValueError(
                "Invalid nonce format. Must be 32-character hex string."
            )

        # Validate timestamp (must be within ±5 minutes of server time)
        now = datetime.utcnow()
        time_diff = abs((now - request_timestamp).total_seconds())

        if time_diff > self.nonce_ttl:
            raise ValueError(
                f"Request timestamp too old/new (diff: {time_diff}s, max: {self.nonce_ttl}s). "
                "Possible replay attack or clock synchronization issue."
            )

        # Create namespaced nonce key
        nonce_key = self._create_nonce_key(nonce, endpoint, user_id)

        # Check and store nonce
        if self.redis_client:
            return self._validate_redis(nonce_key)
        else:
            return self._validate_database(nonce_key)

    def _create_nonce_key(self, nonce: str, endpoint: str, user_id: str) -> str:
        """
        Create namespaced nonce key to prevent cross-endpoint collisions

        Format: nonce:endpoint:user_id:nonce_hash
        """
        # Hash to prevent key length issues
        key_data = f"{endpoint}:{user_id}:{nonce}"
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()[:16]
        return f"nonce:{endpoint}:{user_id}:{key_hash}"

    def _validate_redis(self, nonce_key: str) -> bool:
        """
        Validate nonce using Redis (fast, atomic operation)

        Uses Redis SET with NX (Not eXists) flag for atomic check-and-set.

        Returns:
            True if nonce was stored (first time use)
            False if nonce already exists (replay attempt)
        """
        try:
            # Atomic SET NX with expiration
            # Returns True only if key didn't exist before
            result = self.redis_client.set(
                nonce_key,
                "1",
                ex=self.nonce_ttl,
                nx=True  # Only set if not exists
            )

            return result is not None

        except Exception as e:
            print(f"Redis nonce validation failed, falling back to database: {e}")
            return self._validate_database(nonce_key)

    def _validate_database(self, nonce_key: str) -> bool:
        """
        Validate nonce using database (slower fallback)

        Creates a database table to store used nonces.
        Less performant than Redis but works without external dependencies.

        Returns:
            True if nonce was stored successfully
            False if nonce already exists
        """
        from ..models import Base
        from sqlalchemy import Column, String, DateTime, Index

        # Define nonce table (lazy creation)
        class UsedNonce(Base):
            __tablename__ = "used_nonces"

            nonce_key = Column(String(255), primary_key=True)
            created_at = Column(DateTime, nullable=False, server_default="NOW()")
            expires_at = Column(DateTime, nullable=False, index=True)

            __table_args__ = (
                Index('idx_nonce_expires_at', 'expires_at'),
            )

        # Create table if not exists
        try:
            Base.metadata.create_all(bind=self.db.get_bind(), tables=[UsedNonce.__table__])
        except:
            pass  # Table likely already exists

        # Check if nonce already used
        existing = self.db.query(UsedNonce).filter_by(nonce_key=nonce_key).first()
        if existing:
            return False  # Replay attack detected

        # Store nonce
        try:
            expires_at = datetime.utcnow() + timedelta(seconds=self.nonce_ttl)
            nonce_record = UsedNonce(
                nonce_key=nonce_key,
                expires_at=expires_at
            )
            self.db.add(nonce_record)
            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            print(f"Failed to store nonce: {e}")
            return False  # Fail closed

    def cleanup_expired_nonces(self):
        """
        Clean up expired nonces from database

        Should be run periodically (e.g., daily cron job).
        Redis handles this automatically via TTL.
        """
        if self.redis_client:
            # Redis handles expiration automatically
            return

        # Database cleanup
        try:
            from ..models import Base
            from sqlalchemy import text

            # Delete expired nonces
            self.db.execute(
                text("DELETE FROM used_nonces WHERE expires_at < NOW()")
            )
            self.db.commit()

        except Exception as e:
            print(f"Failed to cleanup expired nonces: {e}")
            self.db.rollback()


# Singleton instance cache
_nonce_service: Optional[NonceService] = None


def get_nonce_service(db: Session) -> NonceService:
    """
    Get or create nonce service instance

    Args:
        db: Database session

    Returns:
        NonceService instance
    """
    global _nonce_service
    if _nonce_service is None:
        _nonce_service = NonceService(db)
    return _nonce_service
