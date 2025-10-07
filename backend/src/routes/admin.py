from fastapi import APIRouter, Depends, status, Request, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, text
from typing import Dict, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from ..database import get_db
from ..models import User, Organization, UserRole
from ..auth import require_admin, AuthService
from ..maintenance import DataRetentionService

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


class UpdateUserRoleRequest(BaseModel):
    role: UserRole


class SuspendUserRequest(BaseModel):
    reason: str


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
    from ..models import Session as UserSession, AuditLog, RefreshToken, PasswordResetToken

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


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get platform-wide statistics for admin dashboard"""

    # User statistics
    total_users = db.query(func.count(User.id)).scalar()
    active_users_30d = db.query(func.count(User.id)).filter(
        User.last_login >= datetime.utcnow() - timedelta(days=30)
    ).scalar()
    new_users_7d = db.query(func.count(User.id)).filter(
        User.created_at >= datetime.utcnow() - timedelta(days=7)
    ).scalar()

    # Organization statistics
    total_orgs = db.query(func.count(Organization.id)).scalar()
    active_orgs = db.query(func.count(Organization.id)).filter(
        Organization.is_active == True
    ).scalar()

    # Try to get expense statistics if the table exists
    try:
        from ..models import Expense
        total_expenses = db.query(func.count(Expense.id)).scalar()
        total_expense_value = db.query(func.sum(Expense.amount)).scalar() or 0
        expenses_this_month = db.query(func.count(Expense.id)).filter(
            Expense.created_at >= datetime.utcnow().replace(day=1)
        ).scalar()
    except:
        total_expenses = 0
        total_expense_value = 0
        expenses_this_month = 0

    # Try to get subscription statistics if the table exists
    try:
        from ..models import Subscription
        active_subscriptions = db.query(func.count(Subscription.id)).filter(
            Subscription.status == "active"
        ).scalar()
        monthly_revenue = db.query(func.sum(Subscription.amount)).filter(
            Subscription.status == "active",
            Subscription.interval == "month"
        ).scalar() or 0
    except:
        active_subscriptions = 0
        monthly_revenue = 0

    return {
        "users": {
            "total": total_users,
            "active_30d": active_users_30d,
            "new_7d": new_users_7d,
            "growth_rate": round((new_users_7d / max(total_users, 1)) * 100, 2)
        },
        "organizations": {
            "total": total_orgs,
            "active": active_orgs
        },
        "expenses": {
            "total_count": total_expenses,
            "total_value": float(total_expense_value),
            "this_month": expenses_this_month
        },
        "revenue": {
            "active_subscriptions": active_subscriptions,
            "monthly_recurring": float(monthly_revenue),
            "annual_recurring": float(monthly_revenue * 12)
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List all users with filtering and pagination"""

    query = db.query(User)

    # Search filter
    if search:
        query = query.filter(
            (User.email.ilike(f"%{search}%")) |
            (User.username.ilike(f"%{search}%")) |
            (User.full_name.ilike(f"%{search}%"))
        )

    # Role filter
    if role:
        query = query.filter(User.role == role)

    # Pagination
    total = query.count()
    users = query.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "username": u.username,
                "full_name": u.full_name,
                "role": u.role,
                "is_active": u.is_active,
                "is_verified": u.is_verified,
                "created_at": u.created_at.isoformat(),
                "last_login": u.last_login.isoformat() if u.last_login else None
            }
            for u in users
        ],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        }
    }


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    request: UpdateUserRoleRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update user role"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = request.role
    db.commit()

    return {"success": True, "user_id": user_id, "new_role": request.role}


@router.post("/users/{user_id}/suspend")
async def suspend_user(
    user_id: str,
    request: SuspendUserRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Suspend user account"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    db.commit()

    return {"success": True, "user_id": user_id}


@router.get("/analytics/usage")
async def get_usage_analytics(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get platform usage analytics"""

    start_date = datetime.utcnow() - timedelta(days=days)

    # Daily active users
    daily_users = db.query(
        func.date(User.last_login).label("date"),
        func.count(User.id).label("count")
    ).filter(
        User.last_login >= start_date
    ).group_by(func.date(User.last_login)).all()

    # Try to get expense analytics if table exists
    try:
        from ..models import Expense
        daily_expenses = db.query(
            func.date(Expense.created_at).label("date"),
            func.count(Expense.id).label("count"),
            func.sum(Expense.amount).label("total_amount")
        ).filter(
            Expense.created_at >= start_date
        ).group_by(func.date(Expense.created_at)).all()
    except:
        daily_expenses = []

    return {
        "period_days": days,
        "daily_active_users": [
            {"date": d.date.isoformat(), "count": d.count}
            for d in daily_users
        ],
        "daily_expenses": [
            {
                "date": d.date.isoformat(),
                "count": d.count,
                "total_amount": float(d.total_amount or 0)
            }
            for d in daily_expenses
        ]
    }


@router.get("/system/health")
async def system_health_check(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Advanced system health check for admins"""

    from ..monitoring import HealthCheck
    from ..cache import cache

    # Database health
    db_health = await HealthCheck.check_database(db)

    # Redis health
    redis_health = await HealthCheck.check_redis()

    # Disk health
    disk_health = HealthCheck.check_disk_space()

    # Memory health
    memory_health = HealthCheck.check_memory()

    # Performance metrics
    performance = {
        "cache_hit_rate": cache.get_hit_rate() if hasattr(cache, 'get_hit_rate') else None,
        "avg_response_time": None  # Would come from monitoring
    }

    overall_status = "healthy"
    if any(h.get("status") == "unhealthy" for h in [db_health, redis_health]):
        overall_status = "unhealthy"
    elif any(h.get("status") == "warning" for h in [disk_health, memory_health]):
        overall_status = "degraded"

    return {
        "overall_status": overall_status,
        "components": {
            "database": db_health,
            "redis": redis_health,
            "disk": disk_health,
            "memory": memory_health
        },
        "performance": performance,
        "timestamp": datetime.utcnow().isoformat()
    }


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
