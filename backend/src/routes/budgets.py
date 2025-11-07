"""
API endpoints for budget management and alerts.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from decimal import Decimal
import uuid

from src.database import get_db
from src.auth import get_current_user
from src.models import (
    User,
    Budget,
    BudgetAlert,
    BudgetPeriod,
    ExpenseCategory,
    Expense,
    OrganizationMember,
    UserRole
)

router = APIRouter(prefix="/api/budgets", tags=["budgets"])


# ============================================================================
# Pydantic Models
# ============================================================================

class BudgetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    amount: float = Field(..., gt=0)
    period: BudgetPeriod
    category: Optional[ExpenseCategory] = None
    user_id: Optional[str] = None  # Optional: for user-specific budgets
    warning_threshold: int = Field(default=75, ge=0, le=100)
    critical_threshold: int = Field(default=90, ge=0, le=100)
    start_date: datetime
    end_date: Optional[datetime] = None


class BudgetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    amount: Optional[float] = Field(None, gt=0)
    period: Optional[BudgetPeriod] = None
    category: Optional[ExpenseCategory] = None
    warning_threshold: Optional[int] = Field(None, ge=0, le=100)
    critical_threshold: Optional[int] = Field(None, ge=0, le=100)
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None


class BudgetResponse(BaseModel):
    id: str
    organization_id: str
    user_id: Optional[str]
    name: str
    description: Optional[str]
    amount: float
    period: str
    category: Optional[str]
    warning_threshold: int
    critical_threshold: int
    is_active: bool
    start_date: datetime
    end_date: Optional[datetime]
    current_spending: float
    percentage_used: float
    remaining: float
    status: str  # on_track, warning, critical, exceeded
    created_at: datetime

    class Config:
        from_attributes = True


class BudgetAlertResponse(BaseModel):
    id: str
    budget_id: str
    alert_type: str
    threshold_percentage: int
    actual_amount: float
    budget_amount: float
    message: str
    is_acknowledged: bool
    acknowledged_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Helper Functions
# ============================================================================

async def get_user_organization(db: AsyncSession, user_id: str) -> Optional[str]:
    """Get the organization ID for a user"""
    stmt = select(OrganizationMember).where(
        and_(
            OrganizationMember.user_id == user_id,
            OrganizationMember.is_active == True
        )
    ).limit(1)
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()
    return member.organization_id if member else None


async def calculate_budget_spending(
    db: AsyncSession,
    budget: Budget,
    start_date: datetime,
    end_date: datetime
) -> Decimal:
    """Calculate total spending for a budget period"""
    query = select(func.sum(Expense.amount)).where(
        and_(
            Expense.organization_id == budget.organization_id,
            Expense.created_at >= start_date,
            Expense.created_at <= end_date,
            Expense.status.in_(['pending', 'approved'])  # Include pending and approved expenses
        )
    )

    # Filter by category if specified
    if budget.category:
        query = query.where(Expense.category == budget.category)

    # Filter by user if specified
    if budget.user_id:
        query = query.where(Expense.user_id == budget.user_id)

    result = await db.execute(query)
    total = result.scalar_one()
    return Decimal(total or 0)


def get_budget_period_dates(budget: Budget) -> tuple[datetime, datetime]:
    """Get the start and end dates for the current budget period"""
    now = datetime.utcnow()

    if budget.period == BudgetPeriod.MONTHLY:
        start = datetime(now.year, now.month, 1)
        if now.month == 12:
            end = datetime(now.year + 1, 1, 1) - timedelta(seconds=1)
        else:
            end = datetime(now.year, now.month + 1, 1) - timedelta(seconds=1)

    elif budget.period == BudgetPeriod.QUARTERLY:
        quarter = (now.month - 1) // 3 + 1
        start_month = (quarter - 1) * 3 + 1
        start = datetime(now.year, start_month, 1)
        end_month = start_month + 3
        if end_month > 12:
            end = datetime(now.year + 1, end_month - 12, 1) - timedelta(seconds=1)
        else:
            end = datetime(now.year, end_month, 1) - timedelta(seconds=1)

    elif budget.period == BudgetPeriod.YEARLY:
        start = datetime(now.year, 1, 1)
        end = datetime(now.year, 12, 31, 23, 59, 59)

    else:
        start = budget.start_date
        end = budget.end_date or now

    # Respect budget start/end dates
    start = max(start, budget.start_date)
    if budget.end_date:
        end = min(end, budget.end_date)

    return start, end


def calculate_budget_status(percentage_used: float, warning: int, critical: int) -> str:
    """Determine budget status based on percentage used"""
    if percentage_used >= 100:
        return "exceeded"
    elif percentage_used >= critical:
        return "critical"
    elif percentage_used >= warning:
        return "warning"
    else:
        return "on_track"


# ============================================================================
# Budget Endpoints
# ============================================================================

@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    data: BudgetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new budget"""

    # Get user's organization
    org_id = await get_user_organization(db, current_user.id)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a member of any organization"
        )

    # Only admins and managers can create budgets
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can create budgets"
        )

    # Validate thresholds
    if data.critical_threshold <= data.warning_threshold:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Critical threshold must be greater than warning threshold"
        )

    # Create budget
    budget = Budget(
        id=f"budget_{uuid.uuid4().hex[:16]}",
        organization_id=org_id,
        user_id=data.user_id,
        name=data.name,
        description=data.description,
        amount=Decimal(str(data.amount)),
        period=data.period,
        category=data.category,
        warning_threshold=data.warning_threshold,
        critical_threshold=data.critical_threshold,
        start_date=data.start_date,
        end_date=data.end_date
    )

    db.add(budget)
    await db.commit()
    await db.refresh(budget)

    # Calculate current spending
    start_date, end_date = get_budget_period_dates(budget)
    current_spending = await calculate_budget_spending(db, budget, start_date, end_date)
    percentage_used = float((current_spending / budget.amount) * 100) if budget.amount > 0 else 0
    remaining = float(budget.amount - current_spending)
    status_str = calculate_budget_status(percentage_used, budget.warning_threshold, budget.critical_threshold)

    return BudgetResponse(
        id=budget.id,
        organization_id=budget.organization_id,
        user_id=budget.user_id,
        name=budget.name,
        description=budget.description,
        amount=float(budget.amount),
        period=budget.period.value,
        category=budget.category.value if budget.category else None,
        warning_threshold=budget.warning_threshold,
        critical_threshold=budget.critical_threshold,
        is_active=budget.is_active,
        start_date=budget.start_date,
        end_date=budget.end_date,
        current_spending=float(current_spending),
        percentage_used=round(percentage_used, 2),
        remaining=remaining,
        status=status_str,
        created_at=budget.created_at
    )


