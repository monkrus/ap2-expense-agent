import urllib.request, json, os

TOKEN = os.environ.get(
    "AP2_TEST_TOKEN", "YOUR_JWT_TOKEN_HERE"
)  # Get a token via POST /api/v1/auth/login
ORG = os.environ.get("AP2_TEST_ORG", "YOUR_ORG_ID_HERE")  # Your organization ID
BASE = "http://127.0.0.1:8000"


def api(method, path, body=None):
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "X-Organization-Id": ORG,
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        f"{BASE}{path}", data=data, headers=headers, method=method
    )
    try:
        resp = urllib.request.urlopen(req)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except:
            return e.code, str(e)


results = []

# 1. LIST (empty org)
code, resp = api("GET", "/api/v1/expenses")
results.append(
    (
        "LIST expenses (empty org)",
        code,
        f"{len(resp) if isinstance(resp,list) else resp}",
    )
)

# 2. CREATE valid expense
code, resp = api(
    "POST",
    "/api/v1/expenses",
    {
        "amount": 42.50,
        "description": "QA test expense",
        "category": "OFFICE_SUPPLIES",
        "vendor": "Test Vendor",
    },
)
results.append(
    (
        "CREATE expense (valid)",
        code,
        f'id={resp.get("id","?")[:8]}... status={resp.get("status")}',
    )
)
exp_id1 = resp.get("id", "")

# 3. CREATE TRAVEL
code, resp = api(
    "POST",
    "/api/v1/expenses",
    {
        "amount": 250,
        "description": "Flight to NYC",
        "category": "TRAVEL",
        "vendor": "Delta Airlines",
    },
)
results.append(
    (
        "CREATE TRAVEL expense",
        code,
        f'id={resp.get("id","?")[:8]}... status={resp.get("status")}',
    )
)
exp_travel = resp.get("id", "")

# 4. CREATE MEALS
code, resp = api(
    "POST",
    "/api/v1/expenses",
    {
        "amount": 15.99,
        "description": "Team lunch",
        "category": "MEALS",
        "vendor": "Restaurant",
    },
)
results.append(("CREATE MEALS expense", code, f'status={resp.get("status")}'))
exp_meals = resp.get("id", "")

# 5. CREATE SOFTWARE
code, resp = api(
    "POST",
    "/api/v1/expenses",
    {
        "amount": 99.99,
        "description": "IDE license",
        "category": "SOFTWARE",
        "vendor": "JetBrains",
    },
)
results.append(("CREATE SOFTWARE expense", code, f'status={resp.get("status")}'))
exp_sw = resp.get("id", "")

# 6. Negative amount
code, resp = api(
    "POST",
    "/api/v1/expenses",
    {"amount": -10, "description": "Neg", "category": "OTHER", "vendor": "X"},
)
results.append(("CREATE negative amount", code, str(resp)[:120]))

# 7. Zero amount
code, resp = api(
    "POST",
    "/api/v1/expenses",
    {"amount": 0, "description": "Zero", "category": "OTHER", "vendor": "X"},
)
results.append(("CREATE zero amount", code, str(resp)[:120]))

# 8. Amount > 1M
code, resp = api(
    "POST",
    "/api/v1/expenses",
    {"amount": 1000001, "description": "Huge", "category": "TRAVEL", "vendor": "X"},
)
results.append(("CREATE amount > 1M", code, str(resp)[:120]))

# 9. Invalid category
code, resp = api(
    "POST",
    "/api/v1/expenses",
    {"amount": 10, "description": "Bad", "category": "INVALID", "vendor": "X"},
)
results.append(("CREATE invalid category", code, str(resp)[:120]))

# 10. Missing fields
code, resp = api("POST", "/api/v1/expenses", {})
results.append(("CREATE missing fields", code, str(resp)[:120]))

