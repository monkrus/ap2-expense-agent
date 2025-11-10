"""
Google Cloud Marketplace Webhook Routes
Handles procurement, entitlement changes, and cancellations
"""

import json
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..gcp import (
    handle_entitlement_cancellation,
    handle_entitlement_update,
    handle_procurement_webhook,
)
from ..gcp.marketplace_client import GCPMarketplaceClient
from ..gcp.usage_reporter import run_hourly_usage_reporting
from ..services.trial_service import TrialService

router = APIRouter(prefix="/api/webhooks/gcp", tags=["gcp-webhooks"])


def verify_gcp_signature(request_body: bytes, signature: Optional[str]) -> bool:
    """
    Verify that webhook request came from Google

    Args:
        request_body: Raw request body
        signature: X-Goog-Signature header value

    Returns:
        True if valid, False otherwise

    Security:
    - NEVER bypasses signature verification in any environment
    - Use test webhook secret for development/testing
    - Fails closed if secret not configured
    """
    if not settings.gcp_webhook_secret:
        # SECURITY: Fail closed - never allow unsigned webhooks
        print("ERROR: GCP webhook secret not configured. Rejecting webhook.")
        print(
            "Set GCP_WEBHOOK_SECRET environment variable with test or production secret."
        )
        return False

    if not signature:
        print("ERROR: Missing X-Goog-Signature header. Possible forged webhook.")
        return False

    # Always verify signature, regardless of environment
    is_valid = GCPMarketplaceClient.verify_webhook_signature(
        request_body, signature, settings.gcp_webhook_secret
    )

    if not is_valid:
        print(
            f"ERROR: GCP webhook signature verification failed (env: {settings.environment})"
        )

    return is_valid


@router.post("/procurement")
async def gcp_procurement_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_goog_signature: Optional[str] = Header(None),
):
    """
    Handle new customer signup from GCP Marketplace

    Called when:
    - Company clicks "Subscribe" on GCP Marketplace
    - Google provisions the infrastructure
    - Customer account needs to be created

    Expected payload:
    {
        "entitlement_id": "ent_abc123",
        "account_id": "acct_456",
        "plan": "professional",
        "user_email": "admin@company.com",
        "company_name": "Acme Corp",
        "state": "ACTIVE"
    }

    Returns:
    {
        "status": "created",
        "organization_id": "org_xyz",
        "admin_email": "admin@company.com"
    }
    """
    # Get raw body for signature verification
    body = await request.body()

    # Verify signature
    if not verify_gcp_signature(body, x_goog_signature):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook signature"
        )

    # Parse payload
    try:
        webhook_data = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload"
        )

    # Process procurement
    try:
        result = await handle_procurement_webhook(webhook_data, db)
        return result

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process procurement: {str(e)}",
        )


@router.post("/entitlement-updated")
async def gcp_entitlement_update_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_goog_signature: Optional[str] = Header(None),
):
    """
    Handle tier upgrade/downgrade from GCP Marketplace

    Called when:
    - Customer changes their plan in GCP Console
    - Google updates the entitlement

    Expected payload:
    {
        "entitlement_id": "ent_abc123",
        "account_id": "acct_456",
        "new_plan": "enterprise",
        "old_plan": "professional",
        "effective_at": "2025-10-31T12:00:00Z"
    }

    Returns:
    {
        "status": "updated",
        "old_tier": "professional",
        "new_tier": "enterprise"
    }
    """
    # Get raw body for signature verification
    body = await request.body()

    # Verify signature
    if not verify_gcp_signature(body, x_goog_signature):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook signature"
        )

    # Parse payload
    try:
        webhook_data = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload"
        )

    # Process entitlement update
    try:
        result = await handle_entitlement_update(webhook_data, db)
        return result

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process entitlement update: {str(e)}",
        )


@router.post("/entitlement-cancelled")
async def gcp_entitlement_cancel_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_goog_signature: Optional[str] = Header(None),
):
    """
    Handle subscription cancellation from GCP Marketplace

    Called when:
    - Customer cancels their subscription
    - Grace period starts (7 days to export data)

    Expected payload:
    {
        "entitlement_id": "ent_abc123",
        "account_id": "acct_456",
        "cancellation_reason": "customer_requested",
        "effective_at": "2025-11-30T23:59:59Z"
    }

    Returns:
    {
        "status": "cancelled",
        "organization_id": "org_xyz",
        "grace_period_days": 7
    }
    """
    # Get raw body for signature verification
    body = await request.body()

    # Verify signature
    if not verify_gcp_signature(body, x_goog_signature):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook signature"
        )

    # Parse payload
    try:
        webhook_data = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload"
        )

    # Process cancellation
    try:
        result = await handle_entitlement_cancellation(webhook_data, db)
        return result

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process cancellation: {str(e)}",
        )


@router.post("/report-usage")
async def gcp_report_usage_cron(
    request: Request,
    db: Session = Depends(get_db),
    x_cloudscheduler: Optional[str] = Header(None),
):
    """
    Hourly usage reporting to GCP Marketplace

    This endpoint is called by Cloud Scheduler every hour.
    It aggregates usage for all organizations and reports to GCP.

    Security:
    - Only accepts requests from Cloud Scheduler
    - Validates X-CloudScheduler header

    Returns:
    {
        "timestamp": "2025-10-31T12:00:00Z",
        "total_subscriptions": 50,
        "successful": [...],
        "failed": [...],
        "skipped": [...]
    }
    """
    # Verify request is from Cloud Scheduler
    if settings.environment == "production":
        if not x_cloudscheduler:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized: Not from Cloud Scheduler",
            )

    try:
        # Run hourly reporting
        results = await run_hourly_usage_reporting(db)
        return results

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to report usage: {str(e)}",
        )


@router.get("/health")
async def gcp_webhook_health():
    """
    Health check for GCP webhooks

    Used by Google to verify endpoint is reachable
    """
    return {
        "status": "healthy",
        "service": "gcp-marketplace-webhooks",
        "timestamp": str(datetime.utcnow()),
    }


@router.post("/process-trials")
async def process_trials(
    request: Request,
    db: Session = Depends(get_db),
    x_cloudscheduler: Optional[str] = Header(None, alias="X-CloudScheduler"),
):
    """
    Process expiring and expired trials (called by Cloud Scheduler)

    This endpoint should be called daily by a cron job to:
    - Send warnings for expiring trials (7, 3, 1 day before)
    - Convert or suspend expired trials

    Security: Verifies X-CloudScheduler header
    """
    # Verify this is from Cloud Scheduler (or allow in dev mode)
    if settings.environment != "development" and not x_cloudscheduler:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Endpoint only accessible by Cloud Scheduler",
        )

    try:
        trial_service = TrialService(db)

        # Process expiring trials (send warnings)
        expiring_result = trial_service.process_expiring_trials()

        # Process expired trials (convert or suspend)
        expired_result = trial_service.process_expired_trials()

        return {
            "status": "success",
            "timestamp": str(datetime.utcnow()),
            "expiring_trials": expiring_result,
            "expired_trials": expired_result,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process trials: {str(e)}",
        )


from datetime import datetime