@router.get("", response_model=List[BudgetResponse])
async def list_budgets(
    active_only: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all budgets for the organization"""

    # Get user's organization
    org_id = await get_user_organization(db, current_user.id)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a member of any organization"
        )

    query = select(Budget).where(Budget.organization_id == org_id)

    if active_only:
        query = query.where(Budget.is_active == True)

    # Non-admins can only see organization-wide budgets or their own
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        query = query.where(
            (Budget.user_id == None) | (Budget.user_id == current_user.id)
        )

    query = query.order_by(Budget.created_at.desc())

    result = await db.execute(query)
    budgets = result.scalars().all()

    # Calculate spending for each budget
    budget_responses = []
    for budget in budgets:
        start_date, end_date = get_budget_period_dates(budget)
        current_spending = await calculate_budget_spending(db, budget, start_date, end_date)
        percentage_used = float((current_spending / budget.amount) * 100) if budget.amount > 0 else 0
        remaining = float(budget.amount - current_spending)
        status_str = calculate_budget_status(percentage_used, budget.warning_threshold, budget.critical_threshold)

        budget_responses.append(BudgetResponse(
            id=budget.id,
            organization_id=budget.organization_id,
            user_id=budget.user_id,
            name=budget.name,
            description=budget.description,
            amount=float(budget.amount),
            period=budget.period.value,
            category=budget.category.value if budget.category else None,
            warning_threshold=budget.warning_threshold,
            critical_threshold=budget.critical_threshold,
            is_active=budget.is_active,
            start_date=budget.start_date,
            end_date=budget.end_date,
            current_spending=float(current_spending),
            percentage_used=round(percentage_used, 2),
            remaining=remaining,
            status=status_str,
            created_at=budget.created_at
        ))

    return budget_responses


@router.get("/{budget_id}", response_model=BudgetResponse)
async def get_budget(
    budget_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific budget"""

    org_id = await get_user_organization(db, current_user.id)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a member of any organization"
        )

    stmt = select(Budget).where(
        and_(
            Budget.id == budget_id,
            Budget.organization_id == org_id
        )
    )
    result = await db.execute(stmt)
    budget = result.scalar_one_or_none()

    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found"
        )

    # Check access
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        if budget.user_id and budget.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this budget"
            )

    # Calculate current spending
    start_date, end_date = get_budget_period_dates(budget)
    current_spending = await calculate_budget_spending(db, budget, start_date, end_date)
    percentage_used = float((current_spending / budget.amount) * 100) if budget.amount > 0 else 0
    remaining = float(budget.amount - current_spending)
    status_str = calculate_budget_status(percentage_used, budget.warning_threshold, budget.critical_threshold)

    return BudgetResponse(
        id=budget.id,
        organization_id=budget.organization_id,
        user_id=budget.user_id,
        name=budget.name,
        description=budget.description,
        amount=float(budget.amount),
        period=budget.period.value,
        category=budget.category.value if budget.category else None,
        warning_threshold=budget.warning_threshold,
        critical_threshold=budget.critical_threshold,
        is_active=budget.is_active,
        start_date=budget.start_date,
        end_date=budget.end_date,
        current_spending=float(current_spending),
        percentage_used=round(percentage_used, 2),
        remaining=remaining,
        status=status_str,
        created_at=budget.created_at
    )


