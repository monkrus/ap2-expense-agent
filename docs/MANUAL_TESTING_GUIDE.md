# Manual Testing Guide - All New Features

Complete step-by-step guide to manually test all newly implemented features.

## Prerequisites

### 1. Start the Backend Server

```bash
cd backend
python -m uvicorn src.api:app --reload --port 8000
```

**Verify**: Backend running at http://127.0.0.1:8000

### 2. Start the Frontend Server

```bash
cd frontend
npm run dev
```

**Verify**: Frontend running at http://localhost:5173 or http://localhost:5174

### 3. Test Users

You'll need these users (create if they don't exist):

**Employee**: `emptest` / `employee@test.com`
**Admin**: `admintest` / `admin@test.com`

---

## Feature 1: Expense Editing (PUT Endpoint)

### Test 1.1: Employee Can Edit Pending Expense

**Steps:**
1. Login as **emptest** (employee)
2. Go to Employee Dashboard
3. Submit a new expense:
   - Vendor: "Edit Test Vendor"
   - Amount: $100.00
   - Category: "Travel"
   - Description: "This will be edited"
4. Note the expense ID from the response
5. While still PENDING, try to edit it using API:

**Using Browser Console (F12):**
```javascript
// Get your auth token from localStorage
const token = localStorage.getItem('access_token');

// Edit the expense
fetch('/api/v1/expenses/YOUR_EXPENSE_ID', {
  method: 'PUT',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    user_id: 'YOUR_USER_ID',
    amount: 150.00,
    vendor: "EDITED Vendor",
    category: "Software",
    description: "Successfully edited!"
  })
})
.then(r => r.json())
.then(d => console.log(d));
```

**Expected Result:**
```json
{
  "success": true,
  "message": "Expense updated successfully",
  "expense": {
    "id": "...",
    "amount": 150.00,
    "vendor": "EDITED Vendor",
    "category": "Software",
    "description": "Successfully edited!",
    "status": "pending"
  }
}
```

✅ **Pass Criteria**: Expense details updated, status remains pending

### Test 1.2: Cannot Edit Approved Expense

**Steps:**
1. Login as **admintest** (admin)
2. Approve the expense from Test 1.1
3. Login back as **emptest**
4. Try to edit the now-approved expense (use same API call)

**Expected Result:**
```json
{
  "detail": "Cannot edit expense with status: approved. Only pending expenses can be edited."
}
```

✅ **Pass Criteria**: Error message, status code 400

### Test 1.3: Employee Cannot Edit Other User's Expense

**Steps:**
1. Create an expense as **emptest**
2. Login as different employee
3. Try to edit emptest's expense

**Expected Result:**
```json
{
  "detail": "You can only edit your own expenses"
}
```

✅ **Pass Criteria**: Error message, status code 403

---

## Feature 2: Expense Withdrawal (DELETE Endpoint)

### Test 2.1: Employee Can Withdraw Pending Expense

**Steps:**
1. Login as **emptest**
2. Submit a new expense:
   - Description: "Will be withdrawn"
   - Amount: $50.00
3. Immediately withdraw it using API:

**Using Browser Console:**
```javascript
const token = localStorage.getItem('access_token');

fetch('/api/v1/expenses/YOUR_EXPENSE_ID/withdraw', {
  method: 'DELETE',
  headers: {
    'Authorization': `Bearer ${token}`
  }
})
.then(r => r.json())
.then(d => console.log(d));
```

**Expected Result:**
```json
{
  "success": true,
  "message": "Expense withdrawn successfully",
  "expense_id": "..."
}
```

4. Refresh the page - expense should disappear from Active tab

✅ **Pass Criteria**: Expense withdrawn, removed from pending list

---

## Feature 3: Enhanced Error Handling & Retry Logic

### Test 3.1: User-Friendly Error Messages

**Steps:**
1. Logout from application
2. Try to access `/api/v1/expenses/report` without token:

