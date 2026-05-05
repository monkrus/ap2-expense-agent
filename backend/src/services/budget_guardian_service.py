"""
Budget Guardian Service - Proactive budget enforcement agent.

Evaluates budgets on every expense submission and provides warnings/blocks.
Monitors all active budgets and creates alerts when thresholds are crossed.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from ..models import (
    Budget,
    BudgetAlert,
    BudgetPeriod,
    Expense,
    Notification,
    NotificationType,
    OrganizationMember,
    User,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Result Types
# ============================================================================


@dataclass
class BudgetImpact:
    """Impact of an expense on a single budget."""

    budget_id: str
    budget_name: str
    budget_amount: float
    current_spending: float
    proposed_total: float
    percentage_before: float
    percentage_after: float
    status_before: str
    status_after: str


@dataclass
class BudgetGuardianResult:
    """Result of evaluating an expense against all applicable budgets."""

    allowed: bool = True
    warnings: List[str] = field(default_factory=list)
    blocks: List[str] = field(default_factory=list)
    budget_impacts: List[BudgetImpact] = field(default_factory=list)


@dataclass
class BudgetHealthReport:
    """Health status of a single budget."""

    budget_id: str
    budget_name: str
    period: str
    category: Optional[str]
    budget_amount: float
    current_spending: float
    remaining: float
    percentage_used: float
    status: str  # on_track, warning, critical, exceeded
    days_remaining: Optional[int]
    projected_end_spending: Optional[float]


# ============================================================================
# Helper Functions (reused from routes/budgets.py)
# ============================================================================


def _get_budget_period_dates(budget: Budget) -> tuple:
    """Get the start and end dates for the current budget period."""
    from datetime import timedelta

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


def _calculate_spending(
    db: Session, budget: Budget, start_date: datetime, end_date: datetime
) -> Decimal:
    """Calculate total spending for a budget period."""
    from sqlalchemy import func

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


def _budget_status(percentage_used: float, warning: int, critical: int) -> str:
    """Determine budget status based on percentage used."""
    if percentage_used >= 100:
        return "exceeded"
    elif percentage_used >= critical:
        return "critical"
    elif percentage_used >= warning:
        return "warning"
    return "on_track"


# ============================================================================
# Budget Guardian Service
# ============================================================================


class BudgetGuardianService:
    """
    Proactive budget enforcement agent.

    Evaluates expenses against budgets before they are saved,
    monitors budget health, and creates alerts when thresholds are crossed.
    """

    def __init__(self, db: Session):
        self.db = db

    def evaluate_expense(
        self,
        expense_amount: float,
        organization_id: str,
        category: Optional[str] = None,
        user_id: Optional[str] = None,
        hard_block: bool = False,
    ) -> BudgetGuardianResult:
        """
        Evaluate an expense against all applicable budgets.

        Args:
            expense_amount: The proposed expense amount
            organization_id: The organization to check budgets for
            category: Expense category (for category-specific budgets)
            user_id: User ID (for user-specific budgets)
            hard_block: If True, block expenses that would exceed 100% of budget

        Returns:
            BudgetGuardianResult with allowed status, warnings, blocks, and impacts
        """
        result = BudgetGuardianResult()
        amount = Decimal(str(expense_amount))

        # Find all applicable active budgets
        budgets = self._find_applicable_budgets(organization_id, category, user_id)

        for budget in budgets:
            start_date, end_date = _get_budget_period_dates(budget)
            current_spending = _calculate_spending(
                self.db, budget, start_date, end_date
            )
            proposed_total = current_spending + amount
            budget_amount = Decimal(str(budget.amount))

            pct_before = (
                float((current_spending / budget_amount) * 100)
                if budget_amount > 0
                else 0
            )
            pct_after = (
                float((proposed_total / budget_amount) * 100)
                if budget_amount > 0
                else 0
            )
            status_before = _budget_status(
                pct_before, budget.warning_threshold, budget.critical_threshold
            )
            status_after = _budget_status(
                pct_after, budget.warning_threshold, budget.critical_threshold
            )

            impact = BudgetImpact(
                budget_id=budget.id,
                budget_name=budget.name,
                budget_amount=float(budget_amount),
                current_spending=float(current_spending),
                proposed_total=float(proposed_total),
                percentage_before=round(pct_before, 2),
                percentage_after=round(pct_after, 2),
                status_before=status_before,
                status_after=status_after,
            )
            result.budget_impacts.append(impact)

            # Check if expense would cross warning threshold
            if (
                pct_before < budget.warning_threshold
                and pct_after >= budget.warning_threshold
            ):
                result.warnings.append(
                    f"Budget '{budget.name}' will reach {pct_after:.1f}% "
                    f"(warning threshold: {budget.warning_threshold}%)"
                )

            # Check if expense would cross critical threshold
            if (
                pct_before < budget.critical_threshold
                and pct_after >= budget.critical_threshold
            ):
                result.warnings.append(
                    f"Budget '{budget.name}' will reach {pct_after:.1f}% "
                    f"(critical threshold: {budget.critical_threshold}%)"
                )

            # Check if expense would exceed 100%
            if pct_after >= 100:
                msg = (
                    f"Budget '{budget.name}' would be exceeded: "
                    f"${float(proposed_total):,.2f} / ${float(budget_amount):,.2f} "
                    f"({pct_after:.1f}%)"
                )
                if hard_block:
                    result.blocks.append(msg)
                    result.allowed = False
                else:
                    result.warnings.append(msg)

            # Create alerts for threshold crossings
            self.create_alerts_if_needed(budget, proposed_total)

        return result

    def check_all_budgets(self, organization_id: str) -> List[BudgetHealthReport]:
        """
        Scan all active budgets for an org and return health status.

        Args:
            organization_id: Organization to check

        Returns:
            List of BudgetHealthReport for each active budget
        """
        stmt = select(Budget).where(
            and_(
                Budget.organization_id == organization_id,
                Budget.is_active == True,
            )
        )
        result = self.db.execute(stmt)
        budgets = result.scalars().all()

        reports = []
        now = datetime.utcnow()

        for budget in budgets:
            # Skip budgets with no period set
            if budget.period is None:
                continue

            # Skip expired budgets
            if budget.end_date:
                end_check = budget.end_date
                if isinstance(end_check, datetime):
                    if end_check < now:
                        continue
                elif end_check < now.date():
                    continue

            start_date, end_date = _get_budget_period_dates(budget)
            current_spending = _calculate_spending(
                self.db, budget, start_date, end_date
            )
            budget_amount = Decimal(str(budget.amount))

            pct_used = (
                float((current_spending / budget_amount) * 100)
                if budget_amount > 0
                else 0
            )
            remaining = float(budget_amount - current_spending)
            status = _budget_status(
                pct_used, budget.warning_threshold, budget.critical_threshold
            )

            # Calculate days remaining in period
            days_remaining = max(0, (end_date - now).days) if end_date > now else 0

            # Calculate projected end-of-period spending
            days_elapsed = max(1, (now - start_date).days)
            total_days = max(1, (end_date - start_date).days)
            daily_rate = float(current_spending) / days_elapsed
            projected = daily_rate * total_days if days_elapsed > 0 else 0

            reports.append(
                BudgetHealthReport(
                    budget_id=budget.id,
                    budget_name=budget.name,
                    period=(
                        budget.period.value
                        if hasattr(budget.period, "value")
                        else str(budget.period)
                    ),
                    category=(
                        budget.category.value
                        if budget.category and hasattr(budget.category, "value")
                        else (str(budget.category) if budget.category else None)
                    ),
                    budget_amount=float(budget_amount),
                    current_spending=float(current_spending),
                    remaining=remaining,
                    percentage_used=round(pct_used, 2),
                    status=status,
                    days_remaining=days_remaining,
                    projected_end_spending=round(projected, 2),
                )
            )

        return reports

    def create_alerts_if_needed(
        self, budget: Budget, current_spending: Decimal
    ) -> List[BudgetAlert]:
        """
        Create BudgetAlert records when thresholds are crossed.
        Avoids duplicates by checking if an alert already exists for the current period + type.

        Args:
            budget: The budget to check
            current_spending: Current spending amount (including proposed expense)

        Returns:
            List of newly created BudgetAlert records
        """
        budget_amount = Decimal(str(budget.amount))
        if budget_amount <= 0:
            return []

        pct_used = float((current_spending / budget_amount) * 100)
        start_date, end_date = _get_budget_period_dates(budget)
        alerts_created = []

        # Check each threshold
        thresholds = [
            ("warning", budget.warning_threshold),
            ("critical", budget.critical_threshold),
            ("exceeded", 100),
        ]

        for alert_type, threshold in thresholds:
            if pct_used < threshold:
                continue

            # Check if alert already exists for this period and type
            existing = (
                self.db.execute(
                    select(BudgetAlert).where(
                        and_(
                            BudgetAlert.budget_id == budget.id,
                            BudgetAlert.alert_type == alert_type,
                            BudgetAlert.created_at >= start_date,
                            BudgetAlert.created_at <= end_date,
                        )
                    )
                )
                .scalars()
                .first()
            )

            if existing:
                continue

            # Create new alert
            alert = BudgetAlert(
                id=f"ba_{uuid.uuid4().hex[:16]}",
                budget_id=budget.id,
                alert_type=alert_type,
                threshold_percentage=threshold,
                actual_amount=current_spending,
                budget_amount=budget_amount,
                message=(
                    f"Budget '{budget.name}' has reached {pct_used:.1f}% "
                    f"(${float(current_spending):,.2f} / ${float(budget_amount):,.2f})"
                ),
            )
            self.db.add(alert)
            alerts_created.append(alert)

            # Create in-app notification for org admins
            self._notify_budget_alert(budget, alert_type, pct_used, current_spending)

        if alerts_created:
            self.db.flush()

        return alerts_created

    def _find_applicable_budgets(
        self,
        organization_id: str,
        category: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> list:
        """Find all active budgets that apply to this expense."""
        query = select(Budget).where(
            and_(
                Budget.organization_id == organization_id,
                Budget.is_active == True,
            )
        )
        result = self.db.execute(query)
        all_budgets = result.scalars().all()

        now = datetime.utcnow()
        applicable = []
        for budget in all_budgets:
            # Skip expired budgets
            if budget.end_date:
                end = budget.end_date
                if isinstance(end, datetime):
                    if end < now:
                        continue
                elif end < now.date():
                    continue

            # Skip budgets with zero amount (no meaningful enforcement)
            if not budget.amount or budget.amount == 0:
                continue
            # Org-wide budget (no category or user filter) always applies
            if not budget.category and not budget.user_id:
                applicable.append(budget)
                continue

            # Category-specific budget
            if budget.category and category:
                cat_value = (
                    budget.category.value
                    if hasattr(budget.category, "value")
                    else str(budget.category)
                )
                if cat_value == category:
                    if not budget.user_id:
                        applicable.append(budget)
                    elif budget.user_id == user_id:
                        applicable.append(budget)
                continue

            # User-specific budget (no category filter)
            if budget.user_id and budget.user_id == user_id and not budget.category:
                applicable.append(budget)

        return applicable

    def _notify_budget_alert(
        self,
        budget: Budget,
        alert_type: str,
        percentage: float,
        spending: Decimal,
    ) -> None:
        """Create in-app notifications for org admins about budget alerts."""
        try:
            # Find org admins
            admin_members = (
                self.db.execute(
                    select(OrganizationMember).where(
                        and_(
                            OrganizationMember.organization_id
                            == budget.organization_id,
                            OrganizationMember.role.in_(["owner", "admin"]),
                            OrganizationMember.is_active == True,
                        )
                    )
                )
                .scalars()
                .all()
            )

            title_map = {
                "warning": "Budget Warning",
                "critical": "Budget Critical",
                "exceeded": "Budget Exceeded",
            }

            for member in admin_members:
                notification = Notification(
                    id=str(uuid.uuid4()),
                    user_id=member.user_id,
                    organization_id=budget.organization_id,
                    notification_type=NotificationType.BUDGET_THRESHOLD,
                    title=title_map.get(alert_type, "Budget Alert"),
                    message=(
                        f"Budget '{budget.name}' is at {percentage:.1f}% "
                        f"(${float(spending):,.2f} / ${float(budget.amount):,.2f})"
                    ),
                    is_read=False,
                    created_at=datetime.utcnow(),
                )
                self.db.add(notification)

        except Exception as e:
            logger.error(f"Failed to create budget alert notification: {e}")
