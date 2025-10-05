from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.orm import Session
from typing import Dict

from ..database import get_db
from ..models import User
from ..auth import require_admin, AuthService
from ..maintenance import DataRetentionService

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


@router.post("/maintenance", response_model=dict)
async def run_maintenance(
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Run database maintenance tasks (Admin only)"""
    # Run all cleanup tasks
    stats = DataRetentionService.run_all_cleanup_tasks(db)

    # Log audit event
    AuthService.log_audit(
        db=db,
        user_id=current_user.id,
        action="admin.maintenance",
        resource_type="system",
        details=stats,
        request=request
    )

    return {
        "message": "Maintenance tasks completed successfully",
        "statistics": stats
    }


@router.post("/maintenance/audit-logs", response_model=dict)
async def cleanup_audit_logs(
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Cleanup old audit logs (Admin only)"""
    deleted_count = DataRetentionService.cleanup_old_audit_logs(db)

    AuthService.log_audit(
        db=db,
        user_id=current_user.id,
        action="admin.cleanup_audit_logs",
        resource_type="system",
        details={"deleted_count": deleted_count},
        request=request
    )

    return {
        "message": "Audit logs cleanup completed",
        "deleted_count": deleted_count
    }


@router.post("/maintenance/sessions", response_model=dict)
async def cleanup_sessions(
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Cleanup old sessions (Admin only)"""
    deleted_count = DataRetentionService.cleanup_old_sessions(db)

    AuthService.log_audit(
        db=db,
        user_id=current_user.id,
        action="admin.cleanup_sessions",
        resource_type="system",
        details={"deleted_count": deleted_count},
        request=request
    )

    return {
        "message": "Sessions cleanup completed",
        "deleted_count": deleted_count
    }


@router.post("/maintenance/tokens", response_model=dict)
async def cleanup_tokens(
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Cleanup expired and revoked tokens (Admin only)"""
    revoked_count = DataRetentionService.cleanup_revoked_tokens(db)
    expired_count = DataRetentionService.cleanup_expired_tokens(db)
    reset_count = DataRetentionService.cleanup_used_password_reset_tokens(db)

    total_deleted = revoked_count + expired_count + reset_count

    AuthService.log_audit(
        db=db,
        user_id=current_user.id,
        action="admin.cleanup_tokens",
        resource_type="system",
        details={
            "revoked_tokens": revoked_count,
            "expired_tokens": expired_count,
            "reset_tokens": reset_count,
            "total": total_deleted
        },
        request=request
    )

    return {
        "message": "Tokens cleanup completed",
        "revoked_tokens": revoked_count,
        "expired_tokens": expired_count,
        "reset_tokens": reset_count,
        "total_deleted": total_deleted
    }


@router.get("/stats/database", response_model=dict)
async def get_database_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get database statistics (Admin only)"""
    from sqlalchemy import func, text
    from ..models import User, Session as UserSession, AuditLog, RefreshToken, PasswordResetToken
    from datetime import datetime

    stats = {
        "users": {
            "total": db.query(func.count(User.id)).scalar(),
            "active": db.query(func.count(User.id)).filter(User.is_active == True).scalar(),
            "verified": db.query(func.count(User.id)).filter(User.is_verified == True).scalar(),
            "locked": db.query(func.count(User.id)).filter(User.locked_until > datetime.utcnow()).scalar(),
        },
        "sessions": {
            "total": db.query(func.count(UserSession.id)).scalar(),
            "active": db.query(func.count(UserSession.id)).filter(
                UserSession.revoked == False
            ).scalar(),
        },
        "audit_logs": {
            "total": db.query(func.count(AuditLog.id)).scalar(),
        },
        "tokens": {
            "refresh_tokens": db.query(func.count(RefreshToken.id)).scalar(),
            "revoked_refresh_tokens": db.query(func.count(RefreshToken.id)).filter(
                RefreshToken.revoked == True
            ).scalar(),
            "password_reset_tokens": db.query(func.count(PasswordResetToken.id)).scalar(),
        }
    }

    return stats


@router.post("/users/{user_id}/unlock", response_model=dict)
async def unlock_user_account(
    user_id: str,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Unlock a locked user account (Admin only)"""
    from ..models import User

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Reset lockout fields
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_failed_login = None
    db.commit()

    # Log audit event
    AuthService.log_audit(
        db=db,
        user_id=current_user.id,
        action="admin.unlock_user",
        resource_type="user",
        resource_id=user.id,
        details={"unlocked_user": user.username},
        request=request
    )

    return {
        "message": f"User account '{user.username}' unlocked successfully",
        "user_id": user.id
    }
