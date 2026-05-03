"""
AI Pattern Detection for Intent Mandate Suggestions.

Analyzes a user's expense history to detect recurring vendors/categories
and suggest Intent Mandates that would auto-approve similar expenses.
"""

import logging
import math
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import Expense, ExpenseStatus, IntentMandate

logger = logging.getLogger(__name__)

MIN_EXPENSES_FOR_SUGGESTION = 3  # need at least 3 expenses from same vendor
LOOKBACK_DAYS = 90


def _round_up(value: float, step: float = 25.0) -> float:
    """Round up to nearest step."""
    return math.ceil(value / step) * step


def detect_patterns(
    db: Session,
    user_id: str,
    organization_id: str,
    lookback_days: int = LOOKBACK_DAYS,
) -> List[dict]:
    """
    Analyze a user's recent expenses to find recurring vendor/category
    patterns that could benefit from an Intent Mandate.

    Returns a list of suggestion dicts sorted by potential time savings.
    """
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)

    # Fetch non-auto-approved expenses (these are the ones that could benefit)
    expenses = (
        db.query(Expense)
        .filter(
            Expense.user_id == user_id,
            Expense.organization_id == organization_id,
            Expense.created_at >= cutoff,
            Expense.auto_approved == False,
            Expense.status.in_([
                ExpenseStatus.APPROVED.value,
                ExpenseStatus.PENDING.value,
            ]),
        )
        .all()
    )

    if not expenses:
        return []

    # Group by (vendor_lower, category)
    groups = defaultdict(list)
    for e in expenses:
        vendor = (e.vendor or "").strip().lower()
        category = e.category.value if hasattr(e.category, "value") else str(e.category)
        if vendor:
            groups[(vendor, category)].append(e)

    # Fetch existing active mandates to avoid duplicate suggestions
    existing_mandates = (
        db.query(IntentMandate)
        .filter(
            IntentMandate.user_id == user_id,
            IntentMandate.status == "active",
            IntentMandate.expiration > datetime.utcnow(),
        )
        .all()
    )

    existing_keys = set()
    for m in existing_mandates:
        try:
            import json
            constraints = json.loads(m.constraints)
            constraints = {k: v for k, v in constraints.items() if not k.startswith("@")}
            key = (
                (constraints.get("merchant", "")).strip().lower(),
                (constraints.get("category", "")).strip().lower(),
            )
            existing_keys.add(key)
        except Exception:
            pass

    suggestions = []
    for (vendor, category), exps in groups.items():
        if len(exps) < MIN_EXPENSES_FOR_SUGGESTION:
            continue

        # Skip if a mandate already covers this vendor+category
        if (vendor, category.lower()) in existing_keys:
            continue

        amounts = [float(e.amount) for e in exps]
        max_amount = max(amounts)
        avg_amount = sum(amounts) / len(amounts)
        total_amount = sum(amounts)
        count = len(exps)

        # Calculate suggested constraints with headroom
        suggested_max = _round_up(max_amount * 1.2)
        # Monthly limit: extrapolate from lookback period
        months_in_period = max(lookback_days / 30, 1)
        monthly_rate = total_amount / months_in_period
        suggested_monthly = _round_up(monthly_rate * 1.3)  # 30% buffer
        # Ensure monthly >= max per transaction
        if suggested_monthly < suggested_max:
            suggested_monthly = suggested_max * 2

        # Use original casing from the most recent expense
        original_vendor = exps[-1].vendor or vendor

        # Time saved estimate (3 min per manual approval)
        time_saved_per_month = round(count / months_in_period * 3)

        suggestions.append({
            "vendor": original_vendor,
            "category": category,
            "expense_count": count,
            "avg_amount": round(avg_amount, 2),
            "max_amount": round(max_amount, 2),
            "total_amount": round(total_amount, 2),
            "suggested_constraints": {
                "max_amount": suggested_max,
                "monthly_limit": suggested_monthly,
                "category": category,
                "merchant": original_vendor,
            },
            "estimated_time_saved_minutes_per_month": time_saved_per_month,
            "explanation": (
                f"You've submitted {count} expenses to {original_vendor} "
                f"({category}) in the last {lookback_days} days, averaging "
                f"${avg_amount:.2f} each. Creating this rule would auto-approve "
                f"similar expenses and save ~{time_saved_per_month} min/month."
            ),
        })

    # Sort by expense count (most frequent patterns first)
    suggestions.sort(key=lambda s: s["expense_count"], reverse=True)
    return suggestions
