"""
GCP Marketplace Entitlement Handler
Handles tier changes and cancellations from Google Cloud Marketplace
"""

import uuid
from datetime import datetime
from typing import Dict
from sqlalchemy.orm import Session

from ..models import Organization
from ..models_billing import OrganizationSubscription, BillingEvent
from ..email_service import EmailService
from ..config import settings


async def handle_entitlement_update(
    webhook_data: Dict,
    db: Session
) -> Dict:
    """
    Handle tier upgrade/downgrade from GCP Marketplace

    This is called when a customer changes their plan in GCP Console.

    Args:
        webhook_data: Webhook payload from Google
        {
            "entitlement_id": "ent_abc123",
            "account_id": "acct_456",
            "new_plan": "enterprise",
            "old_plan": "professional",
            "effective_at": "2025-10-31T12:00:00Z"
        }
        db: Database session

    Returns:
        Dict with status, old_tier, new_tier

    Process:
        1. Find subscription by entitlement_id
        2. Update tier in database
        3. Update organization limits
        4. Log billing event
        5. Send notification email to org owner
    """

    try:
        entitlement_id = webhook_data.get("entitlement_id")
        new_plan = webhook_data.get("new_plan")
        old_plan = webhook_data.get("old_plan")

        if not entitlement_id or not new_plan:
            raise ValueError("Missing required fields: entitlement_id or new_plan")

        # === Step 1: Find subscription ===
        subscription = db.query(OrganizationSubscription).filter_by(
            gcp_entitlement_id=entitlement_id
        ).first()

        if not subscription:
            raise ValueError(f"Subscription not found for entitlement {entitlement_id}")

        organization_id = subscription.organization_id
        old_tier = subscription.tier_name

        # === Step 2: Update subscription tier ===
        subscription.tier_name = new_plan
        subscription.tier_id = new_plan
        subscription.updated_at = datetime.utcnow()

        # Update metadata
        metadata = subscription.metadata or {}
        if not isinstance(metadata, dict):
            import json
            metadata = json.loads(metadata) if isinstance(metadata, str) else {}

        metadata["tier_changes"] = metadata.get("tier_changes", [])
        metadata["tier_changes"].append({
            "from": old_tier,
            "to": new_plan,
            "changed_at": datetime.utcnow().isoformat(),
            "source": "gcp_marketplace"
        })
        subscription.metadata = metadata

        # === Step 3: Update organization limits ===
        organization = db.query(Organization).filter_by(id=organization_id).first()
        if organization:
            organization.max_members = get_tier_max_members(new_plan)
            organization.max_expenses_per_month = get_tier_max_expenses(new_plan)

        # === Step 4: Log billing event ===
        billing_event = BillingEvent(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            event_type="gcp_tier_changed",
            event_data={
                "entitlement_id": entitlement_id,
                "old_tier": old_tier,
                "new_tier": new_plan,
                "effective_at": webhook_data.get("effective_at")
            },
            status="success",
            occurred_at=datetime.utcnow()
        )
        db.add(billing_event)

        db.commit()

        # === Step 5: Send notification email ===
        try:
            email_service = EmailService()
            await send_tier_change_email(
                email_service,
                organization_id,
                organization.name if organization else "Your Organization",
                old_tier,
                new_plan,
                db
            )
        except Exception as email_error:
            print(f"Failed to send tier change email: {email_error}")

        return {
            "status": "updated",
            "organization_id": organization_id,
            "old_tier": old_tier,
            "new_tier": new_plan,
            "message": f"Subscription upgraded from {old_tier} to {new_plan}"
        }

    except Exception as e:
        db.rollback()

        # Log error
        try:
            error_event = BillingEvent(
                id=str(uuid.uuid4()),
                organization_id=webhook_data.get("entitlement_id", "unknown"),
                event_type="gcp_tier_change_failed",
                event_data=webhook_data,
                status="failed",
                error_message=str(e),
                occurred_at=datetime.utcnow()
            )
            db.add(error_event)
            db.commit()
        except:
            pass

        raise


