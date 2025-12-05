"""
Marketplace entitlement enforcement middleware.

Adds entitlement context to each request and blocks access for cancelled/suspended plans.
"""

from typing import Dict, Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .config import settings
from .database import SessionLocal
from .models_billing import MarketplaceEntitlement

# Simple plan → limits/features map (placeholder; align with manifest/sku map)
PLAN_FEATURES: Dict[str, Dict] = {
    "starter": {
        "limits": {"users": 25, "expenses_per_month": 500, "ai_categorizations": 500},
        "retention_days": 30,
    },
    "professional": {
        "limits": {"users": 100, "expenses_per_month": None, "ai_categorizations": 5000},
        "retention_days": 90,
    },
    "enterprise": {
        "limits": {"users": 500, "expenses_per_month": None, "ai_categorizations": None},
        "retention_days": 365,
    },
    "enterprise_plus": {
        "limits": {"users": None, "expenses_per_month": None, "ai_categorizations": None},
        "retention_days": 365,
    },
}


def _fetch_entitlement(org_id: str) -> Optional[MarketplaceEntitlement]:
    db = SessionLocal()
    try:
        ent = (
            db.query(MarketplaceEntitlement)
            .filter(MarketplaceEntitlement.organization_id == org_id)
            .order_by(MarketplaceEntitlement.updated_at.desc())
            .first()
        )
        return ent
    finally:
        db.close()


class MarketplaceEnforcementMiddleware(BaseHTTPMiddleware):
    """Attach entitlement context and enforce active state."""

    async def dispatch(self, request: Request, call_next):
        if not settings.enable_gcp_marketplace:
            return await call_next(request)

        org_id = request.headers.get("X-Organization-Id")
        if not org_id:
            return await call_next(request)

        entitlement = _fetch_entitlement(org_id)
        if entitlement:
            plan_key = (entitlement.plan or "").lower()
            plan_features = PLAN_FEATURES.get(plan_key, PLAN_FEATURES.get("starter", {}))
            request.state.entitlement = {
                "plan": entitlement.plan,
                "state": entitlement.state,
                "limits": plan_features.get("limits", {}),
                "retention_days": plan_features.get("retention_days"),
                "trial_end": entitlement.trial_end.isoformat() if entitlement.trial_end else None,
                "grace_end": entitlement.grace_end.isoformat() if entitlement.grace_end else None,
                "entitlement_id": entitlement.entitlement_id,
            }

            if entitlement.state in ("CANCELLED", "SUSPENDED"):
                detail = {
                    "message": "Subscription is inactive. Please reactivate via Google Cloud Marketplace.",
                    "entitlement_id": entitlement.entitlement_id,
                    "state": entitlement.state,
                }
                return JSONResponse(status_code=402, content=detail)
        else:
            # Annotate absence for downstream handlers
            request.state.entitlement = {"state": "missing"}

        return await call_next(request)
