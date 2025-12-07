"""
Limit Enforcement Service

Enforces hard limits for Free tier and soft limits (with overage fees) for paid tiers.
- Free tier: HARD BLOCK when limit exceeded (no payment method)
- Paid tiers: SOFT LIMIT with overage fees (they have payment method)
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import (
    Expense,
    Organization,
    OrganizationMember,
    Subscription,
    SubscriptionTier,
    UsageRecord,
    User,
)
from .tier_limits import TierLimits, get_tier_limits


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

        # Get subscription for this organization
        subscription = self._get_org_subscription(org_id)

        ai_categorization_count = 0
        ocr_scan_count = 0
        ap2_transaction_count = 0

        if subscription:
            # Get AI categorization count from UsageRecord
            ai_categorization_count = (
                self.db.query(func.coalesce(func.sum(UsageRecord.quantity), 0))
                .filter(UsageRecord.subscription_id == subscription.id)
                .filter(UsageRecord.usage_type == "ai_categorization")
                .filter(UsageRecord.created_at >= start_of_month)
                .scalar()
                or 0
            )

            # Get OCR scan count from UsageRecord
            ocr_scan_count = (
                self.db.query(func.coalesce(func.sum(UsageRecord.quantity), 0))
                .filter(UsageRecord.subscription_id == subscription.id)
                .filter(UsageRecord.usage_type == "ocr_scan")
                .filter(UsageRecord.created_at >= start_of_month)
                .scalar()
                or 0
            )

            # Get AP2 transaction count from UsageRecord
            ap2_transaction_count = (
                self.db.query(func.coalesce(func.sum(UsageRecord.quantity), 0))
                .filter(UsageRecord.subscription_id == subscription.id)
                .filter(UsageRecord.usage_type == "ap2_transaction")
                .filter(UsageRecord.created_at >= start_of_month)
                .scalar()
                or 0
            )

        return {
            "expenses": expense_count,
            "members": member_count,
            "ai_categorizations": int(ai_categorization_count),
            "ocr_scans": int(ocr_scan_count),
            "ap2_transactions": int(ap2_transaction_count),
        }

    def _get_org_subscription(self, org_id: str) -> Optional[Subscription]:
        """Get subscription for an organization (via owner)"""
        return (
            self.db.query(Subscription)
            .join(User, Subscription.user_id == User.id)
            .join(OrganizationMember, OrganizationMember.user_id == User.id)
            .filter(OrganizationMember.organization_id == org_id)
            .filter(OrganizationMember.role == "owner")
            .first()
        )

    def check_user_limit(
        self, org_id: str, raise_error: bool = True
    ) -> Tuple[bool, str]:
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

    def check_expense_limit(
        self, org_id: str, raise_error: bool = True
    ) -> Tuple[bool, str]:
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
            message = (
                f"Monthly expense limit reached ({current_expenses}/{max_expenses})"
            )

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

        # Get actual usage from usage tracking
        usage = self.get_current_month_usage(org_id)
        current_ai = usage.get("ai_categorizations", 0)

        if current_ai + count > max_ai:
            message = f"AI categorization limit would be exceeded ({current_ai + count}/{max_ai})"

            if tier == SubscriptionTier.FREE and raise_error:
                raise LimitExceededError(
                    feature="AI Categorization",
                    limit=max_ai,
                    current=current_ai,
                    upgrade_message="Upgrade to Starter to unlock more AI categorizations.",
                )

            return False, message

        return True, f"AI categorization available ({current_ai}/{max_ai})"

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

        # Get actual usage from usage tracking
        usage = self.get_current_month_usage(org_id)
        current_ocr = usage.get("ocr_scans", 0)

        if current_ocr + count > max_ocr:
            message = (
                f"OCR scan limit would be exceeded ({current_ocr + count}/{max_ocr})"
            )

            if tier == SubscriptionTier.FREE and raise_error:
                raise LimitExceededError(
                    feature="OCR Scans",
                    limit=max_ocr,
                    current=current_ocr,
                    upgrade_message="Upgrade to Starter for more receipt scanning.",
                )

            return False, message

        return True, f"OCR scans available ({current_ocr}/{max_ocr})"

    def check_ap2_transaction_limit(
        self, org_id: str, count: int = 1, raise_error: bool = True
    ) -> Tuple[bool, str]:
        """
        Check if organization can use AP2 transactions.

        Returns: (can_use, message)
        Raises: LimitExceededError for Free tier if raise_error=True
        """
        tier, limits = self.get_org_tier(org_id)

        max_ap2 = limits.max_ap2_transactions

        # Free tier has 0 AP2 transactions - always block
        if max_ap2 == 0:
            if tier == SubscriptionTier.FREE and raise_error:
                raise LimitExceededError(
                    feature="AP2 Transactions",
                    limit=0,
                    current=0,
                    upgrade_message="Upgrade to Starter to unlock AP2 automated payments.",
                )
            return False, "AP2 transactions not available on Free tier"

        if max_ap2 is None:  # Unlimited
            return True, "Unlimited AP2 transactions allowed"

        # Get actual usage from usage tracking
        usage = self.get_current_month_usage(org_id)
        current_ap2 = usage.get("ap2_transactions", 0)

        if current_ap2 + count > max_ap2:
            message = f"AP2 transaction limit would be exceeded ({current_ap2 + count}/{max_ap2})"

            if tier == SubscriptionTier.FREE and raise_error:
                raise LimitExceededError(
                    feature="AP2 Transactions",
                    limit=max_ap2,
                    current=current_ap2,
                    upgrade_message="Upgrade to Professional for more AP2 transactions.",
                )

            return False, message

        return True, f"AP2 transactions available ({current_ap2}/{max_ap2})"

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

    def check_daily_rate_limit(
        self, org_id: str, action_type: str, raise_error: bool = True
    ) -> Tuple[bool, str]:
        """
        Check daily rate limit for Free tier (anti-abuse measure).

        Free tier daily limits:
        - 10 expenses per day
        - 3 OCR scans per day
        - 0 AI categorizations per day (blocked)
        - 0 AP2 transactions per day (blocked)

        Returns: (can_proceed, message)
        """
        tier, limits = self.get_org_tier(org_id)

        # Only apply daily rate limits to Free tier
        if tier != SubscriptionTier.FREE:
            return True, "Paid tier - no daily rate limits"

        now = datetime.utcnow()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

        daily_limits = {
            "expense": 10,  # Max 10 expenses per day on Free
            "ocr_scan": 3,  # Max 3 OCR scans per day on Free
            "ai_categorization": 0,  # No AI on Free
            "ap2_transaction": 0,  # No AP2 on Free
        }

        daily_limit = daily_limits.get(action_type)
        if daily_limit is None:
            return True, f"No daily limit for {action_type}"

        # Block AI and AP2 completely on Free tier
        if daily_limit == 0:
            if raise_error:
                raise LimitExceededError(
                    feature=action_type.replace("_", " ").title(),
                    limit=0,
                    current=0,
                    upgrade_message=f"Upgrade to Starter to access {action_type.replace('_', ' ')}.",
                )
            return False, f"{action_type} not available on Free tier"

        # Get today's usage
        if action_type == "expense":
            today_count = (
                self.db.query(func.count(Expense.id))
                .filter(Expense.organization_id == org_id)
                .filter(Expense.created_at >= start_of_day)
                .scalar()
                or 0
            )
        else:
            subscription = self._get_org_subscription(org_id)
            if subscription:
                today_count = (
                    self.db.query(func.coalesce(func.sum(UsageRecord.quantity), 0))
                    .filter(UsageRecord.subscription_id == subscription.id)
                    .filter(UsageRecord.usage_type == action_type)
                    .filter(UsageRecord.created_at >= start_of_day)
                    .scalar()
                    or 0
                )
            else:
                today_count = 0

        if today_count >= daily_limit:
            message = f"Daily {action_type} limit reached ({today_count}/{daily_limit}). Try again tomorrow."

            if raise_error:
                raise LimitExceededError(
                    feature=f"Daily {action_type.replace('_', ' ').title()}",
                    limit=daily_limit,
                    current=today_count,
                    upgrade_message="Upgrade to Starter for higher daily limits.",
                )

            return False, message

        return True, f"Daily {action_type} limit OK ({today_count}/{daily_limit})"

    def get_usage_summary(self, org_id: str) -> dict:
        """
        Get comprehensive usage summary for an organization.

        Useful for displaying usage dashboards and limit warnings.
        """
        tier, limits = self.get_org_tier(org_id)
        usage = self.get_current_month_usage(org_id)

        # Calculate percentages and warnings
        def calc_usage_info(current: int, limit: Optional[int]) -> dict:
            if limit is None:
                return {
                    "current": current,
                    "limit": None,
                    "unlimited": True,
                    "percentage": 0,
                    "warning": False,
                    "blocked": False,
                }
            if limit == 0:
                return {
                    "current": current,
                    "limit": 0,
                    "unlimited": False,
                    "percentage": 100 if current > 0 else 0,
                    "warning": True,
                    "blocked": True,
                }
            percentage = (current / limit) * 100 if limit > 0 else 0
            return {
                "current": current,
                "limit": limit,
                "unlimited": False,
                "percentage": min(percentage, 100),
                "warning": percentage >= 80,
                "blocked": current >= limit,
            }

        return {
            "tier": tier.value,
            "tier_name": limits.name,
            "is_free_tier": tier == SubscriptionTier.FREE,
            "usage": {
                "expenses": calc_usage_info(
                    usage["expenses"], limits.max_expenses_per_month
                ),
                "users": calc_usage_info(usage["members"], limits.max_users),
                "ai_categorizations": calc_usage_info(
                    usage["ai_categorizations"], limits.max_ai_categorizations
                ),
                "ocr_scans": calc_usage_info(
                    usage["ocr_scans"], limits.ocr_scans_included
                ),
                "ap2_transactions": calc_usage_info(
                    usage["ap2_transactions"], limits.max_ap2_transactions
                ),
            },
            "features": {
                "api_access": limits.api_access,
                "sso_enabled": limits.sso_enabled,
                "custom_integrations": limits.custom_integrations,
                "advanced_analytics": limits.advanced_analytics,
                "priority_support": limits.priority_support,
            },
            "data_retention_days": limits.data_retention_days,
        }


def get_limit_enforcer(db: Session) -> LimitEnforcer:
    """Factory function to create a LimitEnforcer instance"""
    return LimitEnforcer(db)
