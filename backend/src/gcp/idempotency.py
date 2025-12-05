"""
Idempotency utilities for GCP Marketplace webhook/event handling.

Uses MarketplaceWebhookEvent table to ensure at-least-once delivery safety.
"""

from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models_billing import MarketplaceWebhookEvent


def _get_event(
    db: Session, handler: str, dedupe_key: str
) -> Optional[MarketplaceWebhookEvent]:
    return (
        db.query(MarketplaceWebhookEvent)
        .filter(
            MarketplaceWebhookEvent.handler == handler,
            MarketplaceWebhookEvent.dedupe_key == dedupe_key,
        )
        .first()
    )


def record_event(
    db: Session, handler: str, dedupe_key: str, payload: Optional[Dict[str, Any]] = None
) -> Tuple[MarketplaceWebhookEvent, bool]:
    """
    Persist an idempotency record. Returns (event_row, created_new).
    If a duplicate exists, returns the existing row with created_new=False.
    """
    existing = _get_event(db, handler, dedupe_key)
    if existing:
        return existing, False

    event = MarketplaceWebhookEvent(
        id=dedupe_key,
        handler=handler,
        dedupe_key=dedupe_key,
        payload=payload,
        status="pending",
    )
    db.add(event)
    try:
        db.commit()
        db.refresh(event)
        return event, True
    except IntegrityError:
        db.rollback()
        existing = _get_event(db, handler, dedupe_key)
        if existing:
            return existing, False
        raise


def mark_success(db: Session, event: MarketplaceWebhookEvent) -> None:
    event.status = "success"
    event.processed_at = datetime.utcnow()
    db.add(event)
    db.commit()


def mark_failure(db: Session, event: MarketplaceWebhookEvent, error: str) -> None:
    event.status = "failed"
    event.error_message = error[:1000]
    event.processed_at = datetime.utcnow()
    db.add(event)
    db.commit()
