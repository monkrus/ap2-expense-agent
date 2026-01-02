"""
Backfill subscriptions for organizations that don't have one
Creates a Free tier subscription for all active organizations without subscriptions
"""
import sys
from pathlib import Path

# Add parent directory to path so we can import from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
import uuid
from src.database import SessionLocal
from src.models import Organization
from src.models_billing import BillingTier, OrganizationSubscription


def backfill_subscriptions():
    """Create Free tier subscriptions for organizations that don't have one"""
    db = SessionLocal()

    try:
        # Get Free tier
        free_tier = (
            db.query(BillingTier)
            .filter(BillingTier.tier_name == "free", BillingTier.is_active == True)
            .first()
        )

        if not free_tier:
            print("ERROR: Free tier not found!")
            print("Please run: python scripts/seed_billing_tiers.py")
            return

        print(f"Found Free tier: {free_tier.tier_name} (${free_tier.base_price_monthly}/mo)")

        # Get all active organizations
        orgs = db.query(Organization).filter(Organization.is_active == True).all()
        print(f"\nFound {len(orgs)} active organizations")

        # Check which ones have subscriptions
        created_count = 0
        skipped_count = 0

        for org in orgs:
            # Check if subscription exists
            existing_sub = (
                db.query(OrganizationSubscription)
                .filter(OrganizationSubscription.organization_id == org.id)
                .first()
            )

            if existing_sub:
                print(f"  ✓ {org.name} ({org.slug}) - already has subscription ({existing_sub.tier_name})")
                skipped_count += 1
                continue

            # Create subscription
            subscription = OrganizationSubscription(
                id=str(uuid.uuid4()),
                organization_id=org.id,
                tier_id=free_tier.id,
                tier_name=free_tier.tier_name,
                status="active",
                billing_period_start=datetime.utcnow(),
            )
            db.add(subscription)
            print(f"  + {org.name} ({org.slug}) - created Free tier subscription")
            created_count += 1

        if created_count > 0:
            db.commit()
            print(f"\n✅ Created {created_count} new subscriptions")
        else:
            print(f"\n✅ All organizations already have subscriptions")

        if skipped_count > 0:
            print(f"   Skipped {skipped_count} organizations (already had subscriptions)")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Backfilling Subscriptions for Organizations")
    print("=" * 60)
    backfill_subscriptions()
