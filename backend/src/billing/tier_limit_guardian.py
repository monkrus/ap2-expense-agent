"""
Tier Limit Guardian - Ensures tier limits remain intact and unmodified

This module provides runtime protection for tier limits:
1. Validates tier limits on application startup
2. Calculates and verifies checksums
3. Detects unauthorized modifications
4. Provides read-only access to tier limits
5. Alerts on tampering attempts
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models_billing import BillingTier

logger = logging.getLogger(__name__)


# OFFICIAL TIER LIMITS - READ ONLY
# These are the IMMUTABLE source of truth
# Changes require approval from Product, Finance, and Legal
OFFICIAL_TIER_LIMITS = {
    "free": {
        "max_users": 2,
        "max_organizations": 1,
        "max_expenses_per_month": 30,
        "max_receipt_size_mb": 5,
        "max_storage_gb": 0.5,
        "ocr_scans_included": 20,
        "ocr_scans_per_day": 3,
        "ai_categorizations_included": 0,
        "ap2_transactions_included": 20,
        "data_retention_days": 90,
    },
    "starter": {
        "max_users": 10,
        "max_organizations": 3,
        "max_expenses_per_month": 100,
        "max_receipt_size_mb": 10,
        "max_storage_gb": 5,
        "ocr_scans_included": 100,
        "ocr_scans_per_day": 20,
        "ai_categorizations_included": 50,
        "ap2_transactions_included": 100,
        "data_retention_days": 365,
    },
    "professional": {
        "max_users": 50,
        "max_organizations": 10,
        "max_expenses_per_month": 500,
        "max_receipt_size_mb": 10,
        "max_storage_gb": 50,
        "ocr_scans_included": None,  # Unlimited
        "ocr_scans_per_day": None,  # Unlimited
        "ai_categorizations_included": 200,
        "ap2_transactions_included": None,  # Unlimited
        "data_retention_days": 1095,  # 3 years
    },
}


class TierLimitTamperError(Exception):
    """Raised when tier limits have been tampered with"""

    pass


class TierLimitGuardian:
    """
    Guardian for tier limits - ensures limits remain intact

    This class provides:
    - Read-only access to tier limits
    - Checksum validation
    - Tamper detection
    - Automatic alerts
    """

    def __init__(self):
        self._cache: Dict[str, Dict] = {}
        self._last_verification: Optional[datetime] = None
        self._verification_failures: List[Dict] = []

    @staticmethod
    def calculate_checksum(tier_name: str, limits: Dict[str, Any]) -> str:
        """
        Calculate SHA256 checksum of tier limits

        Args:
            tier_name: Name of the tier
            limits: Tier limits dictionary

        Returns:
            Hex digest of SHA256 checksum
        """
        # Sort keys to ensure consistent ordering
        data = f"{tier_name}:{json.dumps(limits, sort_keys=True)}"
        return hashlib.sha256(data.encode()).hexdigest()

    def verify_tier_limits(self, db: Session) -> bool:
        """
        Verify all tier limits in database match official specification

        Args:
            db: Database session

        Returns:
            True if all limits are correct, False otherwise

        Raises:
            TierLimitTamperError: If tier limits have been modified
        """
        logger.info("Starting tier limits verification")

        violations = []

        for tier_name, official_limits in OFFICIAL_TIER_LIMITS.items():
            tier = (
                db.query(BillingTier).filter(BillingTier.tier_name == tier_name).first()
            )

            if not tier:
                violation = {
                    "tier": tier_name,
                    "error": "TIER_NOT_FOUND",
                    "message": f"Tier '{tier_name}' not found in database",
                    "severity": "CRITICAL",
                }
                violations.append(violation)
                logger.error(f"SECURITY: {violation['message']}")
                continue

            # Verify each limit
            for key, expected_value in official_limits.items():
                actual_value = tier.limits.get(key)

                if actual_value != expected_value:
                    violation = {
                        "tier": tier_name,
                        "error": "LIMIT_MISMATCH",
                        "field": key,
                        "expected": expected_value,
                        "actual": actual_value,
                        "severity": "CRITICAL",
                        "message": f"Tier '{tier_name}' limit '{key}' mismatch: expected {expected_value}, got {actual_value}",
                    }
                    violations.append(violation)
                    logger.error(f"SECURITY: {violation['message']}")

            # Verify checksum if available
            official_checksum = self.calculate_checksum(tier_name, official_limits)
            actual_checksum = self.calculate_checksum(tier_name, tier.limits)

            if official_checksum != actual_checksum:
                violation = {
                    "tier": tier_name,
                    "error": "CHECKSUM_MISMATCH",
                    "expected_checksum": official_checksum,
                    "actual_checksum": actual_checksum,
                    "severity": "CRITICAL",
                    "message": f"Tier '{tier_name}' checksum mismatch - limits may have been tampered with",
                }
                violations.append(violation)
                logger.error(f"SECURITY: {violation['message']}")

        self._last_verification = datetime.utcnow()

        if violations:
            self._verification_failures = violations

            # Log detailed violation report
            logger.critical("=" * 60)
            logger.critical("TIER LIMIT TAMPERING DETECTED")
            logger.critical("=" * 60)
            for violation in violations:
                logger.critical(json.dumps(violation, indent=2))
            logger.critical("=" * 60)
            logger.critical("IMMEDIATE ACTION REQUIRED:")
            logger.critical("1. Investigate who modified tier limits")
            logger.critical("2. Run: python backend/seed_billing_tiers.py --force")
            logger.critical("3. Review audit logs in tier_limit_audit table")
            logger.critical("4. Notify security team")
            logger.critical("=" * 60)

            # Raise exception to prevent application from starting
            raise TierLimitTamperError(
                f"Tier limits have been tampered with. {len(violations)} violations detected. "
                f"See logs for details. Application startup blocked for security."
            )

        logger.info("[PASS] Tier limits verification passed - all limits are correct")
        return True

    def get_tier_limits(self, tier_name: str, db: Session) -> Dict[str, Any]:
        """
        Get tier limits (read-only)

        ALWAYS returns official limits, never from database
        Use this instead of querying database directly

        Args:
            tier_name: Name of the tier
            db: Database session (used for verification only)

        Returns:
            Tier limits dictionary

        Raises:
            ValueError: If tier not found
            TierLimitTamperError: If tier limits have been tampered with
        """
        if tier_name not in OFFICIAL_TIER_LIMITS:
            raise ValueError(f"Unknown tier: {tier_name}")

        # Verify limits on first access or if cache is stale
        if (
            not self._last_verification
            or (datetime.utcnow() - self._last_verification).total_seconds() > 3600
        ):
            self.verify_tier_limits(db)

        # Return copy to prevent modification
        return OFFICIAL_TIER_LIMITS[tier_name].copy()

    def is_limit_unlimited(self, tier_name: str, limit_key: str) -> bool:
        """
        Check if a specific limit is unlimited (None)

        Args:
            tier_name: Name of the tier
            limit_key: Key of the limit to check

        Returns:
            True if unlimited, False otherwise
        """
        if tier_name not in OFFICIAL_TIER_LIMITS:
            return False

        return OFFICIAL_TIER_LIMITS[tier_name].get(limit_key) is None

    def get_all_tier_limits(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all tier limits (read-only)

        Returns:
            Dictionary of all tier limits
        """
        # Return deep copy to prevent modification
        return {tier: limits.copy() for tier, limits in OFFICIAL_TIER_LIMITS.items()}

    def get_verification_status(self) -> Dict[str, Any]:
        """
        Get current verification status

        Returns:
            Dictionary with verification status
        """
        return {
            "last_verification": (
                self._last_verification.isoformat() if self._last_verification else None
            ),
            "failures": self._verification_failures,
            "is_healthy": len(self._verification_failures) == 0,
        }

    def force_verification(self) -> bool:
        """
        Force immediate verification of tier limits

        Returns:
            True if verification passed, False otherwise
        """
        db = SessionLocal()
        try:
            return self.verify_tier_limits(db)
        finally:
            db.close()