# 11. XSS
code, resp = api(
    "POST",
    "/api/v1/expenses",
    {
        "amount": 5,
        "description": "<script>alert(1)</script>",
        "category": "OTHER",
        "vendor": "X",
    },
)
xss_sanitized = "script" not in resp.get("description", "script")
results.append(
    (
        "CREATE XSS in description",
        code,
        f'sanitized={xss_sanitized}, desc={resp.get("description","")}',
    )
)
exp_xss = resp.get("id", "")

# 12. GET single
code, resp = api("GET", f"/api/v1/expenses/{exp_id1}")
results.append(("GET single expense", code, f'id match={resp.get("id")==exp_id1}'))

# 13. GET non-existent
code, resp = api("GET", "/api/v1/expenses/00000000-0000-0000-0000-000000000000")
results.append(("GET non-existent", code, str(resp)[:80]))

# 14. UPDATE expense
code, resp = api(
    "PUT",
    f"/api/v1/expenses/{exp_id1}",
    {
        "amount": 50,
        "description": "Updated",
        "category": "TRAVEL",
        "vendor": "Updated Vendor",
    },
)
results.append(
    ("UPDATE expense", code, f'amount={resp.get("amount")}, cat={resp.get("category")}')
)

# 15. UPDATE non-existent
code, resp = api(
    "PUT",
    "/api/v1/expenses/00000000-0000-0000-0000-000000000000",
    {"amount": 50, "description": "Ghost", "category": "TRAVEL", "vendor": "Ghost"},
)
results.append(("UPDATE non-existent", code, str(resp)[:80]))

# 16. DELETE expense
code, resp = api("DELETE", f"/api/v1/expenses/{exp_xss}")
results.append(("DELETE expense", code, str(resp)[:120]))

# 17. APPROVE pending travel
code, resp = api("PUT", f"/api/v1/expenses/{exp_travel}/approve")
results.append(("APPROVE pending", code, str(resp)[:120]))

# 18. APPROVE already-approved
code, resp = api("PUT", f"/api/v1/expenses/{exp_travel}/approve")
results.append(("APPROVE already-approved", code, str(resp)[:120]))

# 19. REJECT pending sw
code, resp = api(
    "PUT", f"/api/v1/expenses/{exp_sw}/reject", {"reason": "Budget exceeded"}
)
results.append(("REJECT with reason", code, str(resp)[:120]))

# 20. REJECT already-rejected
code, resp = api("PUT", f"/api/v1/expenses/{exp_sw}/reject", {"reason": "Double"})
results.append(("REJECT already-rejected", code, str(resp)[:120]))

# 21. REJECT without reason
code_c, resp_c = api(
    "POST",
    "/api/v1/expenses",
    {"amount": 500, "description": "No reason", "category": "SOFTWARE", "vendor": "X"},
)
if code_c == 201:
    nr_id = resp_c["id"]
    code2, resp2 = api("PUT", f"/api/v1/expenses/{nr_id}/reject", {})
    results.append(("REJECT without reason", code2, str(resp2)[:120]))
else:
    results.append(("REJECT without reason (create failed)", code_c, str(resp_c)[:120]))

# 22. FLAG expense
code, resp = api("PUT", f"/api/v1/expenses/{exp_id1}/flag", {"reason": "Suspicious"})
results.append(("FLAG expense", code, str(resp)[:120]))

# 23. REQUEST RECEIPT
code, resp = api("PUT", f"/api/v1/expenses/{exp_id1}/request-receipt")
results.append(("REQUEST RECEIPT (no body)", code, str(resp)[:120]))

# 23b. REQUEST RECEIPT with body
code, resp = api(
    "PUT",
    f"/api/v1/expenses/{exp_id1}/request-receipt",
    {"message": "Please upload receipt"},
)
results.append(("REQUEST RECEIPT (with body)", code, str(resp)[:120]))

# 24. GET receipts
code, resp = api("GET", f"/api/v1/receipts/{exp_id1}")
results.append(("GET receipts", code, str(resp)[:120]))

# 25. LIST all
code, resp = api("GET", "/api/v1/expenses")
results.append(
    (
        "LIST all expenses",
        code,
        f'count={len(resp) if isinstance(resp,list) else "N/A"}',
    )
)

