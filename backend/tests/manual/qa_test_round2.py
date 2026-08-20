"""
QA Test Round 2: Re-test edge cases that hit rate limiting in round 1
Rate limit is 5/minute, so we add 65s delays between batches.
"""

import json
import time

import requests

BASE = "http://127.0.0.1:8000"
LOGIN_URL = f"{BASE}/api/v1/auth/login"
FLOW_URL = f"{BASE}/api/ap2/complete-flow"

results = []


def log(test_name, status, detail=""):
    results.append({"test": test_name, "status": status, "detail": detail})
    print(f"[{status}] {test_name}: {detail}")


# Login
resp = requests.post(LOGIN_URL, json={"username": "adminfree", "password": "Testme1!"})
token = resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

print("Waiting 65s for rate limit to reset...")
time.sleep(65)

# BATCH 1 (max 5 calls)

print("\n" + "=" * 80)
print("TEST 7: Edge Case - Empty Items Array")
print("=" * 80)
resp = requests.post(
    FLOW_URL,
    json={
        "items": [],
        "merchant": "TestMerchant",
        "constraints": {
            "max_amount": 0,
            "monthly_limit": 0,
            "category": "OTHER",
            "merchant": "TestMerchant",
        },
    },
    headers=headers,
)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:500]}")
if resp.status_code == 200:
    d = resp.json()
    log(
        "T7-empty-items",
        "FAIL",
        f"Backend accepted empty items array. ap2_flow_complete={d.get('ap2_flow_complete')}",
    )
elif resp.status_code in (400, 422):
    log("T7-empty-items", "PASS", f"Rejected empty items: {resp.status_code}")
else:
    log("T7-empty-items", "FAIL", f"Unexpected: {resp.status_code}: {resp.text[:200]}")


print("\n" + "=" * 80)
print("TEST 8: Edge Case - Items Without Amount Field")
print("=" * 80)
resp = requests.post(
    FLOW_URL,
    json={
        "items": [{"description": "No amount item"}],
        "merchant": "TestMerchant",
        "constraints": {
            "max_amount": 100.00,
            "monthly_limit": 100.00,
            "category": "OTHER",
            "merchant": "TestMerchant",
        },
    },
    headers=headers,
)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:500]}")
if resp.status_code == 200:
    d = resp.json()
    amount = d.get("payment_result", {}).get("amount", "?")
    log(
        "T8-missing-amount",
        "FAIL",
        f"Accepted item without amount field. Processed amount: {amount}",
    )
elif resp.status_code in (400, 422):
    log("T8-missing-amount", "PASS", f"Rejected missing amount: {resp.status_code}")
else:
    log(
        "T8-missing-amount",
        "FAIL",
        f"Unexpected: {resp.status_code}: {resp.text[:200]}",
    )


print("\n" + "=" * 80)
print("TEST 9: No constraints sent (backend auto-generate)")
print("=" * 80)
resp = requests.post(
    FLOW_URL,
    json={
        "items": [{"description": "Widget", "amount": 19.99, "category": "OTHER"}],
        "merchant": "WidgetCo",
    },
    headers=headers,
)
print(f"Status: {resp.status_code}")
data = resp.json()
print(f"Response: {json.dumps(data, indent=2)}")
if resp.status_code == 200 and data.get("ap2_flow_complete"):
    log("T9-no-constraints", "PASS", "Backend auto-generated constraints")
else:
    log("T9-no-constraints", "FAIL", f"Status {resp.status_code}: {data}")


print("\n" + "=" * 80)
print("TEST 10: Constraint Mismatch - max_amount < cart total")
print("=" * 80)
resp = requests.post(
    FLOW_URL,
    json={
        "items": [
            {"description": "Expensive item", "amount": 100.00, "category": "OTHER"}
        ],
        "merchant": "Store",
        "constraints": {
            "max_amount": 50.00,
            "monthly_limit": 50.00,
            "category": "OTHER",
            "merchant": "Store",
        },
    },
    headers=headers,
)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:500]}")
if resp.status_code == 200:
    log(
        "T10-constraint-violation",
        "FAIL",
        "Backend accepted cart exceeding max_amount constraint",
    )
elif resp.status_code in (400, 422):
    log(
        "T10-constraint-violation",
        "PASS",
        f"Rejected constraint violation: {resp.status_code}",
    )
else:
    log(
        "T10-constraint-violation",
        "FAIL",
        f"Unexpected: {resp.status_code}: {resp.text[:200]}",
    )


print("\n" + "=" * 80)
print("TEST 11: Merchant Mismatch in Constraints")
print("=" * 80)
resp = requests.post(
    FLOW_URL,
    json={
        "items": [{"description": "Test item", "amount": 10.00, "category": "OTHER"}],
        "merchant": "Amazon",
        "constraints": {
            "max_amount": 15.00,
            "monthly_limit": 15.00,
            "category": "OTHER",
            "merchant": "Staples",
        },
    },
    headers=headers,
)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:500]}")
if resp.status_code == 200:
    log("T11-merchant-mismatch", "FAIL", "Backend accepted merchant mismatch")
