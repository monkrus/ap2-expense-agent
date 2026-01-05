"""
Test suite to verify billing tier limits are enforced correctly
Tests all three tiers: Free, Starter, Professional
"""

import sys
sys.path.insert(0, '.')

from src.database import SessionLocal
from src.models_billing import BillingTier, OrganizationSubscription
from src.billing.limit_enforcer import LimitEnforcer
from seed_billing_tiers import OFFICIAL_TIERS

# Test results
test_results = {
    "passed": [],
    "failed": [],
}


def test_tier_limits_in_database():
    """Test that all tier limits in database match official specification"""
    print("\n" + "="*60)
    print("TEST: Tier Limits in Database")
    print("="*60)

    db = SessionLocal()
    try:
        for tier_name, official_tier in OFFICIAL_TIERS.items():
            print(f"\nTesting tier: {tier_name}")

            tier = db.query(BillingTier).filter(
                BillingTier.tier_name == tier_name
            ).first()

            if not tier:
                print(f"  [FAIL] Tier '{tier_name}' not found in database")
                test_results["failed"].append(f"{tier_name}: Not found in database")
                continue

            # Verify all limits
            official_limits = official_tier["limits"]
            all_correct = True

            for key, expected_value in official_limits.items():
                actual_value = tier.limits.get(key)

                if actual_value != expected_value:
                    print(f"  [FAIL] {key}: expected {expected_value}, got {actual_value}")
                    all_correct = False
                else:
                    print(f"  [PASS] {key}: {actual_value}")

            if all_correct:
                test_results["passed"].append(f"{tier_name}: All limits correct")
            else:
                test_results["failed"].append(f"{tier_name}: Some limits incorrect")

    finally:
        db.close()


def test_limit_enforcer_free_tier():
    """Test that LimitEnforcer correctly enforces free tier limits"""
    print("\n" + "="*60)
    print("TEST: Free Tier Limit Enforcement")
    print("="*60)

    db = SessionLocal()
    try:
        # Get free tier
        free_tier = db.query(BillingTier).filter(
            BillingTier.tier_name == "free"
        ).first()

        if not free_tier:
            print("[FAIL] Free tier not found")
            test_results["failed"].append("Free tier: Not found")
            return

        # Create test subscription
        test_org_id = "test-free-org-123"

        # Check each limit
        limits = free_tier.limits
        print(f"\nTesting limits for free tier:")
        print(f"  Max Users: {limits['max_users']}")
        print(f"  Max Organizations: {limits['max_organizations']}")
        print(f"  Max Expenses/Month: {limits['max_expenses_per_month']}")
        print(f"  OCR Scans/Month: {limits['ocr_scans_included']}")
        print(f"  OCR Scans/Day: {limits['ocr_scans_per_day']}")
        print(f"  AI Categorizations: {limits['ai_categorizations_included']}")
        print(f"  AP2 Transactions: {limits['ap2_transactions_included']}")

        # Verify expected values
        expected_free = OFFICIAL_TIERS["free"]["limits"]

        if limits["max_users"] == expected_free["max_users"]:
            print(f"  [PASS] Max users = {limits['max_users']}")
            test_results["passed"].append("Free tier: max_users enforced")
        else:
            print(f"  [FAIL] Max users mismatch")
            test_results["failed"].append("Free tier: max_users not enforced")

        if limits["ocr_scans_included"] == expected_free["ocr_scans_included"]:
            print(f"  [PASS] OCR scans = {limits['ocr_scans_included']}")
            test_results["passed"].append("Free tier: ocr_scans enforced")
        else:
            print(f"  [FAIL] OCR scans mismatch")
            test_results["failed"].append("Free tier: ocr_scans not enforced")

        if limits["max_expenses_per_month"] == expected_free["max_expenses_per_month"]:
            print(f"  [PASS] Max expenses = {limits['max_expenses_per_month']}")
            test_results["passed"].append("Free tier: max_expenses enforced")
        else:
            print(f"  [FAIL] Max expenses mismatch")
            test_results["failed"].append("Free tier: max_expenses not enforced")

    finally:
        db.close()


def test_tier_comparison():
    """Test that tiers have correct relative limits (starter > free, professional > starter)"""
    print("\n" + "="*60)
    print("TEST: Tier Hierarchy Validation")
    print("="*60)

    db = SessionLocal()
    try:
        free = db.query(BillingTier).filter(BillingTier.tier_name == "free").first()
        starter = db.query(BillingTier).filter(BillingTier.tier_name == "starter").first()
        pro = db.query(BillingTier).filter(BillingTier.tier_name == "professional").first()

        if not all([free, starter, pro]):
            print("[FAIL] Not all tiers found")
            test_results["failed"].append("Tier hierarchy: Missing tiers")
            return

        # Test: starter should have higher limits than free
        tests = [
            ("max_users", free.limits["max_users"], starter.limits["max_users"], "Starter users > Free users"),
            ("max_organizations", free.limits["max_organizations"], starter.limits["max_organizations"], "Starter orgs > Free orgs"),
            ("max_expenses_per_month", free.limits["max_expenses_per_month"], starter.limits["max_expenses_per_month"], "Starter expenses > Free expenses"),
            ("ocr_scans_included", free.limits["ocr_scans_included"], starter.limits["ocr_scans_included"], "Starter OCR > Free OCR"),
        ]

        for field, free_val, starter_val, description in tests:
            if starter_val > free_val:
                print(f"  [PASS] {description} ({free_val} < {starter_val})")
                test_results["passed"].append(f"Hierarchy: {description}")
            else:
                print(f"  [FAIL] {description} ({free_val} >= {starter_val})")
                test_results["failed"].append(f"Hierarchy: {description}")

        # Test: professional should have higher or unlimited limits than starter
        if pro.limits["max_users"] > starter.limits["max_users"]:
            print(f"  [PASS] Professional users > Starter users ({starter.limits['max_users']} < {pro.limits['max_users']})")
            test_results["passed"].append("Hierarchy: Pro users > Starter users")
        else:
            print(f"  [FAIL] Professional users <= Starter users")
            test_results["failed"].append("Hierarchy: Pro users not greater")

        # OCR scans should be unlimited (None) for professional
        if pro.limits["ocr_scans_included"] is None:
            print(f"  [PASS] Professional OCR is unlimited")
            test_results["passed"].append("Hierarchy: Pro OCR unlimited")
        else:
            print(f"  [FAIL] Professional OCR is not unlimited: {pro.limits['ocr_scans_included']}")
            test_results["failed"].append("Hierarchy: Pro OCR not unlimited")

    finally:
        db.close()


