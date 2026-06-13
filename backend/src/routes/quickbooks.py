"""
QuickBooks Online integration routes.

Handles OAuth2 connect/disconnect, expense sync, and account mapping.
"""

import hashlib
import hmac
import logging
import secrets
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..config import settings
from ..database import get_db
from ..models import OrganizationMember, User
from ..models_billing import QuickBooksConnection
from ..quickbooks.qb_client import QuickBooksClient
from ..quickbooks.qb_sync import QuickBooksSync
from ..quickbooks.token_encryption import encrypt_token

# In-memory store for OAuth state tokens (TTL-based)
# In production, use Redis or DB-backed store
_oauth_states: dict[str, dict] = {}

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/quickbooks", tags=["quickbooks"])

qb_client = QuickBooksClient()


def _get_org_id_for_user(db: Session, user_id: str) -> str:
    """Get org ID for user, raise 404 if not in any org."""
    member = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.user_id == user_id,
            OrganizationMember.is_active == True,
        )
        .first()
    )
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not part of any organization",
        )
    return member.organization_id


def _require_admin(db: Session, user_id: str, org_id: str):
    """Require user to be owner or admin of the org."""
    member = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.user_id == user_id,
            OrganizationMember.organization_id == org_id,
        )
        .first()
    )
    if not member or member.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners/admins can manage QuickBooks integration",
        )


def _create_oauth_state(org_id: str, user_id: str) -> str:
    """Generate a CSRF-safe OAuth state token and store it server-side."""
    # Clean expired states
    now = datetime.utcnow()
    expired = [k for k, v in _oauth_states.items() if v["expires"] < now]
    for k in expired:
        del _oauth_states[k]

    csrf_token = secrets.token_urlsafe(32)
    _oauth_states[csrf_token] = {
        "org_id": org_id,
        "user_id": user_id,
        "expires": now + timedelta(minutes=10),
    }
    return csrf_token


def _validate_oauth_state(state: str) -> dict:
    """Validate and consume a CSRF state token. Returns org_id and user_id."""
    data = _oauth_states.pop(state, None)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state",
        )
    if data["expires"] < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth state expired",
        )
    return data


@router.get("/connect")
async def connect_quickbooks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start QuickBooks OAuth2 flow. Returns authorization URL."""
    if not settings.quickbooks_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="QuickBooks integration not configured",
        )

    org_id = _get_org_id_for_user(db, current_user.id)
    _require_admin(db, current_user.id, org_id)

    state = _create_oauth_state(org_id, current_user.id)
    auth_url = qb_client.get_authorization_url(state=state)

    return {"authorization_url": auth_url}


@router.get("/callback")
async def quickbooks_callback(
    code: str,
    state: str,
    realmId: str,
    db: Session = Depends(get_db),
):
    """Handle QuickBooks OAuth2 callback. Exchanges code for tokens."""
    # Validate CSRF state token
    state_data = _validate_oauth_state(state)
    org_id = state_data["org_id"]
    user_id = state_data["user_id"]

    try:
        tokens = await qb_client.exchange_code(code)
    except Exception as e:
        logger.error(f"QuickBooks token exchange failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to connect to QuickBooks",
        )

    # Upsert the connection
    connection = (
        db.query(QuickBooksConnection)
        .filter(QuickBooksConnection.organization_id == org_id)
        .first()
    )

    encrypted_access = encrypt_token(tokens["access_token"])
    encrypted_refresh = encrypt_token(tokens["refresh_token"])

    if connection:
        connection.realm_id = realmId
        connection.access_token = encrypted_access
        connection.refresh_token = encrypted_refresh
        connection.token_expires_at = tokens["token_expires_at"]
        connection.sync_enabled = True
        connection.updated_at = datetime.utcnow()
    else:
        connection = QuickBooksConnection(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            realm_id=realmId,
            access_token=encrypted_access,
            refresh_token=encrypted_refresh,
            token_expires_at=tokens["token_expires_at"],
            sync_enabled=True,
        )
        db.add(connection)

    db.commit()
    logger.info(f"QuickBooks connected for org {org_id}, realm {realmId}")

    # Redirect to frontend settings page
    frontend_url = settings.frontend_url or "http://localhost:5173"
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url=f"{frontend_url}/integrations?qb=connected")


@router.delete("/disconnect")
async def disconnect_quickbooks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Disconnect QuickBooks from the organization."""
    org_id = _get_org_id_for_user(db, current_user.id)
    _require_admin(db, current_user.id, org_id)

    connection = (
        db.query(QuickBooksConnection)
        .filter(QuickBooksConnection.organization_id == org_id)
        .first()
    )

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No QuickBooks connection found",
        )

    db.delete(connection)
    db.commit()
    logger.info(f"QuickBooks disconnected for org {org_id}")

    return {"success": True, "message": "QuickBooks disconnected"}


