import urllib.request, json

TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjYjhhM2Q5ZS1hNmViLTQyYjEtOTk2My0yMGZkNWZiMWRiYjMiLCJ1c2VybmFtZSI6ImFkbWluZnJlZSIsInJvbGUiOiJhZG1pbiIsImV4cCI6MTc3MTg5MTUwMywiaWF0IjoxNzcxODg3OTAzLCJ0eXBlIjoiYWNjZXNzIn0.zRDaa8tasODudOpHvOCEdG8xecQGMRhdmXTDmiQDSf8'
ORG = 'ccd58bdd-5d7a-426d-8152-56583410a4ce'
BASE = 'http://127.0.0.1:8000'

def api(method, path, body=None):
    headers = {'Authorization': f'Bearer {TOKEN}', 'X-Organization-Id': ORG, 'Content-Type': 'application/json'}
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(f'{BASE}{path}', data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req)
        body = resp.read()
        if not body:
            return resp.status, {'status': 'no_content'}
        try:
            return resp.status, json.loads(body)
        except:
            return resp.status, {'binary': True, 'size': len(body), 'preview': str(body[:30])}
    except urllib.error.HTTPError as e:
        body = e.read()
        if not body:
            return e.code, {'status': 'no_content'}
        try:
            return e.code, json.loads(body)
        except:
            try:
                return e.code, {'raw': body.decode()[:200]}
            except:
                return e.code, {'error': str(e)}

results = []

# ============================================================
# APPROVAL POLICIES (Approval Rules CRUD)
# ============================================================

# 1. LIST approval policies (empty)
code, resp = api('GET', '/api/v1/approval-policies')
results.append(('LIST approval policies', code, f'count={len(resp) if isinstance(resp,list) else resp}'))

# 2. CREATE approval policy
policy_data = {
    'name': 'Low amount auto-approve',
    'description': 'Auto-approve expenses under $100',
    'conditions': {'max_amount': 100, 'categories': ['OFFICE_SUPPLIES', 'MEALS']},
    'auto_approve': True,
    'is_active': True
}
code, resp = api('POST', '/api/v1/approval-policies', policy_data)
results.append(('CREATE approval policy', code, str(resp)[:200]))
policy_id = resp.get('id', '')

# 3. CREATE another policy
policy_data2 = {
    'name': 'Travel requires review',
    'description': 'All travel expenses need manual approval',
    'conditions': {'categories': ['TRAVEL']},
    'auto_approve': False,
    'is_active': True
}
code, resp = api('POST', '/api/v1/approval-policies', policy_data2)
results.append(('CREATE second policy', code, str(resp)[:200]))
policy_id2 = resp.get('id', '')

# 4. GET single policy
if policy_id:
    code, resp = api('GET', f'/api/v1/approval-policies/{policy_id}')
    results.append(('GET single policy', code, f'name={resp.get("name","?")}'))

# 5. UPDATE policy
if policy_id:
    code, resp = api('PUT', f'/api/v1/approval-policies/{policy_id}', {
        'name': 'Updated auto-approve',
        'description': 'Updated desc',
        'conditions': {'max_amount': 200, 'categories': ['OFFICE_SUPPLIES']},
        'auto_approve': True,
        'is_active': True
    })
    results.append(('UPDATE policy', code, str(resp)[:150]))

# 6. GET non-existent policy
code, resp = api('GET', '/api/v1/approval-policies/00000000-0000-0000-0000-000000000000')
results.append(('GET non-existent policy', code, str(resp)[:80]))

# 7. DELETE policy
if policy_id2:
    code, resp = api('DELETE', f'/api/v1/approval-policies/{policy_id2}')
    results.append(('DELETE policy', code, str(resp)[:120]))

# 8. DELETE already-deleted
if policy_id2:
    code, resp = api('DELETE', f'/api/v1/approval-policies/{policy_id2}')
    results.append(('DELETE already-deleted', code, str(resp)[:120]))

# 9. CREATE policy missing fields
code, resp = api('POST', '/api/v1/approval-policies', {})
results.append(('CREATE policy missing fields', code, str(resp)[:200]))

