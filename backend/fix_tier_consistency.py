"""Fix tier configuration consistency across all tiers"""
import json
from src.database import SessionLocal
from src.models_billing import BillingTier

db = SessionLocal()

print("\n" + "=" * 80)
print("FIXING TIER CONFIGURATION CONSISTENCY")
print("=" * 80 + "\n")

# Get all tiers
tiers = db.query(BillingTier).all()

# Standardized limits for each tier
tier_configs = {
    'free': {
        'max_organizations': 1,
        'max_users': 2,
        'max_expenses_per_month': 30,
        'ocr_scans_included': 20,
        'max_ai_categorizations': 0,
        'max_ap2_transactions': 20,
        'data_retention_days': 90,
        'max_receipt_size_mb': 5,
        'max_storage_gb': 1,
    },
    'starter': {
        'max_organizations': 3,
        'max_users': 5,
        'max_expenses_per_month': 50,
        'ocr_scans_included': 20,
        'max_ai_categorizations': 50,  # was ai_categorizations_included
        'max_ap2_transactions': 100,  # was ap2_transactions_included
        'data_retention_days': 365,  # 1 year
        'max_receipt_size_mb': 5,
        'max_storage_gb': 1,
    },
    'professional': {
        'max_organizations': 10,
        'max_users': 25,
        'max_expenses_per_month': 500,
        'ocr_scans_included': 200,
        'max_ai_categorizations': 500,
        'max_ap2_transactions': 1000,
        'data_retention_days': 1095,  # 3 years
        'max_receipt_size_mb': 10,
        'max_storage_gb': 10,
    },
    'enterprise': {
        'max_organizations': None,  # Unlimited (null instead of -1)
        'max_users': None,  # Unlimited
        'max_expenses_per_month': None,  # Unlimited
        'ocr_scans_included': 2000,
        'max_ai_categorizations': 5000,
        'max_ap2_transactions': 10000,
        'data_retention_days': None,  # Unlimited (keep forever)
        'max_receipt_size_mb': 50,
        'max_storage_gb': 100,
    }
}

for tier in tiers:
    tier_name = tier.tier_name.lower()

    if tier_name not in tier_configs:
        print(f"[SKIP] Unknown tier: {tier_name}")
        continue

    print(f"[UPDATE] {tier.tier_name.upper()}")

    # Get new standardized limits
    new_limits = tier_configs[tier_name]

    # Update the limits
    tier.limits = new_limits

    print(f"  Updated limits with {len(new_limits)} standardized fields")

    # Show what changed
    for key, value in sorted(new_limits.items()):
        display_value = "Unlimited" if value is None else value
        print(f"    {key}: {display_value}")

    print()

# Commit changes
try:
    db.commit()
    print("[SUCCESS] All tiers updated successfully!\n")
except Exception as e:
    db.rollback()
    print(f"[ERROR] Failed to update tiers: {e}\n")

# Verify changes
print("=" * 80)
print("VERIFICATION: UPDATED TIER CONFIGURATIONS")
print("=" * 80 + "\n")

tiers = db.query(BillingTier).order_by(BillingTier.base_price_monthly).all()

for tier in tiers:
    limits = tier.limits if isinstance(tier.limits, dict) else json.loads(tier.limits or '{}')
    print(f"{tier.tier_name.upper()}: {len(limits)} limit fields")

    # Check for required fields
    required_fields = [
        'max_organizations',
        'max_users',
        'max_expenses_per_month',
        'ocr_scans_included',
        'max_ai_categorizations',
        'max_ap2_transactions',
        'data_retention_days'
    ]

    missing = [f for f in required_fields if f not in limits]
    if missing:
        print(f"  [WARNING] Missing fields: {missing}")
    else:
        print(f"  [OK] All required fields present")

print("\n" + "=" * 80)

db.close()
