import base64
import json

import pytest

from src.gcp.events import (EventParseError, decode_pubsub_envelope,
                            normalize_entitlement_event)


def make_envelope(payload: dict) -> dict:
    data = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
    return {"message": {"data": data}}


def test_decode_pubsub_envelope_roundtrip():
    payload = {"foo": "bar", "n": 123}
    env = make_envelope(payload)
    assert decode_pubsub_envelope(env) == payload


def test_normalize_plan_change_by_fields():
    payload = {
        "eventType": "ENTITLEMENT_PLAN_CHANGE",
        "entitlementId": "ent_1",
        "oldPlan": "starter",
        "newPlan": "pro",
        "effectiveTime": "2025-11-30T00:00:00Z",
    }
    et, normalized = normalize_entitlement_event(payload)
    assert et == "entitlement_plan_change"
    assert normalized["entitlement_id"] == "ent_1"
    assert normalized["old_plan"] == "starter"
    assert normalized["new_plan"] == "pro"


def test_normalize_cancel_by_state():
    payload = {
        "eventType": "ENTITLEMENT_UPDATE",
        "entitlement": {"id": "ent_2", "state": "CANCELLED"},
        "reason": "customer_requested",
    }
    et, normalized = normalize_entitlement_event(payload)
    assert et == "entitlement_cancelled"
    assert normalized["entitlement_id"] == "ent_2"
    assert normalized["cancellation_reason"] == "customer_requested"


def test_normalize_created_active_state():
    payload = {
        "type": "ENTITLEMENT_UPDATE",
        "entitlement": {"id": "ent_3", "state": "ACTIVE", "plan": "professional"},
    }
    et, normalized = normalize_entitlement_event(payload)
    assert et == "entitlement_created"
    assert normalized["entitlement_id"] == "ent_3"
    assert normalized["plan"] == "professional"


def test_normalize_creation_with_admin_info():
    payload = {
        "eventType": "ENTITLEMENT_CREATE",
        "entitlement": {"id": "ent_9", "state": "ACTIVE", "plan": "starter"},
        "userEmail": "owner@example.com",
        "companyName": "Example Co",
    }
    et, normalized = normalize_entitlement_event(payload)
    assert et == "entitlement_created"
    assert normalized["user_email"] == "owner@example.com"
    assert normalized["company_name"] == "Example Co"


def test_decode_pubsub_missing_data():
    with pytest.raises(EventParseError):
        decode_pubsub_envelope({"message": {}})


def test_normalize_unrecognized_event():
    with pytest.raises(EventParseError):
        normalize_entitlement_event({"eventType": "UNKNOWN_EVENT", "foo": "bar"})