```javascript
fetch('/api/v1/expenses/report')
.then(r => r.json())
.then(d => console.log(d));
```

**Expected Result:**
```json
{
  "detail": "Your session has expired. Please log in again."
}
```

✅ **Pass Criteria**: Clear, user-friendly error message

### Test 3.2: Retry Logic on Network Errors

**Steps:**
1. Login as **emptest**
2. Open DevTools → Network tab
3. Set throttling to "Offline"
4. Try to submit an expense
5. Switch back to "Online" within 5 seconds

**Expected Result:**
- Browser console shows retry messages
- Request eventually succeeds when online
- Expense is submitted

✅ **Pass Criteria**: Automatic retry with exponential backoff

---

## Feature 4: Complete AP2 Audit Trail

### Test 4.1: Approve Expense Creates All Mandates

**Steps:**
1. Login as **emptest**, submit expense:
   - Description: "AP2 Audit Trail Test"
   - Amount: $200.00
2. Note the expense ID
3. Login as **admintest**
4. Approve the expense using API:

```javascript
const token = localStorage.getItem('access_token');

fetch('/api/v1/expenses/approve', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    expense_id: 'YOUR_EXPENSE_ID',
    approver_id: 'YOUR_ADMIN_USER_ID'
  })
})
.then(r => r.json())
.then(d => console.log(d));
```

**Expected Result:**
```json
{
  "success": true,
  "result": {
    "expense_id": "...",
    "status": "approved",
    "transaction_id": "payment_...",
    "mandates": {
      "intent": {
        "id": "intent_...",
        "constraints": {
          "max_amount": 220.00,
          "allowed_categories": ["Travel"],
          "allowed_vendors": ["..."],
          "approver_id": "..."
        },
        "signature": "...",
        "timestamp": "...",
        "expiration": "..."
      },
      "cart": {
        "id": "cart_...",
        "items": [...],
        "total": 200.00,
        "merchant": "...",
        "user_signature": "...",
        "timestamp": "..."
      },
      "payment": {
        "id": "payment_...",
        "payment_method": "corporate_account",
        "status": "approved",
        "audit_trail": {
          "expense_id": "...",
          "submitted_by": "...",
          "reviewed_by": "...",
          "action": "approve",
          "approval_chain": [...],
          "compliance_checks": {...}
        },
        "timestamp": "..."
      }
    }
  }
}
```

✅ **Pass Criteria**:
- Transaction ID returned
- Intent mandate with constraints
- Cart mandate with items
- Payment mandate with audit trail

### Test 4.2: Retrieve Complete Audit Trail

**Steps:**
1. Using the `transaction_id` from Test 4.1
2. Retrieve audit trail:

```javascript
const token = localStorage.getItem('access_token');

fetch('/api/v1/audit/YOUR_TRANSACTION_ID', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
})
.then(r => r.json())
.then(d => console.log(JSON.stringify(d, null, 2)));
```

**Expected Result:**
```json
{
  "transaction_id": "payment_...",
  "complete": true,
  "expense": {
    "id": "...",
    "amount": 200.00,
    "vendor": "...",
    "category": "Travel",
    "description": "AP2 Audit Trail Test",
    "status": "approved",
    "submitted_at": "...",
    "approved_at": "..."
  },
  "intent_mandate": {
    "id": "intent_...",
    "user_id": "...",
    "constraints": {...},
    "timestamp": "...",
    "expiration": "...",
    "signature": "...",
    "status": "active"
  },
  "cart_mandate": {
    "id": "cart_...",
    "items": [...],
    "total": 200.00,
    "merchant": "...",
    "timestamp": "...",
    "user_signature": "...",
    "status": "approved"
  },
  "payment_mandate": {
    "id": "payment_...",
    "payment_method": "corporate_account",
    "status": "approved",
    "timestamp": "...",
    "audit_trail": {...}
  },
  "audit_logs": [...],
  "verification": {
    "chain_complete": true,
    "signatures_valid": true,
    "timestamps_valid": true
  }
}
```

