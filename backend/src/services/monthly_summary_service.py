"""
Monthly auto-approval summary email service.

Gathers per-user statistics for a given month and sends a digest email
showing auto-approval rates, time saved, and top vendors.

Can be triggered via:
  - API endpoint: POST /api/ap2/send-monthly-summary
  - Scheduler: call send_all_monthly_summaries() on the 1st of each month
"""

import logging
from calendar import monthrange
from collections import defaultdict
from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Expense, ExpenseStatus, OrganizationMember, User

logger = logging.getLogger(__name__)

MINUTES_SAVED_PER_AUTO_APPROVAL = 3  # conservative estimate


def _get_month_range(year: int, month: int):
    """Return (start, end) datetimes for a calendar month."""
    start = datetime(year, month, 1)
    _, last_day = monthrange(year, month)
    end = datetime(year, month, last_day, 23, 59, 59)
    return start, end


def gather_user_monthly_stats(
    db: Session,
    user_id: str,
    year: int,
    month: int,
) -> Optional[dict]:
    """
    Gather auto-approval statistics for a single user in a given month.
    Returns None if the user had no expenses that month.
    """
    start, end = _get_month_range(year, month)

    expenses = (
        db.query(Expense)
        .filter(
            Expense.user_id == user_id,
            Expense.created_at >= start,
            Expense.created_at <= end,
        )
        .all()
    )

    if not expenses:
        return None

    total = len(expenses)
    auto_approved = [e for e in expenses if e.auto_approved]
    auto_count = len(auto_approved)
    by_mandate = sum(
        1 for e in auto_approved if e.auto_approved_via == "intent_mandate"
    )
    by_policy = sum(
        1 for e in auto_approved if e.auto_approved_via == "approval_policy"
    )
    manual_count = total - auto_count

    total_amount = sum(float(e.amount) for e in expenses)
    auto_amount = sum(float(e.amount) for e in auto_approved)

    rate = (auto_count / total * 100) if total > 0 else 0
    time_saved = auto_count * MINUTES_SAVED_PER_AUTO_APPROVAL

    # Top vendors by auto-approved count
    vendor_stats = defaultdict(lambda: {"count": 0, "amount": 0.0})
    for e in auto_approved:
        vendor = e.vendor or "Unknown"
        vendor_stats[vendor]["count"] += 1
        vendor_stats[vendor]["amount"] += float(e.amount)

    top_vendors = sorted(
        [{"vendor": k, **v} for k, v in vendor_stats.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:5]

    user = db.query(User).filter(User.id == user_id).first()
    user_name = (user.full_name or user.username or "there") if user else "there"

    month_label = datetime(year, month, 1).strftime("%B %Y")

    return {
        "user_id": user_id,
        "user_email": user.email if user else None,
        "user_name": user_name,
        "month_label": month_label,
        "total_expenses": total,
        "auto_approved_count": auto_count,
        "manual_count": manual_count,
        "auto_approval_rate": rate,
        "total_amount": total_amount,
        "auto_approved_amount": auto_amount,
        "time_saved_minutes": time_saved,
        "by_mandate_count": by_mandate,
        "by_policy_count": by_policy,
        "top_vendors": top_vendors,
    }


async def send_user_monthly_summary(
    db: Session,
    user_id: str,
    year: int,
    month: int,
) -> Optional[dict]:
    """
    Gather stats and send the monthly summary email for one user.
    Returns the summary dict if sent, None if user had no expenses.
    """
    summary = gather_user_monthly_stats(db, user_id, year, month)
    if not summary or not summary.get("user_email"):
        return None

    # Only send if there were auto-approved expenses (no spam for zero activity)
    if summary["auto_approved_count"] == 0:
        return summary  # return stats but don't email

    try:
        from ..email_service import EmailService
        from ..email_templates import get_monthly_auto_approval_summary_email

        subject, html_body, text_body = get_monthly_auto_approval_summary_email(summary)
        await EmailService.send_email(
            summary["user_email"],
            subject,
            html_body=html_body,
            text_body=text_body,
        )
        logger.info(
            f"Monthly summary sent to user {summary['user_id']} for {summary['month_label']}"
        )
    except Exception as e:
        logger.error(
            f"Failed to send monthly summary to user {summary.get('user_id')}: {e}"
        )

    return summary


async def send_all_monthly_summaries(
    year: Optional[int] = None,
    month: Optional[int] = None,
    organization_id: Optional[str] = None,
) -> dict:
    """
    Send monthly summary emails to users who had expenses.
    Scoped to organization_id when provided.
    Defaults to the previous month.

    Returns: {"sent": int, "skipped": int, "errors": int}
    """
    if year is None or month is None:
        now = datetime.utcnow()
        # Default to previous month
        if now.month == 1:
            year = now.year - 1
            month = 12
        else:
            year = now.year
            month = now.month - 1

    start, end = _get_month_range(year, month)
    db = SessionLocal()
    stats = {"sent": 0, "skipped": 0, "errors": 0}

    try:
        # Find users who had expenses in the target month, scoped to org
        query = db.query(Expense.user_id).filter(
            Expense.created_at >= start,
            Expense.created_at <= end,
        )
        if organization_id:
            query = query.filter(Expense.organization_id == organization_id)
        user_ids = query.distinct().all()

        logger.info(
            f"Sending monthly summaries for {datetime(year, month, 1).strftime('%B %Y')} to {len(user_ids)} users"
        )

        for (uid,) in user_ids:
            try:
                result = await send_user_monthly_summary(db, uid, year, month)
                if result and result["auto_approved_count"] > 0:
                    stats["sent"] += 1
                else:
                    stats["skipped"] += 1
            except Exception as e:
                logger.error(f"Error sending summary to user {uid}: {e}")
                stats["errors"] += 1

    finally:
        db.close()

    logger.info(f"Monthly summary complete: {stats}")
    return stats