elif resp.status_code in (400, 422):
    log(
        "T11-merchant-mismatch",
        "PASS",
        f"Rejected merchant mismatch: {resp.status_code}",
    )
else:
    log("T11-merchant-mismatch", "FAIL", f"Unexpected: {resp.status_code}")


print("\nWaiting 65s for rate limit to reset...")
time.sleep(65)

# BATCH 2

print("\n" + "=" * 80)
print("TEST 12: Category Mismatch in Constraints")
print("=" * 80)
resp = requests.post(
    FLOW_URL,
    json={
        "items": [{"description": "Test item", "amount": 10.00, "category": "TRAVEL"}],
        "merchant": "Airlines",
        "constraints": {
            "max_amount": 15.00,
            "monthly_limit": 15.00,
            "category": "OFFICE_SUPPLIES",
            "merchant": "Airlines",
        },
    },
    headers=headers,
)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:500]}")
if resp.status_code == 200:
    log(
        "T12-category-mismatch",
        "FAIL",
        "Backend accepted items with wrong category vs constraint",
    )
elif resp.status_code in (400, 422):
    log(
        "T12-category-mismatch",
        "PASS",
        f"Rejected category mismatch: {resp.status_code}",
    )
else:
    log("T12-category-mismatch", "FAIL", f"Unexpected: {resp.status_code}")


print("\n" + "=" * 80)
print("TEST 20: Special Characters (XSS)")
print("=" * 80)
resp = requests.post(
    FLOW_URL,
    json={
        "items": [
            {
                "description": "Test <script>alert('xss')</script>",
                "amount": 10.00,
                "category": "OTHER",
            }
        ],
        "merchant": 'O\'Reilly & Co "quoted" <b>bold</b>',
        "constraints": {
            "max_amount": 10.50,
            "monthly_limit": 10.50,
            "category": "OTHER",
            "merchant": 'O\'Reilly & Co "quoted" <b>bold</b>',
        },
    },
    headers=headers,
)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:500]}")
if resp.status_code == 200:
    log(
        "T20-special-chars",
        "FAIL",
        "Accepted HTML/script tags in fields - stored XSS risk",
    )
elif resp.status_code in (400, 422):
    log("T20-special-chars", "PASS", f"Rejected: {resp.status_code}")
else:
    log("T20-special-chars", "FAIL", f"Unexpected: {resp.status_code}")


print("\n" + "=" * 80)
print("TEST 21: Very Long Strings (5000 chars)")
print("=" * 80)
long_str = "A" * 5000
resp = requests.post(
    FLOW_URL,
    json={
        "items": [{"description": long_str, "amount": 10.00, "category": "OTHER"}],
        "merchant": long_str,
        "constraints": {
            "max_amount": 10.50,
            "monthly_limit": 10.50,
            "category": "OTHER",
            "merchant": long_str,
        },
    },
    headers=headers,
)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:300]}")
if resp.status_code == 200:
    log(
        "T21-long-strings",
        "FAIL",
        "Accepted 5000-char merchant. DB column is VARCHAR(255)",
    )
elif resp.status_code == 500:
    log(
        "T21-long-strings",
        "FAIL",
        "500 error - DB column overflow, no input validation",
    )
elif resp.status_code in (400, 422):
    log("T21-long-strings", "PASS", f"Rejected: {resp.status_code}")
else:
    log(
        "T21-long-strings", "FAIL", f"Unexpected: {resp.status_code}: {resp.text[:200]}"
    )


print("\n" + "=" * 80)
print("TEST 22: 10 Items")
print("=" * 80)
items_10 = [
    {"description": f"Item {i}", "amount": 10.00 + i, "category": "OTHER"}
    for i in range(10)
]
total_10 = sum(it["amount"] for it in items_10)
resp = requests.post(
    FLOW_URL,
    json={
        "items": items_10,
        "merchant": "BulkStore",
        "constraints": {
            "max_amount": total_10 * 1.05 + 1,
            "monthly_limit": total_10 * 1.05 + 1,
            "category": "OTHER",
            "merchant": "BulkStore",
        },
    },
    headers=headers,
)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    d = resp.json()
    log(
        "T22-10-items",
        "PASS",
        f"10 items accepted. Total: {d.get('payment_result',{}).get('amount')}",
    )
else:
    log("T22-10-items", "FAIL", f"Status {resp.status_code}: {resp.text[:200]}")


