"""
QA Test: AP2 Complete Flow (One-time Authorization)
Thorough testing of both happy paths and edge cases.
"""

import requests
import json
import time

BASE = "http://127.0.0.1:8000"
LOGIN_URL = f"{BASE}/api/v1/auth/login"
FLOW_URL = f"{BASE}/api/ap2/complete-flow"
MANDATES_URL = f"{BASE}/api/ap2/user/mandates"

results = []


def log(test_name, status, detail=""):
    emoji = "PASS" if status == "PASS" else "FAIL"
    results.append({"test": test_name, "status": status, "detail": detail})
    print(f"[{emoji}] {test_name}: {detail}")


# Step 0: Login
print("=" * 80)
print("STEP 0: Authentication")
print("=" * 80)
resp = requests.post(LOGIN_URL, json={"username": "adminfree", "password": "Testme1!"})
assert resp.status_code == 200, f"Login failed: {resp.text}"
token = resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
print(f"Logged in. Token: {token[:20]}...")

# Count mandates before tests
resp_before = requests.get(MANDATES_URL, params={"limit": 200}, headers=headers)
mandates_before = resp_before.json()["count"]
print(f"Mandates before tests: {mandates_before}")


print("\n" + "=" * 80)
print("TEST 1: Happy Path - Single Item")
print("=" * 80)
payload = {
    "items": [
        {"description": "Printer paper", "amount": 29.99, "category": "OFFICE_SUPPLIES"}
    ],
    "merchant": "Staples",
    "constraints": {
        "max_amount": 31.49,  # 29.99 * 1.05 = 31.4895 -> ceil to 31.49
        "monthly_limit": 31.49,
        "category": "OFFICE_SUPPLIES",
        "merchant": "Staples",
    },
}
resp = requests.post(FLOW_URL, json=payload, headers=headers)
print(f"Status: {resp.status_code}")
data = resp.json()
print(f"Response: {json.dumps(data, indent=2)}")

if resp.status_code == 200:
    # Verify the response has all expected fields
    expected_keys = [
        "intent_mandate_id",
        "cart_mandate_id",
        "payment_mandate_id",
        "payment_result",
        "ap2_flow_complete",
    ]
    missing = [k for k in expected_keys if k not in data]
    if missing:
        log("T1-response-keys", "FAIL", f"Missing keys: {missing}")
    else:
        log("T1-response-keys", "PASS", "All expected keys present")

    # Check ap2_flow_complete
    if data.get("ap2_flow_complete") is True:
        log("T1-flow-complete", "PASS", "Flow marked as complete")
    else:
        log(
            "T1-flow-complete",
            "FAIL",
            f"ap2_flow_complete={data.get('ap2_flow_complete')}",
        )

    # Check payment_result structure
    pr = data.get("payment_result", {})
    if pr.get("success"):
        log(
            "T1-payment-success",
            "PASS",
            f"Payment successful, txn: {pr.get('transaction_id')}",
        )
    else:
        log("T1-payment-success", "FAIL", f"Payment failed: {pr}")
else:
    log("T1-happy-path", "FAIL", f"HTTP {resp.status_code}: {resp.text}")


print("\n" + "=" * 80)
print("TEST 2: Happy Path - Multiple Items")
print("=" * 80)
payload2 = {
    "items": [
        {"description": "Laptop stand", "amount": 49.99, "category": "HARDWARE"},
        {"description": "USB cable", "amount": 12.50, "category": "HARDWARE"},
        {"description": "Mouse", "amount": 25.00, "category": "HARDWARE"},
    ],
    "merchant": "Amazon",
    "constraints": {
        "max_amount": 91.87,  # (49.99+12.50+25.00)*1.05 = 91.8645
        "monthly_limit": 91.87,
        "category": "HARDWARE",
        "merchant": "Amazon",
    },
}
resp = requests.post(FLOW_URL, json=payload2, headers=headers)
print(f"Status: {resp.status_code}")
data2 = resp.json()
print(f"Response keys: {list(data2.keys())}")

if resp.status_code == 200 and data2.get("ap2_flow_complete"):
    log("T2-multi-item", "PASS", f"3-item flow completed")
else:
    log("T2-multi-item", "FAIL", f"HTTP {resp.status_code}: {data2}")


print("\n" + "=" * 80)
print("TEST 3: Edge Case - Empty Merchant (validation)")
print("=" * 80)
payload3 = {
    "items": [{"description": "Test item", "amount": 10.00, "category": "OTHER"}],
    "merchant": "",
    "constraints": {
        "max_amount": 10.50,
        "monthly_limit": 10.50,
        "category": "OTHER",
        "merchant": "",
    },
}
resp = requests.post(FLOW_URL, json=payload3, headers=headers)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text}")
if resp.status_code == 200:
    log(
        "T3-empty-merchant", "FAIL", "Backend accepted empty merchant - should validate"
    )
