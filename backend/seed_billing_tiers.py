"""
Seed billing tiers with OFFICIAL tier limits
CRITICAL: These limits are the source of truth for the billing system
DO NOT MODIFY without approval from product/finance teams
"""

import sys
from datetime import datetime
import uuid

from src.database import SessionLocal
from src.models_billing import BillingTier

# OFFICIAL TIER LIMITS - DO NOT MODIFY
# These must match frontend/src/config/constants.js TIER_LIMITS
OFFICIAL_TIERS = {
    "free": {
        "tier_name": "free",
        "display_name": "Free Tier",
        "description": "Perfect for individuals and small teams getting started",
        "base_price_monthly": 0.0,
        "currency": "USD",
        "limits": {
            "max_users": 2,
            "max_organizations": 1,
            "max_expenses_per_month": 30,
            "max_receipt_size_mb": 5,
            "max_storage_gb": 0.5,
            "ocr_scans_included": 20,
            "ocr_scans_per_day": 3,
            "ai_categorizations_included": 0,
            "ap2_transactions_included": 20,
            "data_retention_days": 90,
        },
        "overage_pricing": {
            "ocr_scan_fee": 0.02,  # $0.02 per scan over limit
            "ai_categorization_fee": 0.10,  # Not available on free tier
            "ap2_transaction_fee": 0.05,  # $0.05 per transaction over limit
            "storage_gb_fee": 1.00,  # $1.00 per GB over limit
        },
        "features": [
            "2 users per organization",
            "30 expenses per month",
            "20 OCR scans per month",
            "20 AP2 transactions per month",
            "90 days data retention",
            "Email support",
            "Basic expense tracking",
            "Receipt upload & storage",
        ],
        "is_active": True,
        "is_public": True,
    },
    "starter": {
        "tier_name": "starter",
        "display_name": "Starter Plan",
        "description": "For growing teams that need more power",
        "base_price_monthly": 29.0,
        "currency": "USD",
        "limits": {
            "max_users": 10,
            "max_organizations": 3,
            "max_expenses_per_month": 100,
            "max_receipt_size_mb": 10,
            "max_storage_gb": 5,
            "ocr_scans_included": 100,
            "ocr_scans_per_day": 20,
            "ai_categorizations_included": 50,
            "ap2_transactions_included": 100,
            "data_retention_days": 365,
        },
        "overage_pricing": {
            "ocr_scan_fee": 0.02,
            "ai_categorization_fee": 0.08,
            "ap2_transaction_fee": 0.04,
            "storage_gb_fee": 0.80,
        },
        "features": [
            "10 users per organization",
            "3 organizations",
            "100 expenses per month",
            "100 OCR scans per month",
            "50 AI categorizations per month",
            "100 AP2 transactions per month",
            "1 year data retention",
            "Approval workflows",
            "Advanced analytics",
            "Priority email support",
            "Custom expense categories",
            "Export to CSV/Excel",
        ],
        "is_active": True,
        "is_public": True,
    },
    "professional": {
        "tier_name": "professional",
        "display_name": "Professional Plan",
        "description": "For enterprises with advanced requirements",
        "base_price_monthly": 99.0,
        "currency": "USD",
        "limits": {
            "max_users": 50,
            "max_organizations": 10,
            "max_expenses_per_month": 500,
            "max_receipt_size_mb": 10,
            "max_storage_gb": 50,
            "ocr_scans_included": None,  # Unlimited
            "ocr_scans_per_day": None,  # Unlimited
            "ai_categorizations_included": 200,
            "ap2_transactions_included": None,  # Unlimited
            "data_retention_days": 1095,  # 3 years
        },
        "overage_pricing": {
            "ocr_scan_fee": 0.0,  # Unlimited included
            "ai_categorization_fee": 0.05,
            "ap2_transaction_fee": 0.0,  # Unlimited included
            "storage_gb_fee": 0.50,
        },
        "features": [
            "50 users per organization",
            "10 organizations",
            "500 expenses per month",
            "Unlimited OCR scans",
            "200 AI categorizations per month",
            "Unlimited AP2 transactions",
            "3 years data retention",
            "Full API access",
            "Approval workflows with multi-level approvals",
            "Advanced analytics & reporting",
            "Custom integrations",
            "Dedicated account manager",
            "24/7 priority support",
            "SLA guarantees",
            "Custom branding",
            "Audit logs & compliance reports",
        ],
        "is_active": True,
        "is_public": True,
    },
}


def validate_tier_limits(tier_name: str, limits) -> bool:
    """
    Validate that tier limits match official specification
    Returns True if valid, False otherwise
    """
    official = OFFICIAL_TIERS.get(tier_name)
    if not official:
        print(f"[ERROR] Tier '{tier_name}' not found in OFFICIAL_TIERS")
        return False

    official_limits = official["limits"]

    # Handle if limits is a string (JSON stored as string)
    if isinstance(limits, str):
        import json
        try:
            limits = json.loads(limits)
        except json.JSONDecodeError:
            print(f"[ERROR] Failed to parse limits as JSON")
            return False

    # Check all required fields
    for key, value in official_limits.items():
        if limits.get(key) != value:
            print(f"[ERROR] Tier '{tier_name}' limit mismatch:")
            print(f"  Field: {key}")
            print(f"  Expected: {value}")
            print(f"  Actual: {limits.get(key)}")
            return False

    return True


