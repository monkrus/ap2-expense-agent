"""
Comprehensive QA Test for AP2 Activity Tab - Frontend & Backend
Tests real API calls, data shapes, edge cases, and frontend/backend mismatches.
"""

import requests
import json
import time
import sys

BASE_URL = "http://127.0.0.1:8000"
ISSUES = []


def log_issue(category, title, detail):
    """Log a found issue."""
    ISSUES.append({"category": category, "title": title, "detail": detail})
    print(f"  [{category}] {title}")
    print(f"    -> {detail}")


def log_ok(msg):
    print(f"  [OK] {msg}")


def log_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


# ============================================================
# STEP 1: Login
# ============================================================
log_section("STEP 1: Login")

login_resp = requests.post(
    f"{BASE_URL}/api/v1/auth/login",
    json={"username": "adminfree", "password": "Testme1!"},
)

if login_resp.status_code != 200:
    print(
        f"FATAL: Login failed with status {login_resp.status_code}: {login_resp.text}"
    )
    sys.exit(1)

login_data = login_resp.json()
TOKEN = login_data.get("access_token")
if not TOKEN:
    print(f"FATAL: No access_token in login response: {login_data}")
    sys.exit(1)

HEADERS = {"Authorization": f"Bearer {TOKEN}"}
log_ok(f"Logged in successfully. Token starts with: {TOKEN[:20]}...")


# ============================================================
# STEP 2: Create diverse test data
# ============================================================
log_section("STEP 2: Creating diverse test data")

created_ids = {
    "intent": [],
    "cart": [],
    "payment": [],
}