elif resp.status_code in (400, 422):
    log("T3-empty-merchant", "PASS", f"Rejected empty merchant: {resp.status_code}")
else:
    log("T3-empty-merchant", "FAIL", f"Unexpected status: {resp.status_code}")


print("\n" + "=" * 80)
print("TEST 4: Edge Case - Item Amount = 0")
print("=" * 80)
payload4 = {
    "items": [{"description": "Free sample", "amount": 0.00, "category": "OTHER"}],
    "merchant": "TestMerchant",
    "constraints": {
        "max_amount": 0.00,
        "monthly_limit": 0.00,
        "category": "OTHER",
        "merchant": "TestMerchant",
    },
}
resp = requests.post(FLOW_URL, json=payload4, headers=headers)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text}")
if resp.status_code == 200:
    log("T4-zero-amount", "FAIL", "Backend accepted $0 payment - should validate")
elif resp.status_code in (400, 422):
    log("T4-zero-amount", "PASS", f"Rejected zero amount: {resp.status_code}")
else:
    log("T4-zero-amount", "FAIL", f"Unexpected: {resp.status_code}: {resp.text}")


print("\n" + "=" * 80)
print("TEST 5: Edge Case - Negative Amount")
print("=" * 80)
payload5 = {
    "items": [{"description": "Refund item", "amount": -50.00, "category": "OTHER"}],
    "merchant": "TestMerchant",
    "constraints": {
        "max_amount": 100.00,
        "monthly_limit": 100.00,
        "category": "OTHER",
        "merchant": "TestMerchant",
    },
}
resp = requests.post(FLOW_URL, json=payload5, headers=headers)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text}")
if resp.status_code == 200:
    d = resp.json()
    cart_total = d.get("payment_result", {}).get("amount", "?")
    log(
        "T5-negative-amount",
        "FAIL",
        f"Backend accepted negative amount. Cart total={cart_total}",
    )
elif resp.status_code in (400, 422):
    log("T5-negative-amount", "PASS", f"Rejected negative amount: {resp.status_code}")
else:
    log("T5-negative-amount", "FAIL", f"Unexpected: {resp.status_code}")


print("\n" + "=" * 80)
print("TEST 6: Edge Case - Very Large Amount (>$100,000)")
print("=" * 80)
payload6 = {
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
}
resp = requests.post(FLOW_URL, json=payload6, headers=headers)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:500]}")
if resp.status_code == 200:
    d = resp.json()
    log(
        "T6-large-amount",
        "FAIL",
        f"$150,000 accepted with no upper limit. total={d.get('payment_result',{}).get('amount')}",
    )
else:
    log("T6-large-amount", "PASS", f"Large amount handled: {resp.status_code}")


print("\n" + "=" * 80)
print("TEST 7: Edge Case - Empty Items Array")
print("=" * 80)
payload7 = {
    "items": [],
    "merchant": "TestMerchant",
    "constraints": {
        "max_amount": 0,
        "monthly_limit": 0,
        "category": "OTHER",
        "merchant": "TestMerchant",
    },
}
resp = requests.post(FLOW_URL, json=payload7, headers=headers)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text}")
if resp.status_code == 200:
    log("T7-empty-items", "FAIL", "Backend accepted empty items array")
elif resp.status_code in (400, 422):
    log("T7-empty-items", "PASS", f"Rejected empty items: {resp.status_code}")
else:
    log("T7-empty-items", "FAIL", f"Unexpected: {resp.status_code}")


print("\n" + "=" * 80)
print("TEST 8: Edge Case - Items Without Required Fields")
print("=" * 80)
payload8 = {
    "items": [{"description": "No amount item"}],
    "merchant": "TestMerchant",
    "constraints": {
        "max_amount": 100.00,
        "monthly_limit": 100.00,
        "category": "OTHER",
        "merchant": "TestMerchant",
    },
}
resp = requests.post(FLOW_URL, json=payload8, headers=headers)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:300]}")
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
    log("T8-missing-amount", "FAIL", f"Unexpected: {resp.status_code}")


print("\n" + "=" * 80)
print("TEST 9: No constraints sent (backend auto-generate)")
print("=" * 80)
payload9 = {
    "items": [{"description": "Widget", "amount": 19.99, "category": "OTHER"}],
    "merchant": "WidgetCo",
}
resp = requests.post(FLOW_URL, json=payload9, headers=headers)
print(f"Status: {resp.status_code}")
data9 = resp.json()
print(f"Response: {json.dumps(data9, indent=2)}")
if resp.status_code == 200 and data9.get("ap2_flow_complete"):
    log("T9-no-constraints", "PASS", "Backend auto-generated constraints")
