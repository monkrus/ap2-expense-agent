"""
Notification API routes
Handles notification creation, retrieval, and management
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from ..auth import get_current_active_user
from ..database import get_db
from ..models import (
    Notification,
    NotificationType,
    OrganizationMember,
    OrganizationRole,
    User,
)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
async def get_notifications(
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get notifications for the current user
    """
    query = db.query(Notification).filter(Notification.user_id == current_user.id)

    if unread_only:
        query = query.filter(Notification.is_read == False)

    # Order by most recent first
    notifications = query.order_by(Notification.created_at.desc()).limit(limit).all()

    # Get unread count
    unread_count = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .filter(Notification.is_read == False)
        .count()
    )

    return {
        "notifications": [n.to_dict() for n in notifications],
        "total_count": len(notifications),
        "unread_count": unread_count,
    }


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get count of unread notifications for the current user
    """
    unread_count = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .filter(Notification.is_read == False)
        .count()
    )

    return {"unread_count": unread_count}


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Mark a notification as read
    """
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id)
        .filter(Notification.user_id == current_user.id)
        .first()
    )

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )

    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        db.commit()

    return {"success": True, "message": "Notification marked as read"}


@router.post("/mark-all-read")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Mark all notifications as read for the current user
    """
    count = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .filter(Notification.is_read == False)
        .update({"is_read": True, "read_at": datetime.utcnow()})
    )

    db.commit()

    return {"success": True, "message": f"Marked {count} notifications as read"}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Delete a notification
    """
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id)
        .filter(Notification.user_id == current_user.id)
        .first()
    )

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )

    db.delete(notification)
    db.commit()

    return {"success": True, "message": "Notification deleted"}


@router.post("/batch-expense")
async def send_batch_expense_notification(
    request: Request,
    data: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Send a single summary notification for a batch expense upload.
    """
    count = data.get("count", 0)
    total_amount = data.get("total_amount", 0)
    if count <= 0:
        return {"success": True, "message": "No notification needed"}

    org_id = request.headers.get("X-Organization-Id")
    if not org_id:
        # Try to find user's org
        member = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.is_active == True,
            )
            .first()
        )
        org_id = member.organization_id if member else None

    if not org_id:
        return {"success": False, "message": "No organization context"}

    admin_members = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.role.in_(
                [OrganizationRole.OWNER.value, OrganizationRole.ADMIN.value]
            ),
            OrganizationMember.is_active == True,
        )
        .all()
    )

    display_name = current_user.full_name or current_user.username or current_user.email

    for member in admin_members:
        if member.user_id == current_user.id:
            continue
        notification = Notification(
            id=str(uuid.uuid4()),
            user_id=member.user_id,
            organization_id=org_id,
            notification_type=NotificationType.EXPENSE_SUBMITTED,
            title="Batch Expense Upload",
            message=f"{display_name} submitted {count} expenses (${total_amount:,.2f} total) via batch upload - awaiting approval",
            is_read=False,
            created_at=datetime.utcnow(),
        )
        db.add(notification)

    db.commit()

    return {"success": True, "message": f"Batch notification sent for {count} expenses"}