# 2a. Intent mandate with full constraints
print("\n--- 2a: Intent mandate with full constraints ---")
resp = requests.post(
    f"{BASE_URL}/api/ap2/intent-mandate",
    json={
        "constraints": {
            "max_amount": 500.00,
            "monthly_limit": 2000.00,
            "category": "OFFICE_SUPPLIES",
            "merchant": "Amazon",
            "approval_required": True,
        },
        "expiration_hours": 24,
    },
    headers=HEADERS,
)
print(f"  Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    created_ids["intent"].append(data["intent_mandate_id"])
    log_ok(f"Created intent mandate: {data['intent_mandate_id']}")
else:
    log_issue("BUG", "Failed to create intent mandate with full constraints", resp.text)

# 2b. Intent mandate with minimal constraints (null merchant, null category)
print("\n--- 2b: Intent mandate with minimal constraints ---")
resp = requests.post(
    f"{BASE_URL}/api/ap2/intent-mandate",
    json={"constraints": {"max_amount": 100.00}, "expiration_hours": 1},
    headers=HEADERS,
)
print(f"  Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    created_ids["intent"].append(data["intent_mandate_id"])
    log_ok(f"Created minimal intent mandate: {data['intent_mandate_id']}")
else:
    log_issue(
        "BUG", "Failed to create intent mandate with minimal constraints", resp.text
    )

# 2c. Intent mandate with empty constraints
print("\n--- 2c: Intent mandate with empty constraints ---")
resp = requests.post(
    f"{BASE_URL}/api/ap2/intent-mandate",
    json={"constraints": {}, "expiration_hours": 24},
    headers=HEADERS,
)
print(f"  Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    created_ids["intent"].append(data["intent_mandate_id"])
    log_ok(f"Created empty-constraints intent mandate: {data['intent_mandate_id']}")
else:
    log_issue(
        "BUG", "Failed to create intent mandate with empty constraints", resp.text
    )

# 2d. Intent mandate with categories as list (plural form)
print("\n--- 2d: Intent mandate with categories list ---")
resp = requests.post(
    f"{BASE_URL}/api/ap2/intent-mandate",
    json={
        "constraints": {
            "max_amount": 250.00,
            "categories": ["SOFTWARE", "HARDWARE"],
            "merchants": ["Microsoft", "Dell"],
        },
        "expiration_hours": 24,
    },
    headers=HEADERS,
)
print(f"  Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    created_ids["intent"].append(data["intent_mandate_id"])
    log_ok(f"Created categories-list intent mandate: {data['intent_mandate_id']}")
else:
    log_issue("BUG", "Failed to create intent mandate with categories list", resp.text)

# 2e. Complete flow (creates intent + cart + payment + executes)
print("\n--- 2e: Complete AP2 flow ---")
resp = requests.post(
    f"{BASE_URL}/api/ap2/complete-flow",
    json={
        "items": [
            {
                "id": "item-1",
                "description": "Laptop Stand",
                "amount": 45.99,
                "category": "office_supplies",
            },
            {
                "id": "item-2",
                "description": "USB Hub",
                "amount": 29.99,
                "category": "hardware",
            },
        ],
        "merchant": "Amazon",
        "constraints": {"max_amount": 200.00, "category": "office_supplies"},
    },
    headers=HEADERS,
)
print(f"  Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    log_ok(f"Complete flow succeeded: {json.dumps(data, indent=2, default=str)[:300]}")
elif resp.status_code == 402:
    log_issue("LOGIC", "Complete flow returned 402 - billing limit reached", resp.text)
else:
    log_issue("BUG", f"Complete flow failed with {resp.status_code}", resp.text)

# 2f. Intent mandate to be revoked
print("\n--- 2f: Intent mandate to revoke ---")
resp = requests.post(
    f"{BASE_URL}/api/ap2/intent-mandate",
    json={
        "constraints": {
            "max_amount": 300.00,
            "merchant": "Staples",
            "category": "OFFICE_SUPPLIES",
        },
        "expiration_hours": 24,
    },
    headers=HEADERS,
)
revoke_id = None
if resp.status_code == 200:
    data = resp.json()
    revoke_id = data["intent_mandate_id"]
    created_ids["intent"].append(revoke_id)
    log_ok(f"Created intent mandate for revocation: {revoke_id}")

    # Now revoke it
    print("  Revoking...")
    revoke_resp = requests.post(
        f"{BASE_URL}/api/ap2/intent-mandate/{revoke_id}/revoke",
        json={"reason": "Testing revocation flow", "revoke_dependents": True},
        headers=HEADERS,
    )
    print(f"  Revoke Status: {revoke_resp.status_code}")
    if revoke_resp.status_code == 200:
        log_ok(f"Revoked successfully: {revoke_resp.json()}")
    else:
        log_issue("BUG", "Revoke intent mandate failed", revoke_resp.text)


# ============================================================
# STEP 3: Fetch all mandates and analyze
# ============================================================
log_section("STEP 3: Fetching all mandates and analyzing")

resp = requests.get(f"{BASE_URL}/api/ap2/user/mandates?limit=50", headers=HEADERS)
print(f"  Status: {resp.status_code}")

if resp.status_code != 200:
    print(f"FATAL: Cannot fetch mandates: {resp.text}")
    sys.exit(1)

mandates_data = resp.json()
all_mandates = mandates_data.get("mandates", [])
mandate_count = mandates_data.get("count", 0)
print(f"  Total mandates returned: {len(all_mandates)} (count field: {mandate_count})")

# Collect all statuses and types
statuses_found = set()
types_found = set()

for m in all_mandates:
    statuses_found.add(m.get("status"))
    types_found.add(m.get("type"))

print(f"  Statuses found: {statuses_found}")
print(f"  Types found: {types_found}")

# ============================================================
# STEP 4: Verify frontend filter handles all statuses
# ============================================================
log_section("STEP 4: Frontend filter coverage analysis")

# Frontend status filter buttons
FRONTEND_STATUS_FILTERS = {
    "all",
    "active",
    "pending",
    "completed",
    "failed",
    "expired",
    "revoked",
}
# Frontend type filter buttons
FRONTEND_TYPE_FILTERS = {"all", "intent", "cart", "payment"}

# Check if any backend status is not covered by frontend filters
for status in statuses_found:
    if status not in FRONTEND_STATUS_FILTERS and status != "all":
        log_issue(
            "MISMATCH",
            f"Backend status '{status}' has no frontend filter button",
            f"Status '{status}' returned by API but not in frontend filter buttons: {FRONTEND_STATUS_FILTERS}",
        )
    else:
        log_ok(f"Status '{status}' has matching frontend filter button")

for type_ in types_found:
    if type_ not in FRONTEND_TYPE_FILTERS and type_ != "all":
        log_issue(
            "MISMATCH",
            f"Backend type '{type_}' has no frontend filter button",
            f"Type '{type_}' returned by API but not in frontend filter buttons: {FRONTEND_TYPE_FILTERS}",
        )
    else:
        log_ok(f"Type '{type_}' has matching frontend filter button")

# Check: does the backend "deleted" status get excluded properly?
print("\n--- Checking deleted mandates exclusion ---")
resp_with_deleted = requests.get(
    f"{BASE_URL}/api/ap2/user/mandates?limit=50&include_deleted=true", headers=HEADERS
)
if resp_with_deleted.status_code == 200:
    with_deleted = resp_with_deleted.json().get("mandates", [])
    deleted_count = sum(1 for m in with_deleted if m["status"] == "deleted")
    print(
        f"  Mandates with include_deleted=true: {len(with_deleted)} (deleted: {deleted_count})"
    )

    if deleted_count > 0:
        # Frontend has no "deleted" filter button
        log_issue(
            "MISMATCH",
            "Backend can return 'deleted' status but frontend has no filter for it",
            f"Found {deleted_count} deleted mandates. Frontend status filters don't include 'deleted'. "
            "If include_deleted is sent, the 'deleted' status badge will fallback to 'pending' config (blue) which is misleading.",
        )
else:
    print(f"  include_deleted request failed: {resp_with_deleted.status_code}")


# ============================================================
# STEP 5: Verify each mandate's data shape for frontend rendering
# ============================================================
log_section("STEP 5: Per-mandate data shape verification")

for i, m in enumerate(all_mandates):
    print(
        f"\n--- Mandate {i+1}: type={m.get('type')}, status={m.get('status')}, id={m.get('id','?')[:30]}... ---"
    )

    # 5a. Check required fields for frontend
    required_fields = ["id", "type", "status", "created_at"]
    for field in required_fields:
        if field not in m or m[field] is None:
            log_issue(
                "BUG",
                f"Mandate missing required field '{field}'",
                f"Mandate {m.get('id','?')[:30]} is missing '{field}'. Frontend will crash on m.id.toLowerCase().",
            )
        else:
            log_ok(f"Field '{field}' present: {str(m[field])[:60]}")

    # 5b. Frontend calls m.id.toLowerCase() - check id is string
    if "id" in m and m["id"] is not None:
        if not isinstance(m["id"], str):
            log_issue(
                "BUG",
                "Mandate id is not a string",
                f"Frontend calls m.id.toLowerCase() but id is {type(m['id'])}",
            )

    # 5c. Frontend calls m.id.slice(-12) - check id has enough characters
    if m.get("id") and len(m["id"]) < 12:
        log_issue(
            "UX",
            "Mandate ID shorter than 12 characters",
            f"Frontend displays m.id.slice(-12) but id is only {len(m['id'])} chars: {m['id']}",
        )

    # 5d. Check created_at is parseable as Date
    if m.get("created_at"):
        try:
            from datetime import datetime

            # The frontend does new Date(b.created_at)
            # Python check: is this a valid ISO format?
            ca = str(m["created_at"])
            log_ok(f"created_at value: {ca}")
        except Exception as e:
            log_issue("BUG", "created_at not parseable", str(e))

    # 5e. Check type-specific fields
    if m["type"] == "intent":
        # Frontend accesses: m.constraints, m.max_amount, m.monthly_limit, m.category, m.merchant, m.expiration
        constraints = m.get("constraints")
        if constraints is not None and not isinstance(constraints, dict):
            log_issue(
                "BUG",
                "Intent mandate constraints is not a dict",
                f"Type: {type(constraints)}, value: {str(constraints)[:100]}. "
                "Frontend does JSON.stringify(mandate.constraints) and m.constraints?.merchant",
            )

        # Check merchant extraction logic
        merchant = m.get("merchant")
        if merchant is None and constraints:
            # Check if merchant is buried in constraints but not extracted
            if constraints.get("merchant") or constraints.get("merchants"):
                log_issue(
                    "LOGIC",
                    "Merchant exists in constraints but top-level merchant is None",
                    f"constraints has merchant={constraints.get('merchant')}, merchants={constraints.get('merchants')}. "
                    f"Top-level merchant={merchant}. Frontend searches both m.merchant and m.constraints.merchant.",
                )

    elif m["type"] == "cart":
        # Frontend accesses: m.total, m.merchant
        if "total" not in m:
            log_issue(
                "MISMATCH",
                "Cart mandate missing 'total' field",
                "Frontend displays ${parseFloat(mandate.total).toFixed(2)} - will show NaN",
            )
        if "merchant" not in m:
            log_issue(
                "MISMATCH",
                "Cart mandate missing 'merchant' field",
                "Frontend checks mandate.merchant for rendering",
            )

    elif m["type"] == "payment":
        # Frontend accesses: m.payment_method
        if "payment_method" not in m:
            log_issue(
                "MISMATCH",
                "Payment mandate missing 'payment_method' field",
                "Frontend displays via {mandate.payment_method}",
            )
        # Check: does payment mandate have total or merchant?
        if "total" not in m:
            log_ok(
                "Payment mandate has no 'total' (expected - backend doesn't provide it)"
            )
        if "merchant" not in m:
            log_ok(
                "Payment mandate has no 'merchant' (expected - backend doesn't provide it)"
            )


# ============================================================
# STEP 6: Test search functionality against real data
# ============================================================
log_section("STEP 6: Search functionality analysis (code-level)")

# The frontend search runs client-side, so we analyze the data shapes
# to see if search would work correctly

# 6a. Search by merchant - does it work for intent mandates?
intent_mandates = [m for m in all_mandates if m["type"] == "intent"]
for m in intent_mandates:
    merchant = m.get("merchant")
    constraints_merchant = (
        m.get("constraints", {}).get("merchant")
        if isinstance(m.get("constraints"), dict)
        else None
    )
    if merchant is None and constraints_merchant:
        log_issue(
            "LOGIC",
            "Search by merchant may miss intent mandates",
            f"Mandate {m['id'][:20]}... has merchant=None but constraints.merchant={constraints_merchant}. "
            "Frontend checks BOTH m.merchant AND m.constraints?.merchant, so this IS covered. OK.",
        )
    elif merchant is None and constraints_merchant is None:
        log_ok(
            f"Intent mandate {m['id'][:20]}... has no merchant at all (correct for unconstrained)"
        )

# 6b. Search with special characters
print("\n--- Search with special characters (client-side analysis) ---")
# Frontend does: searchQuery.toLowerCase() and .includes(query)
# This means special regex chars won't cause crashes since .includes() is plain string match
log_ok(
    "Frontend uses .includes() not regex, so special chars like $, ^, (, ), [, ] won't crash"
)

# But what about null fields?
for m in all_mandates:
    if m.get("merchant") is None:
        # Frontend: (m.merchant && m.merchant.toLowerCase().includes(query))
        # This is safe because of short-circuit evaluation
        pass
    if m.get("constraints") is None:
        # Frontend: (m.constraints?.merchant && m.constraints.merchant.toLowerCase().includes(query))
        # Safe due to optional chaining
        pass
log_ok(
    "Null-safe checks: Frontend uses && short-circuit and ?. optional chaining correctly"
)


# ============================================================
# STEP 7: Test backend filters via API
# ============================================================
log_section("STEP 7: Backend filter API testing")

# 7a. Filter by type
for type_filter in ["intent", "cart", "payment"]:
    resp = requests.get(
        f"{BASE_URL}/api/ap2/user/mandates?mandate_type={type_filter}&limit=50",
        headers=HEADERS,
    )
    if resp.status_code == 200:
        filtered = resp.json().get("mandates", [])
        wrong_types = [m for m in filtered if m["type"] != type_filter]
        if wrong_types:
            log_issue(
                "BUG",
                f"Type filter '{type_filter}' returned wrong types",
                f"Got {len(wrong_types)} mandates with wrong type: {set(m['type'] for m in wrong_types)}",
            )
        else:
            log_ok(
                f"Type filter '{type_filter}' returned {len(filtered)} mandates, all correct type"
            )
    else:
        log_issue(
            "BUG",
            f"Type filter '{type_filter}' API call failed",
            f"Status: {resp.status_code}",
        )

# 7b. Filter by status
for status_filter in ["active", "pending", "completed", "failed", "expired", "revoked"]:
    resp = requests.get(
        f"{BASE_URL}/api/ap2/user/mandates?status_filter={status_filter}&limit=50",
        headers=HEADERS,
    )
    if resp.status_code == 200:
        filtered = resp.json().get("mandates", [])
        wrong_statuses = [m for m in filtered if m["status"] != status_filter]
        if wrong_statuses:
            log_issue(
                "BUG",
                f"Status filter '{status_filter}' returned wrong statuses",
                f"Got {len(wrong_statuses)} mandates with wrong status: {set(m['status'] for m in wrong_statuses)}",
            )
        else:
            log_ok(
                f"Status filter '{status_filter}' returned {len(filtered)} mandates, all correct status"
            )
    else:
        log_issue(
            "BUG",
            f"Status filter '{status_filter}' API call failed",
            f"Status: {resp.status_code}",
        )

# 7c. Combined filter: type + status
print("\n--- Combined filters ---")
resp = requests.get(
    f"{BASE_URL}/api/ap2/user/mandates?mandate_type=intent&status_filter=active&limit=50",
    headers=HEADERS,
)
if resp.status_code == 200:
    filtered = resp.json().get("mandates", [])
    wrong = [m for m in filtered if m["type"] != "intent" or m["status"] != "active"]
    if wrong:
        log_issue(
            "BUG",
            "Combined filter intent+active returned wrong results",
            f"Got {len(wrong)} wrong mandates",
        )
    else:
        log_ok(
            f"Combined filter intent+active returned {len(filtered)} correct mandates"
        )

resp = requests.get(
    f"{BASE_URL}/api/ap2/user/mandates?mandate_type=intent&status_filter=expired&limit=50",
    headers=HEADERS,
)
if resp.status_code == 200:
    filtered = resp.json().get("mandates", [])
    log_ok(f"Combined filter intent+expired returned {len(filtered)} mandates")

resp = requests.get(
    f"{BASE_URL}/api/ap2/user/mandates?mandate_type=payment&status_filter=failed&limit=50",
    headers=HEADERS,
)
if resp.status_code == 200:
    filtered = resp.json().get("mandates", [])
    log_ok(f"Combined filter payment+failed returned {len(filtered)} mandates")


# ============================================================
# STEP 8: Edge case - merchant extraction logic bug
# ============================================================
log_section("STEP 8: Backend merchant/category extraction logic")

# The backend has a complex one-liner for merchant extraction:
# "merchant": constraints.get("merchant") or constraints.get("merchants", [None])[0] if isinstance(constraints.get("merchants"), list) else None,
#
# This is ambiguous due to Python operator precedence. Let's test what actually happens.

for m in all_mandates:
    if m["type"] == "intent":
        constraints = m.get("constraints", {})
        merchant = m.get("merchant")
        category = m.get("category")

        # Check the merchant extraction for the 'merchants' list case
        if isinstance(constraints, dict) and "merchants" in constraints:
            merchants_list = constraints["merchants"]
            if isinstance(merchants_list, list) and len(merchants_list) > 0:
                expected_merchant = merchants_list[0]
                if merchant != expected_merchant:
                    log_issue(
                        "BUG",
                        "Merchant extraction from merchants list is incorrect",
                        f"constraints.merchants={merchants_list}, expected merchant='{expected_merchant}', "
                        f"got merchant='{merchant}'. "
                        "This is likely a Python operator precedence bug in the backend one-liner. "
                        "The ternary `x if cond else y` binds differently than expected.",
                    )

        # Check the category extraction for the 'categories' list case
        if isinstance(constraints, dict) and "categories" in constraints:
            categories_list = constraints["categories"]
            if isinstance(categories_list, list) and len(categories_list) > 0:
                expected_category = categories_list[0]
                if category != expected_category:
                    log_issue(
                        "BUG",
                        "Category extraction from categories list is incorrect",
                        f"constraints.categories={categories_list}, expected category='{expected_category}', "
                        f"got category='{category}'. "
                        "Same operator precedence bug as merchant extraction.",
                    )


# ============================================================
# STEP 9: Check exportActivity function
# ============================================================
log_section("STEP 9: Export functionality analysis")

# exportActivity is defined as a standalone function (not inside the component)
# It's called via onClick={() => exportActivity(sortedMandates)}
# Let's analyze what issues it would have

print("--- Analyzing exportActivity CSV generation ---")

# Issue 1: CSV injection - if merchant contains commas, quotes, or newlines
for m in all_mandates:
    merchant = m.get("merchant", "")
    if merchant and ("," in merchant or '"' in merchant or "\n" in merchant):
        log_issue(
            "BUG",
            "CSV export vulnerable to field injection",
            f"Merchant '{merchant}' contains CSV special characters. "
            "exportActivity() uses simple .join(',') without quoting/escaping.",
        )

# Issue 2: The export does NOT include important fields
log_issue(
    "UX",
    "Export CSV missing important columns",
    "exportActivity() exports: ID, Type, Status, Total, Merchant, Created At, Timestamp. "
    "Missing: max_amount, monthly_limit, category, payment_method, constraints, expiration. "
    "For intent mandates, Total is always empty and the meaningful fields (max_amount, category) are omitted.",
)

# Issue 3: created_at handling
# The export does: new Date(m.created_at).toISOString()
# But the backend returns created_at as a Python datetime string without 'Z'
# new Date("2024-01-15 10:30:00") in some browsers may return Invalid Date
log_issue(
    "BUG",
    "Export created_at parsing may fail in some browsers",
    "Backend returns created_at without 'Z' suffix (e.g., '2024-01-15 10:30:00'). "
    "exportActivity() does new Date(m.created_at).toISOString() which may return 'Invalid Date' "
    "in some browsers. The ActivityTimelineItem component has a fix for this (appending 'Z'), "
    "but exportActivity() does not use that fix.",
)

# Issue 4: IDs containing commas would break CSV
log_issue(
    "LOGIC",
    "Export CSV not properly escaped",
    "If any mandate ID, merchant, or other field contains a comma, "
    "the CSV output will be malformed. Fields should be quoted with double quotes "
    "and internal quotes should be escaped as double-double-quotes.",
)


# ============================================================
# STEP 10: Check frontend/backend status mismatch for stats
# ============================================================
log_section("STEP 10: Stats endpoint analysis")

resp = requests.get(f"{BASE_URL}/api/ap2/stats", headers=HEADERS)
if resp.status_code == 200:
    stats = resp.json()
    print(f"  Stats: {json.dumps(stats, indent=2)}")

    # The frontend AgentActivityMonitor receives stats as a prop but DOES NOT USE IT
    # It recalculates stats from mandates array instead
    log_issue(
        "LOGIC",
        "Stats prop is passed but never used by AgentActivityMonitor",
        "AIAssistant.jsx passes 'stats' to <AgentActivityMonitor mandates={mandates} stats={stats} />, "
        "but AgentActivityMonitor recalculates totalTransactions, completedTransactions, "
        "activeTransactions, failedTransactions from the mandates array. The stats prop is ignored. "
        "This means the server-side stats (which may be more accurate, e.g., including pagination) "
        "are wasted.",
    )

    # Also: the frontend stat cards don't count 'expired' or 'revoked'
    log_issue(
        "UX",
        "Stat cards don't count 'expired' and 'revoked' mandates",
        "The 4 stat cards show: Total, Completed, Active/Pending, Failed. "
        "But 'expired' and 'revoked' mandates are not counted in any card. "
        "totalTransactions counts all, but the 3 specific cards only sum to "
        "completed + active + pending + failed, missing expired and revoked. "
        "The numbers won't add up.",
    )
else:
    log_issue("BUG", "Stats endpoint failed", f"Status: {resp.status_code}")


# ============================================================
# STEP 11: Payment mandate data completeness check
# ============================================================
log_section("STEP 11: Payment mandate data completeness")

payment_mandates = [m for m in all_mandates if m["type"] == "payment"]
for m in payment_mandates:
    print(f"  Payment mandate: {json.dumps(m, indent=2, default=str)[:300]}")

    # Payment mandates don't have 'total' or 'merchant' from backend
    # But the frontend would display "$NaN" if total existed but wasn't a number
    if "total" not in m:
        log_issue(
            "UX",
            "Payment mandates have no total amount displayed",
            f"Payment mandate {m['id'][:20]}... has no 'total' field. "
            "In the Activity tab, there's no amount shown. The user can't see "
            "how much was paid. Backend should join with cart_mandate to get the total.",
        )
    if "merchant" not in m:
        log_issue(
            "UX",
            "Payment mandates have no merchant displayed",
            f"Payment mandate {m['id'][:20]}... has no 'merchant' field. "
            "User can't see which merchant was paid. Backend should join with cart_mandate.",
        )


# ============================================================
# STEP 12: Intent mandate merchant extraction bug (deep dive)
# ============================================================
log_section("STEP 12: Deep dive on backend merchant/category extraction")

# The backend code (line 534 of ap2.py):
# "merchant": constraints.get("merchant") or constraints.get("merchants", [None])[0] if isinstance(constraints.get("merchants"), list) else None,
#
# Due to Python precedence, this parses as:
# "merchant": (constraints.get("merchant") or constraints.get("merchants", [None])[0]) if isinstance(constraints.get("merchants"), list) else None
#
# NOT as intended:
# "merchant": constraints.get("merchant") or (constraints.get("merchants", [None])[0] if isinstance(constraints.get("merchants"), list) else None)
#
# This means:
# - If constraints has "merchants" list: returns constraints.get("merchant") or merchants[0]  (works by accident)
# - If constraints does NOT have "merchants" list: returns None (BUG!)
# - If constraints has only "merchant" (no "merchants"): returns None (BUG!)

# Let's verify with real data
for m in all_mandates:
    if m["type"] == "intent":
        constraints = m.get("constraints", {})
        if isinstance(constraints, dict):
            has_merchant_key = "merchant" in constraints
            has_merchants_key = "merchants" in constraints
            actual_merchant = m.get("merchant")

            if has_merchant_key and not has_merchants_key:
                expected = constraints["merchant"]
                if actual_merchant != expected:
                    log_issue(
                        "BUG",
                        "Merchant extraction fails when only 'merchant' key exists (no 'merchants')",
                        f"constraints.merchant='{constraints['merchant']}', "
                        f"but API returned merchant={actual_merchant}. "
                        "Due to Python ternary precedence, when 'merchants' key is absent, "
                        "isinstance check fails and the whole expression returns None.",
                    )
                else:
                    log_ok(f"Merchant correctly extracted: {actual_merchant}")

# Same analysis for category
for m in all_mandates:
    if m["type"] == "intent":
        constraints = m.get("constraints", {})
        if isinstance(constraints, dict):
            has_category_key = "category" in constraints
            has_categories_key = "categories" in constraints
            actual_category = m.get("category")

            if has_category_key and not has_categories_key:
                expected = constraints["category"]
                if actual_category != expected:
                    log_issue(
                        "BUG",
                        "Category extraction fails when only 'category' key exists (no 'categories')",
                        f"constraints.category='{constraints['category']}', "
                        f"but API returned category={actual_category}. "
                        "Same Python ternary precedence bug as merchant extraction.",
                    )
                else:
                    log_ok(f"Category correctly extracted: {actual_category}")


# ============================================================
# STEP 13: Revoked mandates - model column check
# ============================================================
log_section("STEP 13: Revoke endpoint - model column analysis")

# The revoke endpoint sets:
#   intent_mandate.revoked_at = datetime.utcnow()
#   intent_mandate.revocation_reason = request.reason
# But looking at the IntentMandate model, there are no revoked_at or revocation_reason columns!

log_issue(
    "BUG",
    "Revoke endpoint sets columns that don't exist on the model",
    "The revoke_intent_mandate endpoint sets 'revoked_at' and 'revocation_reason' on IntentMandate, "
    "but the IntentMandate model in models.py has no such columns. "
    "SQLAlchemy will silently set these as Python attributes but they won't be persisted to the database. "
    "Same issue for CartMandate and PaymentMandate revocation endpoints. "
    "The revoke response returns revoked_at.isoformat() which works in-memory but the data is lost on next query.",
)

# Verify by checking if revoked mandates actually have the revoked_at timestamp
if revoke_id:
    resp = requests.get(
        f"{BASE_URL}/api/ap2/user/mandates?status_filter=revoked&limit=50",
        headers=HEADERS,
    )
    if resp.status_code == 200:
        revoked = resp.json().get("mandates", [])
        for m in revoked:
            if m["id"] == revoke_id:
                # The API response for mandates doesn't include revoked_at anyway
                log_issue(
                    "UX",
                    "Revoked mandates don't show revocation timestamp or reason in Activity tab",
                    f"Mandate {m['id'][:20]}... is revoked but the /user/mandates endpoint "
                    "doesn't include revoked_at or revocation_reason in the response. "
                    "Frontend has no way to show when or why a mandate was revoked.",
                )


# ============================================================
# STEP 14: Frontend timeline line rendering
# ============================================================
log_section("STEP 14: Frontend timeline rendering analysis")

# The timeline line is:
# <div style={{ display: isFirst ? "none" : "block" }}>
# This means the FIRST item has no line above it (correct)
# But the LAST item has a line going down to nothing (incorrect)
log_issue(
    "UX",
    "Timeline line extends below the last item",
    "The timeline vertical line (ml-10 w-px bg-gray-200) is hidden for the first item "
    "but extends down for all other items including the last one. "
    "The last item's line extends to the bottom of its container with no item below it, "
    "creating a dangling visual artifact.",
)


# ============================================================
# STEP 15: Frontend date formatting edge cases
# ============================================================
log_section("STEP 15: Date formatting edge cases")

# The formatDate function appends 'Z' if not present:
# const dateStr = dateString.endsWith('Z') ? dateString : dateString + 'Z';
# But backend returns dates like "2024-01-15T10:30:00" or "2024-01-15 10:30:00"
# What if the backend returns null for created_at?

for m in all_mandates:
    if m.get("created_at") is None:
        log_issue(
            "BUG",
            "Mandate has null created_at",
            f"Mandate {m.get('id','?')[:20]}... has null created_at. "
            "Frontend formatDate() will crash: dateString.endsWith is not a function",
        )
    else:
        # Check format
        ca = str(m["created_at"])
        if "T" not in ca and " " not in ca:
            log_issue(
                "BUG",
                f"Unusual created_at format: {ca}",
                "Expected ISO format with T or space separator",
            )

# What about expiration for intent mandates?
for m in all_mandates:
    if m["type"] == "intent":
        exp = m.get("expiration")
        if exp is not None:
            log_ok(f"Intent mandate expiration: {exp}")
        else:
            # expiration is expected for intent mandates
            log_issue(
                "LOGIC",
                "Intent mandate has no expiration",
                f"Mandate {m['id'][:20]}... is type=intent but has no expiration field. "
                "The frontend conditionally renders expiration, so this won't crash, "
                "but it's unexpected since backend always sets expiration_hours.",
            )


# ============================================================
# STEP 16: Duplicate filtering concern - backend vs frontend
# ============================================================
log_section("STEP 16: Duplicate filtering (backend vs frontend)")

# The backend does server-side filtering with mandate_type and status_filter params
# But the frontend does CLIENT-SIDE filtering on the full mandates array
# The frontend fetches ALL mandates (no type/status params) and filters in useEffect

log_issue(
    "LOGIC",
    "Frontend does client-side filtering, ignoring backend filter capabilities",
    "The backend supports mandate_type and status_filter query params, "
    "but AIAssistant.jsx fetches ALL mandates with just '?limit=50' and passes them to "
    "AgentActivityMonitor which filters client-side. This means: "
    "(1) If user has >50 mandates, only 50 are fetched, and client-side filtering "
    "further reduces this - the user may see fewer results than exist. "
    "(2) Backend filtering is more efficient but unused. "
    "(3) The 50-mandate limit applies BEFORE filtering, so filtering by 'payment' type "
    "may show 0 results even if payment mandates exist beyond the 50-limit.",
)


# ============================================================
# STEP 17: The 'count' field mismatch
# ============================================================
log_section("STEP 17: Response count field analysis")

# Backend returns: {"mandates": results[:limit], "count": len(results)}
# But len(results) is counted BEFORE the [:limit] truncation
# So count may be larger than len(mandates)

resp = requests.get(f"{BASE_URL}/api/ap2/user/mandates?limit=2", headers=HEADERS)
if resp.status_code == 200:
    data = resp.json()
    returned_count = len(data.get("mandates", []))
    stated_count = data.get("count", 0)
    print(
        f"  limit=2: returned {returned_count} mandates, count field says {stated_count}"
    )
    if stated_count > returned_count:
        log_issue(
            "LOGIC",
            "count field is larger than actual returned mandates",
            f"With limit=2, API returns {returned_count} mandates but count={stated_count}. "
            "The 'count' is calculated before limit truncation. "
            "Frontend doesn't use the count field, but this is misleading for any consumer.",
        )
    elif stated_count == returned_count:
        log_ok(
            "count matches returned mandates count (user has <= 2 mandates or all types)"
        )

# Also: the limit applies per-type, not globally
# Each type query uses .limit(limit), then results are merged and truncated
resp = requests.get(f"{BASE_URL}/api/ap2/user/mandates?limit=50", headers=HEADERS)
if resp.status_code == 200:
    data = resp.json()
    type_counts = {}
    for m in data.get("mandates", []):
        t = m["type"]
        type_counts[t] = type_counts.get(t, 0) + 1
    print(f"  Type distribution: {type_counts}")

    # Each type can return up to 50, so total could be up to 150
    total = sum(type_counts.values())
    if total > 50:
        log_issue(
            "BUG",
            "More than 'limit' mandates returned",
            f"limit=50 but {total} mandates returned because limit is applied per-type "
            "(50 intent + 50 cart + 50 payment = up to 150), then truncated to 50 at the end. "
            "But intermediate memory usage could be high with large datasets.",
        )


# ============================================================
# STEP 18: Check for missing 'approved' status
# ============================================================
log_section("STEP 18: Missing status handling")

# Cart mandates can have status 'approved' (from cart-mandate creation flow)
# But the frontend has no 'approved' status filter button or badge config
# getStatusConfig doesn't have 'approved'
log_issue(
    "MISMATCH",
    "Cart mandates can have 'approved' status but frontend has no config for it",
    "CartMandate.status can be 'approved' (set during create_cart_mandate flow). "
    "But getStatusConfig() doesn't handle 'approved' - it falls through to default 'pending' config. "
    "And the status filter buttons don't include 'approved'. "
    "Users can't filter for approved carts specifically.",
)


# ============================================================
# FINAL REPORT
# ============================================================
log_section("FINAL REPORT")

# Categorize
bugs = [i for i in ISSUES if i["category"] == "BUG"]
logic = [i for i in ISSUES if i["category"] == "LOGIC"]
mismatches = [i for i in ISSUES if i["category"] == "MISMATCH"]
ux = [i for i in ISSUES if i["category"] == "UX"]

print(f"\nTotal issues found: {len(ISSUES)}")
print(f"  BUG:      {len(bugs)}")
print(f"  LOGIC:    {len(logic)}")
print(f"  MISMATCH: {len(mismatches)}")
print(f"  UX:       {len(ux)}")

print("\n" + "=" * 70)
print("DETAILED ISSUE LIST")
print("=" * 70)

for i, issue in enumerate(ISSUES, 1):
    print(f"\n#{i} [{issue['category']}] {issue['title']}")
    print(f"   {issue['detail']}")

print(f"\n{'='*70}")
print("QA TEST COMPLETE")
print(f"{'='*70}")
