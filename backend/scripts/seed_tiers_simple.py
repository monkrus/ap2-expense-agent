import sys
import uuid
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, r'C:\Users\robot\Desktop\ap2-expense-agent\backend')

from src.database import SessionLocal
from src.models_billing import BillingTier

def seed_tiers():
    db = SessionLocal()
    try:
        # Define tiers
        tiers = [
            {
                "tier_name": "free",
                "display_name": "Free",
                "description": "Experience AP2 payment automation free forever",
                "base_price_monthly": 0,
                "currency": "USD",
                "limits": {
                    "max_users": 1,
                    "max_organizations": 1,
                    "max_expenses_per_month": 30,
                    "max_ai_categorizations": 0,
                    "max_ap2_transactions": 20,
                    "ocr_scans_included": 20,
                    "data_retention_days": 90
                },
                "overage_pricing": {},
                "features": ["basic_expense_tracking", "ocr_receipt_scanning", "basic_reports", "ap2_payments"]
            },
            {
                "tier_name": "starter",
                "display_name": "Starter",
                "description": "Great for small teams",
                "base_price_monthly": 29,
                "currency": "USD",
                "limits": {
                    "max_users": 25,
                    "max_organizations": 3,
                    "max_expenses_per_month": 500,
                    "max_ai_categorizations": 200,
                    "max_ap2_transactions": 100,
                    "ocr_scans_included": 200,
                    "data_retention_days": 365
                },
                "overage_pricing": {"expense_overage_per_100": 5},
                "features": ["basic_expense_tracking", "ocr_receipt_scanning", "basic_reports", "ai_categorization", "team_collaboration", "custom_categories"]
            },
            {
                "tier_name": "professional",
                "display_name": "Professional",
                "description": "For growing businesses",
                "base_price_monthly": 99,
                "currency": "USD",
                "limits": {
                    "max_users": 100,
                    "max_organizations": 10,
                    "max_expenses_per_month": 2000,
                    "max_ai_categorizations": 1000,
                    "max_ap2_transactions": 500,
                    "ocr_scans_included": 1000,
                    "data_retention_days": 730
                },
                "overage_pricing": {"expense_overage_per_100": 3},
                "features": ["basic_expense_tracking", "ocr_receipt_scanning", "basic_reports", "ai_categorization", "team_collaboration", "custom_categories", "advanced_analytics", "approval_workflows", "integrations", "priority_support"]
            },
            {
                "tier_name": "enterprise",
                "display_name": "Enterprise",
                "description": "For large organizations",
                "base_price_monthly": 299,
                "currency": "USD",
                "limits": {
                    "max_users": -1,  # Unlimited
                    "max_organizations": -1,  # Unlimited
                    "max_expenses_per_month": -1,  # Unlimited
                    "max_ai_categorizations": -1,  # Unlimited
                    "max_ap2_transactions": -1,  # Unlimited
                    "ocr_scans_included": -1,  # Unlimited
                    "data_retention_days": -1  # Unlimited
                },
                "overage_pricing": {},
                "features": ["basic_expense_tracking", "ocr_receipt_scanning", "basic_reports", "ai_categorization", "team_collaboration", "custom_categories", "advanced_analytics", "approval_workflows", "integrations", "priority_support", "dedicated_support", "custom_integrations", "sla_guarantee", "advanced_security"]
            }
        ]

        created = 0
        for tier_data in tiers:
            # Check if tier already exists
            existing = db.query(BillingTier).filter(
                BillingTier.tier_name == tier_data["tier_name"]
            ).first()

            if existing:
                print(f"Skipped {tier_data['tier_name']} (already exists)")
                continue

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
            created += 1
            print(f"Created {tier_data['tier_name']}")

        db.commit()
        print(f"\nTotal created: {created}")
        return created

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_tiers()
