"""
Google Cloud Marketplace Webhook Routes
Handles procurement, entitlement changes, and cancellations
"""

import json
import logging
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
from ..gcp.events import (
    EventParseError,
    decode_pubsub_envelope,
    normalize_entitlement_event,
)
from ..gcp.idempotency import mark_success, record_event
from ..gcp.marketplace_client import GCPMarketplaceClient
from ..gcp.usage_reporter import run_hourly_usage_reporting
from ..services.trial_service import TrialService

router = APIRouter(prefix="/api/webhooks/gcp", tags=["gcp-webhooks"])
logger = logging.getLogger(__name__)


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
        logger.error(
            "GCP webhook secret not configured. Rejecting webhook. Set GCP_WEBHOOK_SECRET environment variable."
        )
        return False

    if not signature:
        logger.error("Missing X-Goog-Signature header. Possible forged webhook.")
        return False

    # Always verify signature, regardless of environment
    is_valid = GCPMarketplaceClient.verify_webhook_signature(
        request_body, signature, settings.gcp_webhook_secret
    )

    if not is_valid:
        logger.error(
            f"GCP webhook signature verification failed (env: {settings.environment})"
        )

    return is_valid


def verify_google_oidc_token(
    authorization: Optional[str], expected_audience: str
) -> bool:
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

        from google.auth.transport import requests as grequests
        from google.oauth2 import id_token

        req = grequests.Request()
        claims = id_token.verify_oauth2_token(token, req, audience=expected_audience)

        issuer = claims.get("iss")
        if issuer not in ("https://accounts.google.com", "accounts.google.com"):
            return False
        return True
    except Exception as e:
        logger.error(f"OIDC token verification failed: {e}", exc_info=True)
        return False


def require_oidc_or_dev_hmac(
    raw_body: bytes,
    x_signature: Optional[str],
    authorization: Optional[str],
    request_url: str,
) -> None:
    """
    Enforce Google-signed OIDC for webhook callers; allow HMAC only in development.
    """
    audience = settings.gcp_webhook_audience or request_url
    oidc_ok = verify_google_oidc_token(authorization, audience)
    hmac_ok = settings.environment == "development" and verify_gcp_signature(
        raw_body, x_signature
    )

    if settings.environment != "development" and not oidc_ok:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized webhook request (OIDC required)",
        )

    if not (oidc_ok or hmac_ok):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized webhook request",
        )


@router.get("/health")
async def gcp_webhook_health():
    """Lightweight health endpoint for deployment verification."""
    from datetime import datetime

    return {
        "status": "healthy",
        "service": "gcp-marketplace-webhooks",
        "timestamp": datetime.utcnow().isoformat(),
        "jwt_verification": "enabled",
    }