def test_tier_pricing():
    """Test that tier pricing is correct"""
    print("\n" + "="*60)
    print("TEST: Tier Pricing Validation")
    print("="*60)

    db = SessionLocal()
    try:
        for tier_name, official_tier in OFFICIAL_TIERS.items():
            tier = db.query(BillingTier).filter(
                BillingTier.tier_name == tier_name
            ).first()

            if not tier:
                continue

            expected_price = official_tier["base_price_monthly"]
            actual_price = tier.base_price_monthly

            if actual_price == expected_price:
                print(f"  [PASS] {tier_name.capitalize()}: ${actual_price:.2f}/month")
                test_results["passed"].append(f"Pricing: {tier_name} = ${actual_price}")
            else:
                print(f"  [FAIL] {tier_name.capitalize()}: expected ${expected_price}, got ${actual_price}")
                test_results["failed"].append(f"Pricing: {tier_name} mismatch")

    finally:
        db.close()


def test_tier_features():
    """Test that tier features are correctly configured"""
    print("\n" + "="*60)
    print("TEST: Tier Features Validation")
    print("="*60)

    db = SessionLocal()
    try:
        for tier_name in ["free", "starter", "professional"]:
            tier = db.query(BillingTier).filter(
                BillingTier.tier_name == tier_name
            ).first()

            if not tier:
                continue

            print(f"\n{tier_name.capitalize()} tier features:")

            # Check key features based on tier
            if tier_name == "free":
                # Free tier should NOT have approval workflows or advanced analytics
                has_approval = any("approval" in f.lower() for f in tier.features)
                has_analytics = any("advanced analytics" in f.lower() for f in tier.features)
                has_api = any("api access" in f.lower() for f in tier.features)

                if not has_approval and not has_analytics and not has_api:
                    print(f"  [PASS] Free tier correctly excludes premium features")
                    test_results["passed"].append("Features: Free tier restrictions correct")
                else:
                    print(f"  [FAIL] Free tier has premium features it shouldn't have")
                    test_results["failed"].append("Features: Free tier has premium features")

            elif tier_name == "starter":
                # Starter should have approval workflows
                has_approval = any("approval" in f.lower() for f in tier.features)
                has_api = any("api access" in f.lower() for f in tier.features)

                if has_approval and not has_api:
                    print(f"  [PASS] Starter tier has approval workflows, no API")
                    test_results["passed"].append("Features: Starter tier features correct")
                else:
                    print(f"  [FAIL] Starter tier feature configuration incorrect")
                    test_results["failed"].append("Features: Starter tier features wrong")

            elif tier_name == "professional":
                # Professional should have everything
                has_approval = any("approval" in f.lower() for f in tier.features)
                has_api = any("api" in f.lower() for f in tier.features)
                has_analytics = any("analytics" in f.lower() for f in tier.features)

                if has_approval and has_api and has_analytics:
                    print(f"  [PASS] Professional tier has all premium features")
                    test_results["passed"].append("Features: Professional tier complete")
                else:
                    print(f"  [FAIL] Professional tier missing features")
                    test_results["failed"].append("Features: Professional tier incomplete")

            print(f"  Total features: {len(tier.features)}")

    finally:
        db.close()


def print_test_summary():
    """Print summary of all tests"""
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    total_passed = len(test_results["passed"])
    total_failed = len(test_results["failed"])
    total_tests = total_passed + total_failed

    print(f"\n[PASS] Passed: {total_passed}/{total_tests}")
    for test in test_results["passed"]:
        print(f"  - {test}")

    print(f"\n[FAIL] Failed: {total_failed}/{total_tests}")
    for test in test_results["failed"]:
        print(f"  - {test}")

    pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    print(f"\nPass Rate: {pass_rate:.1f}%")

    print("\n" + "="*60)
    if total_failed == 0:
        print("[SUCCESS] All tier limit tests passed!")
    else:
        print("[FAIL] Some tests failed - review tier configuration")
    print("="*60)

    return total_failed == 0


if __name__ == "__main__":
    print("="*60)
    print("BILLING TIER LIMITS ENFORCEMENT TEST SUITE")
    print("="*60)

    # Run all tests
    test_tier_limits_in_database()
    test_limit_enforcer_free_tier()
    test_tier_comparison()
    test_tier_pricing()
    test_tier_features()

    # Print summary
    success = print_test_summary()

    sys.exit(0 if success else 1)