✅ **Pass Criteria**:
- Complete audit trail returned
- All three mandates present
- Verification shows chain complete
- Timestamps in chronological order

### Test 4.3: Rejection Creates Audit Log

**Steps:**
1. Submit expense as **emptest**
2. Login as **admintest**
3. Reject the expense:

```javascript
const token = localStorage.getItem('access_token');

fetch('/api/v1/expenses/reject', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    expense_id: 'YOUR_EXPENSE_ID',
    approver_id: 'YOUR_ADMIN_ID',
    rejection_reason: 'Missing receipt documentation'
  })
})
.then(r => r.json())
.then(d => console.log(d));
```

**Expected Result:**
```json
{
  "success": true,
  "result": {
    "expense_id": "...",
    "status": "rejected",
    "rejected_by": "...",
    "rejected_at": "...",
    "rejection_reason": "Missing receipt documentation"
  }
}
```

✅ **Pass Criteria**:
- Rejection recorded
- Reason stored
- Audit log created

---

## Feature 5: Receipt Upload System

### Test 5.1: Upload Receipt for Expense

**Steps:**
1. Login as **emptest**
2. Submit an expense and note its ID
3. Upload a receipt:

**Using Browser Console:**
```javascript
const token = localStorage.getItem('access_token');

// Create a test file
const file = new File(["test receipt content"], "receipt.pdf", {
  type: "application/pdf"
});

const formData = new FormData();
formData.append('file', file);

fetch('/api/v1/receipts/upload/YOUR_EXPENSE_ID', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
})
.then(r => r.json())
.then(d => console.log(d));
```

**Expected Result:**
```json
{
  "success": true,
  "receipt": {
    "id": "...",
    "filename": "receipt.pdf",
    "file_size": 123,
    "content_type": "application/pdf",
    "uploaded_at": "..."
  }
}
```

✅ **Pass Criteria**: Receipt uploaded, metadata stored

### Test 5.2: List Receipts for Expense

```javascript
const token = localStorage.getItem('access_token');

fetch('/api/v1/receipts/YOUR_EXPENSE_ID', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
})
.then(r => r.json())
.then(d => console.log(d));
```

**Expected Result:**
```json
{
  "receipts": [
    {
      "id": "...",
      "filename": "receipt.pdf",
      "file_size": 123,
      "uploaded_at": "..."
    }
  ]
}
```

✅ **Pass Criteria**: List of receipts returned

### Test 5.3: File Type Validation

**Steps:**
1. Try to upload an invalid file type:

```javascript
const token = localStorage.getItem('access_token');

const file = new File(["test"], "test.exe", {
  type: "application/exe"
});

const formData = new FormData();
formData.append('file', file);

fetch('/api/v1/receipts/upload/YOUR_EXPENSE_ID', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
})
.then(r => r.json())
.then(d => console.log(d));
```

**Expected Result:**
```json
{
  "detail": "File type not allowed. Allowed types: .jpg, .jpeg, .png, .pdf, .gif, .bmp, .webp"
}
```

✅ **Pass Criteria**: Validation error, file rejected

---

## Feature 6: Authorization Checks

### Test 6.1: Employee Cannot Approve Expenses

**Steps:**
1. Login as **emptest** (employee role)
2. Try to approve an expense:

```javascript
const token = localStorage.getItem('access_token');

fetch('/api/v1/expenses/approve', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    expense_id: 'ANY_EXPENSE_ID',
    approver_id: 'ANY_ID'
  })
})
.then(r => r.json())
.then(d => console.log(d));
```

**Expected Result:**
```json
{
  "detail": "Not authorized to approve expenses"
}
```
Status code: 403

✅ **Pass Criteria**: Authorization error returned

### Test 6.2: Admin Can Access All Expenses

**Steps:**
1. Login as **admintest**
2. Access admin endpoint:

```javascript
const token = localStorage.getItem('access_token');

fetch('/api/v1/admin/expenses', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
})
.then(r => r.json())
.then(d => console.log(d));
```

