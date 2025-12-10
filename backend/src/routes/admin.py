from datetime import datetime, timedelta
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import desc, func, text
from sqlalchemy.orm import Session

from ..auth import AuthService, require_admin, require_manager
from ..database import get_db
from ..maintenance import DataRetentionService
from ..models import Organization, User, UserRole

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


class UpdateUserRoleRequest(BaseModel):
    role: UserRole


class SuspendUserRequest(BaseModel):
    reason: str


class CreateUserRequest(BaseModel):
    email: str
    username: str
    full_name: str
    password: str
    role: UserRole
    department_id: Optional[str] = None


class UpdateUserDepartmentRequest(BaseModel):
    department_id: Optional[str] = None


class UpdateUserEmailRequest(BaseModel):
    email: str


class UpdateUserProfileRequest(BaseModel):
    username: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None


@router.post("/maintenance", response_model=dict)
async def run_maintenance(
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
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
        request=request,
    )

    return {"message": "Maintenance tasks completed successfully", "statistics": stats}


@router.post("/maintenance/audit-logs", response_model=dict)
async def cleanup_audit_logs(
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Cleanup old audit logs (Admin only)"""
    deleted_count = DataRetentionService.cleanup_old_audit_logs(db)

    AuthService.log_audit(
        db=db,
        user_id=current_user.id,
        action="admin.cleanup_audit_logs",
        resource_type="system",
        details={"deleted_count": deleted_count},
        request=request,
    )

    return {"message": "Audit logs cleanup completed", "deleted_count": deleted_count}


@router.post("/maintenance/sessions", response_model=dict)
async def cleanup_sessions(
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Cleanup old sessions (Admin only)"""
    deleted_count = DataRetentionService.cleanup_old_sessions(db)

    AuthService.log_audit(
        db=db,
        user_id=current_user.id,
        action="admin.cleanup_sessions",
        resource_type="system",
        details={"deleted_count": deleted_count},
        request=request,
    )

    return {"message": "Sessions cleanup completed", "deleted_count": deleted_count}


@router.post("/maintenance/tokens", response_model=dict)
async def cleanup_tokens(
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
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
            "total": total_deleted,
        },
        request=request,
    )

    return {
        "message": "Tokens cleanup completed",
        "revoked_tokens": revoked_count,
        "expired_tokens": expired_count,
        "reset_tokens": reset_count,
        "total_deleted": total_deleted,
    }


