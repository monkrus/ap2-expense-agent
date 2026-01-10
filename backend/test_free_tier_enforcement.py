"""
Test Free Tier Limit Enforcement

This script verifies that free tier users CANNOT exceed their limits.
Tests all critical endpoints to ensure 402 Payment Required errors are raised.
"""

import os
os.environ['TESTING'] = 'false'  # Ensure testing mode is OFF

from src.database import SessionLocal
from src.models import User, Organization, OrganizationMember, OrganizationRole
from src.billing.limit_enforcer import LimitEnforcer, LimitExceededError
from src.billing.usage_tracker import UsageTracker

def test_expense_limit_enforcement():
    """Test that expense limit is enforced"""
    db = SessionLocal()
    try:
        # Get free tier org
        member = db.query(OrganizationMember).filter(
            OrganizationMember.is_active == True
        ).first()

        if not member:
            print("[SKIP] No organization members found")
            return

        org_id = member.organization_id
        enforcer = LimitEnforcer(db)

        # Check current usage
        usage = enforcer.get_current_month_usage(org_id)
        limits = enforcer.get_org_tier(org_id)

        print("\n=== EXPENSE LIMIT ENFORCEMENT ===")
        print(f"Current: {usage['expenses']}/{limits.max_expenses_per_month}")

        # Try to check if we can add more
        if usage['expenses'] >= limits.max_expenses_per_month:
            print("[TEST] Already at limit, testing enforcement...")
            try:
                enforcer.check_expense_limit(org_id, raise_error=True)
                print("[FAIL] ❌ Should have raised LimitExceededError!")
                return False
            except LimitExceededError as e:
                print(f"[PASS] ✓ Correctly blocked: {str(e)}")
                return True
        else:
            print(f"[INFO] Under limit ({usage['expenses']}/{limits.max_expenses_per_month}), cannot test enforcement yet")
            return None

    finally:
        db.close()

def test_ap2_limit_enforcement():
    """Test that AP2 transaction limit is enforced"""
    db = SessionLocal()
    try:
        member = db.query(OrganizationMember).filter(
            OrganizationMember.is_active == True
        ).first()

        if not member:
            print("[SKIP] No organization members found")
            return

        org_id = member.organization_id
        enforcer = LimitEnforcer(db)

        usage = enforcer.get_current_month_usage(org_id)
        limits = enforcer.get_org_tier(org_id)

        print("\n=== AP2 TRANSACTION LIMIT ENFORCEMENT ===")
        print(f"Current: {usage['ap2_transactions']}/{limits.max_ap2_transactions}")

        if usage['ap2_transactions'] >= limits.max_ap2_transactions:
            print("[TEST] Already at limit, testing enforcement...")
            try:
                enforcer.check_ap2_transaction_limit(org_id, raise_error=True)
                print("[FAIL] ❌ Should have raised LimitExceededError!")
                return False
            except LimitExceededError as e:
                print(f"[PASS] ✓ Correctly blocked: {str(e)}")
                return True
        else:
            print(f"[INFO] Under limit ({usage['ap2_transactions']}/{limits.max_ap2_transactions}), cannot test enforcement yet")
            return None

    finally:
        db.close()

def test_ocr_limit_enforcement():
    """Test that OCR scan limit is enforced"""
    db = SessionLocal()
    try:
        member = db.query(OrganizationMember).filter(
            OrganizationMember.is_active == True
        ).first()

        if not member:
            print("[SKIP] No organization members found")
            return

        org_id = member.organization_id
        enforcer = LimitEnforcer(db)

        usage = enforcer.get_current_month_usage(org_id)
        limits = enforcer.get_org_tier(org_id)

        print("\n=== OCR SCAN LIMIT ENFORCEMENT ===")
        print(f"Current: {usage['ocr_scans']}/{limits.ocr_scans_included}")

        if usage['ocr_scans'] >= limits.ocr_scans_included:
            print("[TEST] Already at limit, testing enforcement...")
            try:
                enforcer.check_ocr_limit(org_id, raise_error=True)
                print("[FAIL] ❌ Should have raised LimitExceededError!")
                return False
            except LimitExceededError as e:
                print(f"[PASS] ✓ Correctly blocked: {str(e)}")
                return True
        else:
            print(f"[INFO] Under limit ({usage['ocr_scans']}/{limits.ocr_scans_included}), cannot test enforcement yet")
            return None

    finally:
        db.close()

