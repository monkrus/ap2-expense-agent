"""
Dead-letter logging for GCP Marketplace webhook and usage flows.

Records failed events so they can be inspected or re-processed later.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from ..models_billing import BillingEvent


def record_dead_letter(
    db: Session,
    event_type: str,
    payload: Dict[str, Any],
    error_message: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Persist failed webhook/usage events for later replay."""
    try:
        event = BillingEvent(
            id=str(uuid.uuid4()),
            organization_id=payload.get("organization_id") or payload.get("entitlement_id") or "unknown",
            event_type=event_type,
            event_data=payload,
            status="failed",
            error_message=error_message,
            occurred_at=datetime.utcnow(),
            event_metadata=metadata or {},
        )
        db.add(event)
        db.commit()
    except Exception as exc:
        # Last resort: avoid raising further; print for diagnostics
        print(f"Failed to record dead-letter event: {exc}")