async def handle_entitlement_cancellation(
    webhook_data: Dict,
    db: Session
) -> Dict:
    """
    Handle subscription cancellation from GCP Marketplace

    This is called when a customer cancels their subscription.

    Args:
        webhook_data: Webhook payload from Google
        {
            "entitlement_id": "ent_abc123",
            "account_id": "acct_456",
            "cancellation_reason": "customer_requested",
            "effective_at": "2025-11-30T23:59:59Z"
        }
        db: Database session

    Returns:
        Dict with status, organization_id

    Process:
        1. Find subscription by entitlement_id
        2. Update status to "cancelled"
        3. Set grace period (7 days to export data)
        4. Deactivate organization (but don't delete)
        5. Log billing event
        6. Send cancellation email
    """

    try:
        entitlement_id = webhook_data.get("entitlement_id")
        cancellation_reason = webhook_data.get("cancellation_reason", "customer_requested")

        if not entitlement_id:
            raise ValueError("Missing required field: entitlement_id")

        # === Step 1: Find subscription ===
        subscription = db.query(OrganizationSubscription).filter_by(
            gcp_entitlement_id=entitlement_id
        ).first()

        if not subscription:
            raise ValueError(f"Subscription not found for entitlement {entitlement_id}")

        organization_id = subscription.organization_id

        # === Step 2: Update subscription status ===
        subscription.status = "cancelled"
        subscription.updated_at = datetime.utcnow()

        # Parse effective date or use now
        effective_at = webhook_data.get("effective_at")
        if effective_at:
            from dateutil import parser
            try:
                cancellation_date = parser.parse(effective_at)
            except:
                cancellation_date = datetime.utcnow()
        else:
            cancellation_date = datetime.utcnow()

        # Update metadata
        metadata = subscription.metadata or {}
        if not isinstance(metadata, dict):
            import json
            metadata = json.loads(metadata) if isinstance(metadata, str) else {}

        metadata["cancellation"] = {
            "cancelled_at": datetime.utcnow().isoformat(),
            "effective_at": cancellation_date.isoformat(),
            "reason": cancellation_reason,
            "source": "gcp_marketplace"
        }
        subscription.metadata = metadata

        # === Step 3: Deactivate organization (soft delete) ===
        # Keep data for 7 days grace period
        organization = db.query(Organization).filter_by(id=organization_id).first()
        if organization:
            organization.is_active = False
            organization.updated_at = datetime.utcnow()

        # === Step 4: Log billing event ===
        billing_event = BillingEvent(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            event_type="gcp_subscription_cancelled",
            event_data={
                "entitlement_id": entitlement_id,
                "reason": cancellation_reason,
                "effective_at": cancellation_date.isoformat()
            },
            status="success",
            occurred_at=datetime.utcnow()
        )
        db.add(billing_event)

        db.commit()

        # === Step 5: Send cancellation email ===
        try:
            email_service = EmailService()
            await send_cancellation_email(
                email_service,
                organization_id,
                organization.name if organization else "Your Organization",
                cancellation_date,
                db
            )
        except Exception as email_error:
            print(f"Failed to send cancellation email: {email_error}")

        return {
            "status": "cancelled",
            "organization_id": organization_id,
            "effective_at": cancellation_date.isoformat(),
            "grace_period_days": 7,
            "message": "Subscription cancelled successfully"
        }

    except Exception as e:
        db.rollback()

        # Log error
        try:
            error_event = BillingEvent(
                id=str(uuid.uuid4()),
                organization_id=webhook_data.get("entitlement_id", "unknown"),
                event_type="gcp_cancellation_failed",
                event_data=webhook_data,
                status="failed",
                error_message=str(e),
                occurred_at=datetime.utcnow()
            )
            db.add(error_event)
            db.commit()
        except:
            pass

        raise


