"""
Limit Enforcement Service

Enforces hard limits for Free tier and soft limits (with overage fees) for paid tiers.
- Free tier: HARD BLOCK when limit exceeded (no payment method)
- Paid tiers: SOFT LIMIT with overage fees (they have payment method)
"""

from typing import Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models import (
    SubscriptionTier,
    Subscription,
    Organization,
    OrganizationMember,
    Expense,
    User,
)
from .tier_limits import get_tier_limits, TierLimits


class LimitExceededError(Exception):
    """Raised when a hard limit is exceeded (Free tier)"""

    def __init__(self, feature: str, limit: int, current: int, upgrade_message: str):
        self.feature = feature
        self.limit = limit
        self.current = current
        self.upgrade_message = upgrade_message
        super().__init__(
            f"{feature} limit exceeded: {current}/{limit}. {upgrade_message}"
        )


class LimitEnforcer:
    """
    Enforces usage limits based on subscription tier.

    - Free tier: Hard limits (blocked)
    - Paid tiers: Soft limits (overage fees charged)
    """

    def __init__(self, db: Session):
        self.db = db

    def get_org_tier(self, org_id: str) -> Tuple[SubscriptionTier, TierLimits]:
        """Get the subscription tier and limits for an organization"""
        # Get organization's subscription
        subscription = (
            self.db.query(Subscription)
            .join(User, Subscription.user_id == User.id)
            .join(OrganizationMember, OrganizationMember.user_id == User.id)
            .filter(OrganizationMember.organization_id == org_id)
            .filter(OrganizationMember.role == "owner")
            .first()
        )

        if subscription and subscription.tier:
            tier = subscription.tier
        else:
            tier = SubscriptionTier.FREE

        limits = get_tier_limits(tier)
        return tier, limits

    def is_free_tier(self, org_id: str) -> bool:
        """Check if organization is on Free tier"""
        tier, _ = self.get_org_tier(org_id)
        return tier == SubscriptionTier.FREE

    def get_current_month_usage(self, org_id: str) -> dict:
        """Get current month's usage for an organization"""
        now = datetime.utcnow()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Count expenses this month
        expense_count = (
            self.db.query(func.count(Expense.id))
            .filter(Expense.organization_id == org_id)
            .filter(Expense.created_at >= start_of_month)
            .scalar()
            or 0
        )

        # Count members
        member_count = (
            self.db.query(func.count(OrganizationMember.id))
            .filter(OrganizationMember.organization_id == org_id)
            .scalar()
            or 0
        )

        # TODO: Get AI categorization count from usage tracking table
        # For now, we'll track this separately
        ai_categorization_count = 0

        # TODO: Get OCR scan count from usage tracking table
        ocr_scan_count = 0

        return {
            "expenses": expense_count,
            "members": member_count,
            "ai_categorizations": ai_categorization_count,
            "ocr_scans": ocr_scan_count,
        }

    def check_user_limit(self, org_id: str, raise_error: bool = True) -> Tuple[bool, str]:
        """
        Check if organization can add more users.

        Returns: (can_add, message)
        Raises: LimitExceededError for Free tier if raise_error=True
        """
        tier, limits = self.get_org_tier(org_id)

        current_members = (
            self.db.query(func.count(OrganizationMember.id))
            .filter(OrganizationMember.organization_id == org_id)
            .scalar()
            or 0
        )

        max_users = limits.max_users
        if max_users is None:  # Unlimited
            return True, "Unlimited users allowed"

        if current_members >= max_users:
            message = f"User limit reached ({current_members}/{max_users})"

            if tier == SubscriptionTier.FREE and raise_error:
                raise LimitExceededError(
                    feature="Users",
                    limit=max_users,
                    current=current_members,
                    upgrade_message="Upgrade to Starter to add more team members.",
                )

            return False, message

        return True, f"Can add users ({current_members}/{max_users})"

    def check_expense_limit(self, org_id: str, raise_error: bool = True) -> Tuple[bool, str]:
        """
        Check if organization can add more expenses this month.

        Returns: (can_add, message)
        Raises: LimitExceededError for Free tier if raise_error=True
        """
        tier, limits = self.get_org_tier(org_id)

        now = datetime.utcnow()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        current_expenses = (
            self.db.query(func.count(Expense.id))
            .filter(Expense.organization_id == org_id)
            .filter(Expense.created_at >= start_of_month)
            .scalar()
            or 0
        )

        max_expenses = limits.max_expenses_per_month
        if max_expenses is None:  # Unlimited
            return True, "Unlimited expenses allowed"

        if current_expenses >= max_expenses:
            message = f"Monthly expense limit reached ({current_expenses}/{max_expenses})"

            if tier == SubscriptionTier.FREE and raise_error:
                raise LimitExceededError(
                    feature="Expenses",
                    limit=max_expenses,
                    current=current_expenses,
                    upgrade_message="Upgrade to Starter to submit more expenses.",
                )

            return False, message

        return True, f"Can add expenses ({current_expenses}/{max_expenses})"

    def check_ai_categorization_limit(
        self, org_id: str, count: int = 1, raise_error: bool = True
    ) -> Tuple[bool, str]:
        """
        Check if organization can use AI categorization.

        Returns: (can_use, message)
        Raises: LimitExceededError for Free tier if raise_error=True
        """
        tier, limits = self.get_org_tier(org_id)

        max_ai = limits.max_ai_categorizations

        # Free tier has 0 AI categorizations - always block
        if max_ai == 0:
            if tier == SubscriptionTier.FREE and raise_error:
                raise LimitExceededError(
                    feature="AI Categorization",
                    limit=0,
                    current=0,
                    upgrade_message="Upgrade to Starter to unlock AI-powered categorization.",
                )
            return False, "AI categorization not available on Free tier"

        if max_ai is None:  # Unlimited
            return True, "Unlimited AI categorizations allowed"

        # TODO: Get actual usage from usage tracking
        # For now, allow if they have any limit
        return True, f"AI categorization available (limit: {max_ai}/month)"

    def check_ocr_limit(
        self, org_id: str, count: int = 1, raise_error: bool = True
    ) -> Tuple[bool, str]:
        """
        Check if organization can use OCR scanning.

        Returns: (can_use, message)
        Raises: LimitExceededError for Free tier if raise_error=True
        """
        tier, limits = self.get_org_tier(org_id)

        max_ocr = limits.ocr_scans_included

        if max_ocr is None:  # Unlimited
            return True, "Unlimited OCR scans allowed"

        # TODO: Get actual usage from usage tracking table
        # For now, we need to track this separately
        current_ocr = 0  # Placeholder

        if current_ocr >= max_ocr:
            message = f"OCR scan limit reached ({current_ocr}/{max_ocr})"

            if tier == SubscriptionTier.FREE and raise_error:
                raise LimitExceededError(
                    feature="OCR Scans",
                    limit=max_ocr,
                    current=current_ocr,
                    upgrade_message="Upgrade to Starter for more receipt scanning.",
                )

            return False, message

        return True, f"OCR scans available ({current_ocr}/{max_ocr})"

    def check_feature_access(
        self, org_id: str, feature: str, raise_error: bool = True
    ) -> Tuple[bool, str]:
        """
        Check if organization has access to a specific feature.

        Features: 'api_access', 'sso_enabled', 'approval_workflows', 'custom_integrations'
        """
        tier, limits = self.get_org_tier(org_id)

        feature_checks = {
            "api_access": (
                limits.api_access,
                "API access requires Professional tier or higher.",
            ),
            "sso_enabled": (
                limits.sso_enabled,
                "SSO/SAML requires Enterprise tier or higher.",
            ),
            "custom_integrations": (
                limits.custom_integrations,
                "Custom integrations require Enterprise tier or higher.",
            ),
            "approval_workflows": (
                tier
                in [
                    SubscriptionTier.PROFESSIONAL,
                    SubscriptionTier.ENTERPRISE,
                    SubscriptionTier.ENTERPRISE_PLUS,
                ],
                "Approval workflows require Professional tier or higher.",
            ),
            "advanced_analytics": (
                limits.advanced_analytics,
                "Advanced analytics require Enterprise tier or higher.",
            ),
        }

        if feature not in feature_checks:
            return True, f"Unknown feature: {feature}"

        has_access, upgrade_message = feature_checks[feature]

        if not has_access:
            if tier == SubscriptionTier.FREE and raise_error:
                raise LimitExceededError(
                    feature=feature.replace("_", " ").title(),
                    limit=0,
                    current=0,
                    upgrade_message=upgrade_message,
                )
            return False, upgrade_message

        return True, f"Feature '{feature}' is available"


def get_limit_enforcer(db: Session) -> LimitEnforcer:
    """Factory function to create a LimitEnforcer instance"""
    return LimitEnforcer(db)
