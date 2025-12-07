"""
Replay dead-lettered GCP Marketplace webhook/usage events from BillingEvent.

Usage (examples):
    python scripts/replay_dlq.py --event-type gcp_webhook_events_dlq --limit 5
    python scripts/replay_dlq.py --event-type gcp_usage_report_dlq --target-url https://your-app.run.app/api/webhooks/gcp/events

Optional signing:
    --hmac-secret <secret>   # adds X-Goog-Signature header (legacy/dev)
    --bearer <token>         # adds Authorization: Bearer <token> header
    --service-account-key sa.json --audience https://your-app.run.app/api/webhooks/gcp/events  # mint Google ID token for prod
"""

import argparse
import hashlib
import hmac
import json
import os
import sys
from typing import Dict, List, Optional

import requests
from google.auth.transport.requests import Request  # type: ignore
from google.oauth2 import service_account  # type: ignore

# Ensure src import works when run from repo root
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.database import SessionLocal  # type: ignore
from src.models_billing import BillingEvent  # type: ignore


def _sign_body(body: bytes, secret: Optional[str]) -> Optional[str]:
    if not secret:
        return None
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def fetch_dlq_events(event_type: str, limit: int) -> List[BillingEvent]:
    db = SessionLocal()
    try:
        events = (
            db.query(BillingEvent)
            .filter(BillingEvent.event_type == event_type)
            .order_by(BillingEvent.occurred_at.desc())
            .limit(limit)
            .all()
        )
        return events
    finally:
        db.close()


def replay_event(
    target_url: str,
    payload: Dict,
    bearer: Optional[str] = None,
    hmac_secret: Optional[str] = None,
) -> requests.Response:
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    sig = _sign_body(body, hmac_secret)
    if sig:
        headers["X-Goog-Signature"] = sig
    return requests.post(target_url, data=body, headers=headers, timeout=30)


def build_bearer_from_service_account(
    key_path: Optional[str], audience: Optional[str]
) -> Optional[str]:
    if not key_path or not audience:
        return None
    creds = service_account.IDTokenCredentials.from_service_account_file(
        key_path, target_audience=audience
    )
    creds.refresh(Request())
    return creds.token


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-type", required=True, help="BillingEvent.event_type to replay")
    parser.add_argument("--limit", type=int, default=10, help="Max events to replay")
    parser.add_argument(
        "--target-url",
        default=os.getenv("DLQ_REPLAY_TARGET", "http://localhost:8000/api/webhooks/gcp/events"),
    )
    parser.add_argument("--bearer", help="Authorization bearer token to include")
    parser.add_argument("--hmac-secret", help="HMAC secret to sign body (dev/legacy)")
    parser.add_argument("--service-account-key", help="Path to service account key for ID token auth")
    parser.add_argument(
        "--audience",
        help="Audience for ID token (use webhook URL). If not set, defaults to target-url when --service-account-key is provided.",
    )
    args = parser.parse_args()

    # If SA key provided, mint ID token unless bearer already set
    if not args.bearer and args.service_account_key:
        audience = args.audience or args.target_url
        args.bearer = build_bearer_from_service_account(args.service_account_key, audience)

    events = fetch_dlq_events(args.event_type, args.limit)
    if not events:
        print(f"No events found for type {args.event_type}")
        return

    print(f"Replaying {len(events)} events to {args.target_url}")
    for ev in events:
        payload = ev.event_data if isinstance(ev.event_data, dict) else {}
        resp = replay_event(
            args.target_url,
            payload,
            bearer=args.bearer,
            hmac_secret=args.hmac_secret,
        )
        status = resp.status_code
        print(f"- Event {ev.id} -> {status}")
        if status >= 300:
            try:
                print(f"  Error: {resp.text}")
            except Exception:
                pass


if __name__ == "__main__":
    main()