print("\n" + "=" * 80)
print("TEST 23: Mixed Categories vs Single Category Constraint")
print("=" * 80)
resp = requests.post(
    FLOW_URL,
    json={
        "items": [
            {"description": "Paper", "amount": 10.00, "category": "OFFICE_SUPPLIES"},
            {"description": "Lunch", "amount": 15.00, "category": "MEALS"},
        ],
        "merchant": "MixedStore",
        "constraints": {
            "max_amount": 30.00,
            "monthly_limit": 30.00,
            "category": "OFFICE_SUPPLIES",
            "merchant": "MixedStore",
        },
    },
    headers=headers,
)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:500]}")
if resp.status_code == 200:
    log(
        "T23-mixed-categories",
        "FAIL",
        "Accepted mixed categories with single-category constraint",
    )
elif resp.status_code in (400, 422):
    log("T23-mixed-categories", "PASS", f"Rejected: {resp.status_code}")
else:
    log("T23-mixed-categories", "FAIL", f"Unexpected: {resp.status_code}")


print("\nWaiting 65s for rate limit to reset...")
time.sleep(65)

# BATCH 3

print("\n" + "=" * 80)
print("TEST 6: Very Large Amount (>$100,000)")
print("=" * 80)
resp = requests.post(
    FLOW_URL,
    json={
        "items": [
            {
                "description": "Enterprise server",
                "amount": 150000.00,
                "category": "HARDWARE",
            }
        ],
        "merchant": "Dell",
        "constraints": {
            "max_amount": 157500.00,
            "monthly_limit": 157500.00,
            "category": "HARDWARE",
            "merchant": "Dell",
        },
    },
    headers=headers,
)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:500]}")
if resp.status_code == 200:
    d = resp.json()
    log(
        "T6-large-amount",
        "FAIL",
        f"$150,000 payment accepted - no upper limit. amount={d.get('payment_result',{}).get('amount')}",
    )
elif resp.status_code in (400, 422):
    log("T6-large-amount", "PASS", f"Large amount rejected: {resp.status_code}")
else:
    log("T6-large-amount", "FAIL", f"Unexpected: {resp.status_code}: {resp.text[:200]}")


print("\n" + "=" * 80)
print("TEST 26: Fractional Penny Amount")
print("=" * 80)
resp = requests.post(
    FLOW_URL,
    json={
        "items": [{"description": "Fractional", "amount": 0.001, "category": "OTHER"}],
        "merchant": "PennyStore",
        "constraints": {
            "max_amount": 0.01,
            "monthly_limit": 0.01,
            "category": "OTHER",
            "merchant": "PennyStore",
        },
    },
    headers=headers,
)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:500]}")
if resp.status_code == 200:
    d = resp.json()
    amount = d.get("payment_result", {}).get("amount")
    log("T26-fractional-penny", "FAIL", f"Accepted sub-penny amount: {amount}")
elif resp.status_code in (400, 422):
    log("T26-fractional-penny", "PASS", f"Rejected sub-penny: {resp.status_code}")
else:
    log("T26-fractional-penny", "FAIL", f"Unexpected: {resp.status_code}")


print("\n" + "=" * 80)
print(
    "TEST 27: Frontend sends constraints but backend also auto-generates - buffer mismatch"
)
print("=" * 80)
# When frontend SENDS constraints: max_amount = total * 1.05 (5% buffer)
# When backend AUTO-GENERATES: max_amount = total * 1.1 (10% buffer)
# This creates inconsistency. Let's verify by sending NO constraints.
resp = requests.post(
    FLOW_URL,
    json={
        "items": [
            {"description": "Buffer test", "amount": 100.00, "category": "OTHER"}
        ],
        "merchant": "BufferStore",
        # No constraints - backend will auto-generate with 10% buffer
    },
    headers=headers,
)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    d = resp.json()
    # Check what constraints were actually used
    intent_id = d.get("intent_mandate_id")
    # Get the mandate to see constraints
    mandates_resp = requests.get(
        f"{BASE}/api/ap2/mandate/{intent_id}/status?mandate_type=intent",
        headers=headers,
    )
    print(f"Intent mandate status: {mandates_resp.text[:300]}")
    log(
        "T27-buffer-mismatch",
        "FAIL",
        "Frontend uses 5% buffer, backend auto uses 10% - inconsistent UX",
    )
else:
    log("T27-buffer-mismatch", "FAIL", f"Could not test: {resp.status_code}")


print("\n" + "=" * 80)
print("ROUND 2 SUMMARY")
print("=" * 80)
pass_count = sum(1 for r in results if r["status"] == "PASS")
fail_count = sum(1 for r in results if r["status"] == "FAIL")
print(f"\nTotal: {len(results)} tests | PASS: {pass_count} | FAIL: {fail_count}")
print()
for r in results:
    marker = "PASS" if r["status"] == "PASS" else "FAIL"
    print(f"  [{marker}] {r['test']}: {r['detail']}")
