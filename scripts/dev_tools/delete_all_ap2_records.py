#!/usr/bin/env python3
"""
Delete all AP2 records (Intent, Cart, and Payment mandates)
"""

import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

# Change to backend directory to use correct database
os.chdir('backend')

from src.database import get_db
from src.models import IntentMandate, CartMandate, PaymentMandate

def main():
    print("=" * 60)
    print("Deleting All AP2 Records")
    print("=" * 60)

    db = next(get_db())

    try:
        # Count before deletion
        intent_count = db.query(IntentMandate).count()
        cart_count = db.query(CartMandate).count()
        payment_count = db.query(PaymentMandate).count()

        print(f"\n📊 Current counts:")
        print(f"   Intent Mandates: {intent_count}")
        print(f"   Cart Mandates: {cart_count}")
        print(f"   Payment Mandates: {payment_count}")
        print(f"   Total: {intent_count + cart_count + payment_count}")

        if intent_count + cart_count + payment_count == 0:
            print("\n✓ No AP2 records found. Nothing to delete.")
            return

        # Delete in correct order (respecting foreign keys)
        print("\n🗑️  Deleting records...")

        # 1. Delete Payment Mandates first (references Cart Mandates)
        print(f"\n   Deleting {payment_count} Payment Mandates...")
        db.query(PaymentMandate).delete()
        print("   ✓ Payment Mandates deleted")

        # 2. Delete Cart Mandates (references Intent Mandates)
        print(f"   Deleting {cart_count} Cart Mandates...")
        db.query(CartMandate).delete()
        print("   ✓ Cart Mandates deleted")

        # 3. Delete Intent Mandates last
        print(f"   Deleting {intent_count} Intent Mandates...")
        db.query(IntentMandate).delete()
        print("   ✓ Intent Mandates deleted")

        # Commit the transaction
        db.commit()
        print("\n✅ All AP2 records deleted successfully!")

        # Verify deletion
        intent_remaining = db.query(IntentMandate).count()
        cart_remaining = db.query(CartMandate).count()
        payment_remaining = db.query(PaymentMandate).count()

        print(f"\n📊 Remaining counts:")
        print(f"   Intent Mandates: {intent_remaining}")
        print(f"   Cart Mandates: {cart_remaining}")
        print(f"   Payment Mandates: {payment_remaining}")
        print(f"   Total: {intent_remaining + cart_remaining + payment_remaining}")

        if intent_remaining + cart_remaining + payment_remaining == 0:
            print("\n✓ Verification passed: All AP2 records deleted")
        else:
            print("\n⚠️ Warning: Some records remain")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        db.close()

    print("\n" + "=" * 60)
    print("Deletion Complete")
    print("=" * 60)

if __name__ == "__main__":
    main()