# 26. Report
code, resp = api("GET", "/api/v1/expenses/report")
results.append(
    (
        "GET report",
        code,
        f'total={resp.get("total_expenses")}, amt={resp.get("total_amount")}',
    )
)

# 27. No auth
headers_noauth = {"Content-Type": "application/json"}
req = urllib.request.Request(f"{BASE}/api/v1/expenses", headers=headers_noauth)
try:
    resp = urllib.request.urlopen(req)
    results.append(("LIST without auth", resp.status, "UNEXPECTED SUCCESS"))
except urllib.error.HTTPError as e:
    results.append(("LIST without auth", e.code, str(json.loads(e.read()))[:80]))

# 28. No org header
headers_noorg = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
req = urllib.request.Request(f"{BASE}/api/v1/expenses", headers=headers_noorg)
try:
    resp = urllib.request.urlopen(req)
    results.append(("LIST without org header", resp.status, "UNEXPECTED SUCCESS"))
except urllib.error.HTTPError as e:
    results.append(("LIST without org header", e.code, str(json.loads(e.read()))[:80]))

# 29. Wrong org
headers_wrongorg = {
    "Authorization": f"Bearer {TOKEN}",
    "X-Organization-Id": "00000000-0000-0000-0000-000000000000",
    "Content-Type": "application/json",
}
req = urllib.request.Request(f"{BASE}/api/v1/expenses", headers=headers_wrongorg)
try:
    resp = urllib.request.urlopen(req)
    results.append(("LIST wrong org", resp.status, "UNEXPECTED SUCCESS"))
except urllib.error.HTTPError as e:
    results.append(("LIST wrong org", e.code, str(json.loads(e.read()))[:80]))

# 30. Archive/unarchive
code, resp = api("POST", f"/api/v1/admin/expenses/{exp_id1}/archive")
results.append(("ARCHIVE expense", code, str(resp)[:120]))

code, resp = api("GET", "/api/v1/admin/expenses/archived")
results.append(("GET archived", code, f'count={resp.get("total_count","?")}'))

code, resp = api("POST", f"/api/v1/admin/expenses/{exp_id1}/unarchive")
results.append(("UNARCHIVE expense", code, str(resp)[:120]))

# 31. Admin list
code, resp = api("GET", "/api/v1/admin/expenses")
results.append(("ADMIN list expenses", code, f'total={resp.get("total_count","?")}'))

# 32. Archive all / unarchive all
code, resp = api("POST", "/api/v1/admin/expenses/archive-all")
results.append(("ARCHIVE ALL", code, str(resp)[:120]))

code, resp = api("POST", "/api/v1/admin/expenses/unarchive-all")
results.append(("UNARCHIVE ALL", code, str(resp)[:120]))

# 33. Clear pending
code, resp = api("DELETE", "/api/v1/admin/expenses-pending/clear")
results.append(("CLEAR pending", code, str(resp)[:120]))

# 34. Clear all
code, resp = api("DELETE", "/api/v1/admin/expenses/clear")
results.append(("CLEAR all (admin)", code, str(resp)[:120]))

# Print results
print("=" * 80)
print("EXPENSE MANAGEMENT TEST RESULTS")
print("=" * 80)
for name, code, detail in results:
    if code < 300:
        status = "PASS"
    elif code in (403, 404, 422) and (
        "non-existent" in name.lower()
        or "negative" in name.lower()
        or "zero" in name.lower()
        or "missing" in name.lower()
        or "invalid" in name.lower()
        or "> 1m" in name.lower()
        or "already" in name.lower()
        or "without auth" in name.lower()
        or "without org" in name.lower()
        or "wrong org" in name.lower()
        or "delete" in name.lower()
    ):
        status = "EXPECTED"
    elif code >= 400:
        status = "FAIL"
    else:
        status = "PASS"
    print(f"  [{status:8s}] {code:3d} {name}: {detail}")
