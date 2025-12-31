"""
Disable Enterprise tier in the database
Mark it as inactive and not public so it won't show up in pricing pages
"""
import sys
sys.path.insert(0, r'C:\Users\robot\Desktop\ap2-expense-agent\backend')

from src.database import SessionLocal
from src.models_billing import BillingTier

db = SessionLocal()

try:
    # Find Enterprise tier
    enterprise_tier = db.query(BillingTier).filter(BillingTier.tier_name == "enterprise").first()

    if not enterprise_tier:
        print("[OK] No Enterprise tier found in database - nothing to disable")
    else:
        # Mark as inactive and not public
        enterprise_tier.is_active = False
        enterprise_tier.is_public = False

        db.commit()

        print("[SUCCESS] Enterprise tier disabled successfully!")
        print(f"   Tier: {enterprise_tier.display_name}")
        print(f"   Status: is_active={enterprise_tier.is_active}, is_public={enterprise_tier.is_public}")

except Exception as e:
    db.rollback()
    print(f"[ERROR] {e}")
    raise
finally:
    db.close()
