"""Check all billing tiers configuration"""
import json
from src.database import SessionLocal
from src.models_billing import BillingTier

db = SessionLocal()

print("\n" + "=" * 100)
print("ALL BILLING TIERS CONFIGURATION")
print("=" * 100 + "\n")

tiers = db.query(BillingTier).order_by(BillingTier.base_price_monthly).all()

print(f"Total Tiers Found: {len(tiers)}\n")

for tier in tiers:
    print("-" * 100)
    print(f"TIER: {tier.tier_name.upper()}")
    print("-" * 100)
    print(f"Display Name:    {tier.display_name}")
    print(f"Price:           ${tier.base_price_monthly:.2f} {tier.currency}/month")
    print(f"Description:     {tier.description}")
    print(f"Active:          {tier.is_active}")
    print(f"Public:          {tier.is_public}")

    # Parse limits
    limits = tier.limits if isinstance(tier.limits, dict) else json.loads(tier.limits or '{}')

    print(f"\nLIMITS:")
    for key, value in sorted(limits.items()):
        key_formatted = key.replace('_', ' ').title()
        print(f"  {key_formatted:<35} {value}")

    # Parse features
    features = tier.features if isinstance(tier.features, list) else json.loads(tier.features or '[]')

    print(f"\nFEATURES:")
    if isinstance(features, list):
        for feature in features:
            print(f"  - {feature}")
    elif isinstance(features, dict):
        for key, value in sorted(features.items()):
            status = "[OK]" if value else "[X]"
            print(f"  {status} {key}")

    # Parse overage pricing
    overage = tier.overage_pricing if isinstance(tier.overage_pricing, dict) else json.loads(tier.overage_pricing or '{}')

    if overage:
        print(f"\nOVERAGE PRICING:")
        for key, value in sorted(overage.items()):
            key_formatted = key.replace('_', ' ').title()
            print(f"  {key_formatted:<35} ${value}")
    else:
        print(f"\nOVERAGE PRICING: None (hard limits)")

    print()

print("=" * 100)

# Summary table
print("\nSUMMARY COMPARISON TABLE")
print("=" * 100)

comparison_fields = [
    'max_organizations',
    'max_users',
    'max_expenses_per_month',
    'ocr_scans_included',
    'max_ai_categorizations',
    'max_ap2_transactions',
    'data_retention_days'
]

print(f"{'Limit':<35}", end='')
for tier in tiers:
    print(f"{tier.tier_name.upper():<20}", end='')
print()
print("-" * 100)

for field in comparison_fields:
    field_name = field.replace('_', ' ').title()
    print(f"{field_name:<35}", end='')

    for tier in tiers:
        limits = tier.limits if isinstance(tier.limits, dict) else json.loads(tier.limits or '{}')
        value = limits.get(field, 'N/A')

        if value == 'unlimited' or value is None:
            display = 'Unlimited'
        else:
            display = str(value)

        print(f"{display:<20}", end='')
    print()

print("\n" + "=" * 100)

db.close()
