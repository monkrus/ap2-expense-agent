"""
Subscription tier limits and pricing
"""
from dataclasses import dataclass
from typing import Optional
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


# Tier configuration based on MONETIZATION_STRATEGY.md
TIER_CONFIGS = {
    SubscriptionTier.STARTER: TierLimits(
        tier=SubscriptionTier.STARTER,
        name="Starter",
        price_monthly=29.00,
        max_users=25,
        max_expenses_per_month=100,
        max_ai_categorizations=500,
        max_ap2_transactions=0,  # No AP2 in Starter
        ocr_scans_included=100,
        data_retention_days=30,
        priority_support=False,
        custom_integrations=False,
        sso_enabled=False
    ),
    SubscriptionTier.PROFESSIONAL: TierLimits(
        tier=SubscriptionTier.PROFESSIONAL,
        name="Professional",
        price_monthly=99.00,
        max_users=100,
        max_expenses_per_month=None,  # Unlimited
        max_ai_categorizations=5000,
        max_ap2_transactions=100,
        ocr_scans_included=1000,
        data_retention_days=90,
        priority_support=True,
        custom_integrations=False,
        sso_enabled=False
    ),
    SubscriptionTier.ENTERPRISE: TierLimits(
        tier=SubscriptionTier.ENTERPRISE,
        name="Enterprise",
        price_monthly=399.00,
        max_users=500,
        max_expenses_per_month=None,  # Unlimited
        max_ai_categorizations=None,  # Unlimited
        max_ap2_transactions=None,  # Unlimited
        ocr_scans_included=10000,
        data_retention_days=365,
        priority_support=True,
        custom_integrations=True,
        sso_enabled=True
    ),
    SubscriptionTier.ENTERPRISE_PLUS: TierLimits(
        tier=SubscriptionTier.ENTERPRISE_PLUS,
        name="Enterprise Plus",
        price_monthly=999.00,  # Starting price, custom negotiated
        max_users=None,  # Unlimited
        max_expenses_per_month=None,  # Unlimited
        max_ai_categorizations=None,  # Unlimited
        max_ap2_transactions=None,  # Unlimited
        ocr_scans_included=None,  # Unlimited
        data_retention_days=365,
        priority_support=True,
        custom_integrations=True,
        sso_enabled=True
    )
}


def get_tier_limits(tier: SubscriptionTier) -> TierLimits:
    """Get limits for a subscription tier"""
    return TIER_CONFIGS.get(tier, TIER_CONFIGS[SubscriptionTier.STARTER])


# Usage overage fees (per MONETIZATION_STRATEGY.md)
USAGE_FEES = {
    "ap2_transaction": 0.10,  # $0.10 per AP2 transaction
    "ai_categorization": 0.05,  # $0.05 per AI categorization
    "ocr_scan": 0.02  # $0.02 per OCR scan
}
