"""
Update Free tier to allow 2 users instead of 1
"""
import sys
import json
sys.path.insert(0, r'C:\Users\robot\Desktop\ap2-expense-agent\backend')

from src.database import SessionLocal
from src.models_billing import BillingTier

db = SessionLocal()

try:
    # Get Free tier
    free_tier = db.query(BillingTier).filter(BillingTier.tier_name == "free").first()

    if not free_tier:
        print("ERROR: Free tier not found!")
        exit(1)

    print(f"Found Free tier: {free_tier.display_name}")

    # Parse current limits
    limits = json.loads(free_tier.limits)

    print(f"\nCurrent max_users: {limits.get('max_users')}")

    # Update max_users to 2
    limits['max_users'] = 2

    # Save back
    free_tier.limits = json.dumps(limits)
    db.commit()

    print(f"Updated max_users: {limits.get('max_users')}")
    print("\nSUCCESS: Free tier updated to allow 2 users!")

except Exception as e:
    db.rollback()
    print(f"ERROR: {e}")
    raise
finally:
    db.close()
