# Approval Workflow Testing Guide

## Current Setup
- **Admin User**: `adminfree` (admin role)
- **Employee User**: `emp1` (employee role)
- **Free Tier Limit**: 2 users ✓

---

## Manual Testing Steps

### Step 1: Login as Employee (`emp1`)
1. Open http://localhost:5173
2. Login with username: `emp1` (use your password)
3. You should see the Employee Dashboard

### Step 2: Submit an Expense (as Employee)
1. Click **"Submit Expense"** button
2. Fill in the form:
   - **Amount**: $75.00
   - **Vendor**: "Coffee Shop"
   - **Category**: "Meals"
   - **Description**: "Team meeting lunch"
   - **Date**: Today's date
3. Click **"Submit"**
4. **Expected Result**:
   - Success message appears
   - Check if it says "Auto-approved" or "Submitted for approval"

### Step 3: Logout and Login as Admin (`adminfree`)
1. Logout from emp1 account
2. Login with username: `adminfree` (use your password)
3. You should see the Admin Dashboard

### Step 4: Check Pending Approvals (as Admin)
1. Click on **"Pending Approvals"** tab
2. **Expected Result**:
   - If NO auto-approval: You should see the expense submitted by emp1
   - If auto-approved: It will be in "All Expenses" tab with status "APPROVED"

### Step 5: Approve the Expense (as Admin)
1. If expense is in pending:
   - Click the **"Approve via AP2"** button
   - **Expected Result**:
     - Success message appears
     - Expense disappears from pending queue
     - Check "All Expenses" tab - expense should show status "APPROVED"
     - Transaction ID should be generated

### Step 6: Verify in All Expenses
1. Go to **"All Expenses"** tab
2. Find the expense you just approved
3. **Verify**:
   - Status badge shows "APPROVED"
   - "Approved by" shows adminfree
   - "Approved at" shows current timestamp
   - Transaction ID is present

---

## Testing Rejection Workflow

### Step 1: Submit Another Expense (as emp1)
- Amount: $200.00
- Vendor: "Office Supplies Inc"
- Category: "Office"
- Description: "New office chairs"

### Step 2: Reject the Expense (as adminfree)
1. Go to **"Pending Approvals"** tab
2. Click **"Reject"** button on the expense
3. Enter rejection reason: "Please get 3 quotes first"
4. Click **"Reject Expense"**
5. **Expected Result**:
   - Success message appears
   - Expense disappears from pending
   - Check "All Expenses" - status should be "REJECTED"
   - Rejection reason should be visible

---

## Automated Test Script

If you want to run automated tests, use:

```bash
python test_approval_workflow.py adminfree <password> emp1 <password>
```

Example:
```bash
python test_approval_workflow.py adminfree MyPassword123! emp1 EmployeePass123!
```

---

## Common Issues

### Issue 1: All expenses auto-approve
**Cause**: Auto-approval policies are active
**Solution**: This is expected behavior. Expenses matching policy criteria auto-approve.
**To test manual approval**: Submit an expense with a higher amount (>$1000)

### Issue 2: "You cannot approve your own expense"
**Cause**: Logged in as the same user who submitted
**Solution**: Use two different accounts (emp1 submits, adminfree approves)

### Issue 3: Expense not in pending queue
**Possible causes**:
- Auto-approved (check "All Expenses" tab)
- Wrong organization selected
- Database sync issue (refresh page)

---

## Expected Behavior Summary

| Action | User | Expected Result |
|--------|------|-----------------|
| Submit expense | emp1 | Appears in pending OR auto-approved |
| View pending | adminfree | Sees emp1's expense |
| Approve expense | adminfree | Status → APPROVED, Transaction ID generated |
| Reject expense | adminfree | Status → REJECTED, reason visible |
| Approve own expense | emp1 | ERROR: "Cannot approve your own expense" |

---

## Database Verification

To check expense status in database:

```bash
cd backend
.venv/Scripts/python.exe -c "
from src.database import SessionLocal
from src.models import Expense

db = SessionLocal()
expenses = db.query(Expense).order_by(Expense.created_at.desc()).limit(5).all()

print('Recent expenses:')
for e in expenses:
    print(f'{e.id[:8]}... | {e.vendor:20} | ${e.amount:7.2f} | {e.status}')
db.close()
"
```

---

## Next Steps

After successful testing:
1. ✓ Confirm approval workflow works
2. ✓ Verify Free tier limit (2 users) is enforced
3. Test billing dashboard shows correct limits
4. Try adding a 3rd user (should fail with upgrade prompt)
