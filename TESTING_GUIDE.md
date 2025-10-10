# Expense System Testing Guide

## 🚀 Servers Running

- **Backend**: http://127.0.0.1:8000
- **Frontend**: http://localhost:5174
- **API Docs**: http://127.0.0.1:8000/docs

---

## 👥 Test Users

### Employee User 1: testuser
- **Email**: `test@test.com`
- **Password**: (your password for testuser)
- **Role**: EMPLOYEE
- **Current Expenses**: 2 (both approved)

### Employee User 2: emptest
- **Email**: `employee@test.com`
- **Password**: (your password for emptest)
- **Role**: EMPLOYEE
- **Current Expenses**: 3 (2 approved, 1 rejected)

### Admin User: admintest
- **Email**: `admin@test.com`
- **Password**: (your password for admintest)
- **Role**: ADMIN
- **Can**: Approve/reject all expenses, view all user expenses

---

## 🧪 Test Scenarios

### Test 1: Employee Submits New Expense

**Objective**: Verify expense submission and immediate database sync

**Steps**:
1. Open http://localhost:5174
2. Login as **testuser** (`test@test.com`)
3. Navigate to the expense submission form
4. Fill in expense details:
   - **Vendor**: "Sync Test Co"
   - **Amount**: 999.99
   - **Category**: "Travel"
   - **Description**: "Testing real-time sync - testuser submission"
5. Click "Submit Expense"
6. **Expected**:
   - Success message appears
   - Expense appears in **Active** tab immediately
   - Status shows "PENDING"

---

### Test 2: Admin Sees Pending Request Immediately

**Objective**: Verify real-time sync between employee submission and admin view

**Steps**:
1. **Without logging out testuser**, open a new browser window (or incognito)
2. Go to http://localhost:5174
3. Login as **admintest** (`admin@test.com`)
4. Navigate to Admin Dashboard
5. Check pending requests section
6. **Expected**:
   - "Testing real-time sync - testuser submission" appears
   - Shows submitter as "testuser" or "test@test.com"
   - Amount shows $999.99
   - Status is "PENDING"

**Verification**: The expense submitted in Test 1 should be visible immediately without page refresh (or with a single refresh)

---

### Test 3: Admin Approves and Both Views Update

**Objective**: Verify approval workflow and history sync

**Steps**:
1. As **admintest**, find the pending expense from Test 1
2. Click "Approve" button
3. **Expected in Admin View**:
   - Expense disappears from "Active/Pending" tab
   - Expense appears in "History" tab
   - Status shows "APPROVED"
   - Shows who approved it (admintest)
   - Shows approval timestamp

4. Switch back to **testuser** window
5. Refresh the page or navigate to History tab
6. **Expected in Employee View**:
   - Expense no longer in "Active" tab
   - Expense now in "History" tab with status "APPROVED"
   - Shows approval details

---

### Test 4: Second Employee Submits Different Expense

**Objective**: Verify user separation and that admin sees both users' expenses

**Steps**:
1. Logout and login as **emptest** (`employee@test.com`)
2. Submit a new expense:
   - **Vendor**: "Another Vendor Ltd"
   - **Amount**: 555.55
   - **Category**: "Meals"
   - **Description**: "Testing user separation - emptest submission"
3. **Expected**:
   - Expense appears in emptest's Active tab
   - emptest can see own 4 expenses total now (3 old + 1 new)
   - emptest **cannot** see testuser's expenses

4. Switch to **admintest** window
5. Check Admin Dashboard
6. **Expected**:
   - Admin sees both testuser's AND emptest's expenses
   - Can filter by user
   - Can see all pending requests from both users

---

### Test 5: Rejection Workflow

**Objective**: Verify rejection and reason tracking

**Steps**:
1. As **admintest**, find emptest's pending expense
2. Click "Reject" button
3. Enter rejection reason: "Insufficient documentation"
4. Submit rejection
5. **Expected in Admin View**:
   - Expense moves to History
   - Status shows "REJECTED"
   - Rejection reason is visible

6. Login as **emptest**
7. Check History tab
8. **Expected**:
   - Rejected expense visible
   - Can see rejection reason
   - Cannot resubmit or modify

---

### Test 6: Withdraw Pending Expense

**Objective**: Verify employee can withdraw own pending expense

**Steps**:
1. As **testuser**, submit another expense:
   - **Description**: "Test withdrawal - will be withdrawn"
   - **Amount**: 111.11
2. Before admin processes it, click "Withdraw" button
3. **Expected**:
   - Expense status changes to "WITHDRAWN"
   - Disappears from Active tab
   - Admin no longer sees it in pending queue

---

## 🔍 Database Monitoring

During testing, you can monitor the database in real-time:

```bash
python check_users_and_expenses.py
```

This will show:
- All users and their expenses
- Current pending requests
- What admin should see
- Sync verification

---

## ✅ Success Criteria

- [ ] Employee can submit expenses
- [ ] Submissions appear immediately in database
- [ ] Admin sees all pending requests from all users
- [ ] Admin can approve expenses
- [ ] Approval updates both admin and user views
- [ ] Admin can reject with reason
- [ ] Rejection reason visible to user
- [ ] Employee can withdraw own pending expenses
- [ ] Users only see own expenses
- [ ] Admin sees all user expenses
- [ ] History tab shows processed expenses (approved/rejected)
- [ ] Active tab shows only pending expenses

---

## 🐛 Common Issues

### Issue: "Not authorized" error
- **Solution**: Make sure you're logged in as correct user role
- Admin features require ADMIN/MANAGER/ACCOUNTANT role

### Issue: Expense not appearing
- **Solution**: Refresh the page, check browser console for errors
- Verify backend is running on port 8000

### Issue: Can't login
- **Solution**: Check credentials, passwords are case-sensitive
- Use the monitoring script to verify user exists

---

## 📊 Expected Final State After All Tests

**testuser**: 3-4 expenses (2 original approved + 1-2 new from tests)
**emptest**: 4 expenses (3 original + 1 new, some approved/rejected)
**admintest**: Can view all 7-8 total expenses from all users

Run `python check_users_and_expenses.py` to verify!