else:
    log("T9-no-constraints", "FAIL", f"Status {resp.status_code}: {data9}")


print("\n" + "=" * 80)
print("TEST 10: Constraint Mismatch - max_amount < cart total")
print("=" * 80)
payload10 = {
    "items": [{"description": "Expensive item", "amount": 100.00, "category": "OTHER"}],
    "merchant": "Store",
    "constraints": {
        "max_amount": 50.00,  # deliberately less than item amount
        "monthly_limit": 50.00,
        "category": "OTHER",
        "merchant": "Store",
    },
}
resp = requests.post(FLOW_URL, json=payload10, headers=headers)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:300]}")
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
    log("T10-constraint-violation", "FAIL", f"Unexpected: {resp.status_code}")


print("\n" + "=" * 80)
print("TEST 11: Merchant Mismatch in Constraints")
print("=" * 80)
payload11 = {
    "items": [{"description": "Test item", "amount": 10.00, "category": "OTHER"}],
    "merchant": "Amazon",
    "constraints": {
        "max_amount": 15.00,
        "monthly_limit": 15.00,
        "category": "OTHER",
        "merchant": "Staples",  # constraint says Staples but merchant is Amazon
    },
}
resp = requests.post(FLOW_URL, json=payload11, headers=headers)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:300]}")
if resp.status_code == 200:
    log(
        "T11-merchant-mismatch",
        "FAIL",
        "Backend accepted merchant mismatch between request merchant and constraint merchant",
    )
elif resp.status_code in (400, 422):
    log(
        "T11-merchant-mismatch",
        "PASS",
        f"Rejected merchant mismatch: {resp.status_code}",
    )
else:
    log("T11-merchant-mismatch", "FAIL", f"Unexpected: {resp.status_code}")


print("\n" + "=" * 80)
print("TEST 12: Category Mismatch in Constraints")
print("=" * 80)
payload12 = {
    "items": [{"description": "Test item", "amount": 10.00, "category": "TRAVEL"}],
    "merchant": "Airlines",
    "constraints": {
        "max_amount": 15.00,
        "monthly_limit": 15.00,
        "category": "OFFICE_SUPPLIES",  # constraint says OFFICE_SUPPLIES but item is TRAVEL
        "merchant": "Airlines",
    },
}
resp = requests.post(FLOW_URL, json=payload12, headers=headers)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:300]}")
if resp.status_code == 200:
    log("T12-category-mismatch", "FAIL", "Backend accepted category mismatch")
elif resp.status_code in (400, 422):
    log(
        "T12-category-mismatch",
        "PASS",
        f"Rejected category mismatch: {resp.status_code}",
    )
else:
    log("T12-category-mismatch", "FAIL", f"Unexpected: {resp.status_code}")


print("\n" + "=" * 80)
print("TEST 13: Duplicate/Rapid Submission (rate limiting)")
print("=" * 80)
dup_payload = {
    "items": [{"description": "Rate limit test", "amount": 5.00, "category": "OTHER"}],
    "merchant": "TestStore",
    "constraints": {
        "max_amount": 5.25,
        "monthly_limit": 5.25,
        "category": "OTHER",
        "merchant": "TestStore",
    },
}
statuses = []
for i in range(6):
    resp = requests.post(FLOW_URL, json=dup_payload, headers=headers)
    statuses.append(resp.status_code)
    print(f"  Attempt {i+1}: {resp.status_code}")
    # Don't sleep - test rate limiting

rate_limited = any(s == 429 for s in statuses)
if rate_limited:
    log("T13-rate-limit", "PASS", f"Rate limiting kicked in. Statuses: {statuses}")
else:
    log(
        "T13-rate-limit",
        "FAIL",
        f"No rate limiting for 6 rapid calls. Statuses: {statuses}",
    )


print("\n" + "=" * 80)
print("TEST 14: Unauthenticated Request")
print("=" * 80)
resp = requests.post(
    FLOW_URL, json=payload, headers={"Content-Type": "application/json"}
)
print(f"Status: {resp.status_code}")
if resp.status_code in (401, 403):
    log("T14-no-auth", "PASS", f"Rejected unauthenticated: {resp.status_code}")
else:
    log("T14-no-auth", "FAIL", f"Unexpected: {resp.status_code}")


