"""
Update all billing tiers to match finalized pricing structure
"""
import sys
import json
sys.path.insert(0, r'C:\Users\robot\Desktop\ap2-expense-agent\backend')

from src.database import SessionLocal
from src.models_billing import BillingTier

db = SessionLocal()

# Finalized tier configurations
TIER_UPDATES = {
    "free": {
        "description": "Get started with expense tracking - perfect for individuals and small teams",
        "base_price_monthly": 0.00,
        "limits": {
            "max_users": 2,
            "max_organizations": 1,
            "max_expenses_per_month": 30,
            "max_receipt_size_mb": 5,
            "max_storage_gb": 0.5,
            "ap2_transactions_included": 20,
            "ai_categorizations_included": 0,
            "ocr_scans_included": 30,
            "data_retention_days": 90
        },
        "features": [
            "Up to 2 users",
            "30 expenses per month",
            "Expense submission & approval",
            "Receipt upload & OCR (30 scans/month)",
            "AP2 payment processing (20 payments/month)*",
            "Export to CSV, Excel, and PDF",
            "Email notifications",
            "90-day data retention",
            "Community support",
            "*Payment processing fees apply (2.9% + $0.30/transaction)"
        ]
    },
    "starter": {
        "description": "Perfect for small teams getting started with expense management",
        "base_price_monthly": 29.00,
        "limits": {
            "max_users": 5,
            "max_organizations": 3,
            "max_expenses_per_month": 50,
            "max_receipt_size_mb": 5,
            "max_storage_gb": 1,
            "ap2_transactions_included": 100,
            "ai_categorizations_included": 50,
            "ocr_scans_included": 50,
            "data_retention_days": 365
        },
        "features": [
            "Everything in Free",
            "Up to 5 users",
            "50 expenses per month",
            "3 organizations",
            "Receipt OCR (50 scans/month)",
            "AP2 payments (100 payments/month)*",
            "AI categorization (50/month)",
            "Export to CSV, Excel, and PDF",
            "1-year data retention",
            "Email support",
            "*Payment processing fees apply (2.9% + $0.30/transaction)"
        ]
    },
    "professional": {
        "description": "Advanced features for growing businesses",
        "base_price_monthly": 79.00,
        "limits": {
            "max_users": 25,
            "max_organizations": 10,
            "max_expenses_per_month": 500,
            "max_receipt_size_mb": 10,
            "max_storage_gb": 10,
            "ap2_transactions_included": 1000,
            "ai_categorizations_included": 500,
            "ocr_scans_included": 200,
            "data_retention_days": 1095
        },
        "features": [
            "Everything in Starter",
            "Up to 25 users",
            "500 expenses per month",
            "10 organizations",
            "Receipt OCR (200 scans/month)",
            "AP2 payments (1,000 payments/month)*",
            "AI categorization (500/month)",
            "Multi-level approval workflows",
            "Export to CSV, Excel, and PDF",
            "3-year data retention",
            "Priority email support",
            "Dedicated account manager",
            "*Payment processing fees apply (2.9% + $0.30/transaction)"
        ]
    }
}

try:
    updated_count = 0

    for tier_name, updates in TIER_UPDATES.items():
        tier = db.query(BillingTier).filter(BillingTier.tier_name == tier_name).first()

        if not tier:
            print(f"[SKIP] Tier '{tier_name}' not found in database")
            continue

        print(f"\n[UPDATING] {tier.display_name} tier...")

        # Update description
        tier.description = updates["description"]

        # Update price
        tier.base_price_monthly = updates["base_price_monthly"]

        # Update limits
        tier.limits = json.dumps(updates["limits"])

        # Update features
        tier.features = json.dumps(updates["features"])

        db.commit()

        print(f"  Description: {updates['description'][:60]}...")
        print(f"  Price: ${updates['base_price_monthly']}/month")
        print(f"  Limits updated: {len(updates['limits'])} fields")
        print(f"  Features updated: {len(updates['features'])} items")

        updated_count += 1

    print(f"\n[SUCCESS] Updated {updated_count} tier(s)")
    print("\nFinal Pricing Structure:")
    print("=" * 60)

    tiers = db.query(BillingTier).filter(BillingTier.is_active == True).order_by(BillingTier.base_price_monthly).all()
    for tier in tiers:
        limits = json.loads(tier.limits)
        print(f"\n{tier.display_name} - ${tier.base_price_monthly}/month")
        print(f"  Users: {limits.get('max_users', 'N/A')}")
        print(f"  Expenses/mo: {limits.get('max_expenses_per_month', 'N/A')}")
        print(f"  Organizations: {limits.get('max_organizations', 'N/A')}")
        print(f"  OCR Scans/mo: {limits.get('ocr_scans_included', 'N/A')}")
        print(f"  AP2 Payments/mo: {limits.get('ap2_transactions_included', 'N/A')}")
        print(f"  Data Retention: {limits.get('data_retention_days', 'N/A')} days")

except Exception as e:
    db.rollback()
    print(f"[ERROR] {e}")
    raise
finally:
    db.close()
