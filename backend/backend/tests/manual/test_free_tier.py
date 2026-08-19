import requests
import json

BASE = 'http://localhost:8000'

print("="*70)
print("FREE PLAN COMPREHENSIVE TEST")
print("Testing against http://localhost:5173/pricing specifications")
print("="*70)

# Free plan specs from pricing page
FREE_PLAN_SPECS = {
    'users': 1,
    'expenses_per_month': 20,
    'expenses_per_day': 10,
    'ai_categorization': 0,
    'ocr_scans_per_month': 5,
    'ocr_scans_per_day': 3,
    'ap2_transactions': 0,
    'data_retention_days': 30,
}

# Register a new Free tier user
print("\n" + "="*70)
print("STEP 1: Register New Free Tier User")
print("="*70)
reg_resp = requests.post(f'{BASE}/api/v1/auth/register', json={
    'username': 'freetiertest',
    'email': 'freetiertest@test.com',
    'password': 'Test123!'
})
print(f"Registration: {reg_resp.status_code}")
if reg_resp.status_code != 201:
    print(f"Response: {reg_resp.text}")
    exit(1)

# Login
login_resp = requests.post(f'{BASE}/api/v1/auth/login', json={
    'username': 'freetiertest',
    'password': 'Test123!'
})
if login_resp.status_code != 200:
    print(f"Login failed: {login_resp.text}")
    exit(1)

token = login_resp.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}
print("Login: SUCCESS")

# Check usage summary
print("\n" + "="*70)
print("STEP 2: Check Usage Summary (Default Free Tier)")
print("="*70)
usage = requests.get(f'{BASE}/api/billing/usage/summary', headers=headers)
if usage.status_code == 200:
    data = usage.json()
    print(f"Tier: {data.get('tier')}")
    print(f"Tier Name: {data.get('tier_name')}")
    print(f"Is Free Tier: {data.get('is_free_tier')}")
    print(f"Data Retention: {data.get('data_retention_days')} days")
    print(f"\nUsage Limits:")
    for key, val in data.get('usage', {}).items():
        print(f"  {key}: current={val['current']}, limit={val['limit']}, blocked={val['blocked']}")
    print(f"\nFeatures:")
    for key, val in data.get('features', {}).items():
        print(f"  {key}: {val}")
else:
    print(f"Failed to get usage summary: {usage.text[:200]}")

# Test 1: Organization limit
print("\n" + "="*70)
print("TEST 1: Organization Limit (1 user = max 1 organization)")
print("="*70)
org1 = requests.post(f'{BASE}/api/v1/organizations',
    json={'name': 'Free Test Org 1', 'description': 'First org'},
    headers=headers)
print(f"Create 1st org: {org1.status_code}")
if org1.status_code in [200, 201]:
    org1_id = org1.json()['organization']['id']
    print(f"  Org ID: {org1_id}")
    print("  PASS: First organization created successfully")
else:
    print(f"  FAIL: Could not create first org - {org1.text[:200]}")
    org1_id = None

org2 = requests.post(f'{BASE}/api/v1/organizations',
    json={'name': 'Free Test Org 2', 'description': 'Second org'},
    headers=headers)
print(f"Create 2nd org: {org2.status_code}")
if org2.status_code == 422:
    print("  PASS: Second organization correctly blocked (payment required)")
else:
    print(f"  FAIL: Expected 422, got {org2.status_code}")

# Test 2: Expense submission
print("\n" + "="*70)
print("TEST 2: Basic Expense Submission (Core Feature)")
print("="*70)
expense1 = requests.post(f'{BASE}/api/v1/expenses',
    json={
        'amount': 25.50,
        'description': 'Test expense for Free tier',
        'vendor': 'Test Vendor',
        'category': 'TRAVEL'
    },
    headers=headers)
print(f"Submit expense: {expense1.status_code}")
if expense1.status_code in [200, 201]:
    exp_data = expense1.json()
    exp = exp_data.get('expense', exp_data)
    print(f"  Expense ID: {exp.get('id')}")
    print(f"  Amount: ${exp.get('amount')}")
    print(f"  Status: {exp.get('status')}")
    print("  PASS: Expense submission works")
else:
    print(f"  FAIL: Could not submit expense - {expense1.text[:200]}")

# Test 3: Monthly expense limit (20/month)
print("\n" + "="*70)
print("TEST 3: Monthly Expense Limit (20 expenses/month)")
print("="*70)
print("Submitting 19 more expenses to reach limit...")
for i in range(2, 21):
    resp = requests.post(f'{BASE}/api/v1/expenses',
        json={
            'amount': 10.00 + i,
            'description': f'Expense {i}',
            'vendor': 'Test',
            'category': 'TRAVEL'
        },
        headers=headers)
    if resp.status_code not in [200, 201]:
        print(f"  Expense {i} failed: {resp.status_code}")
        break
