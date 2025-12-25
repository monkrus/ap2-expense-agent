"""
Limit Enforcement Service (Marketplace-first).

Uses organization subscriptions and billing tiers for limit enforcement.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Expense, Organization, OrganizationMember, OrganizationRole
from ..models_billing import BillingTier, OrganizationSubscription, UsageMetric


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


@dataclass
class OrgLimits:
    tier_name: str
    max_users: Optional[int]
    max_organizations: Optional[int]
    max_expenses_per_month: Optional[int]
    max_ai_categorizations: Optional[int]
    max_ap2_transactions: Optional[int]
    ocr_scans_included: Optional[int]
    data_retention_days: Optional[int]
    features: Dict[str, bool]
    has_subscription: bool


class LimitEnforcer:
    """Enforces usage limits based on organization subscription tiers."""

    def __init__(self, db: Session):
        self.db = db

    def get_org_tier(self, org_id: str) -> OrgLimits:
        """Get the subscription limits for an organization."""
        org_subscription = (
            self.db.query(OrganizationSubscription)
            .filter(
                OrganizationSubscription.organization_id == org_id,
                OrganizationSubscription.status.in_(["active", "trialing"]),
            )
            .first()
        )

        if not org_subscription:
            return self._default_limits(has_subscription=False)

        tier = None
        if org_subscription.tier_id:
            tier = (
                self.db.query(BillingTier)
                .filter(BillingTier.id == org_subscription.tier_id)
                .first()
            )

        if not tier and org_subscription.tier_name:
            tier = (
                self.db.query(BillingTier)
                .filter(BillingTier.tier_name == org_subscription.tier_name)
                .first()
            )

        if not tier:
            return self._default_limits(
                has_subscription=True, tier_name=org_subscription.tier_name or "unknown"
            )

        limits = self._normalize_limits(tier.limits)
        features = self._feature_flags(tier.features, tier.tier_name)

        return OrgLimits(
            tier_name=tier.tier_name,
            max_users=self._normalize_limit(limits.get("max_users")),
            max_organizations=self._normalize_limit(limits.get("max_organizations")),
            max_expenses_per_month=self._normalize_limit(
                limits.get("max_expenses_per_month")
            ),
            max_ai_categorizations=self._normalize_limit(
                limits.get("max_ai_categorizations")
                or limits.get("ai_categorizations_included")
            ),
            max_ap2_transactions=self._normalize_limit(
                limits.get("max_ap2_transactions")
                or limits.get("ap2_transactions_included")
            ),
            ocr_scans_included=self._normalize_limit(
                limits.get("ocr_scans_included")
            ),
            data_retention_days=limits.get("data_retention_days"),
            features=features,
            has_subscription=True,
        )

    def is_free_tier(self, org_id: str) -> bool:
        """Check if organization is on Free tier."""
        limits = self.get_org_tier(org_id)
        return limits.tier_name.lower() == "free"

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

        ai_categorization_count = self._sum_usage(
            org_id, "ai_categorization", start_of_month
        )
        ocr_scan_count = self._sum_usage(org_id, "ocr_scan", start_of_month)
        ap2_transaction_count = self._sum_usage(
            org_id, "ap2_transaction", start_of_month
        )

        return {
            "expenses": expense_count,
            "members": member_count,
            "ai_categorizations": int(ai_categorization_count),
            "ocr_scans": int(ocr_scan_count),
            "ap2_transactions": int(ap2_transaction_count),
        }

    def _sum_usage(self, org_id: str, usage_type: str, start: datetime) -> int:
        return int(
            self.db.query(func.coalesce(func.sum(UsageMetric.metric_value), 0))
            .filter(
                UsageMetric.organization_id == org_id,
                UsageMetric.metric_type == usage_type,
                UsageMetric.created_at >= start,
            )
            .scalar()
            or 0
        )

    def _require_subscription(self, limits: OrgLimits) -> None:
        if settings.enable_gcp_marketplace and not limits.has_subscription:
            raise LimitExceededError(
                feature="Subscription",
                limit=1,
                current=0,
                upgrade_message="Active Google Cloud Marketplace subscription required.",
            )

    def _default_limits(
        self, has_subscription: bool, tier_name: str = "free"
    ) -> OrgLimits:
        return OrgLimits(
            tier_name=tier_name,
            max_users=1,
            max_organizations=1,
            max_expenses_per_month=20,
            max_ai_categorizations=0,
            max_ap2_transactions=0,
            ocr_scans_included=5,
            data_retention_days=30,
            features={
                "api_access": False,
                "sso_enabled": False,
                "custom_integrations": False,
                "advanced_analytics": False,
                "approval_workflows": False,
                "priority_support": False,
            },
            has_subscription=has_subscription,
        )

    def _normalize_limits(self, value: object) -> Dict:
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}

    def _normalize_limit(self, value: Optional[object]) -> Optional[int]:
        if value is None:
            return None
        try:
            limit = int(value)
        except (TypeError, ValueError):
            return None
        if limit < 0:
            return None
        return limit

    def _feature_flags(self, value: object, tier_name: Optional[str]) -> Dict[str, bool]:
        features = []
        if isinstance(value, list):
            features = value
        elif isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    features = parsed
                else:
                    features = [value]
            except json.JSONDecodeError:
                features = [value]

        normalized = {str(item).strip().lower() for item in features if item}
        tier_rank = {
            "free": 0,
            "starter": 1,
            "professional": 2,
            "enterprise": 3,
            "enterprise_plus": 4,
        }
        rank = tier_rank.get((tier_name or "").lower(), 0)

        return {
            "api_access": ("api" in " ".join(normalized)) or rank >= 3,
            "sso_enabled": ("sso" in " ".join(normalized)) or rank >= 3,
            "custom_integrations": ("integration" in " ".join(normalized)) or rank >= 3,
            "advanced_analytics": ("analytics" in " ".join(normalized)) or rank >= 2,
            "approval_workflows": ("approval" in " ".join(normalized)) or rank >= 2,
            "priority_support": ("priority" in " ".join(normalized)) or rank >= 2,
        }

    def check_user_limit(
        self, org_id: str, raise_error: bool = True
    ) -> Tuple[bool, str]:
        """
        Check if organization can add more users.

        Returns: (can_add, message)
        Raises: LimitExceededError for Free tier if raise_error=True
        """
        limits = self.get_org_tier(org_id)
        self._require_subscription(limits)

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

            if limits.tier_name.lower() == "free" and raise_error:
                raise LimitExceededError(
                    feature="Users",
                    limit=max_users,
                    current=current_members,
                    upgrade_message="Upgrade to Starter to add more team members.",
                )

            return False, message

        return True, f"Can add users ({current_members}/{max_users})"

    def check_organization_limit(
        self, user_id: str, raise_error: bool = True
    ) -> Tuple[bool, str]:
        """
        Check if user can create more organizations.

        For free tier users, we need to:
        1. Count how many organizations the user owns (is OWNER of)
        2. Check against max_organizations limit for their tier
        3. Raise error if limit exceeded and raise_error=True

        Args:
            user_id: ID of user attempting to create organization
            raise_error: If True, raise LimitExceededError for Free tier

        Returns: (can_create, message)
        Raises: LimitExceededError for Free tier if raise_error=True
        """

        # Count organizations where user is OWNER
        current_org_count = (
            self.db.query(func.count(OrganizationMember.id.distinct()))
            .join(Organization, OrganizationMember.organization_id == Organization.id)
            .filter(OrganizationMember.user_id == user_id)
            .filter(OrganizationMember.role == OrganizationRole.OWNER)
            .filter(OrganizationMember.is_active == True)
            .filter(Organization.is_active == True)
            .scalar()
            or 0
        )

        # Get user's tier limits from their first owned organization
        # For free tier users with no orgs yet, use default free tier limits
        user_org = (
            self.db.query(Organization)
            .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
            .filter(OrganizationMember.user_id == user_id)
            .filter(OrganizationMember.role == OrganizationRole.OWNER)
            .filter(OrganizationMember.is_active == True)
            .filter(Organization.is_active == True)
            .first()
        )

        if user_org:
            # User has an organization, get their tier from it
            limits = self.get_org_tier(user_org.id)
        else:
            # New user with no organizations, assume free tier
            limits = self._default_limits(has_subscription=False, tier_name="free")

        max_orgs = limits.max_organizations

        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[ORG_LIMIT_CHECK] user_id={user_id}, current_count={current_org_count}, max={max_orgs}, tier={limits.tier_name}")

        if max_orgs is None:  # Unlimited
            return True, "Unlimited organizations allowed"

        if current_org_count >= max_orgs:
            message = f"Organization limit reached ({current_org_count}/{max_orgs})"
            logger.warning(f"[ORG_LIMIT_EXCEEDED] {message}, tier={limits.tier_name}, raise_error={raise_error}")

            if limits.tier_name.lower() == "free" and raise_error:
                logger.error(f"[ORG_LIMIT_ERROR] Raising LimitExceededError for user {user_id}")
                raise LimitExceededError(
                    feature="Organizations",
                    limit=max_orgs,
                    current=current_org_count,
                    upgrade_message="You've reached your Free plan's limit of 1 organization. Upgrade to Starter ($29/month) to create up to 3 organizations.",
                )

            return False, message

        return True, f"Can create organizations ({current_org_count}/{max_orgs})"

    def check_expense_limit(
        self, org_id: str, raise_error: bool = True
    ) -> Tuple[bool, str]:
        """
        Check if organization can add more expenses this month.

        Returns: (can_add, message)
        Raises: LimitExceededError for Free tier if raise_error=True
        """
        limits = self.get_org_tier(org_id)
        self._require_subscription(limits)

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

            if limits.tier_name.lower() == "free" and raise_error:
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
        limits = self.get_org_tier(org_id)
        self._require_subscription(limits)

        max_ai = limits.max_ai_categorizations

        # Free tier has 0 AI categorizations - always block
        if max_ai == 0:
            if limits.tier_name.lower() == "free" and raise_error:
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

            if limits.tier_name.lower() == "free" and raise_error:
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
        limits = self.get_org_tier(org_id)
        self._require_subscription(limits)

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

            if limits.tier_name.lower() == "free" and raise_error:
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
        limits = self.get_org_tier(org_id)
        self._require_subscription(limits)

        max_ap2 = limits.max_ap2_transactions

        # Free tier has 0 AP2 transactions - always block
        if max_ap2 == 0:
            if limits.tier_name.lower() == "free" and raise_error:
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

            if limits.tier_name.lower() == "free" and raise_error:
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
        limits = self.get_org_tier(org_id)
        self._require_subscription(limits)

        feature_checks = {
            "api_access": (
                limits.features.get("api_access", False),
                "API access requires Professional tier or higher.",
            ),
            "sso_enabled": (
                limits.features.get("sso_enabled", False),
                "SSO/SAML requires Enterprise tier or higher.",
            ),
            "custom_integrations": (
                limits.features.get("custom_integrations", False),
                "Custom integrations require Enterprise tier or higher.",
            ),
            "approval_workflows": (
                limits.features.get("approval_workflows", False),
                "Approval workflows require Professional tier or higher.",
            ),
            "advanced_analytics": (
                limits.features.get("advanced_analytics", False),
                "Advanced analytics require Enterprise tier or higher.",
            ),
        }

        if feature not in feature_checks:
            return True, f"Unknown feature: {feature}"

        has_access, upgrade_message = feature_checks[feature]

        if not has_access:
            if limits.tier_name.lower() == "free" and raise_error:
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
        limits = self.get_org_tier(org_id)
        self._require_subscription(limits)

        # Only apply daily rate limits to Free tier
        if limits.tier_name.lower() != "free":
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
            today_count = self._sum_usage(org_id, action_type, start_of_day)

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
        limits = self.get_org_tier(org_id)
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
            "tier": limits.tier_name,
            "tier_name": limits.tier_name,
            "is_free_tier": limits.tier_name.lower() == "free",
            "subscription_active": limits.has_subscription,
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
                "api_access": limits.features.get("api_access", False),
                "sso_enabled": limits.features.get("sso_enabled", False),
                "custom_integrations": limits.features.get("custom_integrations", False),
                "advanced_analytics": limits.features.get("advanced_analytics", False),
                "priority_support": limits.features.get("priority_support", False),
            },
            "data_retention_days": limits.data_retention_days,
        }


def get_limit_enforcer(db: Session) -> LimitEnforcer:
    """Factory function to create a LimitEnforcer instance"""
    return LimitEnforcer(db)
