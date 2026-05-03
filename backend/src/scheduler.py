"""
Background scheduler for auto-submitting recurring expenses.
Runs as a background task to process scheduled expense submissions.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import SessionLocal
from src.models import (
    Expense,
    ExpenseNotification,
    ExpenseStatus,
    RecurringExpenseTemplate,
    RecurringFrequency,
    ScheduledExpense,
    User,
)

logger = logging.getLogger(__name__)


class RecurringExpenseScheduler:
    """Scheduler for processing recurring expense auto-submissions"""

    def __init__(self, check_interval: int = 60):
        """
        Initialize the scheduler.

        Args:
            check_interval: How often to check for pending expenses (in seconds)
        """
        self.check_interval = check_interval
        self.running = False
        self.task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the scheduler"""
        if self.running:
            logger.warning("Scheduler is already running")
            return

        self.running = True
        self.task = asyncio.create_task(self._run())
        logger.info(
            f"Recurring expense scheduler started (check interval: {self.check_interval}s)"
        )

    async def stop(self):
        """Stop the scheduler"""
        if not self.running:
            return

        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Recurring expense scheduler stopped")

    async def _run(self):
        """Main scheduler loop"""
        while self.running:
            try:
                await self.process_pending_expenses()
            except Exception as e:
                logger.error(f"Error processing recurring expenses: {e}", exc_info=True)

            # Check if monthly summaries should be sent (1st of month, early morning)
            try:
                await self._check_monthly_summaries()
            except Exception as e:
                logger.error(f"Error checking monthly summaries: {e}", exc_info=True)

            # Wait before next check
            await asyncio.sleep(self.check_interval)

    async def _check_monthly_summaries(self):
        """Send monthly summary emails on the 1st of each month."""
        now = datetime.utcnow()
        # Only run on the 1st, between 06:00-06:05 UTC (within one check interval)
        if now.day != 1 or now.hour != 6 or now.minute >= 10:
            return

        # Use a simple flag to avoid re-sending within the same hour
        month_key = f"{now.year}-{now.month}"
        if getattr(self, "_last_summary_month", None) == month_key:
            return
        self._last_summary_month = month_key

        logger.info(f"Triggering monthly auto-approval summaries for previous month")
        try:
            from src.services.monthly_summary_service import send_all_monthly_summaries
            result = await send_all_monthly_summaries()
            logger.info(f"Monthly summaries result: {result}")
        except Exception as e:
            logger.error(f"Monthly summary sending failed: {e}", exc_info=True)

    async def process_pending_expenses(self):
        """Process all pending recurring expense submissions"""
        async with SessionLocal() as db:
            # Find all active templates that are due for submission
            now = datetime.utcnow()

            stmt = select(RecurringExpenseTemplate).where(
                and_(
                    RecurringExpenseTemplate.is_active == True,
                    RecurringExpenseTemplate.is_paused == False,
                    RecurringExpenseTemplate.next_run_date <= now,
                )
            )

            result = await db.execute(stmt)
            templates = result.scalars().all()

            logger.info(
                f"Found {len(templates)} recurring expense templates due for processing"
            )

            for template in templates:
                try:
                    await self._process_template(db, template)
                except Exception as e:
                    logger.error(
                        f"Error processing template {template.id}: {e}", exc_info=True
                    )

            await db.commit()

    async def _process_template(
        self, db: AsyncSession, template: RecurringExpenseTemplate
    ):
        """
        Process a single recurring expense template.

        Args:
            db: Database session
            template: Recurring expense template to process
        """
        logger.info(f"Processing recurring expense template: {template.id}")

        # Check if template has ended
        if template.end_date and template.end_date < datetime.utcnow():
            template.is_active = False
            logger.info(f"Template {template.id} has ended, marking as inactive")
            return

        # Create scheduled expense record
        scheduled = ScheduledExpense(
            id=f"scheduled_{uuid.uuid4().hex[:16]}",
            template_id=template.id,
            scheduled_date=template.next_run_date,
            status="pending",
        )
        db.add(scheduled)

        try:
            if template.auto_submit:
                # Auto-submit the expense
                expense = await self._submit_expense(db, template)
                scheduled.expense_id = expense.id
                scheduled.status = "submitted"
                scheduled.processed_at = datetime.utcnow()

                # Run auto-approval (same logic as manual expenses)
                try:
                    from src.services.auto_approval_service import evaluate_auto_approval, notify_admins_new_expense
                    user = db.query(User).filter(User.id == template.user_id).first()
                    if user:
                        approval_result = await evaluate_auto_approval(
                            db, expense, user, template.organization_id
                        )
                        if not approval_result.approved:
                            notify_admins_new_expense(db, expense, user, template.organization_id)
                except Exception as e:
                    logger.error(f"Auto-approval check failed for scheduled expense: {e}")

                # Update template statistics
                template.total_submitted += 1
                template.last_submitted_at = datetime.utcnow()

                # Create notification
                await self._create_notification(
                    db,
                    template.user_id,
                    "recurring_submitted",
                    f"Recurring expense auto-submitted: {template.vendor}",
                    f"Your recurring expense for {template.vendor} (${template.amount}) has been automatically submitted.",
                    expense_id=expense.id,
                    template_id=template.id,
                )

                logger.info(
                    f"Auto-submitted expense {expense.id} from template {template.id}"
                )

            else:
                # Just create a notification for manual submission
                await self._create_notification(
                    db,
                    template.user_id,
                    "recurring_reminder",
                    f"Reminder: Recurring expense due - {template.vendor}",
                    f"Your recurring expense for {template.vendor} (${template.amount}) is due. Please submit it manually.",
                    template_id=template.id,
                )
                scheduled.status = "skipped"
                scheduled.processed_at = datetime.utcnow()

        except Exception as e:
            logger.error(f"Error submitting expense for template {template.id}: {e}")
            scheduled.status = "failed"
            scheduled.error_message = str(e)
            scheduled.processed_at = datetime.utcnow()

        # Calculate next run date
        template.next_run_date = self._calculate_next_run_date(
            template.next_run_date, template.frequency
        )

        logger.info(
            f"Next run date for template {template.id}: {template.next_run_date}"
        )

    async def _submit_expense(
        self, db: AsyncSession, template: RecurringExpenseTemplate
    ) -> Expense:
        """
        Submit an expense from a template.

        Args:
            db: Database session
            template: Recurring expense template

        Returns:
            Created expense
        """
        expense = Expense(
            id=f"EXP-{uuid.uuid4().hex[:12].upper()}",
            organization_id=template.organization_id,
            user_id=template.user_id,
            amount=template.amount,
            vendor=template.vendor,
            category=template.category,
            description=f"{template.description} (Auto-submitted from recurring template)",
            status=ExpenseStatus.PENDING,
            date=datetime.utcnow(),
            intent_mandate_id=template.intent_mandate_id,
        )

        db.add(expense)
        return expense

    async def _create_notification(
        self,
        db: AsyncSession,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        expense_id: Optional[str] = None,
        template_id: Optional[str] = None,
    ):
        """Create a notification for the user"""
        notification = ExpenseNotification(
            id=f"notif_{uuid.uuid4().hex[:16]}",
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            expense_id=expense_id,
            template_id=template_id,
        )
        db.add(notification)

    def _calculate_next_run_date(
        self, current_date: datetime, frequency: RecurringFrequency
    ) -> datetime:
        """
        Calculate the next run date based on frequency.

        Args:
            current_date: Current scheduled date
            frequency: Recurrence frequency

        Returns:
            Next scheduled date
        """
        if frequency == RecurringFrequency.WEEKLY:
            return current_date + timedelta(days=7)
        elif frequency == RecurringFrequency.BIWEEKLY:
            return current_date + timedelta(days=14)
        elif frequency == RecurringFrequency.MONTHLY:
            # Add one month (approximately)
            next_month = current_date.month + 1
            next_year = current_date.year
            if next_month > 12:
                next_month = 1
                next_year += 1
            return current_date.replace(year=next_year, month=next_month)
        elif frequency == RecurringFrequency.QUARTERLY:
            # Add 3 months
            next_month = current_date.month + 3
            next_year = current_date.year
            while next_month > 12:
                next_month -= 12
                next_year += 1
            return current_date.replace(year=next_year, month=next_month)
        elif frequency == RecurringFrequency.YEARLY:
            return current_date.replace(year=current_date.year + 1)
        else:
            # Default to monthly
            return current_date + timedelta(days=30)


# Global scheduler instance
_scheduler: Optional[RecurringExpenseScheduler] = None


async def get_scheduler() -> RecurringExpenseScheduler:
    """Get or create the global scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = RecurringExpenseScheduler(
            check_interval=300
        )  # Check every 5 minutes
    return _scheduler


async def start_scheduler():
    """Start the global scheduler"""
    scheduler = await get_scheduler()
    await scheduler.start()


async def stop_scheduler():
    """Stop the global scheduler"""
    if _scheduler:
        await _scheduler.stop()
