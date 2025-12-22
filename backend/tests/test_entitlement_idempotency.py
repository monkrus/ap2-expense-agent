import uuid
from datetime import datetime

from src.gcp.entitlement_handler import (
    handle_entitlement_cancellation,
    handle_entitlement_update,
)
from src.models_billing import BillingEvent, OrganizationSubscription


def seed_subscription(db, org_id: str, entitlement_id: str, plan: str = "professional"):
    sub = OrganizationSubscription(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        tier_id=plan,
        tier_name=plan,
        gcp_entitlement_id=entitlement_id,
        status="active",
        created_at=datetime.utcnow(),
    )
    db.add(sub)
    db.commit()
    return sub


import pytest

pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
async def test_tier_change_idempotency(db_session):
    org_id = f"org_{uuid.uuid4().hex[:8]}"
    entitlement_id = f"ent_{uuid.uuid4().hex[:8]}"
    seed_subscription(db_session, org_id, entitlement_id, plan="starter")

    payload = {
        "entitlement_id": entitlement_id,
        "new_plan": "enterprise",
        "old_plan": "starter",
        "effective_at": "2025-11-10T11:00:00Z",
    }

    res1 = await handle_entitlement_update(payload, db_session)
    res2 = await handle_entitlement_update(payload, db_session)

    assert res1["status"] in ("updated", "already_processed")
    assert res2["status"] == "already_processed"

    events = (
        db_session.query(BillingEvent).filter_by(event_type="gcp_tier_changed").all()
    )
    assert len(events) == 1


@pytest.mark.asyncio
async def test_cancellation_idempotency(db_session):
    org_id = f"org_{uuid.uuid4().hex[:8]}"
    entitlement_id = f"ent_{uuid.uuid4().hex[:8]}"
    seed_subscription(db_session, org_id, entitlement_id, plan="professional")

    payload = {
        "entitlement_id": entitlement_id,
        "cancellation_reason": "customer_requested",
        "effective_at": "2025-11-10T12:00:00Z",
    }

    res1 = await handle_entitlement_cancellation(payload, db_session)
    res2 = await handle_entitlement_cancellation(payload, db_session)

    assert res1["status"] in ("cancelled", "already_processed")
    assert res2["status"] == "already_processed"

    events = (
        db_session.query(BillingEvent)
        .filter_by(event_type="gcp_subscription_cancelled")
        .all()
    )
    assert len(events) == 1
