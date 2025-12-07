"""
GCP Marketplace Events parsing utilities
Parses Pub/Sub push envelopes and normalizes Consumer Procurement events
"""

import base64
import json
from typing import Any, Dict, Optional, Tuple


class EventParseError(Exception):
    pass


def decode_pubsub_envelope(envelope: Dict[str, Any]) -> Dict[str, Any]:
    """Decode Pub/Sub push envelope and return inner JSON payload dict."""
    try:
        message = envelope.get("message", {})
        data_b64 = message.get("data")
        if not data_b64:
            raise EventParseError("Missing message.data in Pub/Sub envelope")
        data_bytes = base64.b64decode(data_b64)
        return json.loads(data_bytes.decode("utf-8"))
    except Exception as e:
        raise EventParseError(f"Failed to decode Pub/Sub envelope: {e}")


def _normalize_entitlement_name(name: str) -> str:
    """Strip provider prefix to return bare entitlement id."""
    if not name:
        return name
    # Expected format: providers/{project}/entitlements/{id}
    parts = name.split("/")
    return parts[-1] if parts else name


def normalize_entitlement_event(payload: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    Normalize Consumer Procurement entitlement events to internal handler payloads.

    Returns:
        (event_type, normalized_payload)
        event_type in { 'entitlement_plan_change', 'entitlement_cancelled', 'entitlement_created' }
    """
    # Attempt to extract common fields across entitlement events
    # Known keys seen in procurement payloads:
    # - eventType, entitlement (object with name/id/state/plan/etc.)
    # - entitlementId, accountId, state, oldPlan, newPlan, effectiveTime
    event_type = payload.get("eventType") or payload.get("type") or ""

    entitlement = payload.get("entitlement") or {}
    entitlement_id_raw = (
        payload.get("entitlementId")
        or entitlement.get("id")
        or entitlement.get("name")
        or ""
    )
    entitlement_id = _normalize_entitlement_name(entitlement_id_raw)
    account_id = payload.get("accountId") or entitlement.get("accountId")
    state = payload.get("state") or entitlement.get("state")
    old_plan = payload.get("oldPlan") or payload.get("previousPlan")
    new_plan = (
        payload.get("newPlan")
        or payload.get("plan")
        or entitlement.get("plan")
        or entitlement.get("planName")
    )
    effective_at = (
        payload.get("effectiveTime")
        or payload.get("effective_at")
        or payload.get("eventTime")
    )

    # Optional customer/admin hints for provisioning
    user_email = (
        payload.get("user_email")
        or payload.get("userEmail")
        or payload.get("adminEmail")
        or (payload.get("customer") or {}).get("email")
    )
    company_name = (
        payload.get("company_name")
        or payload.get("companyName")
        or (payload.get("customer") or {}).get("company")
        or (payload.get("account") or {}).get("displayName")
    )

    # Heuristics to classify event
    et = event_type.upper()
    if "PLAN_CHANGE" in et or (old_plan and new_plan and old_plan != new_plan):
        return (
            "entitlement_plan_change",
            {
                "entitlement_id": entitlement_id,
                "account_id": account_id,
                "old_plan": old_plan,
                "new_plan": new_plan,
                "effective_at": effective_at,
            },
        )

    if "CANCEL" in et or (state and state.upper() in ("CANCELLED", "CANCELED")):
        return (
            "entitlement_cancelled",
            {
                "entitlement_id": entitlement_id,
                "account_id": account_id,
                "cancellation_reason": payload.get("reason") or "customer_requested",
                "effective_at": effective_at,
            },
        )

    # Fallback: creation/activation
    if (state and state.upper() in ("ACTIVE", "ENTITLED")) or "CREATE" in et:
        created = {
            "entitlement_id": entitlement_id,
            "account_id": account_id,
            "plan": new_plan,
            "state": state,
        }
        if user_email:
            created["user_email"] = user_email
        if company_name:
            created["company_name"] = company_name
        return ("entitlement_created", created)

    # Unknown event
    raise EventParseError(f"Unrecognized entitlement event: {payload}")
