"""
Analytics endpoints for organization-level insights
Provides chart-ready data for dashboard visualizations
"""

from datetime import datetime, timedelta, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from ..auth import get_current_active_user
from ..database import get_db
from ..models import Expense, ExpenseStatus, ExpenseCategory, User, OrganizationMember
from ..tenant_context import verify_organization_access

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


def get_org_id_from_request(request: Request) -> str:
    """Extract organization ID from request headers"""
    org_id = request.headers.get("X-Organization-Id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization context required (X-Organization-Id header missing)"
        )
    return org_id


@router.get("/dashboard")
async def get_dashboard_analytics(
    request: Request,
    days: int = Query(30, ge=7, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get comprehensive analytics for organization dashboard

    Returns chart-ready data for:
    - Spending over time (line chart)
    - Category breakdown (pie chart)
    - Top spenders (bar chart)
    - Status distribution (donut chart)
    - Monthly comparison metrics
    """
    org_id = get_org_id_from_request(request)

    # Verify access
    if not verify_organization_access(current_user.id, org_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this organization"
        )

    start_date = datetime.utcnow() - timedelta(days=days)

    # 1. Spending Over Time (Daily aggregation for line chart)
    daily_spending = (
        db.query(
            func.date(Expense.created_at).label("date"),
            func.count(Expense.id).label("count"),
            func.sum(Expense.amount).label("total_amount"),
        )
        .filter(
            Expense.organization_id == org_id,
            Expense.created_at >= start_date,
        )
        .group_by(func.date(Expense.created_at))
        .order_by(func.date(Expense.created_at))
        .all()
    )

    # 2. Category Breakdown (Pie chart)
    category_breakdown = (
        db.query(
            Expense.category,
            func.count(Expense.id).label("count"),
            func.sum(Expense.amount).label("total_amount"),
        )
        .filter(
            Expense.organization_id == org_id,
            Expense.created_at >= start_date,
        )
        .group_by(Expense.category)
        .all()
    )

    # 3. Top Spenders (Bar chart)
    top_spenders = (
        db.query(
            User.full_name,
            User.username,
            func.count(Expense.id).label("expense_count"),
            func.sum(Expense.amount).label("total_amount"),
        )
        .join(Expense, Expense.user_id == User.id)
        .filter(
            Expense.organization_id == org_id,
            Expense.created_at >= start_date,
        )
        .group_by(User.id, User.full_name, User.username)
        .order_by(func.sum(Expense.amount).desc())
        .limit(10)
        .all()
    )

    # 4. Status Distribution (Donut chart)
    status_distribution = (
        db.query(
            Expense.status,
            func.count(Expense.id).label("count"),
            func.sum(Expense.amount).label("total_amount"),
        )
        .filter(
            Expense.organization_id == org_id,
            Expense.created_at >= start_date,
        )
        .group_by(Expense.status)
        .all()
    )

    # 5. Monthly Comparison (current vs previous period)
    current_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    previous_month_start = (current_month_start - timedelta(days=1)).replace(day=1)

    current_month_stats = (
        db.query(
            func.count(Expense.id).label("count"),
            func.sum(Expense.amount).label("total_amount"),
        )
        .filter(
            Expense.organization_id == org_id,
            Expense.created_at >= current_month_start,
        )
        .first()
    )

    previous_month_stats = (
        db.query(
            func.count(Expense.id).label("count"),
            func.sum(Expense.amount).label("total_amount"),
        )
        .filter(
            Expense.organization_id == org_id,
            Expense.created_at >= previous_month_start,
            Expense.created_at < current_month_start,
        )
        .first()
    )

    # Calculate percentage changes
    current_count = current_month_stats.count or 0
    previous_count = previous_month_stats.count or 0
    current_amount = float(current_month_stats.total_amount or 0)
    previous_amount = float(previous_month_stats.total_amount or 0)

    count_change = ((current_count - previous_count) / previous_count * 100) if previous_count > 0 else 0
    amount_change = ((current_amount - previous_amount) / previous_amount * 100) if previous_amount > 0 else 0

    # 6. Top Vendors
    top_vendors = (
        db.query(
            Expense.vendor,
            func.count(Expense.id).label("count"),
            func.sum(Expense.amount).label("total_amount"),
        )
        .filter(
            Expense.organization_id == org_id,
            Expense.created_at >= start_date,
            Expense.vendor.isnot(None),
            Expense.vendor != "",
        )
        .group_by(Expense.vendor)
        .order_by(func.sum(Expense.amount).desc())
        .limit(10)
        .all()
    )

    # Format response
    return {
        "period": {
            "days": days,
            "start_date": start_date.isoformat(),
            "end_date": datetime.utcnow().isoformat(),
        },
        "spending_over_time": [
            {
                "date": d.date.isoformat() if isinstance(d.date, (date, datetime)) else str(d.date),
                "count": d.count,
                "amount": float(d.total_amount or 0),
            }
            for d in daily_spending
        ],
        "category_breakdown": [
            {
                "category": c.category,
                "count": c.count,
                "amount": float(c.total_amount or 0),
                "percentage": 0,  # Will be calculated on frontend
            }
            for c in category_breakdown
        ],
        "top_spenders": [
            {
                "name": s.full_name or s.username,
                "username": s.username,
                "expense_count": s.expense_count,
                "total_amount": float(s.total_amount or 0),
            }
            for s in top_spenders
        ],
        "status_distribution": [
            {
                "status": s.status,
                "count": s.count,
                "amount": float(s.total_amount or 0),
            }
            for s in status_distribution
        ],
        "monthly_comparison": {
            "current_month": {
                "count": current_count,
                "amount": current_amount,
            },
            "previous_month": {
                "count": previous_count,
                "amount": previous_amount,
            },
            "changes": {
                "count_change_percent": round(count_change, 2),
                "amount_change_percent": round(amount_change, 2),
            },
        },
        "top_vendors": [
            {
                "vendor": v.vendor,
                "count": v.count,
                "amount": float(v.total_amount or 0),
            }
            for v in top_vendors
        ],
    }


@router.get("/summary")
async def get_analytics_summary(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get quick summary metrics for analytics cards
    """
    org_id = get_org_id_from_request(request)

    # Verify access
    if not verify_organization_access(current_user.id, org_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this organization"
        )

    # Overall totals
    total_stats = (
        db.query(
            func.count(Expense.id).label("total_count"),
            func.sum(Expense.amount).label("total_amount"),
        )
        .filter(Expense.organization_id == org_id)
        .first()
    )

    # This month
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_stats = (
        db.query(
            func.count(Expense.id).label("count"),
            func.sum(Expense.amount).label("amount"),
        )
        .filter(
            Expense.organization_id == org_id,
            Expense.created_at >= month_start,
        )
        .first()
    )

    # Pending approvals
    pending_count = (
        db.query(func.count(Expense.id))
        .filter(
            Expense.organization_id == org_id,
            Expense.status == ExpenseStatus.PENDING,
        )
        .scalar() or 0
    )

    # Active users count
    active_users = (
        db.query(func.count(func.distinct(OrganizationMember.user_id)))
        .filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.is_active == True,
        )
        .scalar() or 0
    )

    return {
        "all_time": {
            "total_expenses": total_stats.total_count or 0,
            "total_amount": float(total_stats.total_amount or 0),
        },
        "this_month": {
            "count": month_stats.count or 0,
            "amount": float(month_stats.amount or 0),
        },
        "pending_approvals": pending_count,
        "active_users": active_users,
    }


# ============================================================================
# Reconciliation & Reporting Endpoints
# ============================================================================


@router.get("/variance-report")
async def get_variance_report(
    request: Request,
    period: str = Query("monthly", description="Budget period: monthly, quarterly, yearly"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Budget vs actual variance report.
    Shows each budget's variance with over/under status.
    """
    org_id = get_org_id_from_request(request)

    if not verify_organization_access(current_user.id, org_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this organization",
        )

    from ..services.reconciliation_service import ReconciliationService

    service = ReconciliationService(db)
    report = service.generate_variance_report(org_id, period)

    return {
        "organization_id": report.organization_id,
        "period": report.period,
        "generated_at": report.generated_at,
        "total_budgeted": report.total_budgeted,
        "total_actual": report.total_actual,
        "total_variance": report.total_variance,
        "over_budget_count": report.over_budget_count,
        "under_budget_count": report.under_budget_count,
        "budgets": [
            {
                "budget_id": b.budget_id,
                "budget_name": b.budget_name,
                "category": b.category,
                "period": b.period,
                "budgeted_amount": b.budgeted_amount,
                "actual_spending": b.actual_spending,
                "variance_amount": b.variance_amount,
                "variance_percentage": b.variance_percentage,
                "status": b.status,
            }
            for b in report.budgets
        ],
    }


@router.get("/category-reconciliation")
async def get_category_reconciliation(
    request: Request,
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Category-level reconciliation report.
    Shows spending by category vs budgeted amounts, flags unbudgeted spending.
    """
    org_id = get_org_id_from_request(request)

    if not verify_organization_access(current_user.id, org_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this organization",
        )

    parsed_start = datetime.fromisoformat(start_date) if start_date else None
    parsed_end = datetime.fromisoformat(end_date) if end_date else None

    from ..services.reconciliation_service import ReconciliationService

    service = ReconciliationService(db)
    report = service.generate_category_reconciliation(org_id, parsed_start, parsed_end)

    return {
        "organization_id": report.organization_id,
        "start_date": report.start_date,
        "end_date": report.end_date,
        "generated_at": report.generated_at,
        "total_budgeted": report.total_budgeted,
        "total_actual": report.total_actual,
        "unbudgeted_spending": report.unbudgeted_spending,
        "categories": [
            {
                "category": c.category,
                "budgeted_amount": c.budgeted_amount,
                "actual_spending": c.actual_spending,
                "variance_amount": c.variance_amount,
                "variance_percentage": c.variance_percentage,
                "expense_count": c.expense_count,
                "is_budgeted": c.is_budgeted,
            }
            for c in report.categories
        ],
    }


@router.get("/user-spending")
async def get_user_spending_report(
    request: Request,
    period: str = Query("monthly", description="Budget period: monthly, quarterly, yearly"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Per-user spending report.
    Shows each user's spending, expense count, and budget comparison.
    """
    org_id = get_org_id_from_request(request)

    if not verify_organization_access(current_user.id, org_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this organization",
        )

    from ..services.reconciliation_service import ReconciliationService

    service = ReconciliationService(db)
    report = service.generate_user_spending_report(org_id, period)

    return {
        "organization_id": report.organization_id,
        "period": report.period,
        "generated_at": report.generated_at,
        "total_users": report.total_users,
        "total_spending": report.total_spending,
        "users": [
            {
                "user_id": u.user_id,
                "user_name": u.user_name,
                "email": u.email,
                "expense_count": u.expense_count,
                "total_spending": u.total_spending,
                "budget_amount": u.budget_amount,
                "percentage_used": u.percentage_used,
                "avg_expense": u.avg_expense,
            }
            for u in report.users
        ],
    }


@router.get("/budget-forecast/{budget_id}")
async def get_budget_forecast(
    budget_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Budget forecast based on current spending rate.
    Projects end-of-period total and flags if projected to exceed budget.
    """
    org_id = get_org_id_from_request(request)

    if not verify_organization_access(current_user.id, org_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this organization",
        )

    from ..services.reconciliation_service import ReconciliationService

    service = ReconciliationService(db)
    forecast = service.get_budget_forecast(budget_id)

    if not forecast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    return {
        "budget_id": forecast.budget_id,
        "budget_name": forecast.budget_name,
        "budget_amount": forecast.budget_amount,
        "current_spending": forecast.current_spending,
        "daily_spending_rate": forecast.daily_spending_rate,
        "days_elapsed": forecast.days_elapsed,
        "days_remaining": forecast.days_remaining,
        "projected_end_spending": forecast.projected_end_spending,
        "projected_variance": forecast.projected_variance,
        "projected_status": forecast.projected_status,
    }
