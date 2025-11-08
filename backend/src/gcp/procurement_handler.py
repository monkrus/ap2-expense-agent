"""
GCP Marketplace Procurement Handler
Handles new customer signups from Google Cloud Marketplace
"""

import secrets
import string
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..email_service import EmailService
from ..models import (Organization, OrganizationMember, OrganizationRole, User,
                      UserRole)
from ..models_billing import BillingEvent, OrganizationSubscription


def generate_secure_password(length: int = 16) -> str:
    """Generate a secure random password"""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    password = "".join(secrets.choice(alphabet) for _ in range(length))
    return password


def generate_slug(name: str) -> str:
    """Generate URL-friendly slug from organization name"""
    import re

    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    # Add random suffix to ensure uniqueness
    slug = f"{slug}-{secrets.token_hex(4)}"
    return slug


async def handle_procurement_webhook(webhook_data: Dict, db: Session) -> Dict:
    """
    Handle new customer signup from GCP Marketplace

    This is called when a company clicks "Subscribe" on GCP Marketplace.

    Args:
        webhook_data: Webhook payload from Google
        {
            "entitlement_id": "ent_abc123",
            "account_id": "acct_456",
            "plan": "professional",
            "user_email": "admin@company.com",
            "company_name": "Acme Corp",
            "state": "ACTIVE"
        }
        db: Database session

    Returns:
        Dict with organization_id, admin_user_id, status

    Process:
        1. Create Organization (company = tenant)
        2. Create admin User (or link existing)
        3. Add admin as Organization OWNER
        4. Create Subscription linked to GCP entitlement
        5. Send welcome email with temporary password
        6. Log billing event
    """

    try:
        # Extract data from webhook
        entitlement_id = webhook_data.get("entitlement_id")
        account_id = webhook_data.get("account_id")
        plan = webhook_data.get("plan", "professional")  # Default to professional
        admin_email = webhook_data.get("user_email")
        company_name = webhook_data.get("company_name", "New Organization")

        # Validate required fields
        if not entitlement_id or not admin_email:
            raise ValueError("Missing required fields: entitlement_id or user_email")

        # Check if organization already exists for this entitlement
        existing_sub = (
            db.query(OrganizationSubscription)
            .filter_by(gcp_entitlement_id=entitlement_id)
            .first()
        )

        if existing_sub:
            # Organization already created, return existing info
            return {
                "status": "already_exists",
                "organization_id": existing_sub.organization_id,
                "message": "Organization already provisioned for this entitlement",
            }

        # === Step 1: Create Organization ===
        org_id = str(uuid.uuid4())
        organization = Organization(
            id=org_id,
            name=company_name,
            slug=generate_slug(company_name),
            description=f"Organization created via Google Cloud Marketplace",
            currency="USD",
            timezone="UTC",
            max_members=get_tier_max_members(plan),
            is_active=True,
        )
        db.add(organization)
        db.flush()

        # === Step 2: Create or find admin user ===
        admin_user = db.query(User).filter_by(email=admin_email).first()
        temp_password = None

        if not admin_user:
            # Create new admin user
            temp_password = generate_secure_password()
            from ..auth import AuthService

            admin_user = User(
                id=str(uuid.uuid4()),
                email=admin_email,
                username=admin_email.split("@")[0],
                hashed_password=AuthService.hash_password(temp_password),
                full_name=admin_email.split("@")[0].replace(".", " ").title(),
                role=UserRole.ADMIN,
                is_active=True,
                is_verified=True,  # Auto-verify GCP users
                created_at=datetime.utcnow(),
            )
            db.add(admin_user)
            db.flush()

        # === Step 3: Add admin as Organization OWNER ===
        membership = OrganizationMember(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            user_id=admin_user.id,
            role=OrganizationRole.OWNER,
            is_active=True,
            joined_at=datetime.utcnow(),
        )
        db.add(membership)

        # === Step 4: Create Subscription linked to GCP ===
        subscription = OrganizationSubscription(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            tier_id=plan,
            tier_name=plan,
            gcp_account_id=account_id,
            gcp_entitlement_id=entitlement_id,
            marketplace_order_id=webhook_data.get("order_id"),
            status="active",
            billing_period_start=datetime.utcnow(),
            billing_period_end=datetime.utcnow() + timedelta(days=30),
            next_billing_date=datetime.utcnow() + timedelta(days=30),
            is_trial=False,  # GCP handles trials
            metadata={
                "source": "gcp_marketplace",
                "provisioned_at": datetime.utcnow().isoformat(),
                "initial_plan": plan,
            },
            created_at=datetime.utcnow(),
        )
        db.add(subscription)

        # === Step 5: Log billing event ===
        billing_event = BillingEvent(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            event_type="gcp_procurement_created",
            event_data={
                "entitlement_id": entitlement_id,
                "account_id": account_id,
                "plan": plan,
                "admin_email": admin_email,
                "company_name": company_name,
            },
            status="success",
            occurred_at=datetime.utcnow(),
        )
        db.add(billing_event)

        # Commit all changes
        db.commit()
        db.refresh(organization)
        db.refresh(admin_user)

        # === Step 6: Send welcome email ===
        try:
            email_service = EmailService()
            await send_gcp_welcome_email(
                email_service,
                admin_email,
                company_name,
                organization.slug,
                temp_password,  # Only included if new user
            )
        except Exception as email_error:
            # Log but don't fail the entire process
            print(f"Failed to send welcome email: {email_error}")

        return {
            "status": "created",
            "organization_id": org_id,
            "organization_name": company_name,
            "organization_slug": organization.slug,
            "admin_user_id": admin_user.id,
            "admin_email": admin_email,
            "subscription_id": subscription.id,
            "tier": plan,
            "message": "Organization successfully provisioned",
        }

    except IntegrityError as e:
        db.rollback()
        # Handle unique constraint violations
        raise ValueError(f"Database integrity error: {str(e)}")

    except Exception as e:
        db.rollback()
        # Log error
        try:
            error_event = BillingEvent(
                id=str(uuid.uuid4()),
                organization_id=webhook_data.get("company_name", "unknown"),
                event_type="gcp_procurement_failed",
                event_data=webhook_data,
                status="failed",
                error_message=str(e),
                occurred_at=datetime.utcnow(),
            )
            db.add(error_event)
            db.commit()
        except:
            pass

        raise