@router.get("/status")
async def quickbooks_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get QuickBooks connection and sync status."""
    org_id = _get_org_id_for_user(db, current_user.id)
    sync = QuickBooksSync(db)
    return await sync.get_sync_status(org_id)


@router.post("/sync")
async def trigger_sync(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually trigger sync of approved expenses to QuickBooks."""
    org_id = _get_org_id_for_user(db, current_user.id)
    _require_admin(db, current_user.id, org_id)

    sync = QuickBooksSync(db)
    results = await sync.sync_pending_expenses(org_id)

    synced = sum(1 for r in results if r.get("synced"))
    return {
        "total": len(results),
        "synced": synced,
        "failed": len(results) - synced,
        "details": results,
    }


@router.get("/accounts")
async def get_qb_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get expense accounts from QuickBooks for category mapping."""
    org_id = _get_org_id_for_user(db, current_user.id)

    connection = (
        db.query(QuickBooksConnection)
        .filter(QuickBooksConnection.organization_id == org_id)
        .first()
    )
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No QuickBooks connection found",
        )

    sync = QuickBooksSync(db)
    access_token = await sync._ensure_fresh_token(connection)

    accounts = await qb_client.get_accounts(connection.realm_id, access_token)
    return {
        "accounts": [
            {"id": a["Id"], "name": a["Name"], "type": a.get("AccountSubType", "")}
            for a in accounts
        ]
    }


@router.get("/vendors")
async def get_qb_vendors(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get vendors from QuickBooks."""
    org_id = _get_org_id_for_user(db, current_user.id)

    connection = (
        db.query(QuickBooksConnection)
        .filter(QuickBooksConnection.organization_id == org_id)
        .first()
    )
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No QuickBooks connection found",
        )

    sync = QuickBooksSync(db)
    access_token = await sync._ensure_fresh_token(connection)

    vendors = await qb_client.get_vendors(connection.realm_id, access_token)
    return {"vendors": [{"id": v["Id"], "name": v["DisplayName"]} for v in vendors]}


def _verify_intuit_signature(payload_body: bytes, signature: str) -> bool:
    """Verify Intuit webhook HMAC-SHA256 signature."""
    verifier_token = settings.quickbooks_webhook_verifier_token
    if not verifier_token:
        logger.warning(
            "Intuit webhook verifier token not configured, skipping verification"
        )
        return True
    expected = hmac.new(
        verifier_token.encode("utf-8"),
        payload_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/webhook/disconnect")
async def intuit_disconnect_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Handle Intuit App Center disconnect webhook.

    When a user disconnects the app from Intuit's side (My Apps page),
    Intuit sends a POST with the realmId. We clean up stored tokens.
    Validates the X-Intuit-Signature HMAC header before processing.
    """
    payload_body = await request.body()
    signature = request.headers.get("intuit-signature", "")

    if settings.quickbooks_webhook_verifier_token and not _verify_intuit_signature(
        payload_body, signature
    ):
        logger.warning("Intuit webhook signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        import json

        payload = json.loads(payload_body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payload")

    # Intuit sends {"eventNotifications": [{"realmId": "...", "dataChangeEvent": {...}}]}
    notifications = payload.get("eventNotifications", [])
    if not notifications:
        # Simple disconnect payload: {"realmId": "123456"}
        realm_id = payload.get("realmId")
        if realm_id:
            notifications = [{"realmId": realm_id}]

    for notification in notifications:
        realm_id = notification.get("realmId")
        if not realm_id:
            continue

        connection = (
            db.query(QuickBooksConnection)
            .filter(QuickBooksConnection.realm_id == realm_id)
            .first()
        )
        if connection:
            org_id = connection.organization_id
            db.delete(connection)
            db.commit()
            logger.info(
                f"QuickBooks disconnected via Intuit webhook for org {org_id}, "
                f"realm {realm_id}"
            )

    return {"status": "ok"}
