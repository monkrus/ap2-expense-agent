"""
Dead Letter Queue Administration Routes
Endpoints for managing failed webhook events
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..gcp.dead_letter_queue import WebhookDLQ

router = APIRouter(prefix="/api/admin/dlq", tags=["dlq-admin"])


@router.get("/stats")
async def get_dlq_stats(db: Session = Depends(get_db)):
    """
    Get DLQ statistics

    Returns:
        Statistics about failed webhooks
    """
    dlq = WebhookDLQ(db)
    stats = dlq.get_dlq_stats()
    return stats


@router.get("/failed-webhooks")
async def list_failed_webhooks(
    handler: Optional[str] = Query(None, description="Filter by handler name"),
    limit: int = Query(100, le=1000, description="Max results to return"),
    max_age_hours: Optional[int] = Query(
        None, description="Only show failures within last N hours"
    ),
    db: Session = Depends(get_db),
):
    """
    List failed webhooks in the DLQ

    Args:
        handler: Optional handler name filter
        limit: Maximum number of results
        max_age_hours: Only show recent failures

    Returns:
        List of failed webhook events
    """
    dlq = WebhookDLQ(db)
    events = dlq.get_failed_webhooks(
        handler=handler, limit=limit, max_age_hours=max_age_hours
    )

    return {
        "total": len(events),
        "events": [
            {
                "id": event.id,
                "handler": event.handler,
                "dedupe_key": event.dedupe_key,
                "status": event.status,
                "error_message": event.error_message,
                "created_at": event.created_at.isoformat() if event.created_at else None,
                "processed_at": event.processed_at.isoformat() if event.processed_at else None,
                "payload_preview": str(event.payload)[:200] + "..."
                if event.payload
                else None,
            }
            for event in events
        ],
    }


@router.post("/retry/{event_id}")
async def retry_webhook(event_id: str, db: Session = Depends(get_db)):
    """
    Retry a specific failed webhook

    Args:
        event_id: ID of webhook event to retry

    Returns:
        Retry result
    """
    dlq = WebhookDLQ(db)
    success, error = dlq.retry_failed_webhook(event_id)

    if not success:
        raise HTTPException(status_code=400, detail=error or "Retry failed")

    return {"status": "success", "event_id": event_id, "message": "Webhook retried successfully"}


@router.post("/retry-all")
async def retry_all_failed(
    handler: Optional[str] = Query(None, description="Filter by handler name"),
    max_age_hours: int = Query(24, description="Only retry failures within last N hours"),
    batch_size: int = Query(10, le=100, description="Number to retry in one batch"),
    db: Session = Depends(get_db),
):
    """
    Retry all failed webhooks (or filtered subset)

    Args:
        handler: Optional handler name filter
        max_age_hours: Only retry recent failures
        batch_size: Max number to retry at once

    Returns:
        Retry statistics
    """
    dlq = WebhookDLQ(db)
    results = dlq.retry_all_failed(
        handler=handler, max_age_hours=max_age_hours, batch_size=batch_size
    )

    return {
        "status": "completed",
        "total_attempted": results["total"],
        "successful": results["successful"],
        "failed": results["failed"],
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.delete("/purge")
async def purge_old_events(
    days: int = Query(30, ge=1, le=365, description="Delete events older than N days"),
    db: Session = Depends(get_db),
):
    """
    Purge old webhook events from DLQ

    Args:
        days: Delete events older than this many days

    Returns:
        Number of events deleted
    """
    dlq = WebhookDLQ(db)
    deleted_count = dlq.purge_old_events(days=days)

    return {
        "status": "success",
        "deleted_count": deleted_count,
        "cutoff_date": (datetime.utcnow().date() - timedelta(days=days)).isoformat(),
    }


@router.get("/event/{event_id}")
async def get_event_details(event_id: str, db: Session = Depends(get_db)):
    """
    Get detailed information about a specific webhook event

    Args:
        event_id: ID of the webhook event

    Returns:
        Full event details including payload
    """
    from ..models_billing import MarketplaceWebhookEvent

    event = db.query(MarketplaceWebhookEvent).filter_by(id=event_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return {
        "id": event.id,
        "handler": event.handler,
        "dedupe_key": event.dedupe_key,
        "status": event.status,
        "error_message": event.error_message,
        "payload": event.payload,
        "created_at": event.created_at.isoformat() if event.created_at else None,
        "processed_at": event.processed_at.isoformat() if event.processed_at else None,
    }


from datetime import timedelta
