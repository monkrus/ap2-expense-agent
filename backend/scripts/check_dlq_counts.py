"""
Report counts of dead-lettered Marketplace events by event_type.

Usage:
    python scripts/check_dlq_counts.py --event-types gcp_webhook_events_dlq gcp_usage_report_dlq

Integration tips:
- Use --threshold to exit non-zero when any count exceeds the limit (for CI/monitoring).
- Use --json for machine-readable output.
"""

import argparse
import os
import sys
from collections import Counter
from typing import Iterable, List

# Ensure src imports resolve
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.database import SessionLocal  # type: ignore
from src.models_billing import BillingEvent  # type: ignore


def fetch_counts(event_types: Iterable[str]) -> Counter:
    db = SessionLocal()
    try:
        counter = Counter()
        for et in event_types:
            count = (
                db.query(BillingEvent)
                .filter(BillingEvent.event_type == et)
                .count()
            )
            counter[et] = count
        return counter
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--event-types",
        nargs="+",
        default=[
            "gcp_webhook_events_dlq",
            "gcp_webhook_procurement_dlq",
            "gcp_webhook_entitlement_update_dlq",
            "gcp_webhook_entitlement_cancel_dlq",
            "gcp_usage_report_dlq",
        ],
        help="Event types to count",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=-1,
        help="Fail (exit 1) if any event type exceeds this count. -1 to disable.",
    )
    parser.add_argument("--json", action="store_true", help="Output JSON instead of plain text")
    args = parser.parse_args()

    counts = fetch_counts(args.event_types)
    if args.json:
        import json

        print(json.dumps(counts, default=int))
    else:
        for et in args.event_types:
            print(f"{et}: {counts.get(et, 0)}")

    if args.threshold >= 0:
        if any(counts[et] > args.threshold for et in args.event_types):
            sys.exit(1)


if __name__ == "__main__":
    main()
