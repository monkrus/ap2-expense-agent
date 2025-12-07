"""
Entitlement/plan-based feature gating helpers.

Use in routes as a dependency to enforce Marketplace/plan limits before executing handlers.
"""

from typing import Dict, Iterable, Set

from fastapi import HTTPException, status

from ..models_billing import OrganizationSubscription

# Allowed tiers per feature key (expand as needed)
ALLOWED_FEATURES: Dict[str, Set[str]] = {
    "ai_categorization": {"starter", "professional", "enterprise"},
    "ap2_payments": {"professional", "enterprise"},
    "sso": {"enterprise"},
    "advanced_analytics": {"professional", "enterprise"},
    "receipt_ai": {"starter", "professional", "enterprise"},
    "export_analytics": {"professional", "enterprise"},
}


def _normalize_tier(tier: str) -> str:
    return (tier or "").strip().lower()


def can_access_feature(tier: str, feature_key: str) -> bool:
    """Return True if the given tier is allowed to use the feature."""
    allowed = ALLOWED_FEATURES.get(feature_key)
    if not allowed:
        # Unknown feature defaults to allow to avoid breaking new routes; update map as we roll out gating.
        return True
    return _normalize_tier(tier) in allowed


def ensure_feature_access(subscription: OrganizationSubscription, feature_key: str) -> None:
    """
    Raise HTTP 403 if subscription tier is not allowed for the feature.

    Args:
        subscription: OrganizationSubscription model (must include tier_id or tier_name)
        feature_key: Feature identifier string (e.g., "ap2_payments")
    """
    tier = subscription.tier_id or subscription.tier_name
    if not can_access_feature(tier, feature_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "feature_not_in_plan",
                "feature": feature_key,
                "plan": tier,
                "allowed_plans": sorted(ALLOWED_FEATURES.get(feature_key, [])),
                "upgrade_prompt": "Upgrade your plan in Billing to access this feature.",
            },
        )
