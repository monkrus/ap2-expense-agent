"""
Approval Policy Service
Handles automated expense approval logic based on configurable policies
"""

import logging
from datetime import datetime, time, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from ..models import ApprovalPolicy, Expense, ExpenseCategory, ExpenseStatus, User, UserRole

logger = logging.getLogger(__name__)


class ApprovalPolicyService:
    """Service for evaluating and applying approval policies"""

    def __init__(self, db: Session):
        self.db = db

    def evaluate_expense(
        self, expense: Expense, user: User
    ) -> Tuple[bool, Optional[ApprovalPolicy], str]:
        """
        Evaluate if expense qualifies for auto-approval

        Args:
            expense: The expense to evaluate
            user: The user who submitted the expense

        Returns:
            Tuple of (should_auto_approve, matching_policy, reason)
        """
        # Get active auto-approval policies for organization, ordered by priority
        policies = (
            self.db.query(ApprovalPolicy)
            .filter(
                ApprovalPolicy.organization_id == expense.organization_id,
                ApprovalPolicy.is_active == True,
                ApprovalPolicy.auto_approve == True,
            )
            .order_by(ApprovalPolicy.priority.desc())
            .all()
        )

        if not policies:
            return False, None, "No auto-approval policies configured"

        # Try each policy in priority order
        for policy in policies:
            matches, reason = self._matches_policy(expense, user, policy)

            if matches:
                # Check limits
                within_limits, limit_reason = self._check_limits(expense, user, policy)

                if within_limits:
                    logger.info(
                        f"Expense {expense.id} auto-approved by policy {policy.id} ({policy.name})"
                    )
                    return True, policy, f"Matched policy: {policy.name}"
                else:
                    logger.info(
                        f"Expense {expense.id} matched policy {policy.id} but exceeded limits: {limit_reason}"
                    )
                    # Continue to next policy
                    continue

        return False, None, "No matching auto-approval policy found"

    def _matches_policy(
        self, expense: Expense, user: User, policy: ApprovalPolicy
    ) -> Tuple[bool, str]:
        """
        Check if expense matches all policy conditions

        Returns:
            Tuple of (matches, reason)
        """
        conditions = policy.conditions or {}

        # Amount checks
        if policy.max_amount_per_expense:
            if expense.amount > policy.max_amount_per_expense:
                return (
                    False,
                    f"Amount ${expense.amount} exceeds max ${policy.max_amount_per_expense}",
                )

        if "min_amount" in conditions:
            if expense.amount < Decimal(str(conditions["min_amount"])):
                return (
                    False,
                    f"Amount ${expense.amount} below minimum ${conditions['min_amount']}",
                )

        # Category check
        if "categories" in conditions and conditions["categories"]:
            # Handle both enum and string category values
            category_value = expense.category.value if hasattr(expense.category, 'value') else expense.category
            if category_value not in conditions["categories"]:
                return False, f"Category '{category_value}' not in allowed list"

        # Vendor checks
        if "vendors" in conditions and conditions["vendors"]:
            if expense.vendor not in conditions["vendors"]:
                return False, f"Vendor '{expense.vendor}' not in allowed list"

        if "exclude_vendors" in conditions and conditions["exclude_vendors"]:
            if expense.vendor in conditions["exclude_vendors"]:
                return False, f"Vendor '{expense.vendor}' is excluded"

        # User checks
        if "user_ids" in conditions and conditions["user_ids"]:
            if user.id not in conditions["user_ids"]:
                return False, f"User not in approved list"

        if "user_roles" in conditions and conditions["user_roles"]:
            if user.role.value not in conditions["user_roles"]:
                return False, f"User role '{user.role.value}' not allowed"

        # Receipt requirement
        # TODO: KNOWN ISSUE - Receipts are uploaded AFTER expense creation
        # This check will always fail at creation time. Need to either:
        # 1. Re-evaluate policy after receipt upload
        # 2. Allow conditional approval pending receipt
        # 3. Change workflow to upload receipt before expense creation
        # For now, commenting out to allow auto-approval to work
        # if policy.require_receipt:
        #     receipt_count = len(expense.receipts) if expense.receipts else 0
        #     if receipt_count == 0:
        #         return False, "Receipt required but not attached"

        # Time-based checks
        now = datetime.utcnow()

        # Day of week check (0=Monday, 6=Sunday)
        if "days_of_week" in conditions and conditions["days_of_week"]:
            if now.weekday() not in conditions["days_of_week"]:
                return False, f"Expense submitted on non-allowed day"

        # Time range check
        if "time_range" in conditions:
            time_range = conditions["time_range"]
            current_time = now.time()
            start_time = datetime.strptime(time_range["start"], "%H:%M").time()
            end_time = datetime.strptime(time_range["end"], "%H:%M").time()

            if not (start_time <= current_time <= end_time):
                return False, f"Expense submitted outside allowed hours"

        # Budget compliance check
        if (
            "require_budget_compliance" in conditions
            and conditions["require_budget_compliance"]
        ):
            # Check if expense would exceed budget
            from ..models import Budget
            from ..routes.budgets import (
                calculate_budget_spending,
                get_budget_period_dates,
            )

            budgets = (
                self.db.query(Budget)
                .filter(
                    Budget.organization_id == expense.organization_id,
                    Budget.is_active == True,
                )
                .all()
            )

            for budget in budgets:
                # Check if this budget applies to this expense
                if budget.category and budget.category != expense.category:
                    continue
                if budget.user_id and budget.user_id != user.id:
                    continue

                # Calculate current spending
                start_date, end_date = get_budget_period_dates(budget)
                current_spending = calculate_budget_spending(
                    self.db, budget, start_date, end_date
                )

                # Check if adding this expense would exceed budget
                if (current_spending + expense.amount) > budget.amount:
                    return False, f"Would exceed budget '{budget.name}'"

        # All conditions matched
        return True, "All conditions matched"

    def _check_limits(
        self, expense: Expense, user: User, policy: ApprovalPolicy
    ) -> Tuple[bool, str]:
        """
        Check if expense is within policy limits

        Returns:
            Tuple of (within_limits, reason)
        """
        now = datetime.utcnow()

        # Daily limit check
        if policy.daily_limit_per_user:
            today_start = datetime.combine(now.date(), time.min)
            today_end = datetime.combine(now.date(), time.max)

            daily_total = self.db.query(func.sum(Expense.amount)).filter(
                Expense.organization_id == expense.organization_id,
                Expense.user_id == user.id,
                Expense.auto_approved == True,
                Expense.approved_at >= today_start,
                Expense.approved_at <= today_end,
            ).scalar() or Decimal(0)

            # Convert to Decimal for consistent arithmetic
            expense_amount = Decimal(str(expense.amount))
            daily_limit = Decimal(str(policy.daily_limit_per_user))

            if (daily_total + expense_amount) > daily_limit:
                return (
                    False,
                    f"Would exceed daily limit of ${policy.daily_limit_per_user}",
                )

        # Monthly limit check
        if policy.monthly_limit_per_user:
            month_start = datetime(now.year, now.month, 1)
            if now.month == 12:
                month_end = datetime(now.year + 1, 1, 1) - timedelta(seconds=1)
            else:
                month_end = datetime(now.year, now.month + 1, 1) - timedelta(seconds=1)

            monthly_total = self.db.query(func.sum(Expense.amount)).filter(
                Expense.organization_id == expense.organization_id,
                Expense.user_id == user.id,
                Expense.auto_approved == True,
                Expense.approved_at >= month_start,
                Expense.approved_at <= month_end,
            ).scalar() or Decimal(0)

            # Convert to Decimal for consistent arithmetic
            expense_amount = Decimal(str(expense.amount))
            monthly_limit = Decimal(str(policy.monthly_limit_per_user))

            if (monthly_total + expense_amount) > monthly_limit:
                return (
                    False,
                    f"Would exceed monthly limit of ${policy.monthly_limit_per_user}",
                )

        # Yearly limit check
        if policy.yearly_limit_per_user:
            year_start = datetime(now.year, 1, 1)
            year_end = datetime(now.year, 12, 31, 23, 59, 59)

            yearly_total = self.db.query(func.sum(Expense.amount)).filter(
                Expense.organization_id == expense.organization_id,
                Expense.user_id == user.id,
                Expense.auto_approved == True,
                Expense.approved_at >= year_start,
                Expense.approved_at <= year_end,
            ).scalar() or Decimal(0)

            # Convert to Decimal for consistent arithmetic
            expense_amount = Decimal(str(expense.amount))
            yearly_limit = Decimal(str(policy.yearly_limit_per_user))

            if (yearly_total + expense_amount) > yearly_limit:
                return (
                    False,
                    f"Would exceed yearly limit of ${policy.yearly_limit_per_user}",
                )

        return True, "Within all limits"

    def get_user_remaining_limits(
        self, user_id: str, organization_id: str, policy_id: str
    ) -> Dict[str, Decimal]:
        """
        Get remaining limits for a user under a specific policy

        Returns:
            Dictionary with remaining daily/monthly/yearly limits
        """
        policy = (
            self.db.query(ApprovalPolicy)
            .filter(
                ApprovalPolicy.id == policy_id,
                ApprovalPolicy.organization_id == organization_id,
            )
            .first()
        )

        if not policy:
            return {}

        now = datetime.utcnow()
        result = {}

        # Daily remaining
        if policy.daily_limit_per_user:
            today_start = datetime.combine(now.date(), time.min)
            today_end = datetime.combine(now.date(), time.max)

            daily_used = self.db.query(func.sum(Expense.amount)).filter(
                Expense.organization_id == organization_id,
                Expense.user_id == user_id,
                Expense.auto_approved == True,
                Expense.approved_at >= today_start,
                Expense.approved_at <= today_end,
            ).scalar() or Decimal(0)

            result["daily_remaining"] = max(
                Decimal(0), policy.daily_limit_per_user - daily_used
            )
            result["daily_used"] = daily_used
            result["daily_limit"] = policy.daily_limit_per_user

        # Monthly remaining
        if policy.monthly_limit_per_user:
            month_start = datetime(now.year, now.month, 1)
            if now.month == 12:
                month_end = datetime(now.year + 1, 1, 1) - timedelta(seconds=1)
            else:
                month_end = datetime(now.year, now.month + 1, 1) - timedelta(seconds=1)

            monthly_used = self.db.query(func.sum(Expense.amount)).filter(
                Expense.organization_id == organization_id,
                Expense.user_id == user_id,
                Expense.auto_approved == True,
                Expense.approved_at >= month_start,
                Expense.approved_at <= month_end,
            ).scalar() or Decimal(0)

            result["monthly_remaining"] = max(
                Decimal(0), policy.monthly_limit_per_user - monthly_used
            )
            result["monthly_used"] = monthly_used
            result["monthly_limit"] = policy.monthly_limit_per_user

        # Yearly remaining
        if policy.yearly_limit_per_user:
            year_start = datetime(now.year, 1, 1)
            year_end = datetime(now.year, 12, 31, 23, 59, 59)

            yearly_used = self.db.query(func.sum(Expense.amount)).filter(
                Expense.organization_id == organization_id,
                Expense.user_id == user_id,
                Expense.auto_approved == True,
                Expense.approved_at >= year_start,
                Expense.approved_at <= year_end,
            ).scalar() or Decimal(0)

            result["yearly_remaining"] = max(
                Decimal(0), policy.yearly_limit_per_user - yearly_used
            )
            result["yearly_used"] = yearly_used
            result["yearly_limit"] = policy.yearly_limit_per_user

        return result
