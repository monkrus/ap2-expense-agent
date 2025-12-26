"""
Notification API routes
Handles notification creation, retrieval, and management
"""

from datetime import datetime, timedelta
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..auth import get_current_active_user
from ..database import get_db
from ..models import User, Notification, NotificationType

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
    notifications = (
        query.order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )

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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
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
    unread_notifications = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .filter(Notification.is_read == False)
        .all()
    )

    count = 0
    for notification in unread_notifications:
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        count += 1

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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )

    db.delete(notification)
    db.commit()

    return {"success": True, "message": "Notification deleted"}