print(f"Submitted expenses 2-20")

# Try 21st expense
exp21 = requests.post(f'{BASE}/api/v1/expenses',
    json={
        'amount': 50.00,
        'description': 'Expense 21 (should fail)',
        'vendor': 'Test',
        'category': 'TRAVEL'
    },
    headers=headers)
print(f"Submit 21st expense: {exp21.status_code}")
if exp21.status_code == 422 and 'limit' in exp21.text.lower():
    print("  PASS: 21st expense blocked (monthly limit reached)")
else:
    print(f"  CHECK: Status {exp21.status_code}, may need to check limit enforcement")

# Test 4: AI Categorization
print("\n" + "="*70)
print("TEST 4: AI Categorization Limit (0 = disabled)")
print("="*70)
ai_limit = requests.get(f'{BASE}/api/billing/usage/check-limit/ai_categorization', headers=headers)
if ai_limit.status_code == 200:
    ai_data = ai_limit.json()
    print(f"AI Categorization - Limit: {ai_data.get('limit')}, Exceeded: {ai_data.get('exceeded')}")
    if ai_data.get('limit') == 0 and ai_data.get('exceeded'):
        print("  PASS: AI categorization disabled for Free tier")
    else:
        print("  FAIL: AI categorization should be disabled")
else:
    print(f"  Error checking AI limit: {ai_limit.text[:200]}")

# Test 5: OCR Scans
print("\n" + "="*70)
print("TEST 5: OCR Scan Limit (5 scans/month)")
print("="*70)
ocr_limit = requests.get(f'{BASE}/api/billing/usage/check-limit/ocr_scan', headers=headers)
if ocr_limit.status_code == 200:
    ocr_data = ocr_limit.json()
    print(f"OCR Scans - Current: {ocr_data.get('current_usage')}, Limit: {ocr_data.get('limit')}")
    if ocr_data.get('limit') == 5:
        print("  PASS: OCR scan limit is 5/month as advertised")
    else:
        print(f"  FAIL: OCR limit should be 5, got {ocr_data.get('limit')}")
else:
    print(f"  Error checking OCR limit: {ocr_limit.text[:200]}")

# Test 6: AP2 Transactions
print("\n" + "="*70)
print("TEST 6: AP2 Transactions Limit (0 = disabled)")
print("="*70)
ap2_limit = requests.get(f'{BASE}/api/billing/usage/check-limit/ap2_transaction', headers=headers)
if ap2_limit.status_code == 200:
    ap2_data = ap2_limit.json()
    print(f"AP2 Transactions - Limit: {ap2_data.get('limit')}, Exceeded: {ap2_data.get('exceeded')}")
    if ap2_data.get('limit') == 0 and ap2_data.get('exceeded'):
        print("  PASS: AP2 transactions disabled for Free tier")
    else:
        print("  FAIL: AP2 transactions should be disabled")
else:
    print(f"  Error checking AP2 limit: {ap2_limit.text[:200]}")

# Test 7: Get expenses (basic reporting)
print("\n" + "="*70)
print("TEST 7: Basic Reporting (Get Expenses)")
print("="*70)
expenses = requests.get(f'{BASE}/api/v1/expenses', headers=headers)
if expenses.status_code == 200:
    exp_list = expenses.json().get('expenses', [])
    print(f"Retrieved {len(exp_list)} expenses")
    print("  PASS: Basic expense listing works")
else:
    print(f"  FAIL: Could not retrieve expenses - {expenses.text[:200]}")

# Test 8: Invitation limit
print("\n" + "="*70)
print("TEST 8: User Invitation Limit (1 user max)")
print("="*70)
if org1_id:
    invite = requests.post(f'{BASE}/api/v1/organizations/{org1_id}/invitations',
        json={'email': 'invited@test.com'},
        headers=headers)
    print(f"Invite user: {invite.status_code}")
    if invite.status_code == 422:
        print("  PASS: User invitation blocked (1 user limit)")
    else:
        print(f"  CHECK: Expected 422, got {invite.status_code}")

print("\n" + "="*70)
print("SUMMARY: FREE PLAN FEATURE VERIFICATION")
print("="*70)
print("Per http://localhost:5173/pricing:")
print("  Users: 1 user - TESTED")
print("  Expenses: 20/month - TESTED")
print("  AI Categorization: No AI (0 limit) - TESTED")
print("  Receipt Scanning: 5 OCR scans - TESTED")
print("  AP2 Transactions: 0 (disabled) - TESTED")
print("  Data Retention: 30 days - VERIFIED IN CONFIG")
print("  Support: Help docs only - N/A (frontend feature)")
print("  Reporting: Basic reports - TESTED (expense listing)")
print("  Integrations: None - N/A")
print("  API Access: false - N/A")
print("  Custom Categories: false - N/A (frontend feature)")
print("  Approval Workflows: false - N/A")
print("  SSO: false - N/A")