@router.patch("/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: str,
    data: BudgetUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a budget"""

    # Only admins and managers can update budgets
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can update budgets"
        )

    org_id = await get_user_organization(db, current_user.id)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a member of any organization"
        )

    stmt = select(Budget).where(
        and_(
            Budget.id == budget_id,
            Budget.organization_id == org_id
        )
    )
    result = await db.execute(stmt)
    budget = result.scalar_one_or_none()

    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found"
        )

    # Update fields
    if data.name is not None:
        budget.name = data.name
    if data.description is not None:
        budget.description = data.description
    if data.amount is not None:
        budget.amount = Decimal(str(data.amount))
    if data.period is not None:
        budget.period = data.period
    if data.category is not None:
        budget.category = data.category
    if data.warning_threshold is not None:
        budget.warning_threshold = data.warning_threshold
    if data.critical_threshold is not None:
        budget.critical_threshold = data.critical_threshold
    if data.end_date is not None:
        budget.end_date = data.end_date
    if data.is_active is not None:
        budget.is_active = data.is_active

    await db.commit()
    await db.refresh(budget)

    # Calculate current spending
    start_date, end_date = get_budget_period_dates(budget)
    current_spending = await calculate_budget_spending(db, budget, start_date, end_date)
    percentage_used = float((current_spending / budget.amount) * 100) if budget.amount > 0 else 0
    remaining = float(budget.amount - current_spending)
    status_str = calculate_budget_status(percentage_used, budget.warning_threshold, budget.critical_threshold)

    return BudgetResponse(
        id=budget.id,
        organization_id=budget.organization_id,
        user_id=budget.user_id,
        name=budget.name,
        description=budget.description,
        amount=float(budget.amount),
        period=budget.period.value,
        category=budget.category.value if budget.category else None,
        warning_threshold=budget.warning_threshold,
        critical_threshold=budget.critical_threshold,
        is_active=budget.is_active,
        start_date=budget.start_date,
        end_date=budget.end_date,
        current_spending=float(current_spending),
        percentage_used=round(percentage_used, 2),
        remaining=remaining,
        status=status_str,
        created_at=budget.created_at
    )


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a budget"""

    # Only admins can delete budgets
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete budgets"
        )

    org_id = await get_user_organization(db, current_user.id)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a member of any organization"
        )

    stmt = select(Budget).where(
        and_(
            Budget.id == budget_id,
            Budget.organization_id == org_id
        )
    )
    result = await db.execute(stmt)
    budget = result.scalar_one_or_none()

    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found"
        )

    await db.delete(budget)
    await db.commit()


# ============================================================================
# Budget Alert Endpoints
# ============================================================================

@router.get("/{budget_id}/alerts", response_model=List[BudgetAlertResponse])
async def get_budget_alerts(
    budget_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all alerts for a budget"""

    org_id = await get_user_organization(db, current_user.id)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a member of any organization"
        )

    # Verify budget exists and user has access
    budget_stmt = select(Budget).where(
        and_(
            Budget.id == budget_id,
            Budget.organization_id == org_id
        )
    )
    budget_result = await db.execute(budget_stmt)
    budget = budget_result.scalar_one_or_none()

    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found"
        )

    # Check access
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        if budget.user_id and budget.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this budget's alerts"
            )

    query = select(BudgetAlert).where(
        BudgetAlert.budget_id == budget_id
    ).order_by(BudgetAlert.created_at.desc())

    result = await db.execute(query)
    alerts = result.scalars().all()

    return [
        BudgetAlertResponse(
            id=alert.id,
            budget_id=alert.budget_id,
            alert_type=alert.alert_type,
            threshold_percentage=alert.threshold_percentage,
            actual_amount=float(alert.actual_amount),
            budget_amount=float(alert.budget_amount),
            message=alert.message,
            is_acknowledged=alert.is_acknowledged,
            acknowledged_at=alert.acknowledged_at,
            created_at=alert.created_at
        )
        for alert in alerts
    ]


@router.post("/{budget_id}/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    budget_id: str,
    alert_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Acknowledge a budget alert"""

    org_id = await get_user_organization(db, current_user.id)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a member of any organization"
        )

    # Get alert
    alert_stmt = select(BudgetAlert).where(
        and_(
            BudgetAlert.id == alert_id,
            BudgetAlert.budget_id == budget_id
        )
    )
    alert_result = await db.execute(alert_stmt)
    alert = alert_result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )

    # Verify budget access
    budget_stmt = select(Budget).where(Budget.id == budget_id)
    budget_result = await db.execute(budget_stmt)
    budget = budget_result.scalar_one_or_none()

    if not budget or budget.organization_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found"
        )

    # Acknowledge alert
    alert.is_acknowledged = True
    alert.acknowledged_at = datetime.utcnow()
    alert.acknowledged_by = current_user.id

    await db.commit()

    return {"success": True, "message": "Alert acknowledged"}
