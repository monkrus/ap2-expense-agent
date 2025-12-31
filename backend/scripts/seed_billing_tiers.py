"""
Seed billing tiers for development and testing.
This script creates the three standard billing tiers: Starter, Professional, and Enterprise.
"""
import sys
import os
from datetime import datetime
import uuid
import json

# Add parent directory to path to import from src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import settings
from src.models_billing import BillingTier

# Billing tier definitions
BILLING_TIERS = [
    {
        "tier_name": "free",
        "display_name": "Free",
        "description": "Get started with expense tracking - perfect for individuals and small teams",
        "base_price_monthly": 0.00,
        "currency": "USD",
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
        "overage_pricing": {
            "per_additional_user": 0,
            "per_additional_expense": 0,
            "per_additional_ap2_transaction": 0,
            "per_additional_ai_categorization": 0,
            "per_additional_ocr_scan": 0
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
    {
        "tier_name": "starter",
        "display_name": "Starter",
        "description": "Perfect for small teams getting started with expense management",
        "base_price_monthly": 29.00,
        "currency": "USD",
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
        "overage_pricing": {
            "per_additional_user": 5.00,
            "per_additional_expense": 0.50,
            "per_additional_ap2_transaction": 0.10,
            "per_additional_ai_categorization": 0.05,
            "per_additional_ocr_scan": 0.02
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
    {
        "tier_name": "professional",
        "display_name": "Professional",
        "description": "Advanced features for growing businesses",
        "base_price_monthly": 79.00,
        "currency": "USD",
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
        "overage_pricing": {
            "per_additional_user": 4.00,
            "per_additional_expense": 0.30,
            "per_additional_ap2_transaction": 0.08,
            "per_additional_ai_categorization": 0.04,
            "per_additional_ocr_scan": 0.015
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
    },
    # ENTERPRISE TIER DISABLED - May be enabled later
    # {
    #     "tier_name": "enterprise",
    #     "display_name": "Enterprise",
    #     "description": "Enterprise-grade solution with unlimited scale",
    #     "base_price_monthly": 299.99,
    #     "currency": "USD",
    #     "limits": {
    #         "max_users": -1,  # Unlimited
    #         "max_expenses_per_month": -1,  # Unlimited
    #         "max_receipt_size_mb": 50,
    #         "max_storage_gb": 100,
    #         "ap2_transactions_included": 10000,
    #         "ai_categorizations_included": 5000,
    #         "ocr_scans_included": 2000
    #     },
    #     "overage_pricing": {
    #         "per_additional_user": 0,  # Unlimited users
    #         "per_additional_expense": 0,  # Unlimited expenses
    #         "per_additional_ap2_transaction": 0.05,
    #         "per_additional_ai_categorization": 0.03,
    #         "per_additional_ocr_scan": 0.01
    #     },
    #     "features": [
    #         "Everything in Professional",
    #         "Unlimited users & expenses",
    #         "Custom integrations",
    #         "SSO & SAML authentication",
    #         "Advanced security features",
    #         "Custom approval workflows",
    #         "White-label options",
    #         "Dedicated infrastructure",
    #         "99.9% SLA",
    #         "24/7 phone support",
    #         "Custom training & onboarding",
    #         "Quarterly business reviews"
    #     ]
    # }
]

def seed_billing_tiers():
    """Seed billing tiers into the database."""
    print("=" * 80)
    print("Seeding Billing Tiers")
    print("=" * 80)
    print()

    # Create engine and session
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        stats = {
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "total": len(BILLING_TIERS)
        }

        for tier_data in BILLING_TIERS:
            # Check if tier already exists
            existing_tier = db.query(BillingTier).filter(
                BillingTier.tier_name == tier_data["tier_name"]
            ).first()

            if existing_tier:
                print(f"[!] Tier '{tier_data['tier_name']}' already exists. Skipping.")
                stats["skipped"] += 1
                continue

            # Create new tier
            tier = BillingTier(
                id=str(uuid.uuid4()),
                tier_name=tier_data["tier_name"],
                display_name=tier_data["display_name"],
                description=tier_data["description"],
                base_price_monthly=tier_data["base_price_monthly"],
                currency=tier_data["currency"],
                limits=json.dumps(tier_data["limits"]),
                overage_pricing=json.dumps(tier_data["overage_pricing"]),
                features=json.dumps(tier_data["features"]),
                is_active=True,
                is_public=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            db.add(tier)
            print(f"[+] Created tier: {tier_data['display_name']} (${tier_data['base_price_monthly']}/month)")
            stats["created"] += 1

        db.commit()

        print()
        print("=" * 80)
        print("Seeding Complete")
        print("=" * 80)
        print(f"Created: {stats['created']}")
        print(f"Skipped: {stats['skipped']}")
        print(f"Total:   {stats['total']}")
        print()

        # Display created tiers
        if stats["created"] > 0:
            print("Created Tiers:")
            print("-" * 80)
            tiers = db.query(BillingTier).all()
            for tier in tiers:
                limits = json.loads(tier.limits)
                features = json.loads(tier.features)
                print(f"\n{tier.display_name} - ${tier.base_price_monthly}/month")
                print(f"  {tier.description}")
                print(f"  Users: {limits['max_users'] if limits['max_users'] != -1 else 'Unlimited'}")
                print(f"  Expenses/month: {limits['max_expenses_per_month'] if limits['max_expenses_per_month'] != -1 else 'Unlimited'}")
                print(f"  Features: {len(features)}")

        return stats

    except Exception as e:
        db.rollback()
        print(f"\n[X] Error seeding billing tiers: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    try:
        stats = seed_billing_tiers()
        sys.exit(0)
    except Exception as e:
        print(f"\n[X] Failed to seed billing tiers: {str(e)}")
        sys.exit(1)
