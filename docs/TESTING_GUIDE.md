# AP2 Expense Management Agent - Testing Guide

**Last Updated**: October 12, 2025
**Application Version**: 1.0.0

## Table of Contents

1. [Quick Start](#quick-start)
2. [Test Users](#test-users)
3. [Manual Testing Scenarios](#manual-testing-scenarios)
4. [API Testing](#api-testing)
5. [Frontend Testing](#frontend-testing)
6. [AP2 Protocol Testing](#ap2-protocol-testing)
7. [Security Testing](#security-testing)
8. [Performance Testing](#performance-testing)
9. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

- Backend running on `http://localhost:8000`
- Frontend running on `http://localhost:5173`
- Database initialized and migrated

### Starting the Application

```bash
# Terminal 1 - Backend
cd backend
.venv\Scripts\activate
uvicorn src.api:app --reload --port 8000

# Terminal 2 - Frontend
cd frontend
npm run dev
```

### Access URLs

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

---

## Test Users

### Admin User (Full Access)

```
Username: admintest
Password: Admin123!
Email: admin@test.com
Role: ADMIN
```

**Permissions**:
- ✅ View all expenses from all users
- ✅ Approve/reject expense requests
- ✅ Access admin dashboard
- ✅ View all reports and analytics
- ✅ Manage users and organizations
- ✅ Access billing and subscription data

### Employee User (Standard Access)

```
Username: emptest
Password: Employee123!
Email: employee@test.com
Role: EMPLOYEE
```

**Permissions**:
- ✅ Submit new expenses
- ✅ View own expenses
- ✅ Edit pending expenses
- ✅ Withdraw pending expenses
- ✅ Upload receipts
- ✅ Export own expense reports
- ❌ Cannot approve/reject expenses
- ❌ Cannot view other users' expenses

### Additional Test Users

```
Username: testuser
Email: test@test.com
Role: EMPLOYEE
Status: Active, Unverified

Username: newuser123
Email: newuser@example.com
Role: EMPLOYEE
Status: Active, Unverified
```

**Note**: Set passwords for additional users using the admin panel or password reset flow.

---

## Manual Testing Scenarios

### Scenario 1: Employee Expense Submission Flow

**Objective**: Test the complete employee expense workflow from submission to approval.

**Steps**:

1. **Login as Employee**
   - Navigate to http://localhost:5173
   - Username: `emptest`
   - Password: `Employee123!`
   - Click "Login"
   - ✅ Verify: Redirected to Employee Dashboard

2. **Submit New Expense**
   - Click "Submit Expense" button
   - Fill in expense details:
     - **Amount**: 125.50
     - **Vendor**: Starbucks Coffee
     - **Category**: Meals
     - **Description**: Team meeting breakfast
   - Click "Submit"
   - ✅ Verify: Success message appears
   - ✅ Verify: Expense appears in "Active Expenses" tab with status "Pending"

3. **Upload Receipt**
   - Find the newly submitted expense
   - Click "Receipt" button
   - Drag and drop a receipt image or click to browse
   - ✅ Verify: Upload progress shows
   - ✅ Verify: Receipt preview appears
   - ✅ Verify: Success message confirms upload

4. **Edit Pending Expense**
   - Find the expense in "Active Expenses"
   - Click "Edit" button
   - Change amount to 135.75
   - Update description
   - Click "Save Changes"
   - ✅ Verify: Changes saved successfully
   - ✅ Verify: Updated values display correctly

5. **Logout as Employee**
   - Click user menu (top-right)
   - Click "Logout"
   - ✅ Verify: Redirected to login page

6. **Login as Admin**
   - Username: `admintest`
   - Password: `Admin123!`
   - ✅ Verify: Redirected to Admin Dashboard

7. **View Pending Expenses**
   - Navigate to "Pending Expenses" section
   - ✅ Verify: Employee's expense appears in the list
   - ✅ Verify: Employee name and email displayed
   - ✅ Verify: Amount, vendor, category correct

8. **Approve Expense**
   - Find the employee's expense
   - Click "Approve" button
   - Confirm approval in dialog
   - ✅ Verify: Success message appears
   - ✅ Verify: Expense status changes to "Approved"
   - ✅ Verify: Expense moves to "History" tab
   - ✅ Verify: Transaction ID generated

9. **Verify AP2 Audit Trail**
   - Click on the approved expense
   - Click "View Audit Trail" button
   - ✅ Verify: Three mandates present:
     - **Intent Mandate**: Employee's submission
     - **Cart Mandate**: Expense added to cart
     - **Payment Mandate**: Admin's approval
   - ✅ Verify: All timestamps recorded
   - ✅ Verify: Transaction ID matches

10. **Logout as Admin**
    - Logout and return to login page

11. **Login as Employee Again**
    - Login with employee credentials
    - ✅ Verify: Approved expense in "History" tab
    - ✅ Verify: Status shows "Approved"
    - ✅ Verify: Approver name displayed

**Expected Result**: Complete expense lifecycle from submission to approval with AP2 audit trail.

---

### Scenario 2: Expense Rejection Flow

**Objective**: Test expense rejection and employee notification.

**Steps**:

1. **Login as Employee** (`emptest`)
2. **Submit Expense**
   - Amount: 5000.00
   - Vendor: Luxury Hotel
   - Category: Travel
   - Description: Weekend stay
3. **Login as Admin** (`admintest`)
4. **Reject Expense**
   - Find the expense in pending list
   - Click "Reject" button
   - Enter rejection reason: "Exceeds policy limits. Please resubmit with itemized breakdown."
   - Click "Confirm Rejection"
   - ✅ Verify: Status changes to "Rejected"
   - ✅ Verify: Rejection reason saved
5. **Login as Employee**
   - Check "History" tab
   - ✅ Verify: Rejected expense appears
   - ✅ Verify: Rejection reason visible
   - ✅ Verify: Cannot edit rejected expense

**Expected Result**: Expense rejected with reason, employee can view rejection details.

---

### Scenario 3: Expense Withdrawal

**Objective**: Test employee ability to withdraw pending expenses.

**Steps**:

1. **Login as Employee** (`emptest`)
2. **Submit Expense**
   - Amount: 50.00
   - Vendor: Uber
   - Category: Transportation
   - Description: Airport ride
3. **Withdraw Expense**
   - Find expense in "Active Expenses"
   - Click "Withdraw" button
   - Confirm withdrawal
   - ✅ Verify: Expense removed from active list
   - ✅ Verify: Success message appears
4. **Check History**
   - Navigate to "History" tab
   - ✅ Verify: Withdrawn expense not shown (filtered out)

**Expected Result**: Employee can withdraw pending expenses before approval.

---

### Scenario 4: Export Functionality

**Objective**: Test CSV and PDF export features.

**Steps**:

1. **Login as Employee** with multiple expenses
2. **Export as CSV**
   - Click "Export" button in header
   - Select "CSV" format
   - Click "Download CSV"
   - ✅ Verify: CSV file downloads
   - ✅ Verify: Open in Excel - all expenses present
   - ✅ Verify: Columns: Date, Vendor, Amount, Category, Status, Description
3. **Export as PDF**
   - Click "Export" button
   - Select "PDF" format
   - Click "Download PDF"
   - ✅ Verify: PDF file downloads
   - ✅ Verify: Open PDF - formatted expense report
   - ✅ Verify: Summary statistics present
   - ✅ Verify: Expense details table formatted

**Expected Result**: Both CSV and PDF exports contain accurate expense data.

---

### Scenario 5: Multi-Tab Management

**Objective**: Test Active/History tab functionality.

**Steps**:

1. **Login as Employee**
2. **Active Tab**
   - ✅ Verify: Shows only PENDING expenses
   - ✅ Verify: Edit/Receipt/Withdraw buttons present
3. **History Tab**
   - ✅ Verify: Shows APPROVED and REJECTED expenses
   - ✅ Verify: No action buttons (read-only)
   - ✅ Verify: Approval/rejection info displayed
4. **Submit New Expense**
   - ✅ Verify: Immediately appears in Active tab
5. **Get Expense Approved**
   - Login as admin and approve
   - Return to employee dashboard
   - ✅ Verify: Expense moved from Active to History
   - ✅ Verify: Real-time update (or after refresh)

**Expected Result**: Tabs correctly filter expenses by status with appropriate actions.

---

### Scenario 6: Password Change

**Objective**: Test password change functionality.

**Steps**:

1. **Login as Employee**
2. **Navigate to Password Change**
   - Click user menu
   - Click "Change Password"
3. **Change Password**
   - Enter current password: `Employee123!`
   - Enter new password: `NewPassword456!`
   - Confirm new password: `NewPassword456!`
   - Click "Change Password"
   - ✅ Verify: Success message
4. **Logout**
5. **Login with New Password**
   - Username: `emptest`
   - Password: `NewPassword456!`
   - ✅ Verify: Login successful
6. **Reset Password Back** (for continued testing)
   - Change password back to `Employee123!`

**Expected Result**: Password change works, new password required for subsequent logins.

---

## API Testing

### Using cURL

#### 1. Login (Get Access Token)

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admintest",
    "password": "Admin123!"
  }'
```

**Expected Response**:
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "abc123...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "email": "admin@test.com",
    "username": "admintest",
    "full_name": "Admin Test User",
    "role": "admin",
    "is_active": true
  }
}
```

#### 2. Submit Expense (Employee)

```bash
# First, login as employee and get token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"emptest","password":"Employee123!"}' \
  | jq -r '.access_token')

# Submit expense
curl -X POST http://localhost:8000/api/v1/expenses \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "user_id": "employee-id-here",
    "amount": 75.50,
    "vendor": "Office Depot",
    "category": "office_supplies",
    "description": "Printer paper and pens"
  }'
```

#### 3. Get All Pending Expenses (Admin)

```bash
# Login as admin
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admintest","password":"Admin123!"}' \
  | jq -r '.access_token')

# Get pending expenses
curl -X GET http://localhost:8000/api/v1/expenses/all-pending \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

#### 4. Approve Expense (Admin)

```bash
curl -X POST http://localhost:8000/api/v1/expenses/approve \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "expense_id": "expense-id-here",
    "approver_id": "admin-id-here"
  }'
```

#### 5. Get Expense Report (Employee)

```bash
curl -X GET http://localhost:8000/api/v1/expenses/report \
  -H "Authorization: Bearer $TOKEN"
```

#### 6. Get AP2 Audit Trail

```bash
curl -X GET http://localhost:8000/api/v1/audit/{transaction_id} \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Using Postman

1. **Import Collection**:
   - Create new collection: "AP2 Expense Agent"
   - Set base URL variable: `{{base_url}}` = `http://localhost:8000`

2. **Setup Environment**:
   - Variable: `access_token` (set from login response)
   - Variable: `base_url` = `http://localhost:8000`

3. **Test Requests**:
   - POST `/api/v1/auth/login` - Login
   - POST `/api/v1/expenses` - Submit expense
   - GET `/api/v1/expenses/all-pending` - Get pending (admin)
   - POST `/api/v1/expenses/approve` - Approve expense
   - GET `/api/v1/expenses/report` - Get report

---

## Frontend Testing

### Component Testing Checklist

#### Login Component
- [ ] Username and password fields present
- [ ] Validation errors display for empty fields
- [ ] Invalid credentials show error message
- [ ] Successful login redirects to dashboard
- [ ] "Forgot Password" link works
- [ ] Loading state during authentication
- [ ] Remember me checkbox (if present)

#### Employee Dashboard
- [ ] Active/History tabs present
- [ ] Submit Expense button visible
- [ ] Export button in header
- [ ] Expense list displays correctly
- [ ] Pagination works (if applicable)
- [ ] Filter/search functionality
- [ ] Real-time status updates

#### Expense Submission Form
- [ ] All fields present (Amount, Vendor, Category, Description)
- [ ] Category dropdown populated
- [ ] Form validation (required fields, amount > 0)
- [ ] Success/error messages display
- [ ] Form clears after submission
- [ ] Cancel button works

#### Receipt Upload Component
- [ ] Drag-and-drop area visible
- [ ] File browser opens on click
- [ ] File type validation (images, PDF)
- [ ] File size validation (max 5MB)
- [ ] Upload progress indicator
- [ ] Preview after upload
- [ ] Error handling for invalid files

#### Admin Dashboard
- [ ] Pending expenses table
- [ ] Approve/Reject buttons
- [ ] User information displayed
- [ ] Status filter dropdown
- [ ] Total amount calculation
- [ ] Expense count badges
- [ ] Export all expenses option

#### Expense Export Component
- [ ] Format selection (CSV/PDF)
- [ ] Export summary shows counts
- [ ] Download triggers correctly
- [ ] Files contain correct data
- [ ] Formatting preserved

---

## AP2 Protocol Testing

### Three-Mandate Verification

**Test Objective**: Verify complete AP2 compliance with all three mandates.

**Steps**:

1. **Submit Expense** (Intent Mandate)
   - Login as employee
   - Submit expense
   - Record expense ID

2. **Approve Expense** (Cart + Payment Mandates)
   - Login as admin
   - Approve the expense
   - Record transaction ID

3. **Verify Audit Trail**
   - Call API: `GET /api/v1/audit/{transaction_id}`
   - ✅ **Verify Intent Mandate**:
     ```json
     {
       "mandate_type": "intent",
       "user_id": "employee-id",
       "timestamp": "2025-10-12T10:00:00Z",
       "amount": 125.50,
       "vendor": "Starbucks Coffee",
       "status": "declared"
     }
     ```
   - ✅ **Verify Cart Mandate**:
     ```json
     {
       "mandate_type": "cart",
       "expense_id": "expense-id",
       "timestamp": "2025-10-12T10:00:05Z",
       "items": [...],
       "status": "pending_approval"
     }
     ```
   - ✅ **Verify Payment Mandate**:
     ```json
     {
       "mandate_type": "payment",
       "approver_id": "admin-id",
       "timestamp": "2025-10-12T10:05:00Z",
       "amount": 125.50,
       "status": "approved"
     }
     ```

4. **Verify Immutability**
   - Attempt to modify audit records
   - ✅ Verify: Audit records cannot be changed
   - ✅ Verify: All timestamps preserved
   - ✅ Verify: Complete chain of custody

**Expected Result**: All three mandates present, timestamped, and immutable.

---

## Security Testing

### Authentication Security

#### Test 1: Brute Force Protection

```bash
# Attempt 6 failed logins
for i in {1..6}; do
  curl -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"admintest","password":"WrongPassword"}'
  sleep 1
done
```

**Expected**: Account locked after 5 attempts, returns 423 Locked status.

#### Test 2: Token Expiration

```bash
# Get token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admintest","password":"Admin123!"}' \
  | jq -r '.access_token')

# Use immediately (should work)
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/auth/me

# Wait 1 hour + 1 minute
sleep 3661

# Use expired token (should fail)
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/auth/me
```

**Expected**: Token expires after 1 hour, returns 401 Unauthorized.

#### Test 3: Authorization Checks

```bash
# Login as employee
EMP_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"emptest","password":"Employee123!"}' \
  | jq -r '.access_token')

# Attempt to access admin endpoint
curl -H "Authorization: Bearer $EMP_TOKEN" \
  http://localhost:8000/api/v1/expenses/all-pending
```

**Expected**: Returns 403 Forbidden (employee cannot access admin endpoints).

### Input Validation

#### Test 1: SQL Injection Attempt

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin'\''--",
    "password": "anything"
  }'
```

**Expected**: Login fails, no SQL error exposed.

#### Test 2: XSS Prevention

```bash
curl -X POST http://localhost:8000/api/v1/expenses \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "amount": 100,
    "vendor": "<script>alert(\"XSS\")</script>",
    "category": "meals",
    "description": "Test"
  }'
```

**Expected**: Script tags escaped/sanitized in response and storage.

---

## Performance Testing

### Load Testing with Apache Bench

```bash
# Test login endpoint
ab -n 1000 -c 10 -p login.json -T application/json \
  http://localhost:8000/api/v1/auth/login

# Test expense submission (requires auth)
ab -n 500 -c 5 -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/expenses/report
```

**Metrics to Monitor**:
- Requests per second
- Mean response time
- 95th percentile response time
- Failed requests (should be 0%)

**Expected Performance**:
- Login: >100 req/sec, <100ms response
- Expense queries: >200 req/sec, <50ms response
- Expense submission: >50 req/sec, <200ms response

---

## Troubleshooting

### Issue: Cannot Login

**Symptoms**: Login fails with correct credentials

**Solutions**:
1. Check backend is running: `curl http://localhost:8000/health`
2. Verify database migrations: `cd backend && alembic current`
3. Check user exists: `cd backend && python check_users_and_expenses.py`
4. Reset password using script above
5. Check for account lockout (wait 30 minutes or reset in DB)

### Issue: Frontend Not Loading

**Symptoms**: http://localhost:5173 shows error or blank page

**Solutions**:
1. Check frontend process: `tasklist | findstr node`
2. Restart frontend: `cd frontend && npm run dev`
3. Clear browser cache and reload
4. Check console for errors (F12)
5. Verify API connection in browser network tab

### Issue: Expenses Not Appearing

**Symptoms**: Submitted expenses don't show in dashboard

**Solutions**:
1. Check browser console for errors
2. Verify API response: Open Network tab, check `/api/v1/expenses/report`
3. Check filter/tab selection (Active vs History)
4. Verify expense status in database
5. Refresh page

### Issue: Receipt Upload Fails

**Symptoms**: Receipt upload shows error or doesn't complete

**Solutions**:
1. Check file size (must be <5MB)
2. Verify file type (JPEG, PNG, GIF, PDF only)
3. Check backend logs for upload errors
4. Ensure storage directory writable
5. Test with smaller image

### Issue: Export Not Working

**Symptoms**: Export button doesn't download file

**Solutions**:
1. Check popup blocker settings
2. Verify browser download permissions
3. Check if expenses exist to export
4. Try different format (CSV vs PDF)
5. Check browser console for JavaScript errors

---

## Test Results Documentation

### Test Execution Template

```
Test Date: _______________
Tester: _______________
Environment: Development / Staging / Production

| Scenario | Status | Issues Found | Notes |
|----------|--------|--------------|-------|
| Scenario 1: Employee Expense Flow | ☐ Pass ☐ Fail | | |
| Scenario 2: Expense Rejection | ☐ Pass ☐ Fail | | |
| Scenario 3: Expense Withdrawal | ☐ Pass ☐ Fail | | |
| Scenario 4: Export Functionality | ☐ Pass ☐ Fail | | |
| Scenario 5: Multi-Tab Management | ☐ Pass ☐ Fail | | |
| Scenario 6: Password Change | ☐ Pass ☐ Fail | | |
| API Tests | ☐ Pass ☐ Fail | | |
| Security Tests | ☐ Pass ☐ Fail | | |
| Performance Tests | ☐ Pass ☐ Fail | | |

Critical Issues Found: _____
Medium Issues Found: _____
Low Issues Found: _____

Overall Status: ☐ Ready for Deployment ☐ Needs Fixes
```

---

## Next Steps After Testing

1. **Document all issues** found during testing
2. **Prioritize bugs** by severity (Critical, High, Medium, Low)
3. **Create GitHub issues** for tracking
4. **Fix critical bugs** before deployment
5. **Re-test** after fixes
6. **Update documentation** based on findings
7. **Prepare deployment checklist**

---

**For additional support or questions, contact the development team.**