# 10. CREATE policy invalid data
code, resp = api('POST', '/api/v1/approval-policies', {'name': '', 'conditions': 'invalid'})
results.append(('CREATE policy invalid data', code, str(resp)[:200]))

# 11. Test policy endpoint
code, resp = api('POST', '/api/v1/approval-policies/test', {
    'amount': 50,
    'category': 'OFFICE_SUPPLIES',
    'vendor': 'Test'
})
results.append(('TEST policy (should auto-approve)', code, str(resp)[:200]))

# 12. Test policy with specific ID
if policy_id:
    code, resp = api('POST', f'/api/v1/approval-policies/{policy_id}/test', {
        'amount': 50,
        'category': 'OFFICE_SUPPLIES',
        'vendor': 'Test'
    })
    results.append(('TEST specific policy', code, str(resp)[:200]))

# 13. Test policy - over threshold
code, resp = api('POST', '/api/v1/approval-policies/test', {
    'amount': 5000,
    'category': 'TRAVEL',
    'vendor': 'Test'
})
results.append(('TEST policy (over threshold)', code, str(resp)[:200]))

# 14. Policy analytics/statistics
code, resp = api('GET', '/api/v1/approval-policies/analytics/statistics')
results.append(('GET policy analytics', code, str(resp)[:200]))

# ============================================================
# APPROVE/REJECT WORKFLOW - with correct permissions
# ============================================================

# Create a pending expense to approve
code, resp = api('POST', '/api/v1/expenses', {'amount': 75, 'description': 'Pending for approval test', 'category': 'TRAVEL', 'vendor': 'Test'})
results.append(('CREATE pending expense', code, f'status={resp.get("status")}'))
pending_id = resp.get('id', '')

# Try to approve - check if admin can approve own expenses
if pending_id:
    code, resp = api('PUT', f'/api/v1/expenses/{pending_id}/approve')
    results.append(('APPROVE own expense', code, str(resp)[:150]))

# ============================================================
# RECURRING EXPENSES
# ============================================================

# 15. LIST recurring expenses
code, resp = api('GET', '/api/recurring-expenses')
results.append(('LIST recurring expenses', code, str(resp)[:200]))

# 16. CREATE recurring expense
recur_data = {
    'amount': 29.99,
    'description': 'Monthly software sub',
    'category': 'SOFTWARE',
    'vendor': 'GitHub',
    'frequency': 'monthly',
    'start_date': '2026-03-01'
}
code, resp = api('POST', '/api/recurring-expenses', recur_data)
results.append(('CREATE recurring expense', code, str(resp)[:200]))
recur_id = resp.get('id', resp.get('template_id', ''))

# 17. GET recurring
if recur_id:
    code, resp = api('GET', f'/api/recurring-expenses/{recur_id}')
    results.append(('GET recurring expense', code, str(resp)[:150]))

# 18. Pause recurring
if recur_id:
    code, resp = api('PUT', f'/api/recurring-expenses/{recur_id}/pause')
    results.append(('PAUSE recurring', code, str(resp)[:150]))

# 19. Resume recurring
if recur_id:
    code, resp = api('PUT', f'/api/recurring-expenses/{recur_id}/resume')
    results.append(('RESUME recurring', code, str(resp)[:150]))

# ============================================================
# EXPORT
# ============================================================
code, resp = api('GET', '/api/v1/expenses/export')
results.append(('EXPORT expenses (PDF)', code, 'Got PDF' if isinstance(resp, str) and 'PDF' in str(resp) else str(resp)[:80]))

# Print results
print("=" * 80)
print("APPROVAL POLICIES & WORKFLOW TEST RESULTS")
print("=" * 80)
for name, code, detail in results:
    if code < 300:
        status = 'PASS'
    elif code in (404, 422) and ('non-existent' in name.lower() or 'missing' in name.lower() or 'invalid' in name.lower() or 'already-deleted' in name.lower()):
        status = 'EXPECTED'
    elif code >= 400:
        status = 'ISSUE'
    else:
        status = 'PASS'
    print(f'  [{status:8s}] {code:3d} {name}: {detail}')