async def send_tier_change_email(
    email_service: EmailService,
    organization_id: str,
    organization_name: str,
    old_tier: str,
    new_tier: str,
    db: Session
):
    """Send email notification about tier change"""

    from ..models import OrganizationMember, User

    # Get organization owners
    owners = db.query(User).join(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.role == "owner",
        OrganizationMember.is_active == True
    ).all()

    app_url = settings.frontend_url or "https://your-app.run.app"

    is_upgrade = tier_priority(new_tier) > tier_priority(old_tier)
    change_type = "upgraded" if is_upgrade else "downgraded"
    emoji = "🎉" if is_upgrade else "📋"

    for owner in owners:
        subject = f"{emoji} Your subscription has been {change_type}"
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h1 style="color: #4F46E5;">{emoji} Subscription {change_type.title()}!</h1>

            <p>Hi there,</p>

            <p>Your subscription for <strong>{organization_name}</strong> has been {change_type}.</p>

            <div style="background: #F3F4F6; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>Previous Plan:</strong> {old_tier.title()}</p>
                <p><strong>New Plan:</strong> {new_tier.title()}</p>
            </div>

            {"<p>🎊 Congratulations! You now have access to more features and higher limits.</p>" if is_upgrade else ""}

            <h2 style="color: #4F46E5;">What's Next?</h2>
            <p>Your new plan features are active immediately. <a href="{app_url}/settings/billing">View your updated limits</a></p>

            <p style="margin-top: 30px;">Best regards,<br>
            The AP2 Expense Agent Team</p>
        </body>
        </html>
        """

        await email_service.send_email(
            to_email=owner.email,
            subject=subject,
            body=body
        )


async def send_cancellation_email(
    email_service: EmailService,
    organization_id: str,
    organization_name: str,
    effective_date: datetime,
    db: Session
):
    """Send email notification about cancellation"""

    from ..models import OrganizationMember, User

    # Get organization owners
    owners = db.query(User).join(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.role == "owner",
        OrganizationMember.is_active == True
    ).all()

    app_url = settings.frontend_url or "https://your-app.run.app"

    for owner in owners:
        subject = f"Your subscription has been cancelled"
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h1 style="color: #EF4444;">Subscription Cancelled</h1>

            <p>Hi there,</p>

            <p>Your subscription for <strong>{organization_name}</strong> has been cancelled via Google Cloud Marketplace.</p>

            <div style="background: #FEF2F2; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #EF4444;">
                <p><strong>Effective Date:</strong> {effective_date.strftime('%B %d, %Y')}</p>
                <p><strong>Grace Period:</strong> 7 days to export your data</p>
            </div>

            <h2 style="color: #EF4444;">Important: Export Your Data</h2>
            <p>You have <strong>7 days</strong> to export all your data before the account is deactivated.</p>

            <ol>
                <li><a href="{app_url}/settings/export">Export expenses and reports</a></li>
                <li><a href="{app_url}/settings/export">Download receipts</a></li>
                <li><a href="{app_url}/settings/export">Export user data</a></li>
            </ol>

            <div style="background: #EFF6FF; padding: 15px; border-left: 4px solid #3B82F6; margin: 20px 0;">
                <p><strong>Changed your mind?</strong></p>
                <p>You can reactivate your subscription anytime within the grace period through the <a href="https://console.cloud.google.com/marketplace">GCP Console</a>.</p>
            </div>

            <p>We're sorry to see you go. If you have any feedback about how we can improve, please let us know.</p>

            <p style="margin-top: 30px;">Best regards,<br>
            The AP2 Expense Agent Team</p>
        </body>
        </html>
        """

        await email_service.send_email(
            to_email=owner.email,
            subject=subject,
            body=body
        )


def get_tier_max_members(tier: str) -> int:
    """Get max members limit for a tier"""
    tier_limits = {
        "free": 5,
        "starter": 25,
        "professional": 100,
        "enterprise": 10000
    }
    return tier_limits.get(tier.lower(), 25)


def get_tier_max_expenses(tier: str) -> int:
    """Get max expenses per month for a tier"""
    tier_limits = {
        "free": 50,
        "starter": 500,
        "professional": None,  # Unlimited
        "enterprise": None  # Unlimited
    }
    return tier_limits.get(tier.lower(), 500)


def tier_priority(tier: str) -> int:
    """Get tier priority for comparison"""
    priorities = {
        "free": 0,
        "starter": 1,
        "professional": 2,
        "enterprise": 3
    }
    return priorities.get(tier.lower(), 0)