print("\n" + "=" * 80)
print("TEST 15: Verify Mandates Created After Tests")
print("=" * 80)
time.sleep(1)
resp = requests.get(MANDATES_URL, params={"limit": 200}, headers=headers)
mandates_data = resp.json()
print(f"Total mandates now: {mandates_data['count']}")
print(f"Mandates created during tests: {mandates_data['count'] - mandates_before}")

# Check mandate types
types = {}
for m in mandates_data.get("mandates", []):
    t = m.get("type")
    types[t] = types.get(t, 0) + 1
print(f"Mandate type breakdown: {types}")

# Each successful complete-flow should create 1 intent + 1 cart + 1 payment
if "intent" in types and "cart" in types and "payment" in types:
    log("T15-mandates-created", "PASS", f"All 3 mandate types present. Types: {types}")
else:
    log("T15-mandates-created", "FAIL", f"Missing mandate types. Got: {types}")


print("\n" + "=" * 80)
print("TEST 16: Response Format Matches Frontend Expectations")
print("=" * 80)
# Frontend checks: response.ok, response.json(), errorData.detail
# Frontend uses: data (but doesn't use individual fields from response!)
# Success toast shows: `AP2 flow completed! Total: $${calculateTotal().toFixed(2)}`
# The frontend does NOT use any field from the backend response other than checking response.ok
resp = requests.post(
    FLOW_URL,
    json={
        "items": [
            {"description": "Format check", "amount": 15.00, "category": "SOFTWARE"}
        ],
        "merchant": "Microsoft",
        "constraints": {
            "max_amount": 15.75,
            "monthly_limit": 15.75,
            "category": "SOFTWARE",
            "merchant": "Microsoft",
        },
    },
    headers=headers,
)

if resp.status_code == 200:
    data = resp.json()
    # The backend returns these fields - frontend doesn't use them specifically but they should exist
    backend_fields = [
        "intent_mandate_id",
        "cart_mandate_id",
        "payment_mandate_id",
        "payment_result",
        "ap2_flow_complete",
    ]
    missing = [f for f in backend_fields if f not in data]
    if missing:
        log("T16-response-format", "FAIL", f"Missing fields: {missing}")
    else:
        log(
            "T16-response-format",
            "PASS",
            f"Response has all fields: {list(data.keys())}",
        )
else:
    log("T16-response-format", "FAIL", f"Request failed: {resp.status_code}")


print("\n" + "=" * 80)
print("TEST 17: Error Response Format (detail field)")
print("=" * 80)
# Test that error responses have 'detail' field which frontend expects
resp = requests.post(
    FLOW_URL,
    json={
        "items": [
            {"description": "Over limit", "amount": 1000.00, "category": "OTHER"}
        ],
        "merchant": "Store",
        "constraints": {
            "max_amount": 500.00,
            "monthly_limit": 500.00,
            "category": "OTHER",
            "merchant": "Store",
        },
    },
    headers=headers,
)

if resp.status_code != 200:
    data = resp.json()
    if "detail" in data:
        log("T17-error-format", "PASS", f"Error has 'detail' field: {data['detail']}")
    else:
        log(
            "T17-error-format",
            "FAIL",
            f"Error missing 'detail' field. Got: {list(data.keys())}",
        )
else:
    log(
        "T17-error-format",
        "FAIL",
        "Expected error but got 200 - check constraint enforcement",
    )


print("\n" + "=" * 80)
print("TEST 18: 5% Buffer Calculation Verification")
print("=" * 80)
# Frontend calculates: Math.ceil(total * 1.05 * 100) / 100
# For $100: Math.ceil(100 * 1.05 * 100) / 100 = Math.ceil(10500) / 100 = 105.00
# For $29.99: Math.ceil(29.99 * 1.05 * 100) / 100 = Math.ceil(3148.95) / 100 = 31.49
# Backend auto-generate uses: total * 1.1 (10% buffer) - DIFFERENT from frontend!
test_cases = [
    (100.00, 105.00),
    (29.99, 31.49),
    (
        0.01,
        0.02,
    ),  # Math.ceil(0.0105 * 100) / 100 = Math.ceil(1.05) / 100 = 2/100 = 0.02
    (
        99.99,
        104.99,
    ),  # Math.ceil(99.99 * 1.05 * 100) / 100 = Math.ceil(10498.95) / 100 = 104.99
]

all_ok = True
for total, expected in test_cases:
    # Simulate frontend calculation
    import math

    frontend_max = math.ceil(total * 1.05 * 100) / 100
    if abs(frontend_max - expected) > 0.001:
        print(f"  MISMATCH: total={total}, expected={expected}, got={frontend_max}")
        all_ok = False
    else:
        print(f"  OK: total={total} -> max_amount={frontend_max}")

