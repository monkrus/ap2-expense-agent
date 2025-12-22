"""
Fix existing organizations to have correct max_members based on owner's subscription tier.

This script fixes the bug where all organizations were created with max_members=25
regardless of the owner's subscription tier.
"""

import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from src.database import SessionLocal
from src.models import Organization, OrganizationMember, OrganizationRole, Subscription, SubscriptionTier
from src.billing.tier_limits import get_tier_limits

def fix_organization_max_members():
    """Fix max_members for all active organizations based on owner's subscription tier"""
    db = SessionLocal()

    try:
        # Get all active organizations
        orgs = db.query(Organization).filter(Organization.is_active == True).all()

        print(f"\n{'='*80}")
        print(f"Fixing max_members for {len(orgs)} active organizations")
        print(f"{'='*80}\n")

        updated_count = 0

        for org in orgs:
            # Find the organization owner
            owner_membership = (
                db.query(OrganizationMember)
                .filter(OrganizationMember.organization_id == org.id)
                .filter(OrganizationMember.role == OrganizationRole.OWNER)
                .filter(OrganizationMember.is_active == True)
                .first()
            )

            if not owner_membership:
                print(f"WARNING: Organization '{org.name}' (slug: {org.slug}) has no owner - SKIPPING")
                continue

            # Get owner's subscription
            owner_subscription = (
                db.query(Subscription)
                .filter(Subscription.user_id == owner_membership.user_id)
                .filter(Subscription.status.in_(["active", "trialing"]))
                .first()
            )

            # Determine tier (no subscription = Free tier)
            owner_tier = owner_subscription.tier if owner_subscription else SubscriptionTier.FREE
            tier_limits = get_tier_limits(owner_tier)

            # Get correct max_members from tier
            correct_max_members = tier_limits.max_users

            # Check if update needed
            if org.max_members != correct_max_members:
                old_value = org.max_members
                org.max_members = correct_max_members
                updated_count += 1

                print(f"[UPDATED] '{org.name}' (slug: {org.slug})")
                print(f"   Tier: {owner_tier.value}")
                print(f"   Max Members: {old_value} -> {correct_max_members}")
                print()
            else:
                print(f"[OK] '{org.name}' (slug: {org.slug}) - already has correct max_members={org.max_members}")

        # Commit all changes
        if updated_count > 0:
            db.commit()
            print(f"\n{'='*80}")
            print(f"SUCCESS: Updated {updated_count} organization(s)")
            print(f"{'='*80}\n")
        else:
            print(f"\n{'='*80}")
            print(f"OK: All organizations already have correct max_members")
            print(f"{'='*80}\n")

    except Exception as e:
        db.rollback()
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

    return True

if __name__ == "__main__":
    print("\n" + "="*80)
    print("Organization max_members Fix Script")
    print("="*80)

    success = fix_organization_max_members()

    if success:
        print("\nSUCCESS: Script completed successfully")
        sys.exit(0)
    else:
        print("\nFAILED: Script failed")
        sys.exit(1)
