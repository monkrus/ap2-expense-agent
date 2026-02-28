"""
Reconciliation & Reporting Service - Autonomous variance analysis agent.

Generates budget-vs-actual reports, category reconciliation,
user spending reports, and budget forecasts.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from ..models import (
    Budget,
    BudgetPeriod,
    Expense,
    ExpenseCategory,
    OrganizationMember,
    User,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Result Types
# ============================================================================


@dataclass
class BudgetVariance:
    """Variance data for a single budget."""

    budget_id: str
    budget_name: str
    category: Optional[str]
    period: str
    budgeted_amount: float
    actual_spending: float
    variance_amount: float  # positive = under budget, negative = over budget
    variance_percentage: float
    status: str  # under_budget, on_track, over_budget


@dataclass
class VarianceReport:
    """Full variance report for an organization."""

    organization_id: str
    period: str
    generated_at: str
    budgets: List[BudgetVariance] = field(default_factory=list)
    total_budgeted: float = 0.0
    total_actual: float = 0.0
    total_variance: float = 0.0
    over_budget_count: int = 0
    under_budget_count: int = 0


@dataclass
class CategoryVariance:
    """Spending data for a single category."""

    category: str
    budgeted_amount: Optional[float]  # None if no budget for this category
    actual_spending: float
    variance_amount: Optional[float]
    variance_percentage: Optional[float]
    expense_count: int
    is_budgeted: bool


@dataclass
class CategoryReport:
    """Category-level reconciliation report."""

    organization_id: str
    start_date: str
    end_date: str
    generated_at: str
    categories: List[CategoryVariance] = field(default_factory=list)
    total_budgeted: float = 0.0
    total_actual: float = 0.0
    unbudgeted_spending: float = 0.0


@dataclass
class UserSpending:
    """Spending data for a single user."""

    user_id: str
    user_name: str
    email: str
    expense_count: int
    total_spending: float
    budget_amount: Optional[float]  # None if no user-specific budget
    percentage_used: Optional[float]
    avg_expense: float


@dataclass
class UserReport:
    """Per-user spending report."""

    organization_id: str
    period: str
    generated_at: str
    users: List[UserSpending] = field(default_factory=list)
    total_users: int = 0
    total_spending: float = 0.0


@dataclass
class ForecastResult:
    """Budget forecast based on current spending rate."""

    budget_id: str
    budget_name: str
    budget_amount: float
    current_spending: float
    daily_spending_rate: float
    days_elapsed: int
    days_remaining: int
    projected_end_spending: float
    projected_variance: float
    projected_status: str  # on_track, will_exceed, will_under


# ============================================================================
# Helper Functions
# ============================================================================


def _get_period_dates(period: str) -> tuple:
    """Get start and end dates for a budget period type."""
    now = datetime.utcnow()

    if period == BudgetPeriod.MONTHLY or period == "monthly":
        start = datetime(now.year, now.month, 1)
        if now.month == 12:
            end = datetime(now.year + 1, 1, 1) - timedelta(seconds=1)
        else:
            end = datetime(now.year, now.month + 1, 1) - timedelta(seconds=1)
    elif period == BudgetPeriod.QUARTERLY or period == "quarterly":
        quarter = (now.month - 1) // 3 + 1
        start_month = (quarter - 1) * 3 + 1
        start = datetime(now.year, start_month, 1)
        end_month = start_month + 3
        if end_month > 12:
            end = datetime(now.year + 1, end_month - 12, 1) - timedelta(seconds=1)
        else:
            end = datetime(now.year, end_month, 1) - timedelta(seconds=1)
    elif period == BudgetPeriod.YEARLY or period == "yearly":
        start = datetime(now.year, 1, 1)
        end = datetime(now.year, 12, 31, 23, 59, 59)
    else:
        # Default to monthly
        start = datetime(now.year, now.month, 1)
        if now.month == 12:
            end = datetime(now.year + 1, 1, 1) - timedelta(seconds=1)
        else:
            end = datetime(now.year, now.month + 1, 1) - timedelta(seconds=1)

    return start, end


def _calculate_budget_spending(
    db: Session, budget: Budget, start_date: datetime, end_date: datetime
) -> Decimal:
    """Calculate total spending for a budget period."""
    query = select(func.sum(Expense.amount)).where(
        and_(
            Expense.organization_id == budget.organization_id,
            Expense.created_at >= start_date,
            Expense.created_at <= end_date,
            Expense.status.in_(["pending", "approved"]),
        )
    )
    if budget.category:
        query = query.where(Expense.category == budget.category)
    if budget.user_id:
        query = query.where(Expense.user_id == budget.user_id)

    result = db.execute(query)
    total = result.scalar_one()
    return Decimal(str(total or 0))


def _get_budget_period_dates(budget: Budget) -> tuple:
    """Get the start and end dates for the current budget period."""
    now = datetime.utcnow()

    # Guard against null period - default to using budget's own date range
    if budget.period is None:
        start = budget.start_date
        end = budget.end_date or now
        start = max(start, budget.start_date)
        if budget.end_date:
            end = min(end, budget.end_date)
        return start, end

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

    start = max(start, budget.start_date)
    if budget.end_date:
        end = min(end, budget.end_date)

    return start, end


# ============================================================================
# Reconciliation Service
# ============================================================================


class ReconciliationService:
    """
    Autonomous reconciliation and reporting agent.

    Generates budget-vs-actual reports, category reconciliation,
    user spending reports, and budget forecasts.
    """

    def __init__(self, db: Session):
        self.db = db

    def generate_variance_report(
        self, organization_id: str, period: str = "monthly"
    ) -> VarianceReport:
        """
        Generate a budget-vs-actual variance report.

        For each active budget: calculates budgeted amount, actual spending,
        variance ($), and variance (%).

        Args:
            organization_id: Organization to report on
            period: Budget period to analyze (monthly, quarterly, yearly)

        Returns:
            VarianceReport with per-budget variance data
        """
        start_date, end_date = _get_period_dates(period)

        # Get all active budgets for this org and period
        query = select(Budget).where(
            and_(
                Budget.organization_id == organization_id,
                Budget.is_active == True,
            )
        )
        result = self.db.execute(query)
        budgets = result.scalars().all()

        report = VarianceReport(
            organization_id=organization_id,
            period=period,
            generated_at=datetime.utcnow().isoformat(),
        )

        for budget in budgets:
            # Skip budgets with no period set
            if budget.period is None:
                continue

            b_start, b_end = _get_budget_period_dates(budget)
            actual = float(
                _calculate_budget_spending(self.db, budget, b_start, b_end)
            )
            budgeted = float(budget.amount)
            variance = budgeted - actual
            variance_pct = (variance / budgeted * 100) if budgeted > 0 else 0

            if actual > budgeted:
                status = "over_budget"
                report.over_budget_count += 1
            elif actual >= budgeted * 0.9:
                status = "on_track"
            else:
                status = "under_budget"
                report.under_budget_count += 1

            cat_value = None
            if budget.category:
                cat_value = budget.category.value if hasattr(budget.category, "value") else str(budget.category)

            report.budgets.append(
                BudgetVariance(
                    budget_id=budget.id,
                    budget_name=budget.name,
                    category=cat_value,
                    period=budget.period.value if hasattr(budget.period, "value") else str(budget.period),
                    budgeted_amount=budgeted,
                    actual_spending=round(actual, 2),
                    variance_amount=round(variance, 2),
                    variance_percentage=round(variance_pct, 2),
                    status=status,
                )
            )

            report.total_budgeted += budgeted
            report.total_actual += actual

        report.total_variance = round(report.total_budgeted - report.total_actual, 2)
        report.total_budgeted = round(report.total_budgeted, 2)
        report.total_actual = round(report.total_actual, 2)

        return report

    def generate_category_reconciliation(
        self,
        organization_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> CategoryReport:
        """
        Generate category-level reconciliation report.

        Breaks down spending by category vs budgeted amounts.
        Shows unbudgeted spending (expenses in categories with no budget).

        Args:
            organization_id: Organization to report on
            start_date: Report start date (defaults to start of current month)
            end_date: Report end date (defaults to now)

        Returns:
            CategoryReport with per-category variance data
        """
        now = datetime.utcnow()
        if not start_date:
            start_date = datetime(now.year, now.month, 1)
        if not end_date:
            end_date = now

        # Get actual spending by category
        spending_query = (
            self.db.query(
                Expense.category,
                func.count(Expense.id).label("count"),
                func.sum(Expense.amount).label("total"),
            )
            .filter(
                Expense.organization_id == organization_id,
                Expense.created_at >= start_date,
                Expense.created_at <= end_date,
                Expense.status.in_(["pending", "approved"]),
            )
            .group_by(Expense.category)
            .all()
        )

        # Build spending map
        spending_map: Dict[str, tuple] = {}
        for row in spending_query:
            cat = row.category
            if hasattr(cat, "value"):
                cat = cat.value
            spending_map[str(cat)] = (row.count, float(row.total or 0))

        # Get category-specific budgets
        budget_query = select(Budget).where(
            and_(
                Budget.organization_id == organization_id,
                Budget.is_active == True,
                Budget.category.isnot(None),
            )
        )
        budget_result = self.db.execute(budget_query)
        budgets = budget_result.scalars().all()

        budget_map: Dict[str, float] = {}
        for budget in budgets:
            cat = budget.category.value if hasattr(budget.category, "value") else str(budget.category)
            budget_map[cat] = float(budget.amount)

        report = CategoryReport(
            organization_id=organization_id,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            generated_at=now.isoformat(),
        )

        # Combine all categories (budgeted + actual)
        all_categories = set(list(spending_map.keys()) + list(budget_map.keys()))

        for cat in sorted(all_categories):
            count, actual = spending_map.get(cat, (0, 0.0))
            budgeted = budget_map.get(cat)
            is_budgeted = budgeted is not None

            variance_amt = None
            variance_pct = None
            if is_budgeted:
                variance_amt = round(budgeted - actual, 2)
                variance_pct = round((variance_amt / budgeted * 100) if budgeted > 0 else 0, 2)
                report.total_budgeted += budgeted
            else:
                report.unbudgeted_spending += actual

            report.total_actual += actual

            report.categories.append(
                CategoryVariance(
                    category=cat,
                    budgeted_amount=round(budgeted, 2) if budgeted is not None else None,
                    actual_spending=round(actual, 2),
                    variance_amount=variance_amt,
                    variance_percentage=variance_pct,
                    expense_count=count,
                    is_budgeted=is_budgeted,
                )
            )

        report.total_budgeted = round(report.total_budgeted, 2)
        report.total_actual = round(report.total_actual, 2)
        report.unbudgeted_spending = round(report.unbudgeted_spending, 2)

        return report

    def generate_user_spending_report(
        self, organization_id: str, period: str = "monthly"
    ) -> UserReport:
        """
        Generate per-user spending report.

        Shows each user's spending, expense count, and comparison to
        user-specific budgets (if any).

        Args:
            organization_id: Organization to report on
            period: Budget period to analyze

        Returns:
            UserReport with per-user spending data
        """
        start_date, end_date = _get_period_dates(period)

        # Get spending per user
        user_spending = (
            self.db.query(
                User.id,
                User.full_name,
                User.username,
                User.email,
                func.count(Expense.id).label("expense_count"),
                func.sum(Expense.amount).label("total_amount"),
            )
            .join(Expense, Expense.user_id == User.id)
            .join(
                OrganizationMember,
                and_(
                    OrganizationMember.user_id == User.id,
                    OrganizationMember.organization_id == organization_id,
                    OrganizationMember.is_active == True,
                ),
            )
            .filter(
                Expense.organization_id == organization_id,
                Expense.created_at >= start_date,
                Expense.created_at <= end_date,
                Expense.status.in_(["pending", "approved"]),
            )
            .group_by(User.id, User.full_name, User.username, User.email)
            .order_by(func.sum(Expense.amount).desc())
            .all()
        )

        # Get user-specific budgets
        user_budgets_query = select(Budget).where(
            and_(
                Budget.organization_id == organization_id,
                Budget.is_active == True,
                Budget.user_id.isnot(None),
            )
        )
        user_budgets = self.db.execute(user_budgets_query).scalars().all()
        budget_map = {b.user_id: float(b.amount) for b in user_budgets}

        report = UserReport(
            organization_id=organization_id,
            period=period,
            generated_at=datetime.utcnow().isoformat(),
        )

        for row in user_spending:
            total = float(row.total_amount or 0)
            count = row.expense_count or 0
            budget_amt = budget_map.get(row.id)
            pct_used = None
            if budget_amt and budget_amt > 0:
                pct_used = round((total / budget_amt) * 100, 2)

            report.users.append(
                UserSpending(
                    user_id=row.id,
                    user_name=row.full_name or row.username,
                    email=row.email,
                    expense_count=count,
                    total_spending=round(total, 2),
                    budget_amount=round(budget_amt, 2) if budget_amt is not None else None,
                    percentage_used=pct_used,
                    avg_expense=round(total / count, 2) if count > 0 else 0,
                )
            )
            report.total_spending += total

        report.total_users = len(report.users)
        report.total_spending = round(report.total_spending, 2)

        return report

    def get_budget_forecast(self, budget_id: str) -> Optional[ForecastResult]:
        """
        Forecast end-of-period spending based on current rate.

        Args:
            budget_id: Budget to forecast

        Returns:
            ForecastResult with projected spending, or None if budget not found
        """
        budget = self.db.execute(
            select(Budget).where(Budget.id == budget_id)
        ).scalar_one_or_none()

        if not budget:
            return None

        start_date, end_date = _get_budget_period_dates(budget)
        now = datetime.utcnow()

        current_spending = float(
            _calculate_budget_spending(self.db, budget, start_date, end_date)
        )
        budget_amount = float(budget.amount)

        days_elapsed = max(1, (now - start_date).days)
        total_days = max(1, (end_date - start_date).days)
        days_remaining = max(0, (end_date - now).days)

        daily_rate = current_spending / days_elapsed
        projected = daily_rate * total_days
        projected_variance = budget_amount - projected

        if projected > budget_amount:
            projected_status = "will_exceed"
        elif projected > budget_amount * 0.9:
            projected_status = "on_track"
        else:
            projected_status = "will_under"

        return ForecastResult(
            budget_id=budget.id,
            budget_name=budget.name,
            budget_amount=budget_amount,
            current_spending=round(current_spending, 2),
            daily_spending_rate=round(daily_rate, 2),
            days_elapsed=days_elapsed,
            days_remaining=days_remaining,
            projected_end_spending=round(projected, 2),
            projected_variance=round(projected_variance, 2),
            projected_status=projected_status,
        )