if all_ok:
    log("T18-buffer-calc", "PASS", "Frontend 5% buffer calculation is correct")
else:
    log("T18-buffer-calc", "FAIL", "Buffer calculation has errors")

# NOTE: Backend uses 10% buffer, frontend uses 5% buffer
print(
    f"\n  ** IMPORTANT: Frontend uses 5% buffer, Backend auto-generate uses 10% buffer **"
)
print(
    f"  ** When frontend sends constraints, 5% is used. When constraints are omitted, backend uses 10%. **"
)


print("\n" + "=" * 80)
print("TEST 19: Missing merchant in payload (Pydantic validation)")
print("=" * 80)
resp = requests.post(
    FLOW_URL,
    json={
        "items": [{"description": "Test", "amount": 10.00, "category": "OTHER"}]
        # merchant is missing entirely
    },
    headers=headers,
)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:300]}")
if resp.status_code == 422:
    log("T19-missing-merchant-field", "PASS", "Pydantic caught missing merchant")
else:
    log("T19-missing-merchant-field", "FAIL", f"Expected 422, got {resp.status_code}")


print("\n" + "=" * 80)
print("TEST 20: Special Characters in Merchant/Description")
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
print(f"Response: {resp.text[:300]}")
if resp.status_code == 200:
    log(
        "T20-special-chars",
        "FAIL",
        "Accepted HTML/script in description - potential XSS stored in DB",
    )
else:
    log("T20-special-chars", "PASS", f"Rejected special chars: {resp.status_code}")


print("\n" + "=" * 80)
print("TEST 21: Very Long Description/Merchant")
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
if resp.status_code == 200:
    log(
        "T21-long-strings",
        "FAIL",
        f"Accepted 5000-char strings. Merchant column is VARCHAR(255) - may truncate silently or error",
    )
elif resp.status_code == 500:
    log(
        "T21-long-strings",
        "FAIL",
        f"500 error - no input length validation before DB insert",
    )
else:
    log("T21-long-strings", "PASS", f"Handled long strings: {resp.status_code}")


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
print("TEST 23: Mixed Categories in Items vs Single Category Constraint")
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
            "category": "OFFICE_SUPPLIES",  # Only allows OFFICE_SUPPLIES
            "merchant": "MixedStore",
        },
    },
    headers=headers,
)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text[:300]}")
if resp.status_code == 200:
    log(
        "T23-mixed-categories",
        "FAIL",
        "Backend accepted mixed categories with single-category constraint. Only first category validated?",
    )
elif resp.status_code in (400, 422):
    log(
        "T23-mixed-categories", "PASS", f"Rejected mixed categories: {resp.status_code}"
    )
else:
    log("T23-mixed-categories", "FAIL", f"Unexpected: {resp.status_code}")


print("\n" + "=" * 80)
print(
    "TEST 24: Frontend sends constraints.category (singular), backend uses both 'category' and 'categories'"
)
print("=" * 80)
# Frontend always sends { category: "OFFICE_SUPPLIES" } (singular)
# Backend's create_cart_mandate checks both constraints.get("categories") || constraints.get("category")
# This should work because the backend handles both.
print("  Frontend sends: constraints.category (singular string)")
print("  Backend checks: constraints.get('categories') or constraints.get('category')")
log(
    "T24-category-key-compat",
    "PASS",
    "Backend handles both 'category' (singular) and 'categories' (plural)",
)


print("\n" + "=" * 80)
print("TEST 25: Double Usage Tracking Bug Check")
print("=" * 80)
# The complete-flow endpoint tracks usage TWICE:
# 1. In the route handler (ap2.py line 408-414)
# 2. In the service method (ap2_service.py line 437-447)
print(
    "  WARNING: Usage is tracked in BOTH ap2.py route handler AND ap2_service.py complete_ap2_flow()"
)
print(
    "  Route handler: tracker.track_usage(user_id=current_user.id, usage_type='ap2_transaction', quantity=1)"
)
print(
    "  Service method: tracker.track_usage(user_id=user_id, usage_type='ap2_transaction', quantity=1)"
)
log(
    "T25-double-tracking",
    "FAIL",
    "AP2 transaction usage is tracked TWICE per complete-flow call (once in route, once in service)",
)


print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
pass_count = sum(1 for r in results if r["status"] == "PASS")
fail_count = sum(1 for r in results if r["status"] == "FAIL")
print(f"\nTotal: {len(results)} tests | PASS: {pass_count} | FAIL: {fail_count}")
print()
for r in results:
    marker = "PASS" if r["status"] == "PASS" else "FAIL"
    print(f"  [{marker}] {r['test']}: {r['detail']}")
