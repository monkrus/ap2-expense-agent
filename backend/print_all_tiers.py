"""
Print comprehensive table of all billing tiers
"""
import sys
import json
sys.path.insert(0, r'C:\Users\robot\Desktop\ap2-expense-agent\backend')

from src.database import SessionLocal
from src.models_billing import BillingTier

db = SessionLocal()

try:
    # Get all tiers ordered by price
    tiers = db.query(BillingTier).order_by(BillingTier.base_price_monthly).all()

    print("\n" + "=" * 120)
    print("BILLING TIERS - COMPLETE SETTINGS")
    print("=" * 120)

    for tier in tiers:
        # Parse JSON fields
        limits = json.loads(tier.limits) if isinstance(tier.limits, str) else tier.limits
        features = json.loads(tier.features) if isinstance(tier.features, str) else tier.features
        overage = json.loads(tier.overage_pricing) if isinstance(tier.overage_pricing, str) else tier.overage_pricing

        print(f"\n{'=' * 120}")
        print(f"TIER: {tier.display_name} (${tier.base_price_monthly}/month)")
        print(f"{'=' * 120}")
        print(f"Internal Name: {tier.tier_name}")
        print(f"Description: {tier.description}")
        print(f"Currency: {tier.currency}")
        print(f"Active: {tier.is_active}")
        print(f"Public: {tier.is_public}")

        print(f"\nLIMITS:")
        print(f"  {'Limit Type':<35} {'Value':<20} {'Display'}")
        print(f"  {'-' * 35} {'-' * 20} {'-' * 40}")

        limit_display = {
            'max_users': 'Maximum Users',
            'max_organizations': 'Maximum Organizations',
            'max_expenses_per_month': 'Expenses per Month',
            'max_ai_categorizations': 'AI Categorizations per Month',
            'max_ap2_transactions': 'AP2 Transactions per Month',
            'ocr_scans_included': 'OCR Scans per Month',
            'data_retention_days': 'Data Retention (days)'
        }

        for key, display_name in limit_display.items():
            value = limits.get(key, 'Not set')
            if value == -1:
                display = 'Unlimited'
            elif value == 0:
                display = 'Not available'
            elif isinstance(value, int):
                display = f"{value:,}"
            else:
                display = str(value)
            print(f"  {display_name:<35} {str(value):<20} {display}")

        print(f"\nFEATURES:")
        if features:
            for feature in features:
                print(f"  - {feature}")
        else:
            print("  (No features listed)")

        if overage:
            print(f"\nOVERAGE PRICING:")
            for key, value in overage.items():
                print(f"  - {key}: ${value}")
        else:
            print(f"\nOVERAGE PRICING: None")

    # Create comparison table
    print(f"\n\n{'=' * 120}")
    print("QUICK COMPARISON TABLE")
    print(f"{'=' * 120}\n")

    # Header
    header = f"{'Feature':<40}"
    for tier in tiers:
        header += f"{tier.display_name:<20}"
    print(header)
    print("-" * 120)

    # Price
    row = f"{'Monthly Price':<40}"
    for tier in tiers:
        row += f"${tier.base_price_monthly:<19}"
    print(row)

    # All limits
    limit_keys = [
        ('max_users', 'Users'),
        ('max_organizations', 'Organizations'),
        ('max_expenses_per_month', 'Expenses/month'),
        ('max_ai_categorizations', 'AI Categorizations/month'),
        ('max_ap2_transactions', 'AP2 Transactions/month'),
        ('ocr_scans_included', 'OCR Scans/month'),
        ('data_retention_days', 'Data Retention (days)')
    ]

    for key, display_name in limit_keys:
        row = f"{display_name:<40}"
        for tier in tiers:
            limits = json.loads(tier.limits) if isinstance(tier.limits, str) else tier.limits
            value = limits.get(key, 'N/A')
            if value == -1:
                display = 'Unlimited'
            elif value == 0:
                display = 'None'
            else:
                display = str(value)
            row += f"{display:<20}"
        print(row)

    print("\n" + "=" * 120)
    print(f"Total Tiers: {len(tiers)}")
    print("=" * 120 + "\n")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