# Global singleton instance
_guardian_instance: Optional[TierLimitGuardian] = None


def get_tier_limit_guardian() -> TierLimitGuardian:
    """
    Get the global TierLimitGuardian instance

    Returns:
        TierLimitGuardian singleton instance
    """
    global _guardian_instance

    if _guardian_instance is None:
        _guardian_instance = TierLimitGuardian()

    return _guardian_instance


def verify_tier_limits_on_startup():
    """
    Verify tier limits when application starts

    This function should be called during application initialization
    to ensure tier limits are intact before accepting requests

    Raises:
        TierLimitTamperError: If tier limits have been tampered with
    """
    logger.info("Verifying tier limits on application startup...")

    guardian = get_tier_limit_guardian()
    db = SessionLocal()

    try:
        guardian.verify_tier_limits(db)
        logger.info(
            "[PASS] Tier limits verification passed - application startup allowed"
        )
    except TierLimitTamperError as e:
        logger.critical(
            f"[FAIL] Tier limits verification FAILED - application startup BLOCKED"
        )
        logger.critical(f"Error: {e}")
        raise
    finally:
        db.close()


# Expose for easy imports
__all__ = [
    "TierLimitGuardian",
    "TierLimitTamperError",
    "get_tier_limit_guardian",
    "verify_tier_limits_on_startup",
    "OFFICIAL_TIER_LIMITS",
]
