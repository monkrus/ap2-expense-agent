"""
Customer Onboarding Service
Handles multi-step onboarding flow for new users and organizations
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from ..email_service import EmailService
from ..models import Organization, OrganizationMember, OrganizationRole, User


class OnboardingStep:
    """Onboarding step tracker"""

    ACCOUNT_CREATED = "account_created"
    EMAIL_VERIFIED = "email_verified"
    ORGANIZATION_CREATED = "organization_created"
    TEAM_INVITED = "team_invited"
    FIRST_EXPENSE = "first_expense"
    PAYMENT_METHOD = "payment_method"
    COMPLETED = "completed"


class OnboardingService:
    """Manage customer onboarding flow"""

    def __init__(self, db: Session):
        self.db = db
        self.email_service = EmailService()

    async def start_onboarding(self, user: User) -> Dict:
        """
        Start onboarding flow for new user

        Returns onboarding checklist and next steps
        """
        # Check onboarding progress
        progress = self._get_onboarding_progress(user)

        # Send welcome email
        await self.email_service.send_welcome_email(
            to_email=user.email, username=user.username, full_name=user.full_name
        )

        return {
            "user_id": user.id,
            "current_step": progress["current_step"],
            "completed_steps": progress["completed_steps"],
            "remaining_steps": progress["remaining_steps"],
            "progress_percentage": progress["percentage"],
            "next_action": self._get_next_action(progress["current_step"]),
        }

    def complete_step(self, user: User, step: str) -> Dict:
        """Mark onboarding step as complete"""
        # Update user onboarding metadata
        if not user.onboarding_data:
            user.onboarding_data = {}

        user.onboarding_data[step] = {
            "completed": True,
            "completed_at": datetime.utcnow().isoformat(),
        }

        # Check if all steps completed
        if self._is_onboarding_complete(user):
            user.onboarding_completed = True
            user.onboarding_completed_at = datetime.utcnow()

        self.db.commit()
        return self._get_onboarding_progress(user)

    def create_organization_step(
        self, user: User, org_name: str, org_slug: str
    ) -> Organization:
        """
        Onboarding step: Create organization
        """
        # Create organization
        org = Organization(
            id=f"org_{uuid.uuid4().hex[:12]}",
            name=org_name,
            slug=org_slug,
            created_at=datetime.utcnow(),
            is_active=True,
        )
        self.db.add(org)

        # Add user as owner
        member = OrganizationMember(
            id=f"member_{uuid.uuid4().hex[:12]}",
            organization_id=org.id,
            user_id=user.id,
            role=OrganizationRole.OWNER,
            joined_at=datetime.utcnow(),
        )
        self.db.add(member)
        self.db.commit()

        # Mark step complete
        self.complete_step(user, OnboardingStep.ORGANIZATION_CREATED)

        return org

    async def invite_team_step(
        self, user: User, organization_id: str, email_addresses: List[str]
    ) -> List[str]:
        """
        Onboarding step: Invite team members
        """
        invitation_ids = []

        for email in email_addresses:
            # Send invitation
            invitation_id = await self._send_team_invitation(
                user, organization_id, email
            )
            invitation_ids.append(invitation_id)

        # Mark step complete
        self.complete_step(user, OnboardingStep.TEAM_INVITED)

        return invitation_ids

    def add_payment_method_step(
        self, user: User, stripe_payment_method_id: str
    ) -> Dict:
        """
        Onboarding step: Add payment method
        """
        # Store payment method (integrate with Stripe)
        # This would call StripeService to attach payment method

        # Mark step complete
        self.complete_step(user, OnboardingStep.PAYMENT_METHOD)

        return {"success": True}

    def _get_onboarding_progress(self, user: User) -> Dict:
        """Calculate onboarding progress"""
        all_steps = [
            OnboardingStep.ACCOUNT_CREATED,
            OnboardingStep.EMAIL_VERIFIED,
            OnboardingStep.ORGANIZATION_CREATED,
            OnboardingStep.TEAM_INVITED,
            OnboardingStep.FIRST_EXPENSE,
            OnboardingStep.PAYMENT_METHOD,
        ]

        completed = []
        if user.onboarding_data:
            completed = [
                step
                for step in all_steps
                if user.onboarding_data.get(step, {}).get("completed")
            ]

        # Account created is automatic
        if OnboardingStep.ACCOUNT_CREATED not in completed:
            completed.append(OnboardingStep.ACCOUNT_CREATED)

        # Email verified check
        if user.is_verified and OnboardingStep.EMAIL_VERIFIED not in completed:
            completed.append(OnboardingStep.EMAIL_VERIFIED)

        remaining = [s for s in all_steps if s not in completed]
        current_step = remaining[0] if remaining else OnboardingStep.COMPLETED

        return {
            "completed_steps": completed,
            "remaining_steps": remaining,
            "current_step": current_step,
            "total_steps": len(all_steps),
            "percentage": int((len(completed) / len(all_steps)) * 100),
        }

    def _get_next_action(self, current_step: str) -> Dict:
        """Get suggested next action for user"""
        actions = {
            OnboardingStep.EMAIL_VERIFIED: {
                "title": "Verify your email",
                "description": "Check your inbox for verification link",
                "cta": "Resend verification email",
            },
            OnboardingStep.ORGANIZATION_CREATED: {
                "title": "Create your organization",
                "description": "Set up your company workspace",
                "cta": "Create organization",
            },
            OnboardingStep.TEAM_INVITED: {
                "title": "Invite your team",
                "description": "Add team members to collaborate",
                "cta": "Invite team members",
            },
            OnboardingStep.FIRST_EXPENSE: {
                "title": "Submit your first expense",
                "description": "Try creating an expense report",
                "cta": "Create expense",
            },
            OnboardingStep.PAYMENT_METHOD: {
                "title": "Add payment method",
                "description": "Add a card to start your subscription",
                "cta": "Add payment method",
            },
        }

        return actions.get(
            current_step,
            {
                "title": "You're all set!",
                "description": "Onboarding complete",
                "cta": "Go to dashboard",
            },
        )

    def _is_onboarding_complete(self, user: User) -> bool:
        """Check if all onboarding steps are complete"""
        progress = self._get_onboarding_progress(user)
        return progress["percentage"] == 100

    async def _send_team_invitation(
        self, inviter: User, organization_id: str, email: str
    ) -> str:
        """Send team invitation email"""
        # Create invitation token
        invitation_id = f"inv_{uuid.uuid4().hex[:16]}"

        # Get organization
        org = (
            self.db.query(Organization)
            .filter(Organization.id == organization_id)
            .first()
        )

        # Send email
        if org:
            await self.email_service.send_organization_invitation_email(
                to_email=email,
                organization_name=org.name,
                inviter_name=inviter.full_name or inviter.username,
                invitation_token=invitation_id,
            )

        return invitation_id
