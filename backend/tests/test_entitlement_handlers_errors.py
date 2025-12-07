import pytest
from sqlalchemy.orm import Session

from src.gcp.entitlement_handler import (
    handle_entitlement_cancellation,
    handle_entitlement_update,
)


@pytest.mark.asyncio
async def test_update_missing_entitlement_id_raises(db_session: Session):
    with pytest.raises(ValueError):
        await handle_entitlement_update({"new_plan": "enterprise"}, db_session)


@pytest.mark.asyncio
async def test_cancel_missing_entitlement_id_raises(db_session: Session):
    with pytest.raises(ValueError):
        await handle_entitlement_cancellation(
            {"reason": "customer_requested"}, db_session
        )
