"""
Subscription tier limits and pricing
"""

from dataclasses import dataclass
from typing import List, Optional

from ..models import SubscriptionTier


@dataclass
class TierLimits:
    """Limits and pricing for a subscription tier"""

    tier: SubscriptionTier
    name: str
    price_monthly: float
    max_users: int
    max_expenses_per_month: Optional[int]  # None = unlimited
    max_ai_categorizations: Optional[int]
    max_ap2_transactions: Optional[int]
    ocr_scans_included: int
    data_retention_days: int
    priority_support: bool
    custom_integrations: bool
    sso_enabled: bool
    # New advanced features
    white_label: bool = False
    api_access: bool = False
    advanced_analytics: bool = False
    dedicated_account_manager: bool = False
    sla_guarantee: str = None  # e.g., "99.9%", "99.99%"
    support_channels: List[str] = None  # e.g., ["email", "phone", "slack"]


# Tier configuration based on MONETIZATION_STRATEGY.md
TIER_CONFIGS = {
    SubscriptionTier.STARTER: TierLimits(
        tier=SubscriptionTier.STARTER,
        name="Starter",
        price_monthly=29.00,
        max_users=5,
        max_expenses_per_month=50,
        max_ai_categorizations=100,
        max_ap2_transactions=10,  # Let them try AP2!
        ocr_scans_included=50,
        data_retention_days=30,
        priority_support=False,
        custom_integrations=False,
        sso_enabled=False,
        white_label=False,
        api_access=False,
        advanced_analytics=False,
        dedicated_account_manager=False,
        sla_guarantee=None,
        support_channels=["email"],
    ),
    SubscriptionTier.PROFESSIONAL: TierLimits(
        tier=SubscriptionTier.PROFESSIONAL,
        name="Pro",
        price_monthly=99.00,
        max_users=25,
        max_expenses_per_month=None,  # Unlimited
        max_ai_categorizations=2000,
        max_ap2_transactions=50,
        ocr_scans_included=500,
        data_retention_days=90,
        priority_support=True,
        custom_integrations=False,
        sso_enabled=False,
        white_label=False,
        api_access=False,
        advanced_analytics=False,
        dedicated_account_manager=False,
        sla_guarantee=None,
        support_channels=["email", "chat"],
    ),
    SubscriptionTier.ENTERPRISE: TierLimits(
        tier=SubscriptionTier.ENTERPRISE,
        name="Enterprise",
        price_monthly=399.00,
        max_users=100,
        max_expenses_per_month=None,  # Unlimited
        max_ai_categorizations=None,  # Unlimited
        max_ap2_transactions=None,  # Unlimited
        ocr_scans_included=5000,
        data_retention_days=365,
        priority_support=True,
        custom_integrations=True,
        sso_enabled=True,
        white_label=False,
        api_access=True,
        advanced_analytics=True,
        dedicated_account_manager=False,
        sla_guarantee="99.9%",
        support_channels=["email", "chat", "phone", "slack"],
    ),
    SubscriptionTier.ENTERPRISE_PLUS: TierLimits(
        tier=SubscriptionTier.ENTERPRISE_PLUS,
        name="Enterprise +",
        price_monthly=999.00,  # Starting price, custom negotiated
        max_users=None,  # Unlimited
        max_expenses_per_month=None,  # Unlimited
        max_ai_categorizations=None,  # Unlimited
        max_ap2_transactions=None,  # Unlimited
        ocr_scans_included=None,  # Unlimited
        data_retention_days=365,
        priority_support=True,
        custom_integrations=True,
        sso_enabled=True,
        white_label=True,
        api_access=True,
        advanced_analytics=True,
        dedicated_account_manager=True,
        sla_guarantee="99.99%",
        support_channels=["email", "chat", "phone", "slack", "dedicated"],
    ),
}


def get_tier_limits(tier: SubscriptionTier) -> TierLimits:
    """Get limits for a subscription tier"""
    return TIER_CONFIGS.get(tier, TIER_CONFIGS[SubscriptionTier.STARTER])


# Usage overage fees (per MONETIZATION_STRATEGY.md)
USAGE_FEES = {
    "expense": 0.01,  # $0.01 per expense overage
    "ap2_transaction": 0.10,  # $0.10 per AP2 transaction
    "ai_categorization": 0.05,  # $0.05 per AI categorization
    "ocr_scan": 0.02,  # $0.02 per OCR scan
}