def seed_billing_tiers(force_update: bool = False):
    """
    Seed or update billing tiers in database
    Args:
        force_update: If True, update existing tiers even if they differ
    """
    db = SessionLocal()
    try:
        print("="*60)
        print("BILLING TIER SEEDING")
        print("="*60)
        print()

        for tier_name, tier_data in OFFICIAL_TIERS.items():
            print(f"Processing tier: {tier_name}")

            # Check if tier exists
            existing_tier = db.query(BillingTier).filter(
                BillingTier.tier_name == tier_name
            ).first()

            if existing_tier:
                # Validate existing tier against official spec
                if not validate_tier_limits(tier_name, existing_tier.limits):
                    if force_update:
                        print(f"  [WARN] Tier limits mismatch - UPDATING (force=True)")
                        # Update all fields
                        existing_tier.display_name = tier_data["display_name"]
                        existing_tier.description = tier_data["description"]
                        existing_tier.base_price_monthly = tier_data["base_price_monthly"]
                        existing_tier.currency = tier_data["currency"]
                        existing_tier.limits = tier_data["limits"]
                        existing_tier.overage_pricing = tier_data["overage_pricing"]
                        existing_tier.features = tier_data["features"]
                        existing_tier.is_active = tier_data["is_active"]
                        existing_tier.is_public = tier_data["is_public"]
                        existing_tier.updated_at = datetime.utcnow()
                        print(f"  [PASS] Tier '{tier_name}' updated successfully")
                    else:
                        print(f"  [ERROR] Tier limits mismatch - use --force to update")
                        return False
                else:
                    print(f"  [PASS] Tier '{tier_name}' already exists and is correct")
            else:
                # Create new tier
                new_tier = BillingTier(
                    id=str(uuid.uuid4()),
                    tier_name=tier_data["tier_name"],
                    display_name=tier_data["display_name"],
                    description=tier_data["description"],
                    base_price_monthly=tier_data["base_price_monthly"],
                    currency=tier_data["currency"],
                    limits=tier_data["limits"],
                    overage_pricing=tier_data["overage_pricing"],
                    features=tier_data["features"],
                    is_active=tier_data["is_active"],
                    is_public=tier_data["is_public"],
                )
                db.add(new_tier)
                print(f"  [PASS] Tier '{tier_name}' created successfully")

            print()

        # Commit all changes
        db.commit()
        print("="*60)
        print("[SUCCESS] All billing tiers seeded/updated successfully")
        print("="*60)
        return True

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to seed billing tiers: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def verify_tier_limits():
    """
    Verify that all tiers in database match official specification
    """
    db = SessionLocal()
    try:
        print("\n" + "="*60)
        print("TIER LIMITS VERIFICATION")
        print("="*60)
        print()

        all_valid = True
        for tier_name in OFFICIAL_TIERS.keys():
            tier = db.query(BillingTier).filter(
                BillingTier.tier_name == tier_name
            ).first()

            if not tier:
                print(f"[ERROR] Tier '{tier_name}' not found in database")
                all_valid = False
                continue

            if validate_tier_limits(tier_name, tier.limits):
                print(f"[PASS] Tier '{tier_name}' limits are correct")
            else:
                all_valid = False

        print()
        print("="*60)
        if all_valid:
            print("[SUCCESS] All tier limits verified successfully")
        else:
            print("[FAIL] Some tier limits are incorrect - run with --force to fix")
        print("="*60)

        return all_valid

    finally:
        db.close()


def print_tier_comparison():
    """Print a comparison table of all tier limits"""
    print("\n" + "="*60)
    print("TIER LIMITS COMPARISON TABLE")
    print("="*60)
    print()

    print(f"{'Feature':<30} | {'Free':<12} | {'Starter':<12} | {'Professional':<12}")
    print("-" * 80)

    limits_to_show = [
        ("Organizations", "max_organizations"),
        ("Users", "max_users"),
        ("Expenses/month", "max_expenses_per_month"),
        ("OCR Scans/month", "ocr_scans_included"),
        ("AI Categorizations", "ai_categorizations_included"),
        ("AP2 Transactions", "ap2_transactions_included"),
        ("Data Retention", "data_retention_days"),
        ("Price/month", None),
    ]

    for feature_name, limit_key in limits_to_show:
        row = f"{feature_name:<30} |"

        for tier_name in ["free", "starter", "professional"]:
            if limit_key:
                value = OFFICIAL_TIERS[tier_name]["limits"].get(limit_key)
                if value is None:
                    display = "Unlimited"
                elif limit_key == "data_retention_days":
                    display = f"{value} days"
                else:
                    display = str(value)
            else:
                # Price
                display = f"${OFFICIAL_TIERS[tier_name]['base_price_monthly']:.0f}"

            row += f" {display:<12} |"

        print(row)

    print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed billing tiers")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force update existing tiers even if they differ from spec"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Only verify tier limits, don't update"
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Show tier comparison table"
    )

    args = parser.parse_args()

    if args.show:
        print_tier_comparison()
        sys.exit(0)

    if args.verify:
        success = verify_tier_limits()
        sys.exit(0 if success else 1)

    # Default: seed/update tiers
    success = seed_billing_tiers(force_update=args.force)

    if success:
        print_tier_comparison()
        verify_tier_limits()
        sys.exit(0)
    else:
        sys.exit(1)
