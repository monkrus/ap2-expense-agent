"""
Update Free tier with new limits
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

    # New limits - Strategic: Hook users on AP2, make AI the upgrade driver
    new_limits = {
        "max_users": 1,
        "max_organizations": 1,
        "max_expenses_per_month": 30,        # Up from 20 - more generous
        "max_ai_categorizations": 0,         # Down from 10 - manual categorization only
        "max_ap2_transactions": 20,          # Up from 0 - LET THEM TRY YOUR UNIQUE FEATURE!
        "ocr_scans_included": 20,            # Up from 10 - convenience feature
        "data_retention_days": 90            # Same
    }

    # New features
    new_features = [
        "basic_expense_tracking",
        "ocr_receipt_scanning",
        "basic_reports",
        "ap2_payments"  # Highlight AP2 as a feature!
    ]

    # Update
    free_tier.description = "Experience AP2 payment automation free forever"
    free_tier.limits = json.dumps(new_limits)
    free_tier.features = json.dumps(new_features)

    db.commit()

    print("\nSUCCESS: Free tier updated successfully!")
    print("\nNew Limits:")
    for key, value in new_limits.items():
        print(f"  - {key}: {value}")

    print("\nNew Features:")
    for feature in new_features:
        print(f"  - {feature}")

except Exception as e:
    db.rollback()
    print(f"ERROR: {e}")
    raise
finally:
    db.close()
