"""
Shared auto-approval logic for expenses.

Evaluates expenses against:
  Tier 1: AP2 Intent Mandates (Premium)
  Tier 2: Approval Policies (Free)

Used by: manual expense creation, recurring expense creation, and the scheduler.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from ..models import (
    Expense,
    ExpenseStatus,
    Notification,
    NotificationType,
    OrganizationMember,
    OrganizationRole,
    User,
)

logger = logging.getLogger(__name__)


class AutoApprovalResult:
    def __init__(self):
        self.approved = False
        self.via: Optional[str] = None  # "intent_mandate" or "approval_policy"
        self.mandate_id: Optional[str] = None
        self.policy_id: Optional[str] = None
        self.message: Optional[str] = None


async def evaluate_auto_approval(
    db: Session,
    expense: Expense,
    user: User,
    org_id: str,
) -> AutoApprovalResult:
    """
    Run the two-tier auto-approval check on an expense.
    Modifies the expense in-place if auto-approved.
    Caller is responsible for committing the transaction.
    """
    result = AutoApprovalResult()

    # TIER 1: AP2 INTENT MANDATE AUTO-APPROVAL (Premium Feature)
    try:
        from ..payments.ap2_service import AP2PaymentService

        ap2_service = AP2PaymentService(db)

        category_str = expense.category.value if hasattr(expense.category, 'value') else str(expense.category)

        matching_mandate = ap2_service.find_matching_intent_mandate(
            user_id=user.id,
            amount=float(expense.amount),
            category=category_str,
            merchant=expense.vendor,
            organization_id=org_id,
        )

        if matching_mandate:
            logger.info(f"[AP2] Auto-approving expense {expense.id} via Intent Mandate {matching_mandate.id}")

            cart_items = [{
                "description": expense.description or f"Expense: {expense.vendor}",
                "amount": float(expense.amount),
                "vendor": expense.vendor or "Unknown Vendor",
                "category": category_str,
            }]

            now = datetime.utcnow()
            agent_signature = ap2_service._generate_signature(
                user.id,
                {"items": cart_items, "merchant": expense.vendor or "Unknown Vendor"},
                now,
            )

            cart_mandate = await ap2_service.create_cart_mandate(
                intent_mandate_id=matching_mandate.id,
                items=cart_items,
                merchant=expense.vendor or "Unknown Vendor",
                user_signature=agent_signature,
            )

            payment_mandate = await ap2_service.create_payment_mandate(
                cart_mandate_id=cart_mandate.id,
                payment_method="expense_reimbursement",
            )

            expense.status = ExpenseStatus.APPROVED
            expense.approved_by = "ai_agent"
            expense.approved_at = datetime.utcnow()
            expense.auto_approved = True
            expense.auto_approved_via = "intent_mandate"
            expense.intent_mandate_id = matching_mandate.id
            expense.cart_mandate_id = cart_mandate.id
            expense.payment_mandate_id = payment_mandate.id

            # Check if monthly_limit is exhausted
            try:
                constraints = json.loads(matching_mandate.constraints)
                monthly_limit = constraints.get("monthly_limit")
                if monthly_limit:
                    current_usage = ap2_service._get_mandate_monthly_usage(matching_mandate.id, org_id)
                    if current_usage >= float(monthly_limit):
                        matching_mandate.status = "exhausted"
                        db.add(matching_mandate)
                        logger.info(f"[AP2] Intent Mandate {matching_mandate.id} exhausted")
            except Exception as e:
                logger.error(f"[AP2] Failed to check mandate exhaustion: {e}")

            # Send auto-approval notification to user
            try:
                notification = Notification(
                    id=str(uuid.uuid4()),
                    user_id=user.id,
                    organization_id=org_id,
                    notification_type=NotificationType.EXPENSE_APPROVED,
                    title="Expense Auto-Approved by AI",
                    message=f"Your ${float(expense.amount):.2f} expense for {expense.vendor or 'Unknown vendor'} was auto-approved by AI agent via Intent Mandate",
                    expense_id=expense.id,
                    is_read=False,
                    created_at=datetime.utcnow(),
                )
                db.add(notification)
            except Exception as e:
                logger.error(f"Failed to create AP2 auto-approval notification: {e}")

            # Send email notification (async, non-blocking)
            try:
                _send_auto_approval_email(user, expense, "intent_mandate", matching_mandate)
            except Exception as e:
                logger.error(f"Failed to queue auto-approval email: {e}")

            result.approved = True
            result.via = "intent_mandate"
            result.mandate_id = matching_mandate.id
            result.message = "Auto-approved by AI agent via Intent Mandate (AP2)"
            return result

    except ImportError:
        logger.debug("AP2 service not available, skipping Intent Mandate check")
    except Exception as e:
        logger.error(f"[AP2] Intent Mandate evaluation failed (non-blocking): {e}")

    # TIER 2: APPROVAL POLICY AUTO-APPROVAL (Free Feature)
    try:
        from ..services.approval_policy_service import ApprovalPolicyService

        policy_service = ApprovalPolicyService(db)
        should_auto_approve, matching_policy, reason = policy_service.evaluate_expense(
            expense, user
        )

        if should_auto_approve and matching_policy:
            logger.info(f"Auto-approving expense {expense.id} via Approval Policy {matching_policy.id}")

            expense.status = ExpenseStatus.APPROVED
            expense.approved_by = user.id
            expense.approved_at = datetime.utcnow()
            expense.auto_approved = True
            expense.auto_approved_via = "approval_policy"
            expense.approval_policy_id = matching_policy.id

            # Send notification if policy has notify_on_auto_approve enabled
            if matching_policy.notify_on_auto_approve:
                try:
                    notification = Notification(
                        id=str(uuid.uuid4()),
                        user_id=user.id,
                        organization_id=org_id,
                        notification_type=NotificationType.EXPENSE_APPROVED,
                        title="Expense Auto-Approved",
                        message=f"Your ${float(expense.amount):.2f} expense for {expense.vendor or 'Unknown vendor'} was automatically approved by rule: {matching_policy.name}",
                        expense_id=expense.id,
                        is_read=False,
                        created_at=datetime.utcnow(),
                    )
                    db.add(notification)
                    logger.info(f"Notification sent for auto-approved expense {expense.id}")
                except Exception as e:
                    logger.error(f"Failed to create auto-approval notification: {e}")

            # Send email notification (async, non-blocking)
            try:
                _send_auto_approval_email(user, expense, "approval_policy")
            except Exception as e:
                logger.error(f"Failed to queue policy auto-approval email: {e}")

            result.approved = True
            result.via = "approval_policy"
            result.policy_id = matching_policy.id
            result.message = f"Auto-approved by policy: {matching_policy.name}"
            return result

    except ImportError:
        logger.debug("Approval policy service not available")
    except Exception as e:
        logger.error(f"Auto-approval evaluation failed: {e}")

    return result


def _send_auto_approval_email(user: User, expense, approval_via: str, mandate=None):
    """Queue an auto-approval email to the user (fire-and-forget)."""
    import asyncio
    try:
        from ..email_service import EmailService
        from ..email_templates import get_auto_approved_email

        if not user.email:
            return

        expense_data = {
            "amount": float(expense.amount),
            "vendor": expense.vendor or "Unknown",
            "category": expense.category.value if hasattr(expense.category, "value") else str(expense.category),
            "description": expense.description or "",
            "date": str(expense.date) if expense.date else "",
        }

        mandate_details = None
        if mandate:
            try:
                import json as _json
                constraints = _json.loads(mandate.constraints) if isinstance(mandate.constraints, str) else {}
            except Exception:
                constraints = {}
            mandate_details = {
                "name": getattr(mandate, "description", "") or "Intent Mandate",
                "constraints": {k: v for k, v in constraints.items() if not k.startswith("@")},
            }

        subject, html_body, text_body = get_auto_approved_email(
            expense_data, approval_via, mandate_details
        )

        # Schedule the async email send without blocking
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(EmailService.send_email(user.email, subject, html_body=html_body, text_body=text_body))
        except RuntimeError:
            # No running loop -- skip email silently
            logger.debug("No event loop available for auto-approval email")

    except Exception as e:
        logger.error(f"Auto-approval email preparation failed: {e}")


def notify_admins_new_expense(
    db: Session,
    expense: Expense,
    user: User,
    org_id: str,
):
    """Send notifications to admins/owners about a new pending expense."""
    try:
        admin_members = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.role.in_([
                    OrganizationRole.ADMIN.value,
                    OrganizationRole.OWNER.value,
                ]),
                OrganizationMember.is_active == True,
            )
            .all()
        )

        display_name = user.full_name or user.username or user.email

        for member in admin_members:
            if member.user_id == user.id:
                continue
            notification = Notification(
                id=str(uuid.uuid4()),
                user_id=member.user_id,
                organization_id=org_id,
                notification_type=NotificationType.EXPENSE_SUBMITTED,
                title="New Expense Submitted",
                message=f"{display_name} submitted a ${float(expense.amount):.2f} expense for {expense.vendor or 'Unknown vendor'} - awaiting approval",
                expense_id=expense.id,
                is_read=False,
                created_at=datetime.utcnow(),
            )
            db.add(notification)
    except Exception as e:
        logger.error(f"Failed to create admin notifications: {e}", exc_info=True)
