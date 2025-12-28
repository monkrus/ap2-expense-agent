"""
Update the Free tier to allow 2 users instead of 1
"""
import sys
import os
import json

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import settings
from src.models_billing import BillingTier

def update_free_tier():
    """Update Free tier to allow 2 users."""
    print("=" * 80)
    print("Updating Free Tier - Changing max_users from 1 to 2")
    print("=" * 80)
    print()

    # Create engine and session
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Find the free tier
        free_tier = db.query(BillingTier).filter(
            BillingTier.tier_name == "free"
        ).first()

        if not free_tier:
            print("[X] Free tier not found in database!")
            print("    Please run: python backend/scripts/seed_billing_tiers.py")
            return False

        # Parse current limits
        current_limits = json.loads(free_tier.limits) if isinstance(free_tier.limits, str) else free_tier.limits

        print(f"Current limits: {json.dumps(current_limits, indent=2)}")
        print()

        # Update max_users to 2
        current_limits["max_users"] = 2
        free_tier.limits = json.dumps(current_limits)

        # Update description
        free_tier.description = "Free tier with basic features - test approval workflows with 2 users"

        # Commit changes
        db.commit()

        print("[+] Successfully updated Free tier!")
        print(f"    max_users: 1 -> 2")
        print(f"    Description updated to mention 2 users")
        print()

        # Verify update
        db.refresh(free_tier)
        updated_limits = json.loads(free_tier.limits) if isinstance(free_tier.limits, str) else free_tier.limits
        print("Updated limits:")
        print(json.dumps(updated_limits, indent=2))

        return True

    except Exception as e:
        db.rollback()
        print(f"[X] Error updating free tier: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    try:
        success = update_free_tier()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[X] Failed to update free tier: {str(e)}")
        sys.exit(1)
