#!/usr/bin/env python3
"""
Delete all AP2 records using direct SQLite connection
"""

import sys
import sqlite3
sys.stdout.reconfigure(encoding='utf-8')

def main():
    print("=" * 60)
    print("Deleting All AP2 Records")
    print("=" * 60)

    # Connect to the backend database
    db_path = "backend/test.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Count before deletion
        cursor.execute("SELECT COUNT(*) FROM intent_mandates")
        intent_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM cart_mandates")
        cart_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM payment_mandates")
        payment_count = cursor.fetchone()[0]

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

        # 1. Delete Payment Mandates first
        print(f"\n   Deleting {payment_count} Payment Mandates...")
        cursor.execute("DELETE FROM payment_mandates")
        print("   ✓ Payment Mandates deleted")

        # 2. Delete Cart Mandates
        print(f"   Deleting {cart_count} Cart Mandates...")
        cursor.execute("DELETE FROM cart_mandates")
        print("   ✓ Cart Mandates deleted")

        # 3. Delete Intent Mandates
        print(f"   Deleting {intent_count} Intent Mandates...")
        cursor.execute("DELETE FROM intent_mandates")
        print("   ✓ Intent Mandates deleted")

        # Commit the transaction
        conn.commit()
        print("\n✅ All AP2 records deleted successfully!")

        # Verify deletion
        cursor.execute("SELECT COUNT(*) FROM intent_mandates")
        intent_remaining = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM cart_mandates")
        cart_remaining = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM payment_mandates")
        payment_remaining = cursor.fetchone()[0]

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
        conn.rollback()
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

    print("\n" + "=" * 60)
    print("Deletion Complete")
    print("=" * 60)

if __name__ == "__main__":
    main()