async def send_gcp_welcome_email(
    email_service: EmailService,
    admin_email: str,
    company_name: str,
    org_slug: str,
    temp_password: Optional[str] = None,
):
    """
    Send welcome email to new GCP Marketplace customer
    """

    app_url = settings.frontend_url or "https://your-app.run.app"
    login_url = f"{app_url}/login"

    if temp_password:
        # New user - include temporary password
        subject = f"Welcome to AP2 Expense Agent - {company_name}"
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h1 style="color: #4F46E5;">Welcome to AP2 Expense Agent!</h1>

            <p>Hi there,</p>

            <p>Your organization <strong>{company_name}</strong> has been successfully provisioned via Google Cloud Marketplace!</p>

            <h2 style="color: #4F46E5;">Your Account Details</h2>
            <div style="background: #F3F4F6; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>Email:</strong> {admin_email}</p>
                <p><strong>Temporary Password:</strong> <code style="background: white; padding: 5px 10px; border-radius: 3px;">{temp_password}</code></p>
                <p><strong>Organization:</strong> {company_name} ({org_slug})</p>
            </div>

            <h2 style="color: #4F46E5;">Next Steps</h2>
            <ol>
                <li>Log in to your account: <a href="{login_url}" style="color: #4F46E5;">{login_url}</a></li>
                <li>Change your password immediately after first login</li>
                <li>Complete your organization setup (invite team members, configure workflows)</li>
                <li>Start submitting expenses!</li>
            </ol>

            <div style="background: #EFF6FF; padding: 15px; border-left: 4px solid #4F46E5; margin: 20px 0;">
                <p><strong>🚀 Pro Tip:</strong> Use the bulk invite feature to add your entire team via CSV upload!</p>
            </div>

            <h2 style="color: #4F46E5;">Need Help?</h2>
            <p>Check out our documentation or contact support:</p>
            <ul>
                <li>📚 Documentation: <a href="{app_url}/docs">Getting Started Guide</a></li>
                <li>💬 Support: support@ap2expense.com</li>
            </ul>

            <p style="margin-top: 30px;">Best regards,<br>
            The AP2 Expense Agent Team</p>

            <hr style="border: none; border-top: 1px solid #E5E7EB; margin: 30px 0;">
            <p style="font-size: 12px; color: #6B7280;">
                This organization was created via Google Cloud Marketplace.
                To manage your subscription, visit the <a href="https://console.cloud.google.com/marketplace">GCP Console</a>.
            </p>
        </body>
        </html>
        """
    else:
        # Existing user - no password needed
        subject = f"You've been added to {company_name} on AP2 Expense Agent"
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h1 style="color: #4F46E5;">New Organization Created!</h1>

            <p>Hi there,</p>

            <p>Good news! Your organization <strong>{company_name}</strong> has been provisioned via Google Cloud Marketplace.</p>

            <p>You've been added as the <strong>Organization Owner</strong> with full administrative access.</p>

            <h2 style="color: #4F46E5;">Get Started</h2>
            <p>Log in with your existing credentials: <a href="{login_url}" style="color: #4F46E5;">{login_url}</a></p>

            <h2 style="color: #4F46E5;">Next Steps</h2>
            <ol>
                <li>Switch to your new organization: {company_name}</li>
                <li>Complete organization setup</li>
                <li>Invite your team members</li>
                <li>Configure expense approval workflows</li>
            </ol>

            <p style="margin-top: 30px;">Best regards,<br>
            The AP2 Expense Agent Team</p>
        </body>
        </html>
        """

    await email_service.send_email(to_email=admin_email, subject=subject, body=body)


def get_tier_max_members(tier: str) -> int:
    """Get max members limit for a tier"""
    # Tier member limits
    tier_limits = {
        "free": 5,
        "starter": 25,
        "professional": 100,
        "enterprise": 10000,  # Effectively unlimited
    }
    return tier_limits.get(tier.lower(), 25)
