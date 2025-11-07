"""
API endpoints for managing recurring expenses and notifications.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import uuid

from src.database import get_db
from src.auth import get_current_user
from src.models import (
    User,
    RecurringExpenseTemplate,
    ScheduledExpense,
    ExpenseNotification,
    ExpenseCategory,
    RecurringFrequency,
    Organization,
    OrganizationMember
)

router = APIRouter(prefix="/api/recurring-expenses", tags=["recurring-expenses"])
notification_router = APIRouter(prefix="/api/notifications", tags=["notifications"])


# ============================================================================
# Pydantic Models
# ============================================================================

class RecurringExpenseCreate(BaseModel):
    vendor: str = Field(..., min_length=1, max_length=255)
    amount: float = Field(..., gt=0)
    category: ExpenseCategory
    description: str = Field(..., min_length=1)
    frequency: RecurringFrequency
    start_date: datetime
    end_date: Optional[datetime] = None
    intent_mandate_id: Optional[str] = None
    auto_submit: bool = True


class RecurringExpenseUpdate(BaseModel):
    vendor: Optional[str] = Field(None, min_length=1, max_length=255)
    amount: Optional[float] = Field(None, gt=0)
    category: Optional[ExpenseCategory] = None
    description: Optional[str] = Field(None, min_length=1)
    frequency: Optional[RecurringFrequency] = None
    end_date: Optional[datetime] = None
    intent_mandate_id: Optional[str] = None
    auto_submit: Optional[bool] = None
    is_active: Optional[bool] = None
    is_paused: Optional[bool] = None


class RecurringExpenseResponse(BaseModel):
    id: str
    vendor: str
    amount: float
    category: str
    description: str
    frequency: str
    start_date: datetime
    end_date: Optional[datetime]
    next_run_date: datetime
    intent_mandate_id: Optional[str]
    auto_submit: bool
    is_active: bool
    is_paused: bool
    total_submitted: int
    last_submitted_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationResponse(BaseModel):
    id: str
    notification_type: str
    title: str
    message: str
    expense_id: Optional[str]
    template_id: Optional[str]
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Helper Functions
# ============================================================================

def get_user_organization(db: Session, user_id: str) -> Optional[str]:
    """Get the organization ID for a user"""
    stmt = select(OrganizationMember).where(
        and_(
            OrganizationMember.user_id == user_id,
            OrganizationMember.is_active == True
        )
    ).limit(1)
    result = db.execute(stmt)
    member = result.scalar_one_or_none()
    return member.organization_id if member else None


def calculate_next_run_date(start_date: datetime, frequency: RecurringFrequency) -> datetime:
    """Calculate the next run date based on frequency"""
    if frequency == RecurringFrequency.WEEKLY:
        return start_date + timedelta(days=7)
    elif frequency == RecurringFrequency.BIWEEKLY:
        return start_date + timedelta(days=14)
    elif frequency == RecurringFrequency.MONTHLY:
        next_month = start_date.month + 1
        next_year = start_date.year
        if next_month > 12:
            next_month = 1
            next_year += 1
        return start_date.replace(year=next_year, month=next_month)
    elif frequency == RecurringFrequency.QUARTERLY:
        next_month = start_date.month + 3
        next_year = start_date.year
        while next_month > 12:
            next_month -= 12
            next_year += 1
        return start_date.replace(year=next_year, month=next_month)
    elif frequency == RecurringFrequency.YEARLY:
        return start_date.replace(year=start_date.year + 1)
    else:
        return start_date + timedelta(days=30)


# ============================================================================
# Recurring Expense Endpoints
# ============================================================================

@router.post("", response_model=RecurringExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_recurring_expense(
    data: RecurringExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new recurring expense template"""

    claude/start-app-run-tests-011CUsFhjmtARBb1wf79NhDT
    # Get user's organization
    org_id = get_user_organization(db, current_user.id)
    if not org_id:

    # Get user's organization (optional for admins)
    org_id = get_user_organization(db, current_user.id)
    if not org_id and current_user.role != 'admin':
    main
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a member of any organization"
        )

    # Calculate next run date
    next_run = calculate_next_run_date(data.start_date, data.frequency)

    # Create template
    template = RecurringExpenseTemplate(
        id=f"recurring_{uuid.uuid4().hex[:16]}",
        organization_id=org_id,
        user_id=current_user.id,
        vendor=data.vendor,
        amount=data.amount,
        category=data.category,
        description=data.description,
        frequency=data.frequency,
        start_date=data.start_date,
        end_date=data.end_date,
        next_run_date=next_run,
        intent_mandate_id=data.intent_mandate_id,
        auto_submit=data.auto_submit
    )

    db.add(template)
    db.commit()
    db.refresh(template)

    return template


