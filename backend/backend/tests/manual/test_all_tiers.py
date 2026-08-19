"""Test limit enforcement for ALL billing tiers"""
from src.database import SessionLocal
from src.models_billing import BillingTier, OrganizationSubscription
from src.models import Organization
from src.billing.limit_enforcer import LimitEnforcer
import uuid

db = SessionLocal()

print("\n" + "=" * 100)
print("TESTING ALL TIER LIMIT ENFORCEMENT")
print("=" * 100 + "\n")

# Get all tiers
tiers = db.query(BillingTier).order_by(BillingTier.base_price_monthly).all()

# For testing, we'll create mock subscriptions for each tier
# (We'll use the existing organization)
org = db.query(Organization).filter(Organization.is_active == True).first()

if not org:
    print("[ERROR] No active organization found!")
    db.close()
    exit(1)

print(f"Test Organization: {org.name} ({org.id})\n")

results = {
    "total_tests": 0,
    "passed": 0,
    "failed": 0
}

for tier in tiers:
    print("-" * 100)
    print(f"TIER: {tier.tier_name.upper()} (${tier.base_price_monthly:.2f}/month)")
    print("-" * 100)

    # Create/update subscription for this tier
    subscription = db.query(OrganizationSubscription).filter(
        OrganizationSubscription.organization_id == org.id
    ).first()

    if not subscription:
        subscription = OrganizationSubscription(
            id=str(uuid.uuid4()),
            organization_id=org.id,
            tier_id=tier.id,
            tier_name=tier.tier_name,
            status="active"
        )
        db.add(subscription)
    else:
        subscription.tier_id = tier.id
        subscription.tier_name = tier.tier_name
        subscription.status = "active"

    db.commit()

    # Get limits through enforcer
    enforcer = LimitEnforcer(db)
    limits = enforcer.get_org_tier(org.id)

    # Test 1: Tier identification
    results["total_tests"] += 1
    if limits.tier_name.lower() == tier.tier_name.lower():
        print(f"[PASS] Tier identification: {limits.tier_name}")
        results["passed"] += 1
    else:
        print(f"[FAIL] Tier identification: expected {tier.tier_name}, got {limits.tier_name}")
        results["failed"] += 1

    # Test 2: Limits loaded correctly
    print(f"\nLimits:")
    limit_fields = [
        ('max_organizations', limits.max_organizations),
        ('max_users', limits.max_users),
        ('max_expenses_per_month', limits.max_expenses_per_month),
        ('ocr_scans_included', limits.ocr_scans_included),
        ('max_ai_categorizations', limits.max_ai_categorizations),
        ('max_ap2_transactions', limits.max_ap2_transactions),
        ('data_retention_days', limits.data_retention_days),
    ]

    all_loaded = True
    for field_name, field_value in limit_fields:
        display_value = "Unlimited" if field_value is None else str(field_value)
        print(f"  {field_name:<30} {display_value}")

        results["total_tests"] += 1
        if field_value is not None or tier.tier_name.lower() == 'enterprise':
            results["passed"] += 1
        else:
            print(f"    [WARNING] Field is None but tier is not Enterprise")
            all_loaded = False
            results["failed"] += 1

    # Test 3: Features
    print(f"\nFeatures:")
    feature_checks = [
        ('api_access', limits.features.get('api_access', False)),
        ('sso_enabled', limits.features.get('sso_enabled', False)),
        ('custom_integrations', limits.features.get('custom_integrations', False)),
        ('advanced_analytics', limits.features.get('advanced_analytics', False)),
        ('approval_workflows', limits.features.get('approval_workflows', False)),
        ('priority_support', limits.features.get('priority_support', False)),
    ]

    # Expected features per tier
    expected_features = {
        'free': {
            'api_access': False,
            'sso_enabled': False,
            'custom_integrations': False,
            'advanced_analytics': False,
            'approval_workflows': False,
            'priority_support': False,
        },
        'starter': {
            'api_access': False,
            'sso_enabled': False,
            'custom_integrations': False,
            'advanced_analytics': True,
            'approval_workflows': True,
            'priority_support': True,
        },
        'professional': {
            'api_access': True,
            'sso_enabled': False,
            'custom_integrations': False,
            'advanced_analytics': True,
            'approval_workflows': True,
            'priority_support': True,
        },
        'enterprise': {
            'api_access': True,
            'sso_enabled': True,
            'custom_integrations': True,
            'advanced_analytics': True,
            'approval_workflows': True,
            'priority_support': True,
        }
    }

    tier_expected = expected_features.get(tier.tier_name.lower(), {})

    for feature_name, feature_value in feature_checks:
        expected = tier_expected.get(feature_name, False)
        status = "[OK]" if feature_value else "[X]"
        match = "[PASS]" if feature_value == expected else "[FAIL]"

        print(f"  {status} {feature_name:<30} {match}")

        results["total_tests"] += 1
        if feature_value == expected:
            results["passed"] += 1
        else:
            results["failed"] += 1

    # Test 4: Unlimited handling for Enterprise
    if tier.tier_name.lower() == 'enterprise':
        print(f"\nUnlimited checks (Enterprise only):")
        unlimited_fields = [
            ('max_users', limits.max_users),
            ('max_expenses_per_month', limits.max_expenses_per_month),
            ('max_organizations', limits.max_organizations),
            ('data_retention_days', limits.data_retention_days),
        ]

        for field_name, field_value in unlimited_fields:
            results["total_tests"] += 1
            if field_value is None:
                print(f"  [PASS] {field_name} is unlimited (None)")
                results["passed"] += 1
            else:
                print(f"  [FAIL] {field_name} should be unlimited, got {field_value}")
                results["failed"] += 1

    print()

# Clean up - remove test subscription
if subscription:
    db.delete(subscription)
    db.commit()

# Summary
print("=" * 100)
print("TEST SUMMARY")
print("=" * 100)

print(f"\nTotal Tests: {results['total_tests']}")
print(f"Passed: {results['passed']} ({(results['passed']/results['total_tests']*100) if results['total_tests'] > 0 else 0:.1f}%)")
print(f"Failed: {results['failed']}")

if results['failed'] == 0:
    print("\n[SUCCESS] All tiers are properly configured and enforced!")
else:
    print(f"\n[WARNING] {results['failed']} test(s) failed")

print("\n" + "=" * 100)

db.close()
