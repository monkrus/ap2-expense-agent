"""
Dead Letter Queue (DLQ) for Failed GCP Marketplace Webhooks

Stores failed webhook events for later retry or manual investigation.
Prevents data loss when webhook processing fails repeatedly.
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from ..models_billing import MarketplaceWebhookEvent


class WebhookDLQ:
    """
    Dead Letter Queue for failed webhook processing

    When a webhook fails after all retries, it's sent to the DLQ for:
    - Manual investigation
    - Later automatic retry (e.g., when service recovers)
    - Audit trail of failures
    """

    def __init__(self, db: Session):
        self.db = db

    def add_to_dlq(
        self,
        handler: str,
        payload: Dict,
        error_message: str,
        dedupe_key: Optional[str] = None,
    ) -> MarketplaceWebhookEvent:
        """
        Add a failed webhook to the dead letter queue

        Args:
            handler: Handler name (e.g., "gcp_events:entitlement_created")
            payload: Original webhook payload
            error_message: Error message from failed processing
            dedupe_key: Deduplication key (optional, auto-generated if not provided)

        Returns:
            Created MarketplaceWebhookEvent record
        """
        if not dedupe_key:
            dedupe_key = f"{handler}:{uuid.uuid4()}"

        # Check if already in DLQ
        existing = (
            self.db.query(MarketplaceWebhookEvent)
            .filter_by(handler=handler, dedupe_key=dedupe_key)
            .first()
        )

        if existing:
            # Update existing record
            existing.error_message = error_message
            existing.status = "failed"
            self.db.commit()
            return existing

        # Create new DLQ entry
        dlq_event = MarketplaceWebhookEvent(
            id=str(uuid.uuid4()),
            handler=handler,
            dedupe_key=dedupe_key,
            status="failed",
            error_message=error_message,
            payload=payload,
            created_at=datetime.utcnow(),
        )

        self.db.add(dlq_event)
        self.db.commit()

        print(f"[DLQ] Added failed webhook to queue: {handler} - {error_message}")

        return dlq_event

    def get_failed_webhooks(
        self,
        handler: Optional[str] = None,
        limit: int = 100,
        max_age_hours: Optional[int] = None,
    ) -> List[MarketplaceWebhookEvent]:
        """
        Get failed webhooks from DLQ

        Args:
            handler: Filter by handler name (optional)
            limit: Maximum number of records to return
            max_age_hours: Only return failures within last N hours (optional)

        Returns:
            List of failed webhook events
        """
        query = self.db.query(MarketplaceWebhookEvent).filter_by(status="failed")

        if handler:
            query = query.filter_by(handler=handler)

        if max_age_hours:
            cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
            query = query.filter(MarketplaceWebhookEvent.created_at >= cutoff)

        query = query.order_by(MarketplaceWebhookEvent.created_at.desc()).limit(limit)

        return query.all()

    def retry_failed_webhook(
        self, event_id: str
    ) -> tuple[bool, Optional[str]]:
        """
        Retry a failed webhook from the DLQ

        Args:
            event_id: ID of the webhook event to retry

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        event = self.db.query(MarketplaceWebhookEvent).filter_by(id=event_id).first()

        if not event:
            return False, "Event not found"

        if event.status != "failed":
            return False, f"Event status is {event.status}, not failed"

        try:
            # Import handler dynamically to avoid circular imports
            from ..routes.gcp_webhooks import (
                handle_procurement_webhook,
                handle_entitlement_update,
                handle_entitlement_cancellation,
            )

            # Determine which handler to use
            handler_map = {
                "gcp_events:entitlement_created": handle_procurement_webhook,
                "gcp_events:entitlement_plan_change": handle_entitlement_update,
                "gcp_events:entitlement_cancelled": handle_entitlement_cancellation,
            }

            handler_func = handler_map.get(event.handler)

            if not handler_func:
                return False, f"Unknown handler: {event.handler}"

            # Attempt to reprocess
            import asyncio

            result = asyncio.run(handler_func(event.payload, self.db))

            # Mark as success
            event.status = "success"
            event.processed_at = datetime.utcnow()
            event.error_message = None
            self.db.commit()

            print(f"[DLQ] Successfully retried webhook: {event_id}")
            return True, None

        except Exception as e:
            error_msg = str(e)
            print(f"[DLQ] Retry failed for webhook {event_id}: {error_msg}")
            return False, error_msg

    def retry_all_failed(
        self,
        handler: Optional[str] = None,
        max_age_hours: int = 24,
        batch_size: int = 10,
    ) -> Dict:
        """
        Retry all failed webhooks in the DLQ

        Args:
            handler: Filter by handler name (optional)
            max_age_hours: Only retry failures within last N hours
            batch_size: Number of events to retry in one batch

        Returns:
            Dict with retry statistics
        """
        failed_events = self.get_failed_webhooks(
            handler=handler, limit=batch_size, max_age_hours=max_age_hours
        )

        results = {"total": len(failed_events), "successful": 0, "failed": 0}

        for event in failed_events:
            success, error = self.retry_failed_webhook(event.id)
            if success:
                results["successful"] += 1
            else:
                results["failed"] += 1

        print(
            f"[DLQ] Retry batch complete: {results['successful']}/{results['total']} succeeded"
        )

        return results

    def get_dlq_stats(self) -> Dict:
        """
        Get statistics about the dead letter queue

        Returns:
            Dict with DLQ statistics
        """
        # Count by status
        status_counts = (
            self.db.query(
                MarketplaceWebhookEvent.status,
                func.count(MarketplaceWebhookEvent.id),
            )
            .group_by(MarketplaceWebhookEvent.status)
            .all()
        )

        # Count by handler
        handler_counts = (
            self.db.query(
                MarketplaceWebhookEvent.handler,
                func.count(MarketplaceWebhookEvent.id),
            )
            .filter_by(status="failed")
            .group_by(MarketplaceWebhookEvent.handler)
            .all()
        )

        # Recent failures (last 24 hours)
        cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_failures = (
            self.db.query(func.count(MarketplaceWebhookEvent.id))
            .filter(
                and_(
                    MarketplaceWebhookEvent.status == "failed",
                    MarketplaceWebhookEvent.created_at >= cutoff,
                )
            )
            .scalar()
        )

        return {
            "status_counts": dict(status_counts),
            "failed_by_handler": dict(handler_counts),
            "recent_failures_24h": recent_failures,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def purge_old_events(self, days: int = 30) -> int:
        """
        Delete old webhook events from DLQ

        Args:
            days: Delete events older than this many days

        Returns:
            Number of events deleted
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        deleted = (
            self.db.query(MarketplaceWebhookEvent)
            .filter(
                and_(
                    MarketplaceWebhookEvent.status.in_(["success", "failed"]),
                    MarketplaceWebhookEvent.created_at < cutoff,
                )
            )
            .delete()
        )

        self.db.commit()

        print(f"[DLQ] Purged {deleted} old webhook events (older than {days} days)")

        return deleted


def get_webhook_dlq(db: Session) -> WebhookDLQ:
    """
    Get WebhookDLQ instance

    Args:
        db: Database session

    Returns:
        WebhookDLQ instance
    """
    return WebhookDLQ(db)


# Convenience functions for use in webhook handlers
async def add_failed_webhook_to_dlq(
    db: Session,
    handler: str,
    payload: Dict,
    error: Exception,
    dedupe_key: Optional[str] = None,
) -> MarketplaceWebhookEvent:
    """
    Convenience function to add failed webhook to DLQ

    Args:
        db: Database session
        handler: Handler name
        payload: Webhook payload
        error: Exception that caused failure
        dedupe_key: Deduplication key (optional)

    Returns:
        Created DLQ event

    Example:
        try:
            await process_webhook(data)
        except Exception as e:
            await add_failed_webhook_to_dlq(
                db=db,
                handler="gcp_events:entitlement_created",
                payload=data,
                error=e,
                dedupe_key=message_id
            )
    """
    dlq = WebhookDLQ(db)
    return dlq.add_to_dlq(
        handler=handler,
        payload=payload,
        error_message=str(error),
        dedupe_key=dedupe_key,
    )