@router.get("", response_model=List[RecurringExpenseResponse])
def list_recurring_expenses(
    active_only: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all recurring expense templates for the current user"""

    query = select(RecurringExpenseTemplate).where(
        RecurringExpenseTemplate.user_id == current_user.id
    )

    if active_only:
        query = query.where(RecurringExpenseTemplate.is_active == True)

    query = query.order_by(RecurringExpenseTemplate.next_run_date)

    result = db.execute(query)
    templates = result.scalars().all()

    return templates


@router.get("/{template_id}", response_model=RecurringExpenseResponse)
def get_recurring_expense(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific recurring expense template"""

    stmt = select(RecurringExpenseTemplate).where(
        and_(
            RecurringExpenseTemplate.id == template_id,
            RecurringExpenseTemplate.user_id == current_user.id
        )
    )
    result = db.execute(stmt)
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurring expense template not found"
        )

    return template


@router.patch("/{template_id}", response_model=RecurringExpenseResponse)
def update_recurring_expense(
    template_id: str,
    data: RecurringExpenseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a recurring expense template"""

    stmt = select(RecurringExpenseTemplate).where(
        and_(
            RecurringExpenseTemplate.id == template_id,
            RecurringExpenseTemplate.user_id == current_user.id
        )
    )
    result = db.execute(stmt)
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurring expense template not found"
        )

    # Update fields
    if data.vendor is not None:
        template.vendor = data.vendor
    if data.amount is not None:
        template.amount = data.amount
    if data.category is not None:
        template.category = data.category
    if data.description is not None:
        template.description = data.description
    if data.frequency is not None:
        template.frequency = data.frequency
    if data.end_date is not None:
        template.end_date = data.end_date
    if data.intent_mandate_id is not None:
        template.intent_mandate_id = data.intent_mandate_id
    if data.auto_submit is not None:
        template.auto_submit = data.auto_submit
    if data.is_active is not None:
        template.is_active = data.is_active
    if data.is_paused is not None:
        template.is_paused = data.is_paused

    db.commit()
    db.refresh(template)

    return template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recurring_expense(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a recurring expense template"""

    stmt = select(RecurringExpenseTemplate).where(
        and_(
            RecurringExpenseTemplate.id == template_id,
            RecurringExpenseTemplate.user_id == current_user.id
        )
    )
    result = db.execute(stmt)
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurring expense template not found"
        )

    db.delete(template)
    db.commit()


@router.post("/{template_id}/pause", response_model=RecurringExpenseResponse)
def pause_recurring_expense(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Pause a recurring expense template"""

    stmt = select(RecurringExpenseTemplate).where(
        and_(
            RecurringExpenseTemplate.id == template_id,
            RecurringExpenseTemplate.user_id == current_user.id
        )
    )
    result = db.execute(stmt)
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurring expense template not found"
        )

    template.is_paused = True
    db.commit()
    db.refresh(template)

    return template


@router.post("/{template_id}/resume", response_model=RecurringExpenseResponse)
def resume_recurring_expense(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Resume a paused recurring expense template"""

    stmt = select(RecurringExpenseTemplate).where(
        and_(
            RecurringExpenseTemplate.id == template_id,
            RecurringExpenseTemplate.user_id == current_user.id
        )
    )
    result = db.execute(stmt)
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurring expense template not found"
        )

    template.is_paused = False
    db.commit()
    db.refresh(template)

    return template


# ============================================================================
# Notification Endpoints
# ============================================================================

@notification_router.get("", response_model=List[NotificationResponse])
def get_notifications(
    unread_only: bool = False,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get notifications for the current user"""

    query = select(ExpenseNotification).where(
        ExpenseNotification.user_id == current_user.id
    )

    if unread_only:
        query = query.where(ExpenseNotification.is_read == False)

    query = query.order_by(ExpenseNotification.created_at.desc()).limit(limit)

    result = db.execute(query)
    notifications = result.scalars().all()

    return notifications


@notification_router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_as_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a notification as read"""

    stmt = select(ExpenseNotification).where(
        and_(
            ExpenseNotification.id == notification_id,
            ExpenseNotification.user_id == current_user.id
        )
    )
    result = db.execute(stmt)
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )

    notification.is_read = True
    notification.read_at = datetime.utcnow()
    db.commit()
    db.refresh(notification)

    return notification


@notification_router.post("/mark-all-read")
def mark_all_notifications_as_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark all notifications as read for the current user"""

    stmt = select(ExpenseNotification).where(
        and_(
            ExpenseNotification.user_id == current_user.id,
            ExpenseNotification.is_read == False
        )
    )
    result = db.execute(stmt)
    notifications = result.scalars().all()

    count = 0
    for notification in notifications:
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        count += 1

    db.commit()

    return {"marked_as_read": count}


@notification_router.get("/unread-count")
def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the count of unread notifications"""

    stmt = select(func.count()).select_from(ExpenseNotification).where(
        and_(
            ExpenseNotification.user_id == current_user.id,
            ExpenseNotification.is_read == False
        )
    )
    result = db.execute(stmt)
    count = result.scalar_one()

    return {"unread_count": count}
