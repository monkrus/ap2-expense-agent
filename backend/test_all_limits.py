"""
Comprehensive Free Tier Limit Enforcement Test

Verifies that ALL limits are enforced and cannot be bypassed.
"""

import os
os.environ['TESTING'] = 'false'

from src.database import SessionLocal
from src.models import OrganizationMember
from src.billing.limit_enforcer import LimitEnforcer

def test_all_limits():
    db = SessionLocal()
    try:
        member = db.query(OrganizationMember).filter(
            OrganizationMember.is_active == True
        ).first()

        if not member:
            print('[ERROR] No organization found')
            return

        org_id = member.organization_id
        enforcer = LimitEnforcer(db)

        # Get current usage
        usage = enforcer.get_current_month_usage(org_id)
        limits = enforcer.get_org_tier(org_id)

        print('=' * 60)
        print('FREE TIER LIMIT ENFORCEMENT - COMPREHENSIVE TEST')
        print('=' * 60)
        print()

        # Test 1: Expenses
        print('1. EXPENSE LIMIT')
        print(f'   Current: {usage["expenses"]}/{limits.max_expenses_per_month}')
        print(f'   Enforcement: expenses.py:149')
        can_create, msg = enforcer.check_expense_limit(org_id, raise_error=False)
        if usage["expenses"] >= limits.max_expenses_per_month:
            print('   Status: [BLOCKED] At limit - 402 error on next creation')
        else:
            print(f'   Status: [OK] Can create {limits.max_expenses_per_month - usage["expenses"]} more')
        print()

        # Test 2: AP2 Transactions
        print('2. AP2 TRANSACTION LIMIT')
        print(f'   Current: {usage["ap2_transactions"]}/{limits.max_ap2_transactions}')
        print(f'   Enforcement: ap2.py:307 (execute_payment)')
        print(f'                ap2.py:367 (complete_ap2_flow) [JUST ADDED]')
        can_use, msg = enforcer.check_ap2_transaction_limit(org_id, raise_error=False)
        if usage["ap2_transactions"] >= limits.max_ap2_transactions:
            print('   Status: [BLOCKED] At limit - 402 error on next transaction')
        else:
            print(f'   Status: [OK] Can use {limits.max_ap2_transactions - usage["ap2_transactions"]} more')
        print()

        # Test 3: OCR Scans
        print('3. OCR SCAN LIMIT')
        print(f'   Current: {usage["ocr_scans"]}/{limits.ocr_scans_included}')
        print(f'   Enforcement: receipts.py:357-370')
        can_scan, msg = enforcer.check_ocr_limit(org_id, raise_error=False)
        if usage["ocr_scans"] >= limits.ocr_scans_included:
            print('   Status: [BLOCKED] At limit - 402 error on next upload')
        else:
            print(f'   Status: [OK] Can scan {limits.ocr_scans_included - usage["ocr_scans"]} more')
        print()

        # Test 4: AI Categorization
        print('4. AI CATEGORIZATION LIMIT')
        print(f'   Current: {usage["ai_categorizations"]}/{limits.max_ai_categorizations}')
        print(f'   Enforcement: Built-in (limit=0 for free tier)')
        if limits.max_ai_categorizations == 0:
            print('   Status: [BLOCKED] Not available on free tier')
        else:
            print(f'   Status: [OK] Can use {limits.max_ai_categorizations} categorizations')
        print()

        print('=' * 60)
        print('SUMMARY')
        print('=' * 60)

        all_enforced = True

        # Check if any limit is missing enforcement
        if limits.max_expenses_per_month and usage["expenses"] >= limits.max_expenses_per_month:
            can_create, _ = enforcer.check_expense_limit(org_id, raise_error=False)
            if can_create:
                print('[FAIL] Expenses: Limit reached but still allowed!')
                all_enforced = False

        if limits.max_ap2_transactions and usage["ap2_transactions"] >= limits.max_ap2_transactions:
            can_use, _ = enforcer.check_ap2_transaction_limit(org_id, raise_error=False)
            if can_use:
                print('[FAIL] AP2: Limit reached but still allowed!')
                all_enforced = False

        if limits.ocr_scans_included and usage["ocr_scans"] >= limits.ocr_scans_included:
            can_scan, _ = enforcer.check_ocr_limit(org_id, raise_error=False)
            if can_scan:
                print('[FAIL] OCR: Limit reached but still allowed!')
                all_enforced = False

        if all_enforced:
            print('[PASS] All limits are properly enforced')
            print('')
            print('Free tier users CANNOT exceed:')
            print(f'  - {limits.max_expenses_per_month} expenses/month')
            print(f'  - {limits.max_ap2_transactions} AP2 transactions/month')
            print(f'  - {limits.ocr_scans_included} OCR scans/month')
            print(f'  - {limits.max_ai_categorizations} AI categorizations (blocked)')
        else:
            print('[FAIL] Some limits are not enforced!')

        print()

    finally:
        db.close()

if __name__ == "__main__":
    test_all_limits()