@router.get("/stats/database", response_model=dict)
async def get_database_stats(
    current_user: User = Depends(require_admin), db: Session = Depends(get_db)
):
    """Get database statistics (Admin only)"""
    from ..models import AuditLog, PasswordResetToken, RefreshToken
    from ..models import Session as UserSession

    stats = {
        "users": {
            "total": db.query(func.count(User.id)).scalar(),
            "active": db.query(func.count(User.id))
            .filter(User.is_active == True)
            .scalar(),
            "verified": db.query(func.count(User.id))
            .filter(User.is_verified == True)
            .scalar(),
            "locked": db.query(func.count(User.id))
            .filter(User.locked_until > datetime.utcnow())
            .scalar(),
        },
        "sessions": {
            "total": db.query(func.count(UserSession.id)).scalar(),
            "active": db.query(func.count(UserSession.id))
            .filter(UserSession.revoked == False)
            .scalar(),
        },
        "audit_logs": {
            "total": db.query(func.count(AuditLog.id)).scalar(),
        },
        "tokens": {
            "refresh_tokens": db.query(func.count(RefreshToken.id)).scalar(),
            "revoked_refresh_tokens": db.query(func.count(RefreshToken.id))
            .filter(RefreshToken.revoked == True)
            .scalar(),
            "password_reset_tokens": db.query(
                func.count(PasswordResetToken.id)
            ).scalar(),
        },
    }

    return stats


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    current_user: User = Depends(require_admin), db: Session = Depends(get_db)
):
    """Get platform-wide statistics for admin dashboard"""

    # User statistics
    total_users = db.query(func.count(User.id)).scalar()
    active_users_30d = (
        db.query(func.count(User.id))
        .filter(User.last_login >= datetime.utcnow() - timedelta(days=30))
        .scalar()
    )
    new_users_7d = (
        db.query(func.count(User.id))
        .filter(User.created_at >= datetime.utcnow() - timedelta(days=7))
        .scalar()
    )

    # Organization statistics
    total_orgs = db.query(func.count(Organization.id)).scalar()
    active_orgs = (
        db.query(func.count(Organization.id))
        .filter(Organization.is_active == True)
        .scalar()
    )

    # Try to get expense statistics if the table exists
    try:
        from ..models import Expense

        total_expenses = db.query(func.count(Expense.id)).scalar()
        total_expense_value = db.query(func.sum(Expense.amount)).scalar() or 0
        expenses_this_month = (
            db.query(func.count(Expense.id))
            .filter(Expense.created_at >= datetime.utcnow().replace(day=1))
            .scalar()
        )
    except:
        total_expenses = 0
        total_expense_value = 0
        expenses_this_month = 0

    # Try to get subscription statistics if the table exists
    try:
        from ..models_billing import OrganizationSubscription

        active_subscriptions = (
            db.query(func.count(OrganizationSubscription.id))
            .filter(OrganizationSubscription.status == "active")
            .scalar()
        )
        # For now, monthly revenue calculation would need pricing info
        monthly_revenue = 0
    except:
        active_subscriptions = 0
        monthly_revenue = 0

    return {
        "users": {
            "total": total_users,
            "active_30d": active_users_30d,
            "new_7d": new_users_7d,
            "growth_rate": round((new_users_7d / max(total_users, 1)) * 100, 2),
        },
        "organizations": {"total": total_orgs, "active": active_orgs},
        "expenses": {
            "total_count": total_expenses,
            "total_value": float(total_expense_value),
            "this_month": expenses_this_month,
        },
        "revenue": {
            "active_subscriptions": active_subscriptions,
            "monthly_recurring": float(monthly_revenue),
            "annual_recurring": float(monthly_revenue * 12),
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all users with filtering and pagination"""

    query = db.query(User)

    # Search filter
    if search:
        query = query.filter(
            (User.email.ilike(f"%{search}%"))
            | (User.username.ilike(f"%{search}%"))
            | (User.full_name.ilike(f"%{search}%"))
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
                "role": u.role.value,
                "department_id": u.department_id,
                "is_active": u.is_active,
                "is_verified": u.is_verified,
                "created_at": u.created_at.isoformat(),
                "last_login": u.last_login.isoformat() if u.last_login else None,
            }
            for u in users
        ],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page,
        },
    }


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    request: UpdateUserRoleRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update user role"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = request.role
    db.commit()

    return {"success": True, "user_id": user_id, "new_role": request.role}


@router.post("/users/{user_id}/suspend", response_model=dict)
async def suspend_user(
    user_id: str,
    suspend_request: SuspendUserRequest,
    http_request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Suspend user account (Admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Prevent admin from suspending themselves
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot suspend your own account",
        )

    # Check if user is already suspended
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is already suspended",
        )

    user.is_active = False
    user.updated_at = datetime.utcnow()

    # Revoke all active sessions and refresh tokens for this user
    from ..models import RefreshToken
    from ..models import Session as UserSession

    # Revoke all active sessions
    active_sessions = (
        db.query(UserSession)
        .filter(UserSession.user_id == user_id, UserSession.revoked == False)
        .all()
    )
    sessions_revoked = len(active_sessions)
    for session in active_sessions:
        session.revoked = True

    # Revoke all active refresh tokens
    active_tokens = (
        db.query(RefreshToken)
        .filter(RefreshToken.user_id == user_id, RefreshToken.revoked == False)
        .all()
    )
    tokens_revoked = len(active_tokens)
    for token in active_tokens:
        token.revoked = True

    db.commit()

    # Log audit event
    AuthService.log_audit(
        db=db,
        user_id=current_user.id,
        action="admin.suspend_user",
        resource_type="user",
        resource_id=user.id,
        details={
            "suspended_user": user.username,
            "reason": suspend_request.reason,
            "sessions_revoked": sessions_revoked,
            "tokens_revoked": tokens_revoked,
        },
        request=http_request,
    )

    return {
        "success": True,
        "message": f"User '{user.username}' suspended successfully",
        "user_id": user_id,
        "reason": suspend_request.reason,
        "sessions_revoked": sessions_revoked,
        "tokens_revoked": tokens_revoked,
    }


@router.get("/analytics/usage")
async def get_usage_analytics(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get platform usage analytics"""

    start_date = datetime.utcnow() - timedelta(days=days)

    # Daily active users
    daily_users = (
        db.query(
            func.date(User.last_login).label("date"), func.count(User.id).label("count")
        )
        .filter(User.last_login >= start_date)
        .group_by(func.date(User.last_login))
        .all()
    )

    # Try to get expense analytics if table exists
    try:
        from ..models import Expense

        daily_expenses = (
            db.query(
                func.date(Expense.created_at).label("date"),
                func.count(Expense.id).label("count"),
                func.sum(Expense.amount).label("total_amount"),
            )
            .filter(Expense.created_at >= start_date)
            .group_by(func.date(Expense.created_at))
            .all()
        )
    except:
        daily_expenses = []

    return {
        "period_days": days,
        "daily_active_users": [
            {"date": d.date.isoformat(), "count": d.count} for d in daily_users
        ],
        "daily_expenses": [
            {
                "date": d.date.isoformat(),
                "count": d.count,
                "total_amount": float(d.total_amount or 0),
            }
            for d in daily_expenses
        ],
    }


@router.get("/system/health")
async def system_health_check(
    current_user: User = Depends(require_admin), db: Session = Depends(get_db)
):
    """Advanced system health check for admins"""

    from ..cache import cache
    from ..monitoring import HealthCheck

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
        "cache_hit_rate": (
            cache.get_hit_rate() if hasattr(cache, "get_hit_rate") else None
        ),
        "avg_response_time": None,  # Would come from monitoring
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
            "memory": memory_health,
        },
        "performance": performance,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/users/{user_id}/unlock", response_model=dict)
async def unlock_user_account(
    user_id: str,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Unlock a locked user account (Admin only)"""
    from ..models import User

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
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
        request=request,
    )

    return {
        "message": f"User account '{user.username}' unlocked successfully",
        "user_id": user.id,
    }


@router.get("/expenses")
async def get_all_expenses(
    request: Request,
    status: Optional[str] = Query(None),
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db),
):
    """Get all expenses from all users with optional status filter (admin and manager)"""
    import logging

    from ..models import Expense, ExpenseStatus
    from ..models import User as UserModel
    from ..tenant_context import verify_organization_access

    logger = logging.getLogger(__name__)
    logger.info(f"[admin.get_all_expenses] Called with status filter: {status}")

    # SECURITY: Get and validate organization context
    org_id = request.headers.get("X-Organization-Id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required (X-Organization-Id header missing)"
        )

    # SECURITY: Verify user has access to this organization
    if not verify_organization_access(current_user.id, org_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this organization"
        )

    # Build query - exclude withdrawn and archived by default + filter by organization
    query = db.query(Expense).filter(
        Expense.organization_id == org_id,
        Expense.status != ExpenseStatus.WITHDRAWN,
        Expense.is_archived == False
    )

    # Apply status filter if provided
    if status and status != "all":
        try:
            status_enum = ExpenseStatus(status.lower())
            logger.info(
                f"[admin.get_all_expenses] Filtering by status enum: {status_enum}"
            )
            query = query.filter(Expense.status == status_enum)
        except ValueError:
            logger.warning(f"[admin.get_all_expenses] Invalid status value: {status}")
            pass  # Invalid status, ignore filter

    # Get all expenses ordered by creation date (newest first)
    expenses = query.order_by(Expense.created_at.desc()).all()
    logger.info(f"[admin.get_all_expenses] Found {len(expenses)} expenses")

    # Get user details for each expense and include approver info
    result = []
    for e in expenses:
        user = db.query(UserModel).filter(UserModel.id == e.user_id).first()
        approver = None
        if e.approved_by:
            approver = db.query(UserModel).filter(UserModel.id == e.approved_by).first()

        result.append(
            {
                "id": e.id,
                "amount": float(e.amount),
                "vendor": e.vendor,
                "category": e.category,
                "description": e.description,
                "status": e.status.value,
                "date": e.date.isoformat() if e.date else None,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "approved_at": e.approved_at.isoformat() if e.approved_at else None,
                "transaction_id": e.transaction_id,
                "rejection_reason": e.rejection_reason,
                "user_id": e.user_id,
                "user_email": user.email if user else "Unknown",
                "user_name": user.full_name if user else "Unknown",
                "approved_by_name": approver.full_name if approver else None,
                "approved_by_email": approver.email if approver else None,
            }
        )

    # Calculate stats
    total_amount = sum(e["amount"] for e in result)
    pending_count = sum(1 for e in result if e["status"] == "pending")
    approved_count = sum(1 for e in result if e["status"] == "approved")
    rejected_count = sum(1 for e in result if e["status"] == "rejected")

    return {
        "total_count": len(result),
        "total_amount": total_amount,
        "pending_count": pending_count,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "expenses": result,
    }


@router.delete("/expenses-pending/clear", response_model=dict)
async def clear_pending_expenses(
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Clear only pending expense requests (Admin only)"""
    import logging
    import os

    from ..models import Expense, ExpenseComment, ExpenseStatus, Receipt
    from ..tenant_context import verify_organization_access

    logger = logging.getLogger(__name__)
    logger.info(
        f"[admin.clear_pending_expenses] Admin {current_user.username} initiating pending expenses clear"
    )

    # SECURITY: Get and validate organization context
    org_id = request.headers.get("X-Organization-Id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required (X-Organization-Id header missing)"
        )

    # SECURITY: Verify user has access to this organization
    if not verify_organization_access(current_user.id, org_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this organization"
        )

    try:
        # Get all pending expenses for THIS organization only
        pending_expenses = (
            db.query(Expense)
            .filter(
                Expense.organization_id == org_id,
                Expense.status == ExpenseStatus.PENDING
            )
            .all()
        )
        expense_count = len(pending_expenses)

        if expense_count == 0:
            return {
                "success": True,
                "message": "No pending expenses to clear",
                "statistics": {
                    "expenses_deleted": 0,
                    "receipts_deleted": 0,
                    "comments_deleted": 0,
                    "receipt_files_deleted": 0,
                    "receipt_files_failed": 0,
                },
            }

        # Collect IDs for deletion
        pending_expense_ids = [e.id for e in pending_expenses]

        # Delete associated comments
        comment_count = (
            db.query(ExpenseComment)
            .filter(ExpenseComment.expense_id.in_(pending_expense_ids))
            .delete(synchronize_session=False)
        )

        # Delete associated receipts and their files
        receipts = (
            db.query(Receipt).filter(Receipt.expense_id.in_(pending_expense_ids)).all()
        )
        receipt_count = len(receipts)
        deleted_files = 0
        failed_files = 0

        for receipt in receipts:
            # Try to delete the physical file
            if receipt.file_path and os.path.exists(receipt.file_path):
                try:
                    os.remove(receipt.file_path)
                    deleted_files += 1
                except Exception as e:
                    logger.warning(
                        f"Failed to delete receipt file {receipt.file_path}: {e}"
                    )
                    failed_files += 1

        # Delete receipt records
        db.query(Receipt).filter(Receipt.expense_id.in_(pending_expense_ids)).delete(
            synchronize_session=False
        )

        # Delete pending expenses
        db.query(Expense).filter(Expense.id.in_(pending_expense_ids)).delete(
            synchronize_session=False
        )

        # Commit all changes
        db.commit()

        # Log audit event
        AuthService.log_audit(
            db=db,
            user_id=current_user.id,
            action="admin.clear_pending_expenses",
            resource_type="expense",
            details={
                "expenses_deleted": expense_count,
                "receipts_deleted": receipt_count,
                "comments_deleted": comment_count,
                "receipt_files_deleted": deleted_files,
                "receipt_files_failed": failed_files,
            },
            request=request,
        )

        logger.info(
            f"[admin.clear_pending_expenses] Successfully cleared {expense_count} pending expenses"
        )

        return {
            "success": True,
            "message": f"Cleared {expense_count} pending expense(s) successfully",
            "statistics": {
                "expenses_deleted": expense_count,
                "receipts_deleted": receipt_count,
                "comments_deleted": comment_count,
                "receipt_files_deleted": deleted_files,
                "receipt_files_failed": failed_files,
            },
        }

    except Exception as e:
        db.rollback()
        logger.error(
            f"[admin.clear_pending_expenses] Error clearing pending expenses: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear pending expenses: {str(e)}",
        )


@router.post("/expenses/archive-all", response_model=dict)
async def archive_all_expenses(
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Archive all non-pending expenses (Admin only)"""
    import logging

    from ..models import Expense, ExpenseStatus
    from ..tenant_context import verify_organization_access

    logger = logging.getLogger(__name__)
    logger.info(
        f"[admin.archive_all_expenses] Admin {current_user.username} initiating bulk archive"
    )

    # SECURITY: Get and validate organization context
    org_id = request.headers.get("X-Organization-Id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required (X-Organization-Id header missing)"
        )

    # SECURITY: Verify user has access to this organization
    if not verify_organization_access(current_user.id, org_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this organization"
        )

    try:
        # Get all non-pending, non-archived expenses for THIS organization only
        expenses_to_archive = (
            db.query(Expense)
            .filter(
                Expense.organization_id == org_id,
                Expense.status != ExpenseStatus.PENDING,
                Expense.is_archived == False
            )
            .all()
        )

        archive_count = len(expenses_to_archive)

        if archive_count == 0:
            return {
                "success": True,
                "message": "No expenses to archive",
                "statistics": {"expenses_archived": 0},
            }

        # Archive all expenses
        for expense in expenses_to_archive:
            expense.is_archived = True
            expense.archived_at = datetime.utcnow()
            expense.archived_by = current_user.id

        db.commit()

        # Log audit event
        AuthService.log_audit(
            db=db,
            user_id=current_user.id,
            action="admin.archive_all_expenses",
            resource_type="expense",
            details={"expenses_archived": archive_count},
            request=request,
        )

        logger.info(
            f"[admin.archive_all_expenses] Successfully archived {archive_count} expenses"
        )

        return {
            "success": True,
            "message": f"Archived {archive_count} expense(s) successfully",
            "statistics": {"expenses_archived": archive_count},
        }

    except Exception as e:
        db.rollback()
        logger.error(f"[admin.archive_all_expenses] Error archiving expenses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to archive expenses: {str(e)}",
        )


@router.get("/expenses/archived", response_model=dict)
async def get_archived_expenses(
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get all archived expenses (Admin only)"""
    from ..models import Expense
    from ..models import User as UserModel
    from ..tenant_context import verify_organization_access

    # SECURITY: Get and validate organization context
    org_id = request.headers.get("X-Organization-Id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required (X-Organization-Id header missing)"
        )

    # SECURITY: Verify user has access to this organization
    if not verify_organization_access(current_user.id, org_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this organization"
        )

    archived_expenses = (
        db.query(Expense)
        .filter(Expense.organization_id == org_id, Expense.is_archived == True)
        .order_by(Expense.archived_at.desc())
        .all()
    )

    result = []
    for e in archived_expenses:
        user = db.query(UserModel).filter(UserModel.id == e.user_id).first()
        archiver = (
            db.query(UserModel).filter(UserModel.id == e.archived_by).first()
            if e.archived_by
            else None
        )

        result.append(
            {
                "id": e.id,
                "amount": float(e.amount),
                "vendor": e.vendor,
                "category": e.category,
                "description": e.description,
                "status": e.status.value,
                "date": e.date.isoformat() if e.date else None,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "archived_at": e.archived_at.isoformat() if e.archived_at else None,
                "user_id": e.user_id,
                "user_email": user.email if user else "Unknown",
                "user_name": user.full_name if user else "Unknown",
                "archived_by_name": archiver.full_name if archiver else None,
                "archived_by_email": archiver.email if archiver else None,
            }
        )

    return {"total_count": len(result), "expenses": result}


@router.post("/expenses/{expense_id}/archive", response_model=dict)
async def archive_expense(
    expense_id: str,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Archive a single expense (Admin only)"""
    import logging

    from ..models import Expense, ExpenseStatus
    from ..tenant_context import verify_organization_access

    logger = logging.getLogger(__name__)

    # SECURITY: Get and validate organization context
    org_id = request.headers.get("X-Organization-Id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required (X-Organization-Id header missing)"
        )

    # SECURITY: Verify user has access to this organization
    if not verify_organization_access(current_user.id, org_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this organization"
        )

    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.organization_id == org_id
    ).first()
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found"
        )

    if expense.status == ExpenseStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot archive pending expenses",
        )

    if expense.is_archived:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expense is already archived",
        )

    expense.is_archived = True
    expense.archived_at = datetime.utcnow()
    expense.archived_by = current_user.id
    db.commit()

    # Log audit event
    AuthService.log_audit(
        db=db,
        user_id=current_user.id,
        action="admin.archive_expense",
        resource_type="expense",
        resource_id=expense_id,
        details={"expense_id": expense_id},
        request=request,
    )

    logger.info(f"[admin.archive_expense] Archived expense {expense_id}")

    return {
        "success": True,
        "message": "Expense archived successfully",
        "expense_id": expense_id,
    }


@router.post("/expenses/{expense_id}/unarchive", response_model=dict)
async def unarchive_expense(
    expense_id: str,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Unarchive a single expense (Admin only)"""
    import logging

    from ..models import Expense
    from ..tenant_context import verify_organization_access

    logger = logging.getLogger(__name__)

    # SECURITY: Get and validate organization context
    org_id = request.headers.get("X-Organization-Id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required (X-Organization-Id header missing)"
        )

    # SECURITY: Verify user has access to this organization
    if not verify_organization_access(current_user.id, org_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this organization"
        )

    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.organization_id == org_id
    ).first()
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found"
        )

    if not expense.is_archived:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Expense is not archived"
        )

    expense.is_archived = False
    expense.archived_at = None
    expense.archived_by = None
    db.commit()

    # Log audit event
    AuthService.log_audit(
        db=db,
        user_id=current_user.id,
        action="admin.unarchive_expense",
        resource_type="expense",
        resource_id=expense_id,
        details={"expense_id": expense_id},
        request=request,
    )

    logger.info(f"[admin.unarchive_expense] Unarchived expense {expense_id}")

    return {
        "success": True,
        "message": "Expense unarchived successfully",
        "expense_id": expense_id,
    }


@router.post("/expenses/unarchive-all", response_model=dict)
async def unarchive_all_expenses(
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Unarchive all archived expenses (Admin only)"""
    import logging

    from ..models import Expense
    from ..tenant_context import verify_organization_access

    logger = logging.getLogger(__name__)
    logger.info(
        f"[admin.unarchive_all_expenses] Admin {current_user.username} initiating bulk unarchive"
    )

    # SECURITY: Get and validate organization context
    org_id = request.headers.get("X-Organization-Id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required (X-Organization-Id header missing)"
        )

    # SECURITY: Verify user has access to this organization
    if not verify_organization_access(current_user.id, org_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this organization"
        )

    try:
        # Get all archived expenses for THIS organization only
        archived_expenses = db.query(Expense).filter(
            Expense.organization_id == org_id,
            Expense.is_archived == True
        ).all()

        unarchive_count = len(archived_expenses)

        if unarchive_count == 0:
            return {
                "success": True,
                "message": "No archived expenses to restore",
                "statistics": {"expenses_unarchived": 0},
            }

        # Unarchive all expenses
        for expense in archived_expenses:
            expense.is_archived = False
            expense.archived_at = None
            expense.archived_by = None

        db.commit()

        # Log audit event
        AuthService.log_audit(
            db=db,
            user_id=current_user.id,
            action="admin.unarchive_all_expenses",
            resource_type="expense",
            details={"expenses_unarchived": unarchive_count},
            request=request,
        )

        logger.info(
            f"[admin.unarchive_all_expenses] Successfully unarchived {unarchive_count} expenses"
        )

        return {
            "success": True,
            "message": f"Restored {unarchive_count} expense(s) to active successfully",
            "statistics": {"expenses_unarchived": unarchive_count},
        }

    except Exception as e:
        db.rollback()
        logger.error(f"[admin.unarchive_all_expenses] Error unarchiving expenses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unarchive expenses: {str(e)}",
        )


@router.delete("/expenses/clear", response_model=dict)
async def clear_expense_history(
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """DEPRECATED: Use archive instead. Clear all expense records and their associated data (Admin only)"""
    import logging
    import os

    from ..models import Expense, ExpenseComment, Receipt

    logger = logging.getLogger(__name__)
    logger.warning(
        f"[admin.clear_expense_history] DEPRECATED endpoint called by {current_user.username}"
    )

    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="This endpoint is deprecated. Use the archive endpoints instead: POST /api/v1/admin/expenses/archive-all",
    )


# ============================================================================
# USER MANAGEMENT ENDPOINTS
# ============================================================================


@router.post("/users/create", response_model=dict)
async def create_user(
    request: Request,
    user_data: CreateUserRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create a new user (Admin only)"""
    import uuid

    import bcrypt

    # Check if email already exists
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Check if username already exists
    existing_username = (
        db.query(User).filter(User.username == user_data.username).first()
    )
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken"
        )

    # Hash the password
    hashed_password = bcrypt.hashpw(
        user_data.password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    # Create new user
    new_user = User(
        id=str(uuid.uuid4()),
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        role=user_data.role,
        department_id=user_data.department_id,
        is_active=True,
        is_verified=True,  # Admin-created users are pre-verified
        created_at=datetime.utcnow(),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Log audit event
    AuthService.log_audit(
        db=db,
        user_id=current_user.id,
        action="admin.create_user",
        resource_type="user",
        resource_id=new_user.id,
        details={
            "created_user": new_user.username,
            "role": user_data.role.value,
            "department_id": user_data.department_id,
        },
        request=request,
    )

    return {
        "success": True,
        "message": "User created successfully",
        "user": {
            "id": new_user.id,
            "email": new_user.email,
            "username": new_user.username,
            "full_name": new_user.full_name,
            "role": new_user.role.value,
            "department_id": new_user.department_id,
            "is_active": new_user.is_active,
        },
    }


@router.get("/users/{user_id}", response_model=dict)
async def get_user_details(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get detailed user information (Admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role.value,
        "department_id": user.department_id,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "totp_enabled": user.totp_enabled,
        "failed_login_attempts": user.failed_login_attempts,
        "locked_until": user.locked_until.isoformat() if user.locked_until else None,
    }


@router.patch("/users/{user_id}/department", response_model=dict)
async def update_user_department(
    user_id: str,
    request: Request,
    department_data: UpdateUserDepartmentRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update user's department (Admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    old_department = user.department_id
    user.department_id = department_data.department_id
    user.updated_at = datetime.utcnow()
    db.commit()

    # Log audit event
    AuthService.log_audit(
        db=db,
        user_id=current_user.id,
        action="admin.update_user_department",
        resource_type="user",
        resource_id=user.id,
        details={
            "user": user.username,
            "old_department": old_department,
            "new_department": department_data.department_id,
        },
        request=request,
    )

    return {
        "success": True,
        "message": "Department updated successfully",
        "user_id": user_id,
        "department_id": user.department_id,
    }


@router.patch("/users/{user_id}/email", response_model=dict)
async def update_user_email(
    user_id: str,
    request: Request,
    email_data: UpdateUserEmailRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update user's email (Admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Check if email is already taken by another user
    existing_user = (
        db.query(User)
        .filter(User.email == email_data.email, User.id != user_id)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already in use by another user",
        )

    # Validate email format
    import re

    email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_regex, email_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email format"
        )

    old_email = user.email
    user.email = email_data.email
    user.updated_at = datetime.utcnow()
    db.commit()

    # Log audit event
    AuthService.log_audit(
        db=db,
        user_id=current_user.id,
        action="admin.update_user_email",
        resource_type="user",
        resource_id=user.id,
        details={
            "user": user.username,
            "old_email": old_email,
            "new_email": email_data.email,
        },
        request=request,
    )

    return {
        "success": True,
        "message": "Email updated successfully",
        "user_id": user_id,
        "email": user.email,
    }


@router.patch("/users/{user_id}/profile", response_model=dict)
async def update_user_profile(
    user_id: str,
    request: Request,
    profile_data: UpdateUserProfileRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update user's profile information (username, full_name, email) (Admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    changes = {}

    # Update username if provided
    if profile_data.username is not None:
        # Check if username is already taken by another user
        existing_user = (
            db.query(User)
            .filter(User.username == profile_data.username, User.id != user_id)
            .first()
        )

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken by another user",
            )

        changes["username"] = {"old": user.username, "new": profile_data.username}
        user.username = profile_data.username

    # Update full_name if provided
    if profile_data.full_name is not None:
        changes["full_name"] = {"old": user.full_name, "new": profile_data.full_name}
        user.full_name = profile_data.full_name

    # Update email if provided
    if profile_data.email is not None:
        # Check if email is already taken by another user
        existing_user = (
            db.query(User)
            .filter(User.email == profile_data.email, User.id != user_id)
            .first()
        )

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use by another user",
            )

        # Validate email format
        import re

        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_regex, profile_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email format"
            )

        changes["email"] = {"old": user.email, "new": profile_data.email}
        user.email = profile_data.email

    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid fields provided for update",
        )

    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    # Log audit event
    AuthService.log_audit(
        db=db,
        user_id=current_user.id,
        action="admin.update_user_profile",
        resource_type="user",
        resource_id=user.id,
        details={"user": user.username, "changes": changes},
        request=request,
    )

    return {
        "success": True,
        "message": "User profile updated successfully",
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role.value,
            "is_active": user.is_active,
        },
        "changes": changes,
    }


@router.post("/users/{user_id}/activate", response_model=dict)
async def activate_user(
    user_id: str,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Reactivate a suspended user account (Admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Check if user is already active
    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is already active",
        )

    user.is_active = True
    user.updated_at = datetime.utcnow()
    db.commit()

    # Log audit event
    AuthService.log_audit(
        db=db,
        user_id=current_user.id,
        action="admin.activate_user",
        resource_type="user",
        resource_id=user.id,
        details={"activated_user": user.username},
        request=request,
    )

    return {
        "success": True,
        "message": f"User '{user.username}' activated successfully",
        "user_id": user_id,
    }


@router.delete("/users/{user_id}", response_model=dict)
async def delete_user(
    user_id: str,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete a user account (Admin only)

    WARNING: This will delete all user data including:
    - All expenses created by this user
    - All receipts uploaded by this user
    - All comments made by this user
    - All audit logs for this user
    - All sessions and tokens
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Prevent deleting yourself
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    username = user.username

    try:
        # First, log the deletion (before deleting the user)
        AuthService.log_audit(
            db=db,
            user_id=current_user.id,
            action="admin.delete_user",
            resource_type="user",
            resource_id=user_id,
            details={"deleted_user": username},
            request=request,
        )

        # Delete related records that don't have cascade delete
        # Note: The following have cascade delete and will be handled automatically:
        # - refresh_tokens, password_reset_tokens, sessions (via cascade)

        # Delete records where user is referenced but without cascade delete
        from ..models import (
            AuditLog,
            CartMandate,
            Expense,
            ExpenseComment,
            IntentMandate,
            Invoice,
            OrganizationInvitation,
            OrganizationMember,
            PaymentMandate,
            Receipt,
            Subscription,
            UsageRecord,
        )

        # Step 1: Delete AP2 mandates (in correct order due to foreign keys)
        # PaymentMandate → CartMandate → IntentMandate
        # Note: These cascade from IntentMandate, so just delete IntentMandate
        db.query(IntentMandate).filter(IntentMandate.user_id == user_id).delete(
            synchronize_session=False
        )

        # Step 2: Update expenses where user is approver/archiver (preserve expense history)
        db.query(Expense).filter(Expense.approved_by == user_id).update(
            {"approved_by": None}, synchronize_session=False
        )
        db.query(Expense).filter(Expense.archived_by == user_id).update(
            {"archived_by": None}, synchronize_session=False
        )

        # Step 3: Delete comments (must be before expenses due to CASCADE)
        db.query(ExpenseComment).filter(ExpenseComment.user_id == user_id).delete(
            synchronize_session=False
        )

        # Step 4: Delete expenses created by user (this will CASCADE delete receipts and comments)
        # Note: Receipts have CASCADE delete from expenses, so they'll be deleted automatically
        db.query(Expense).filter(Expense.user_id == user_id).delete(
            synchronize_session=False
        )

        # Step 6: Delete billing-related records
        db.query(Invoice).filter(Invoice.user_id == user_id).delete(
            synchronize_session=False
        )
        db.query(UsageRecord).filter(UsageRecord.user_id == user_id).delete(
            synchronize_session=False
        )
        db.query(Subscription).filter(Subscription.user_id == user_id).delete(
            synchronize_session=False
        )

        # Step 7: Delete organization-related records
        db.query(OrganizationInvitation).filter(
            OrganizationInvitation.invited_by == user_id
        ).delete(synchronize_session=False)
        db.query(OrganizationMember).filter(
            OrganizationMember.user_id == user_id
        ).delete(synchronize_session=False)

        # Delete audit logs (optional - you may want to keep these for compliance)
        # Uncomment if you want to delete audit logs:
        # db.query(AuditLog).filter(AuditLog.user_id == user_id).delete()

        # Finally, delete the user
        db.delete(user)
        db.commit()

    except Exception as e:
        db.rollback()
        import traceback

        error_trace = traceback.format_exc()
        print(f"Error deleting user {user_id}: {str(e)}")
        print(f"Traceback: {error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}",
        )

    return {
        "success": True,
        "message": f"User '{username}' and all associated data deleted successfully",
        "user_id": user_id,
    }


@router.get("/users/{user_id}/permissions", response_model=dict)
async def get_user_permissions(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get all permissions for a specific user (Admin only)"""
    from ..permissions import get_user_permissions as get_permissions

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    permissions = get_permissions(user.role)

    return {
        "user_id": user_id,
        "username": user.username,
        "role": user.role.value,
        "permissions": [p.value for p in permissions],
    }


@router.get("/permissions/all", response_model=dict)
async def get_all_permissions(
    current_user: User = Depends(require_admin), db: Session = Depends(get_db)
):
    """Get all available permissions in the system (Admin only)"""
    from ..permissions import ROLE_PERMISSIONS, Permission

    # Group permissions by category
    permissions_by_category = {}
    for perm in Permission:
        category = perm.value.split(":")[0]
        if category not in permissions_by_category:
            permissions_by_category[category] = []
        permissions_by_category[category].append(
            {
                "name": perm.name,
                "value": perm.value,
                "description": perm.name.replace("_", " ").title(),
            }
        )

    # Get role-permission mappings
    role_mappings = {}
    for role, perms in ROLE_PERMISSIONS.items():
        role_mappings[role.value] = [p.value for p in perms]

    return {"categories": permissions_by_category, "role_mappings": role_mappings}
