#!/usr/bin/env python3
"""
Backfill Free subscriptions for existing users who don't have one
This ensures all users have a subscription for usage tracking
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from datetime import datetime, timedelta
from src.database import SessionLocal
from src.models import User, SubscriptionTier
from src.billing import SubscriptionService

def backfill_free_subscriptions():
    """Create Free subscriptions for all users without subscriptions"""
    db = SessionLocal()

    try:
        subscription_service = SubscriptionService(db)

        # Get all users
        all_users = db.query(User).all()

        backfilled = 0
        skipped = 0
        errors = 0

        for user in all_users:
            # Check if user already has a subscription
            existing_sub = subscription_service.get_active_subscription(user.id)

            if existing_sub:
                print(f"SKIP: {user.username} already has subscription (tier={existing_sub.tier.value})")
                skipped += 1
                continue

            # Create Free subscription
            try:
                subscription = subscription_service.create_subscription(
                    user_id=user.id,
                    tier=SubscriptionTier.FREE,
                    trial_days=0
                )
                print(f"CREATED: Free subscription for {user.username} (id={subscription.id})")
                backfilled += 1
            except Exception as e:
                print(f"ERROR: Failed to create subscription for {user.username}: {e}")
                errors += 1

        print("\n" + "="*70)
        print("BACKFILL COMPLETE")
        print("="*70)
        print(f"Total users: {len(all_users)}")
        print(f"Created subscriptions: {backfilled}")
        print(f"Already had subscriptions: {skipped}")
        print(f"Errors: {errors}")
        print("="*70)

    finally:
        db.close()

if __name__ == "__main__":
    print("="*70)
    print("BACKFILLING FREE SUBSCRIPTIONS FOR EXISTING USERS")
    print("="*70)
    print()
    backfill_free_subscriptions()