@router.post("/procurement-simple")
async def handle_procurement_simple(request: Request, db: Session = Depends(get_db)):
    """
    Simple GCP Marketplace webhook handler for testing

    This is a simplified version for local testing and development.
    Uses JWT verification without complex entitlement lookup.

    For production, use /procurement endpoint with full Consumer Procurement API.
    """
    import logging
    import secrets
    import string
    import uuid
    from datetime import datetime

    from ..gcp.jwt_verification import verify_gcp_jwt
    from ..models import (
        Organization,
        OrganizationMember,
        OrganizationRole,
        User,
        UserRole,
    )
    from ..models_billing import OrganizationSubscription

    logger = logging.getLogger(__name__)

    try:
        if settings.environment != "development":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This endpoint is only available in development",
            )

        # Step 1: Extract JWT from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(401, "Missing Bearer token")

        token = auth_header.replace("Bearer ", "")

        # Step 2: Verify JWT (skip audience check for local testing)
        expected_audience = settings.gcp_webhook_audience or str(request.url)
        claims = verify_gcp_jwt(token, audience=expected_audience)

        logger.info(
            "GCP webhook received",
            extra={
                "email": claims.get("email"),
                "sub": claims.get("sub"),
            },
        )

        # Step 3: Parse webhook body
        body = await request.json()
        event_type = body.get("eventType")
        entitlement_data = body.get("entitlement", {})

        logger.info(f"Event type: {event_type}")

        # Step 4: Handle different event types
        if event_type == "ENTITLEMENT_CREATION_REQUESTED":
            # Extract data
            entitlement_id = entitlement_data.get("name")
            account_id = entitlement_data.get("account")
            plan = entitlement_data.get("plan", "professional")
            user_email = entitlement_data.get("usageReportingId") or claims.get("email")
            company_name = entitlement_data.get("metadata", {}).get(
                "companyName", "New Organization"
            )

            if not entitlement_id or not user_email:
                raise HTTPException(400, "Missing entitlement_id or user_email")

            # Check if already created
            existing = (
                db.query(OrganizationSubscription)
                .filter_by(gcp_entitlement_id=entitlement_id)
                .first()
            )

            if existing:
                return {
                    "status": "already_exists",
                    "organization_id": existing.organization_id,
                }

            # Generate secure password (alphanumeric only, bcrypt has 72-byte limit)
            alphabet = string.ascii_letters + string.digits
            temp_password = "".join(secrets.choice(alphabet) for _ in range(16))
            # Ensure password is within bcrypt's 72-byte limit
            temp_password = temp_password[:72]

            # Create organization
            org_id = str(uuid.uuid4())
            slug = company_name.lower().replace(" ", "-") + f"-{secrets.token_hex(4)}"

            org = Organization(
                id=org_id,
                name=company_name,
                slug=slug,
                created_at=datetime.utcnow(),
                is_active=True,
            )
            db.add(org)

            # Check if user exists
            user = db.query(User).filter_by(email=user_email).first()

            if not user:
                # Create new user
                from passlib.context import CryptContext

                pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

                user = User(
                    id=str(uuid.uuid4()),
                    username=user_email.split("@")[0],
                    email=user_email,
                    hashed_password=pwd_context.hash(temp_password),
                    full_name=user_email.split("@")[0].title(),
                    role=UserRole.EMPLOYEE,
                    is_active=True,
                    created_at=datetime.utcnow(),
                )
                db.add(user)

            # Add user as organization owner
            membership = OrganizationMember(
                id=str(uuid.uuid4()),
                organization_id=org_id,
                user_id=user.id,
                role=OrganizationRole.OWNER,
                joined_at=datetime.utcnow(),
                is_active=True,
            )
            db.add(membership)

            # Create subscription
            subscription = OrganizationSubscription(
                id=str(uuid.uuid4()),
                organization_id=org_id,
                tier_id=f"gcp-{plan.lower()}",
                tier_name=plan.upper(),
                gcp_entitlement_id=entitlement_id,
                gcp_account_id=account_id,
                status="active",
                created_at=datetime.utcnow(),
            )
            db.add(subscription)

            # Commit transaction
            db.commit()

            logger.info(
                f"Created organization {org_id} for entitlement {entitlement_id}",
                extra={
                    "organization_id": org_id,
                    "user_email": user_email,
                    "plan": plan,
                },
            )

            return {
                "status": "created",
                "organization_id": org_id,
                "user_id": user.id,
                "temporary_password": temp_password,
                "message": "Organization created successfully",
            }

        elif event_type == "ENTITLEMENT_ACTIVE":
            return {"status": "success", "message": "Entitlement activated"}

        elif event_type == "ENTITLEMENT_CANCELLATION_REQUESTED":
            return {"status": "success", "message": "Cancellation handled"}

        else:
            logger.warning(f"Unknown event type: {event_type}")
            return {"status": "ignored", "message": f"Unknown event: {event_type}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook failed: {e}", exc_info=True)
        raise HTTPException(500, f"Webhook processing failed: {e}")


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

    # Verify request authenticity (OIDC required outside dev)
    require_oidc_or_dev_hmac(body, x_goog_signature, authorization, str(request.url))

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
    require_oidc_or_dev_hmac(
        raw_body, x_goog_signature, authorization, str(request.url)
    )

    # Parse JSON body
    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload"
        )

    # Decode Pub/Sub envelope if present, then normalize
    try:
        envelope = body if isinstance(body, dict) else {}
        message_id = (envelope.get("message") or {}).get("messageId")
        payload = decode_pubsub_envelope(envelope) if "message" in envelope else body
        event_type, normalized = normalize_entitlement_event(payload)
    except EventParseError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid event payload: {e}",
        )

    dedupe_key = message_id or f"{normalized.get('entitlement_id','')}|{event_type}"
    idempotency_row, created = record_event(
        db,
        handler=f"gcp_events:{event_type}",
        dedupe_key=dedupe_key,
        payload=normalized,
    )
    if not created and idempotency_row.status == "success":
        return {"status": "ok", "deduped": True}

    # Route to appropriate handler
    if event_type == "entitlement_plan_change":
        result = await handle_entitlement_update(normalized, db)
    elif event_type == "entitlement_cancelled":
        result = await handle_entitlement_cancellation(normalized, db)
    elif event_type == "entitlement_created":
        if normalized.get("user_email") and normalized.get("company_name"):
            result = await handle_procurement_webhook(normalized, db)
        else:
            result = {
                "status": "acknowledged",
                "entitlement_id": normalized.get("entitlement_id"),
            }
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported event type"
        )

    mark_success(db, idempotency_row)
    return {"status": result.get("status", "ok"), "detail": result}


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
    hmac_ok = settings.environment == "development" and verify_gcp_signature(
        body, x_goog_signature
    )
    if not (oidc_ok or hmac_ok):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized webhook request"
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

    require_oidc_or_dev_hmac(body, x_goog_signature, authorization, str(request.url))

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