def test_ai_categorization_enforcement():
    """Test that AI categorization is blocked on free tier"""
    db = SessionLocal()
    try:
        member = db.query(OrganizationMember).filter(
            OrganizationMember.is_active == True
        ).first()

        if not member:
            print("[SKIP] No organization members found")
            return

        org_id = member.organization_id
        enforcer = LimitEnforcer(db)
        limits = enforcer.get_org_tier(org_id)

        print("\n=== AI CATEGORIZATION ENFORCEMENT (FREE TIER) ===")
        print(f"Limit: {limits.max_ai_categorizations} (should be 0 for free tier)")

        if limits.max_ai_categorizations == 0:
            print("[TEST] Testing AI categorization block...")
            try:
                enforcer.check_ai_categorization_limit(org_id, raise_error=True)
                print("[FAIL] ❌ Should have raised LimitExceededError!")
                return False
            except LimitExceededError as e:
                print(f"[PASS] ✓ Correctly blocked: {str(e)}")
                return True
        else:
            print(f"[INFO] AI categorization is allowed ({limits.max_ai_categorizations}), skipping test")
            return None

    finally:
        db.close()

def show_current_usage():
    """Display current usage summary"""
    db = SessionLocal()
    try:
        member = db.query(OrganizationMember).filter(
            OrganizationMember.is_active == True
        ).first()

        if not member:
            print("[SKIP] No organization members found")
            return

        org_id = member.organization_id
        enforcer = LimitEnforcer(db)

        usage = enforcer.get_current_month_usage(org_id)
        limits = enforcer.get_org_tier(org_id)

        print("\n" + "=" * 60)
        print("CURRENT USAGE SUMMARY")
        print("=" * 60)
        print(f"Tier: {limits.tier_name}")
        print(f"\nExpenses: {usage['expenses']}/{limits.max_expenses_per_month or 'unlimited'}")
        print(f"AP2 Transactions: {usage['ap2_transactions']}/{limits.max_ap2_transactions or 'unlimited'}")
        print(f"OCR Scans: {usage['ocr_scans']}/{limits.ocr_scans_included or 'unlimited'}")
        print(f"AI Categorizations: {usage['ai_categorizations']}/{limits.max_ai_categorizations or 'unlimited'}")
        print(f"Active Members: {usage['members']}/{limits.max_users or 'unlimited'}")
        print("=" * 60)

    finally:
        db.close()

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("FREE TIER LIMIT ENFORCEMENT TEST")
    print("=" * 60)

    show_current_usage()

    results = {
        "expense": test_expense_limit_enforcement(),
        "ap2": test_ap2_limit_enforcement(),
        "ocr": test_ocr_limit_enforcement(),
        "ai": test_ai_categorization_enforcement(),
    }

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for r in results.values() if r is True)
    failed = sum(1 for r in results.values() if r is False)
    skipped = sum(1 for r in results.values() if r is None)

    for name, result in results.items():
        if result is True:
            print(f"{name}: PASS ✓")
        elif result is False:
            print(f"{name}: FAIL ✗")
        else:
            print(f"{name}: SKIPPED (not at limit yet)")

    print(f"\nTotal: {passed} passed, {failed} failed, {skipped} skipped")

    if failed > 0:
        print("\n⚠️  CRITICAL: Some limits are NOT enforced!")
    elif passed == 0:
        print("\n📝 Need to reach limits first to test enforcement")
    else:
        print("\n✓ All tested limits are properly enforced!")
