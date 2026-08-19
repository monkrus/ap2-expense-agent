#!/usr/bin/env python3
"""
Check AP2 records in database
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from backend.src.database import get_db
from backend.src.models import IntentMandate, CartMandate, PaymentMandate, User

def main():
    print("=" * 60)
    print("Checking AP2 Records")
    print("=" * 60)

    db = next(get_db())

    try:
        # Check all users
        users = db.query(User).all()
        print(f"\n📊 Total users in database: {len(users)}")

        # Check mandates per user
        for user in users:
            intent_count = db.query(IntentMandate).filter(IntentMandate.user_id == user.id).count()

            if intent_count > 0:
                print(f"\n👤 User: {user.username} (ID: {user.id})")
                print(f"   Intent Mandates: {intent_count}")

                # Check statuses
                intents = db.query(IntentMandate).filter(IntentMandate.user_id == user.id).all()
                statuses = {}
                for intent in intents:
                    statuses[intent.status] = statuses.get(intent.status, 0) + 1

                print(f"   Status breakdown:")
                for status, count in sorted(statuses.items()):
                    print(f"     - {status}: {count}")

        # Check Cart and Payment mandates
        cart_total = db.query(CartMandate).count()
        payment_total = db.query(PaymentMandate).count()

        print(f"\n📊 Other mandates:")
        print(f"   Cart Mandates: {cart_total}")
        print(f"   Payment Mandates: {payment_total}")

    finally:
        db.close()

    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