**Expected Result:**
```json
{
  "total_count": 10,
  "total_amount": 1500.00,
  "pending_count": 2,
  "approved_count": 7,
  "rejected_count": 1,
  "expenses": [...]
}
```

✅ **Pass Criteria**: All expenses from all users returned

### Test 6.3: Employee Cannot Access Admin Endpoint

**Steps:**
1. Login as **emptest**
2. Try to access admin endpoint (same as Test 6.2)

**Expected Result:**
```json
{
  "detail": "Not authorized to view all expenses"
}
```
Status code: 403

✅ **Pass Criteria**: Access denied

---

## Feature 7: Input Validation

### Test 7.1: Missing Required Fields

**Steps:**
```javascript
const token = localStorage.getItem('access_token');

fetch('/api/v1/expenses', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    amount: 100.00
    // Missing: vendor, category, description, user_id
  })
})
.then(r => r.json())
.then(d => console.log(d));
```

**Expected Result:**
Status code: 422 (Validation Error)

✅ **Pass Criteria**: Validation error with field details

---

## Testing Checklist

Use this checklist to track your testing progress:

### Expense Management
- [ ] ✅ Employee can submit expense
- [ ] ✅ Employee can edit pending expense
- [ ] ✅ Cannot edit approved expense
- [ ] ✅ Cannot edit other user's expense
- [ ] ✅ Employee can withdraw pending expense
- [ ] ✅ Cannot withdraw approved expense

### AP2 Audit Trail
- [ ] ✅ Approval creates Intent mandate
- [ ] ✅ Approval creates Cart mandate
- [ ] ✅ Approval creates Payment mandate
- [ ] ✅ Transaction ID returned
- [ ] ✅ Complete audit trail retrievable
- [ ] ✅ Audit trail shows all mandates
- [ ] ✅ Verification shows chain complete
- [ ] ✅ Rejection creates audit log

### Receipt Management
- [ ] ✅ Can upload receipt (PDF)
- [ ] ✅ Can upload receipt (Image)
- [ ] ✅ Can list receipts for expense
- [ ] ✅ Invalid file types rejected
- [ ] ✅ File size limit enforced (10MB)
- [ ] ✅ Can only upload to own expenses

### Authorization
- [ ] ✅ Employee cannot approve expenses
- [ ] ✅ Admin can approve expenses
- [ ] ✅ Admin can reject expenses
- [ ] ✅ Admin can view all expenses
- [ ] ✅ Employee can only view own expenses
- [ ] ✅ Manager can approve expenses

### Error Handling
- [ ] ✅ User-friendly error messages (401)
- [ ] ✅ User-friendly error messages (403)
- [ ] ✅ User-friendly error messages (404)
- [ ] ✅ Retry logic on network errors
- [ ] ✅ Validation errors returned (422)

---

## API Documentation

For detailed API documentation with all endpoints, visit:

**http://127.0.0.1:8000/docs** (when backend is running)

This provides interactive API testing through Swagger UI.

---

## Troubleshooting

### "401 Unauthorized" errors
- Check if you're logged in
- Check if token is in localStorage: `localStorage.getItem('access_token')`
- Try logging in again

### "403 Forbidden" errors
- Check user role (employee vs admin)
- Admin features require ADMIN, MANAGER, or ACCOUNTANT role

### Network errors
- Verify backend is running on port 8000
- Verify frontend is running on port 5173/5174
- Check browser console for CORS errors

### Database queries
Monitor database state:
```bash
python check_users_and_expenses.py
```

---

## Next Steps

After manual testing:
1. Run automated test suite: `cd backend && pytest tests/ -v`
2. Check test coverage: `pytest tests/ --cov=src --cov-report=html`
3. Review AUTOMATED_TESTING.md for continuous testing

---

## Support

For issues or questions:
- Check backend logs in terminal
- Check browser DevTools console
- Review API docs at /docs endpoint
- Check DATABASE_MIGRATION.md for database issues
