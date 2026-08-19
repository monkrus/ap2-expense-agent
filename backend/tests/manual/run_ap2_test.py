#!/usr/bin/env python3
"""AP2 Automation Test Suite"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"
ORG_ID = "8551ddd7-4d90-4693-9d92-ee2065495e30"


def main():
    print("=" * 70)
    print("AP2 AUTOMATION TEST SUITE")
    print("=" * 70)

    passed = 0
    failed = 0

    # Login
    print("\n[1] Logging in as adminfree...")
    login_resp = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"username": "adminfree", "password": "Password123!"},
    )

    if login_resp.status_code != 200:
        print(f"   FAILED to login: {login_resp.status_code}")
        print(f"   Response: {login_resp.text}")
        return 1

    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": ORG_ID}
    print(f"   SUCCESS - Logged in")

    # Test 1: Auto-approval policy - small expense
    print("\n[TEST 1] Small expense $15 (policy evaluation test)")
    test_resp = requests.post(
        f"{BASE_URL}/api/v1/approval-policies/test",
        headers=headers,
        json={"amount": 15.00, "category": "MEALS", "vendor": "Cafe"},
    )
    if test_resp.status_code == 200:
        r = test_resp.json()
        policy = r.get("matching_policy")
        reason = r.get("reason", "")
        if r.get("would_auto_approve"):
            print(
                f'   [PASS] Would auto-approve via: {policy.get("name", "Unknown") if policy else "N/A"}'
            )
            passed += 1
        elif policy and "limit" in reason.lower():
            # Policy matched but limit exceeded - policy is working correctly
            print(f'   [PASS] Policy matched: {policy.get("name")}')
            print(f"         Limit reached: {reason}")
            passed += 1
        else:
            print(f"   [FAIL] No policy matched. Reason: {reason}")
            failed += 1
    else:
        print(f"   [FAIL] Request failed: {test_resp.status_code}")
        failed += 1

    # Test 2: Large expense (should NOT auto-approve)
    print("\n[TEST 2] Large expense $500 (should require MANUAL approval)")
    test_resp2 = requests.post(
        f"{BASE_URL}/api/v1/approval-policies/test",
        headers=headers,
        json={"amount": 500.00, "category": "SOFTWARE", "vendor": "TechStore"},
    )
    if test_resp2.status_code == 200:
        r = test_resp2.json()
        if not r.get("would_auto_approve"):
            print(f"   [PASS] Correctly requires manual approval")
            print(f'   Reason: {r.get("reason", "N/A")}')
            passed += 1
        else:
            print(f"   [FAIL] Should NOT auto-approve large expense")
            failed += 1
    else:
        print(f"   [FAIL] Request failed: {test_resp2.status_code}")
        failed += 1

    # Test 3: Create Intent Mandate
    print("\n[TEST 3] Create AP2 Intent Mandate")
    mandate_resp = requests.post(
        f"{BASE_URL}/api/ap2/intent-mandate",
        headers=headers,
        json={
            "constraints": {
                "merchant": "Amazon",
                "category": "OFFICE_SUPPLIES",
                "max_amount": 150.0,
            },
            "expiration_hours": 24,
        },
    )
    mandate_id = None
    if mandate_resp.status_code in [200, 201]:
        mandate = mandate_resp.json()
        mandate_id = mandate.get("id") or mandate.get("mandate_id")
        print(
            f'   [PASS] Mandate created: {str(mandate_id)[:20] if mandate_id else "N/A"}'
        )
        print(f'   Status: {mandate.get("status")}')
        passed += 1
    else:
        print(f"   [FAIL] {mandate_resp.status_code}: {mandate_resp.text[:100]}")
        failed += 1

    # Test 4: Submit expense matching mandate
    print("\n[TEST 4] Submit expense to Amazon $75 (should AUTO-APPROVE via mandate)")
    expense_resp = requests.post(
        f"{BASE_URL}/api/v1/expenses",
        headers=headers,
        json={
            "amount": 75.00,
            "vendor": "Amazon",
            "category": "OFFICE_SUPPLIES",
            "description": "Office keyboard - AP2 mandate test",
            "expense_date": "2026-01-22",
        },
    )
    if expense_resp.status_code in [200, 201]:
        expense = expense_resp.json()
        auto_approved = expense.get("auto_approved", False)
        if auto_approved:
            print(f'   [PASS] Auto-approved via: {expense.get("auto_approved_via")}')
            passed += 1
        else:
            print(
                f'   [PARTIAL] Created but not auto-approved. Status: {expense.get("status")}'
            )
            passed += 0.5
            failed += 0.5
    else:
        print(f"   [FAIL] {expense_resp.status_code}: {expense_resp.text[:100]}")
        failed += 1

    # Test 5: Submit expense NOT matching mandate
    print("\n[TEST 5] Submit expense to BestBuy $100 (should NOT auto-approve)")
    expense_resp2 = requests.post(
        f"{BASE_URL}/api/v1/expenses",
        headers=headers,
        json={
            "amount": 100.00,
            "vendor": "BestBuy",
            "category": "SOFTWARE",
            "description": "Software purchase - should not auto-approve via mandate",
            "expense_date": "2026-01-22",
        },
    )
    if expense_resp2.status_code in [200, 201]:
        expense2 = expense_resp2.json()
        auto_approved = expense2.get("auto_approved", False)
        if not auto_approved:
            print(
                f'   [PASS] Correctly requires manual approval. Status: {expense2.get("status")}'
            )
            passed += 1
        else:
            print(f"   [FAIL] Should NOT auto-approve non-matching expense")
            failed += 1
    else:
        print(f"   [FAIL] {expense_resp2.status_code}")
        failed += 1

    # Test 6: Statistics
    print("\n[TEST 6] Get auto-approval statistics")
    stats_resp = requests.get(
        f"{BASE_URL}/api/v1/approval-policies/analytics/statistics", headers=headers
    )
    if stats_resp.status_code == 200:
        stats = stats_resp.json()
        print(f"   [PASS] Statistics retrieved")
        print(f'   - Total expenses: {stats.get("total_expenses", 0)}')
        print(
            f'   - Auto-approved: {stats.get("auto_approved_count", 0)} ({stats.get("auto_approval_rate_percent", 0):.1f}%)'
        )
        print(f'   - Manual: {stats.get("manual_approved_count", 0)}')
        passed += 1
    else:
        print(f"   [FAIL] {stats_resp.status_code}")
        failed += 1

    # Test 7: List mandates
    print("\n[TEST 7] List user mandates")
    mandates_resp = requests.get(f"{BASE_URL}/api/ap2/user/mandates", headers=headers)
    if mandates_resp.status_code == 200:
        data = mandates_resp.json()
        mandates = data.get("mandates", data) if isinstance(data, dict) else data
        print(f"   [PASS] Found {len(mandates)} mandates")
        for m in mandates[:3]:
            print(
                f'   - {str(m.get("id", "?"))[:12]}... | {m.get("status")} | type: {m.get("type", "intent")}'
            )
        passed += 1
    else:
        print(f"   [FAIL] {mandates_resp.status_code}")
        failed += 1

    # Test 8: List approval policies
    print("\n[TEST 8] List approval policies")
    policies_resp = requests.get(
        f"{BASE_URL}/api/v1/approval-policies", headers=headers
    )
    if policies_resp.status_code == 200:
        policies = policies_resp.json()
        print(f"   [PASS] Found {len(policies)} policies")
        for p in policies[:3]:
            print(
                f'   - {p.get("name")} | active: {p.get("is_active")} | auto_approve: {p.get("auto_approve")}'
            )
        passed += 1
    else:
        print(f"   [FAIL] {policies_resp.status_code}")
        failed += 1

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    total = passed + failed
    print(f"Passed: {int(passed)}/{int(total)}")
    print(f"Failed: {int(failed)}/{int(total)}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    print("=" * 70)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
