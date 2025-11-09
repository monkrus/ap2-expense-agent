"""
Database maintenance and data retention tasks
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from .config import settings
from .database import SessionLocal
from .models import AuditLog, PasswordResetToken, RefreshToken
from .models import Session as UserSession

logger = logging.getLogger(__name__)


class DataRetentionService:
    """Service for managing data retention policies"""

    @staticmethod
    def cleanup_old_audit_logs(db: Session) -> int:
        """Delete audit logs older than retention period"""
        cutoff_date = datetime.utcnow() - timedelta(
            days=settings.audit_log_retention_days
        )

        result = db.execute(delete(AuditLog).where(AuditLog.created_at < cutoff_date))

        deleted_count = result.rowcount
        db.commit()

        logger.info(
            f"Deleted {deleted_count} audit logs older than {settings.audit_log_retention_days} days"
        )
        return deleted_count

    @staticmethod
    def cleanup_old_sessions(db: Session) -> int:
        """Delete expired and old sessions"""
        cutoff_date = datetime.utcnow() - timedelta(
            days=settings.session_retention_days
        )

        # Delete sessions that are either expired or older than retention period
        result = db.execute(
            delete(UserSession).where(
                (UserSession.expires_at < datetime.utcnow())
                | (UserSession.created_at < cutoff_date)
            )
        )

        deleted_count = result.rowcount
        db.commit()

        logger.info(f"Deleted {deleted_count} old/expired sessions")
        return deleted_count

    @staticmethod
    def cleanup_revoked_tokens(db: Session) -> int:
        """Delete revoked refresh tokens older than retention period"""
        cutoff_date = datetime.utcnow() - timedelta(
            days=settings.revoked_token_retention_days
        )

        result = db.execute(
            delete(RefreshToken).where(
                (RefreshToken.revoked == True) & (RefreshToken.created_at < cutoff_date)
            )
        )

        deleted_count = result.rowcount
        db.commit()

        logger.info(
            f"Deleted {deleted_count} revoked tokens older than {settings.revoked_token_retention_days} days"
        )
        return deleted_count

    @staticmethod
    def cleanup_expired_tokens(db: Session) -> int:
        """Delete all expired tokens (refresh tokens and password reset tokens)"""
        now = datetime.utcnow()

        # Delete expired refresh tokens
        refresh_result = db.execute(
            delete(RefreshToken).where(RefreshToken.expires_at < now)
        )

        # Delete expired password reset tokens
        reset_result = db.execute(
            delete(PasswordResetToken).where(PasswordResetToken.expires_at < now)
        )

        total_deleted = refresh_result.rowcount + reset_result.rowcount
        db.commit()

        logger.info(f"Deleted {total_deleted} expired tokens")
        return total_deleted

    @staticmethod
    def cleanup_used_password_reset_tokens(db: Session) -> int:
        """Delete used password reset tokens older than 1 day"""
        cutoff_date = datetime.utcnow() - timedelta(days=1)

        result = db.execute(
            delete(PasswordResetToken).where(
                (PasswordResetToken.used == True)
                & (PasswordResetToken.created_at < cutoff_date)
            )
        )

        deleted_count = result.rowcount
        db.commit()

        logger.info(f"Deleted {deleted_count} used password reset tokens")
        return deleted_count

    @staticmethod
    def run_all_cleanup_tasks(db: Session) -> dict:
        """Run all cleanup tasks and return statistics"""
        stats = {
            "audit_logs": DataRetentionService.cleanup_old_audit_logs(db),
            "sessions": DataRetentionService.cleanup_old_sessions(db),
            "revoked_tokens": DataRetentionService.cleanup_revoked_tokens(db),
            "expired_tokens": DataRetentionService.cleanup_expired_tokens(db),
            "used_reset_tokens": DataRetentionService.cleanup_used_password_reset_tokens(
                db
            ),
            "timestamp": datetime.utcnow().isoformat(),
        }

        logger.info(f"Cleanup completed: {stats}")
        return stats


def run_maintenance():
    """Run all database maintenance tasks"""
    logger.info("Starting database maintenance tasks...")

    db = SessionLocal()
    try:
        stats = DataRetentionService.run_all_cleanup_tasks(db)
        logger.info(f"Maintenance completed successfully: {stats}")
        return stats
    except Exception as e:
        logger.error(f"Maintenance task failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run maintenance
    run_maintenance()
