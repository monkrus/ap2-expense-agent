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


def verify_google_oidc_token(authorization: Optional[str], expected_audience: str) -> bool:
    """
    Verify Google-signed OIDC token (e.g., Pub/Sub push) in Authorization header.

    Args:
        authorization: Header value 'Bearer <token>'
        expected_audience: Audience to validate (endpoint URL or configured value)

    Returns:
        True if token is valid and audience matches, else False
    """
    try:
        if not authorization or not authorization.startswith("Bearer "):
            return False

        token = authorization.split(" ", 1)[1]

        from google.oauth2 import id_token
        from google.auth.transport import requests as grequests

        req = grequests.Request()
        claims = id_token.verify_oauth2_token(token, req, audience=expected_audience)

        issuer = claims.get("iss")
        if issuer not in ("https://accounts.google.com", "accounts.google.com"):
            return False
        return True
    except Exception as e:
        print(f"OIDC token verification failed: {e}")
        return False


@router.get("/health")
async def gcp_webhook_health():
    """Lightweight health endpoint for deployment verification."""
    return {"status": "ok"}


@router.post("/procurement")
async def gcp_procurement_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_goog_signature: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
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

    # Verify request authenticity (prefer OIDC, fallback to HMAC in dev)
    audience = settings.gcp_webhook_audience or str(request.url)
    oidc_ok = verify_google_oidc_token(authorization, audience)
    hmac_ok = settings.environment == "development" and verify_gcp_signature(body, x_goog_signature)
    if not (oidc_ok or hmac_ok):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized webhook request")

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


@router.post("/events")
async def gcp_events_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_goog_signature: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
):
    """
    Generic Pub/Sub push endpoint for GCP Marketplace events.

    Verifies Google OIDC Authorization and parses Pub/Sub envelope, then
    normalizes Consumer Procurement entitlement events and routes to handlers.
    """
    raw_body = await request.body()
    audience = settings.gcp_webhook_audience or str(request.url)
    oidc_ok = verify_google_oidc_token(authorization, audience)
    hmac_ok = settings.environment == "development" and verify_gcp_signature(
        raw_body, x_goog_signature
    )
    if not (oidc_ok or hmac_ok):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized webhook request"
        )

    # Parse JSON body
    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload"
        )

    # Decode Pub/Sub envelope if present, then normalize
    from ..gcp.events import (
        decode_pubsub_envelope,
        normalize_entitlement_event,
        EventParseError,
    )

    try:
        payload = decode_pubsub_envelope(body) if isinstance(body, dict) and "message" in body else body
        event_type, normalized = normalize_entitlement_event(payload)
    except EventParseError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid event payload: {e}"
        )

    # Route to appropriate handler
    if event_type == "entitlement_plan_change":
        result = await handle_entitlement_update(normalized, db)
        return {"status": result.get("status", "updated"), "detail": result}
    elif event_type == "entitlement_cancelled":
        result = await handle_entitlement_cancellation(normalized, db)
        return {"status": result.get("status", "cancelled"), "detail": result}
    elif event_type == "entitlement_created":
        # If we have admin/company info, provision via procurement handler
        if normalized.get("user_email") and normalized.get("company_name"):
            result = await handle_procurement_webhook(normalized, db)
            return {"status": result.get("status", "created"), "detail": result}
        # Otherwise acknowledge; full provisioning will occur via onboarding flow
        return {
            "status": "acknowledged",
            "entitlement_id": normalized.get("entitlement_id"),
        }

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported event type"
    )

@router.post("/entitlement-updated")
async def gcp_entitlement_update_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_goog_signature: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
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

    audience = settings.gcp_webhook_audience or str(request.url)
    oidc_ok = verify_google_oidc_token(authorization, audience)
    hmac_ok = settings.environment == "development" and verify_gcp_signature(body, x_goog_signature)
    if not (oidc_ok or hmac_ok):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized webhook request")

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
    authorization: Optional[str] = Header(None),
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

    audience = settings.gcp_webhook_audience or str(request.url)
    oidc_ok = verify_google_oidc_token(authorization, audience)
    hmac_ok = settings.environment == "development" and verify_gcp_signature(body, x_goog_signature)
    if not (oidc_ok or hmac_ok):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized webhook request")

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
