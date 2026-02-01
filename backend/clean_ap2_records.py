"""
Clean all AP2 records - Delete all Intent Mandates, Cart Mandates, and Payment Mandates
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import settings
from src.models import IntentMandate, CartMandate, PaymentMandate

def clean_ap2_records():
    """Delete all AP2 records from the database"""
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        print("[CLEANING] Cleaning AP2 records...")
        print()

        # Count before deletion
        intent_count = db.query(IntentMandate).count()
        cart_count = db.query(CartMandate).count()
        payment_count = db.query(PaymentMandate).count()

        print(f"Found:")
        print(f"  - {intent_count} Intent Mandates")
        print(f"  - {cart_count} Cart Mandates")
        print(f"  - {payment_count} Payment Mandates")
        print()

        if intent_count == 0 and cart_count == 0 and payment_count == 0:
            print("[OK] No AP2 records found. Database is already clean.")
            return

        # Delete in correct order (child tables first due to foreign keys)
        print("Deleting records...")

        # Delete Payment Mandates first (they reference Cart Mandates)
        deleted_payments = db.query(PaymentMandate).delete()
        print(f"  * Deleted {deleted_payments} Payment Mandates")

        # Delete Cart Mandates (they reference Intent Mandates)
        deleted_carts = db.query(CartMandate).delete()
        print(f"  * Deleted {deleted_carts} Cart Mandates")

        # Delete Intent Mandates last
        deleted_intents = db.query(IntentMandate).delete()
        print(f"  * Deleted {deleted_intents} Intent Mandates")

        # Commit the changes
        db.commit()

        print()
        print("[OK] All AP2 records cleaned successfully!")
        print("[READY] You can now start fresh with AP2 testing.")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error cleaning AP2 records: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("AP2 Records Cleanup Script")
    print("=" * 60)
    print()

    confirm = input("WARNING: This will DELETE ALL AP2 records. Continue? (yes/no): ")

    if confirm.lower() in ['yes', 'y']:
        clean_ap2_records()
    else:
        print("[ERROR] Cancelled. No records were deleted.")
