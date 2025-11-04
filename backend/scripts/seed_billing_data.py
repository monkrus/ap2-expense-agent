"""
Seed database with test billing data for testing

This script creates:
- Multiple organizations with different subscription tiers
- Usage records showing various consumption levels
- Overage scenarios for testing
- GCP Marketplace customers
"""

import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

# Fix Windows console encoding for emojis
if sys.platform == "win32":
    import codecs
    sys.stdout.reconfigure(encoding='utf-8')

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database import Base
from src.models import Organization, User, OrganizationMember, OrganizationRole
from src.models_billing import (
    BillingTier,
    OrganizationSubscription,
    UsageMetric,
    BillingEvent
)
from src.config import settings
from src.auth import AuthService
from src.billing.tier_limits import TIER_CONFIGS
from src.models import SubscriptionTier


def create_test_billing_data(db_session):
    """Create comprehensive test billing data"""

    print("🚀 Starting billing data seed...")

    # Step 1: Initialize Billing Tiers
    print("\n1️⃣ Creating billing tiers...")
    tiers = []
    for tier_enum, tier_config in TIER_CONFIGS.items():
        tier = db_session.query(BillingTier).filter_by(tier_name=tier_enum.value).first()

        if not tier:
            tier = BillingTier(
                id=f"tier_{tier_enum.value.lower()}",
                tier_name=tier_enum.value,
                display_name=tier_config.name,
                base_price_monthly=Decimal(str(tier_config.price_monthly)),
                limits={
                    "max_users": tier_config.max_users,
                    "max_expenses_per_month": tier_config.max_expenses_per_month,
                    "max_ai_categorizations": tier_config.max_ai_categorizations,
                    "max_ap2_transactions": tier_config.max_ap2_transactions,
                    "ocr_scans_included": tier_config.ocr_scans_included,
                    "data_retention_days": tier_config.data_retention_days
                },
                overage_pricing={},
                features={
                    "priority_support": tier_config.priority_support,
                    "custom_integrations": tier_config.custom_integrations,
                    "sso_enabled": tier_config.sso_enabled
                },
                is_active=True,
                is_public=True
            )
            db_session.add(tier)
            tiers.append(tier)
            print(f"   ✅ Created tier: {tier_config.name} (${tier_config.price_monthly}/month)")
        else:
            tiers.append(tier)
            print(f"   ⏭️  Tier already exists: {tier_config.name}")

    db_session.commit()

    # Step 2: Create Test Organizations with Different Tiers
    print("\n2️⃣ Creating test organizations...")

    test_orgs = [
        {
            "name": "Acme Startup (Starter Tier)",
            "tier": SubscriptionTier.STARTER,
            "gcp": False,
            "usage_level": "low"  # Under limits
        },
        {
            "name": "TechCorp Inc (Pro Tier)",
            "tier": SubscriptionTier.PROFESSIONAL,
            "gcp": False,
            "usage_level": "medium"  # Near limits
        },
        {
            "name": "Global Enterprises (Enterprise Tier)",
            "tier": SubscriptionTier.ENTERPRISE,
            "gcp": True,  # GCP Marketplace customer
            "usage_level": "high"  # Over limits (but Enterprise has unlimited)
        },
        {
            "name": "SmallCo (Starter - Over Limit)",
            "tier": SubscriptionTier.STARTER,
            "gcp": False,
            "usage_level": "overage"  # Exceeds limits - should show fees
        },
        {
            "name": "MidSizeCo (Pro - High Usage)",
            "tier": SubscriptionTier.PROFESSIONAL,
            "gcp": True,
            "usage_level": "overage"  # Exceeds limits - should show fees
        }
    ]

    organizations = []
    for org_data in test_orgs:
        # Check if org already exists
        org = db_session.query(Organization).filter_by(name=org_data["name"]).first()

        if not org:
            # Generate slug from name
            slug = org_data["name"].lower().replace(" ", "-").replace("(", "").replace(")", "")
            org = Organization(
                id=f"org_{uuid.uuid4().hex[:8]}",
                name=org_data["name"],
                slug=slug,
                description=f"Test organization for {org_data['tier']} tier billing",
                currency="USD",
                timezone="America/Los_Angeles",
                is_active=True,
                created_at=datetime.utcnow() - timedelta(days=30)
            )
            db_session.add(org)
            db_session.flush()

            # Create admin user for this org
            admin_email = org_data["name"].lower().replace(" ", ".").replace("(", "").replace(")", "") + "@test.com"
            admin = User(
                id=f"user_{uuid.uuid4().hex[:8]}",
                email=admin_email,
                username=admin_email.split("@")[0],
                full_name=f"Admin - {org_data['name']}",
                hashed_password=AuthService.hash_password("TestPassword123!"),
                is_active=True,
                is_verified=True,
                created_at=datetime.utcnow() - timedelta(days=30)
            )
            db_session.add(admin)
            db_session.flush()

            # Add admin as organization owner
            member = OrganizationMember(
                id=f"member_{uuid.uuid4().hex[:8]}",
                organization_id=org.id,
                user_id=admin.id,
                role=OrganizationRole.OWNER,
                joined_at=datetime.utcnow() - timedelta(days=30)
            )
            db_session.add(member)

            print(f"   ✅ Created org: {org_data['name']}")
            print(f"      Admin: {admin_email} / TestPassword123!")
        else:
            print(f"   ⏭️  Organization already exists: {org_data['name']}")

        org_data["org_obj"] = org
        organizations.append(org_data)

    db_session.commit()

    # Step 3: Create Subscriptions
    print("\n3️⃣ Creating subscriptions...")

    for org_data in organizations:
        org = org_data["org_obj"]
        tier_enum = org_data["tier"]
        tier = db_session.query(BillingTier).filter_by(tier_name=tier_enum.value).first()

        # Check if subscription exists
        subscription = db_session.query(OrganizationSubscription).filter_by(
            organization_id=org.id
        ).first()

        if not subscription:
            subscription = OrganizationSubscription(
                id=f"sub_{uuid.uuid4().hex[:8]}",
                organization_id=org.id,
                tier_id=tier.id,
                tier_name=tier_enum.value,
                status="active",  # active, trialing, canceled
                billing_period_start=datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0),
                billing_period_end=(datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0) + timedelta(days=32)).replace(day=1) - timedelta(seconds=1),
                next_billing_date=(datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0) + timedelta(days=32)).replace(day=1),
                created_at=datetime.utcnow() - timedelta(days=30)
            )

            # Add GCP details if applicable
            if org_data["gcp"]:
                subscription.gcp_account_id = f"gcp_acct_{uuid.uuid4().hex[:12]}"
                subscription.gcp_entitlement_id = f"ent_{uuid.uuid4().hex[:12]}"

            db_session.add(subscription)

            # Log billing event
            event = BillingEvent(
                id=f"event_{uuid.uuid4().hex[:8]}",
                organization_id=org.id,
                event_type="subscription_created",
                event_data={
                    "tier": tier_enum.value,
                    "is_gcp": org_data["gcp"]
                },
                status="success",
                occurred_at=datetime.utcnow() - timedelta(days=30)
            )
            db_session.add(event)

            gcp_badge = " (GCP)" if org_data["gcp"] else ""
            print(f"   ✅ Created subscription: {org.name} → {tier_enum.value}{gcp_badge}")
        else:
            print(f"   ⏭️  Subscription already exists: {org.name}")

    db_session.commit()

    # Step 4: Create Usage Records
    print("\n4️⃣ Creating usage records...")

    # Usage patterns based on level
    usage_patterns = {
        "low": {
            "ai_categorization": 0.3,  # 30% of limit
            "ap2_transaction": 0.2,    # 20% of limit
            "ocr_scan": 0.4,           # 40% of limit
        },
        "medium": {
            "ai_categorization": 0.75,  # 75% of limit (orange warning)
            "ap2_transaction": 0.65,
            "ocr_scan": 0.80,
        },
        "high": {
            "ai_categorization": 0.95,  # 95% of limit (red warning)
            "ap2_transaction": 0.90,
            "ocr_scan": 0.85,
        },
        "overage": {
            "ai_categorization": 1.15,  # 115% of limit - overage fees!
            "ap2_transaction": 1.25,
            "ocr_scan": 1.10,
        }
    }

    now = datetime.utcnow()
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    period_end = (period_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)

    for org_data in organizations:
        org = org_data["org_obj"]
        tier_enum = org_data["tier"]
        usage_level = org_data["usage_level"]

        # Get tier limits
        tier_config = TIER_CONFIGS[tier_enum]

        print(f"\n   📊 Creating usage for {org.name} ({usage_level} usage)...")

        # AI Categorizations
        if tier_config.max_ai_categorizations and tier_config.max_ai_categorizations != float('inf'):
            base_count = int(tier_config.max_ai_categorizations * usage_patterns[usage_level]["ai_categorization"])
        else:
            base_count = 1000  # For unlimited tiers, use arbitrary number

        usage = UsageMetric(
            id=f"usage_{uuid.uuid4().hex[:8]}",
            organization_id=org.id,
            metric_type="ai_categorization",
            metric_value=base_count,
            unit="count",
            period_start=period_start,
            period_end=period_end,
            reported_to_gcp=org_data["gcp"],
            created_at=now
        )
        db_session.add(usage)
        print(f"      ✓ AI Categorizations: {base_count}")

        # AP2 Transactions
        if tier_config.max_ap2_transactions and tier_config.max_ap2_transactions != float('inf'):
            base_count = int(tier_config.max_ap2_transactions * usage_patterns[usage_level]["ap2_transaction"])
        else:
            base_count = 500

        usage = UsageMetric(
            id=f"usage_{uuid.uuid4().hex[:8]}",
            organization_id=org.id,
            metric_type="ap2_transaction",
            metric_value=base_count,
            unit="count",
            period_start=period_start,
            period_end=period_end,
            reported_to_gcp=org_data["gcp"],
            created_at=now
        )
        db_session.add(usage)
        print(f"      ✓ AP2 Transactions: {base_count}")

        # OCR Scans
        if tier_config.ocr_scans_included and tier_config.ocr_scans_included != float('inf'):
            base_count = int(tier_config.ocr_scans_included * usage_patterns[usage_level]["ocr_scan"])
        else:
            base_count = 2000

        usage = UsageMetric(
            id=f"usage_{uuid.uuid4().hex[:8]}",
            organization_id=org.id,
            metric_type="ocr_scan",
            metric_value=base_count,
            unit="count",
            period_start=period_start,
            period_end=period_end,
            reported_to_gcp=org_data["gcp"],
            created_at=now
        )
        db_session.add(usage)
        print(f"      ✓ OCR Scans: {base_count}")

    db_session.commit()

    # Step 5: Summary
    print("\n" + "="*60)
    print("✅ BILLING DATA SEED COMPLETE!")
    print("="*60)

    print("\n📋 Summary:")
    print(f"   • {len(tiers)} billing tiers created")
    print(f"   • {len(organizations)} test organizations created")
    print(f"   • {len(organizations)} subscriptions created")
    print(f"   • {len(organizations) * 3} usage metrics created")

    print("\n🧪 Test Accounts Created:")
    for org_data in test_orgs:
        admin_email = org_data["name"].lower().replace(" ", ".").replace("(", "").replace(")", "") + "@test.com"
        print(f"\n   {org_data['name']}")
        print(f"   ├─ Email: {admin_email}")
        print(f"   ├─ Password: TestPassword123!")
        print(f"   ├─ Tier: {org_data['tier'].value}")
        print(f"   ├─ GCP Customer: {'Yes' if org_data['gcp'] else 'No'}")
        print(f"   └─ Usage Level: {org_data['usage_level']}")

    print("\n🌐 Test in Browser:")
    print("   1. Go to: http://localhost:5173")
    print("   2. Login with any account above")
    print("   3. Navigate to:")
    print("      • http://localhost:5173/billing - View usage & billing")
    print("      • http://localhost:5173/pricing - Compare plans")

    print("\n📊 Expected Results:")
    print("   • Acme Startup: Green progress bars (under limits)")
    print("   • TechCorp Inc: Orange progress bars (75-90% used)")
    print("   • Global Enterprises: All green (unlimited)")
    print("   • SmallCo: RED bars + overage fees displayed")
    print("   • MidSizeCo: RED bars + overage fees + GCP badge")

    print("\n💡 Next Steps:")
    print("   • Check billing dashboard for each organization")
    print("   • Verify overage fees calculated correctly")
    print("   • Test tier upgrades/downgrades")
    print("   • Simulate GCP webhooks for procurement")

    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    # Create database connection
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        create_test_billing_data(db)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()
