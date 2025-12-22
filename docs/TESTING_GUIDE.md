# AP2 Expense Management Agent - Testing Guide

**Last Updated**: November 7, 2025
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
Username: adminfree
Password: Testme1!
Email: adminfree@example.com
Role: ADMIN
```

**Permissions**:
- ✅ View all expenses from all users
- ✅ Approve/reject expense requests
- ✅ Access admin dashboard
- ✅ View all reports and analytics
- ✅ Manage users and organizations
- ✅ Access billing and subscription data

### Additional Roles (Optional)

Only `adminfree` is seeded by default. If you need manager/employee/accountant flows, create users via the admin UI or `/api/v1/admin/users/create` and use them in the steps below. For role-specific steps, substitute those users wherever this guide references a non-admin login.

Suggested examples:
- Manager: `manager1` / `Testme1!`
- Employee: `employee1` / `Testme1!`
- Employee 2: `employee2` / `Testme1!`

**Note**: The database is automatically seeded with `adminfree` on startup.


---

## 🧪 Comprehensive Manual Testing Checklist

**Purpose**: Complete end-to-end testing of all features including new Phase 2-4 features (Recurring Expenses, Batch Upload, Budget Management).

**Estimated Time**: 60-90 minutes
**Prerequisites**: Application running on localhost:5173, all test users created

---

### Phase 1: Basic Login & Navigation ✅

**Objective**: Verify authentication and role-based dashboard access.

**Test Steps**:

1. **Admin Login**
   - [ ] Navigate to http://localhost:5173
   - [ ] Login with `adminfree` / `Testme1!`
   - [ ] ✅ Verify dashboard loads successfully
   - [ ] ✅ Verify all admin tabs are visible:
     - Pending Approvals
     - All Expenses
     - Archived
     - User Management
     - Billing & Usage
     - AI Assistant
     - Recurring
     - **Budgets** (NEW!)
   - [ ] ✅ Logout successfully

2. **Manager Login**
   - [ ] Login with `adminfree` / `Testme1!`
   - [ ] ✅ Verify manager dashboard has tabs:
     - Active Expenses
     - History
     - AI Assistant
     - **Recurring** (NEW!)
     - **Budgets** (NEW! - Read-only)
   - [ ] ✅ Verify no admin-only tabs visible
   - [ ] ✅ Logout successfully

3. **Employee Login**
   - [ ] Login with `adminfree` / `Testme1!`
   - [ ] ✅ Verify employee dashboard has tabs:
     - Active Expenses
     - History
     - AI Assistant
     - **Recurring** (NEW!)
     - **Budgets** (NEW! - Read-only)
   - [ ] ✅ Logout successfully

**Expected Results**: All roles can login, see appropriate tabs, no unauthorized access.

---

### Phase 2: Test NEW Feature - Recurring Expenses 🆕

**Objective**: Test recurring expense template creation, management, and scheduling.

**Test as Employee** (`adminfree` or `adminfree`):

1. **Create Recurring Template**
   - [ ] Click "Recurring" tab
   - [ ] Click "Create Recurring Expense" button
   - [ ] Fill out form:
     - **Vendor**: AWS
     - **Amount**: 99.99
     - **Category**: Software
     - **Frequency**: Monthly
     - **Description**: AWS hosting costs
     - **Auto-submit**: ON (toggle enabled)
     - **Next run date**: Today's date
   - [ ] Click "Submit"
   - [ ] ✅ Verify: Success message appears
   - [ ] ✅ Verify: Template appears in list
   - [ ] ✅ Verify: Shows "Active" status
   - [ ] ✅ Verify: Stats show correct count

2. **Pause Template**
   - [ ] Find the AWS template in list
   - [ ] Click "Pause" button
   - [ ] ✅ Verify: Status changes to "Paused"
   - [ ] ✅ Verify: Pause button changes to "Resume"

3. **Resume Template**
   - [ ] Click "Resume" button on paused template
   - [ ] ✅ Verify: Status changes back to "Active"
   - [ ] ✅ Verify: Resume button changes to "Pause"

4. **Edit Template**
   - [ ] Click "Edit" icon (pencil) on template
   - [ ] Change amount to: 149.99
   - [ ] Update description
   - [ ] Click "Save"
   - [ ] ✅ Verify: Changes saved successfully
   - [ ] ✅ Verify: Updated amount displays in list

5. **Create Additional Templates**
   - [ ] Create 2-3 more templates with different frequencies:
     - Weekly template (Office supplies)
     - Quarterly template (Software license)
   - [ ] ✅ Verify: All templates show in list
   - [ ] ✅ Verify: Stats update correctly

6. **Delete Template**
   - [ ] Click "Delete" icon (trash) on one template
   - [ ] Confirm deletion in dialog
   - [ ] ✅ Verify: Template removed from list
   - [ ] ✅ Verify: Stats update

**Expected Results**:
- ✅ Templates created successfully
- ✅ List shows templates with correct stats
- ✅ Pause/Resume works correctly
- ✅ Edit updates template
- ✅ Delete removes template
- ⚠️ **Known Limitation**: Auto-submission requires scheduler (may not work without background worker)

---

### Phase 3: Test NEW Feature - Batch Receipt Upload 🆕

**Objective**: Test multi-file upload with AI extraction and bulk expense creation.

**Test as Employee** (`adminfree` or `adminfree`):

1. **Open Batch Upload**
   - [ ] Go to "Active Expenses" tab
   - [ ] Click purple "Batch Upload" button
   - [ ] ✅ Verify: Upload modal/page opens
   - [ ] ✅ Verify: Drag-drop area visible
   - [ ] ✅ Verify: File browser button present

2. **Upload Multiple Receipts**
   - [ ] Drag and drop 2-3 receipt images (JPG/PNG)
     - Or click to browse and select files
   - [ ] ✅ Verify: Files appear in upload list
   - [ ] ✅ Verify: File names and sizes shown
   - [ ] ✅ Verify: Preview thumbnails visible (if applicable)

3. **Extract Data with AI**
   - [ ] Click "Upload & Extract Data" button
   - [ ] Wait 5-10 seconds for processing
   - [ ] ✅ Verify: Loading indicator shows
   - [ ] ✅ Verify: Extracted data appears for each receipt:
     - Vendor name
     - Amount
     - Category
     - Confidence score
   - [ ] ⚠️ **If GOOGLE_API_KEY not set**:
     - Fields may be empty/default values
     - Can still manually fill and create expenses

4. **Edit Extracted Data**
   - [ ] Click "Edit" on one receipt
   - [ ] Modify the vendor name
   - [ ] Update amount if needed
   - [ ] Click "Save"
   - [ ] ✅ Verify: Changes reflected in preview

5. **Create Individual Expense**
   - [ ] Click "Create" button on single receipt
   - [ ] ✅ Verify: Expense created successfully
   - [ ] ✅ Verify: Receipt removed from batch list
   - [ ] Go to "Active Expenses" tab
   - [ ] ✅ Verify: New expense appears with attached receipt

6. **Create All Expenses (Bulk)**
   - [ ] Return to batch upload (upload more receipts if needed)
   - [ ] Click "Create All Expenses" button
   - [ ] ✅ Verify: All receipts converted to expenses
   - [ ] ✅ Verify: Success message shows count
   - [ ] Go to "Active Expenses" tab
   - [ ] ✅ Verify: All new expenses appear in list

**Expected Results**:
- ✅ Batch upload modal/page opens
- ✅ Multiple files upload successfully
- ⚠️ AI extraction may fail without GOOGLE_API_KEY
  - Without API key: Can still manually fill fields
  - With API key: Auto-extraction works
- ✅ Edit functionality works
- ✅ Individual and bulk creation works
- ✅ Receipts attached to created expenses

---

### Phase 4: Test NEW Feature - Budget Management 🆕

**Objective**: Test budget creation, monitoring, alerts, and role-based access control.

**Test as Admin** (`adminfree`):

1. **View Budget Dashboard**
   - [ ] Click "Budgets" tab
   - [ ] ✅ Verify: Stats cards display:
     - Total Budgets (count)
     - Total Budget Amount ($)
     - Total Spent ($)
     - Budget Status breakdown (On Track/Warning/Critical/Exceeded)
   - [ ] ✅ Verify: Budget list/table visible
   - [ ] ✅ Verify: Filter buttons present
   - [ ] ✅ Verify: "Create Budget" button visible (admin only)

2. **Create Organization-Wide Budget**
   - [ ] Click "Create Budget"
   - [ ] Fill out form:
     - **Name**: Q4 2024 Marketing
     - **Description**: Marketing budget for Q4
     - **Amount**: 50000
     - **Period**: Quarterly
     - **Category**: (Leave blank for all categories)
     - **User**: (Leave blank for organization-wide)
     - **Warning Threshold**: 75%
     - **Critical Threshold**: 90%
     - **Start Date**: Today's date
   - [ ] Click "Create Budget"
   - [ ] ✅ Verify: Success message
   - [ ] ✅ Verify: Budget appears in list
   - [ ] ✅ Verify: Shows correct details:
     - Progress bar at 0% (or based on existing expenses)
     - Status: "ON TRACK" (green badge)
     - Remaining amount shown
     - Period and dates displayed

3. **Create Category-Specific Budget**
   - [ ] Click "Create Budget"
   - [ ] Fill form:
     - **Name**: Software Subscriptions
     - **Amount**: 10000
     - **Period**: Monthly
     - **Category**: Software (select from dropdown)
     - Leave user blank
   - [ ] Create budget
   - [ ] ✅ Verify: Budget created with category filter
   - [ ] ✅ Verify: Only expenses in "Software" category count toward this budget

4. **Create User-Specific Budget**
   - [ ] Create another budget:
     - **Name**: John's Travel Budget
     - **Amount**: 5000
     - **Period**: Monthly
     - **User**: Select `adminfree` from dropdown
   - [ ] ✅ Verify: Budget created
   - [ ] ✅ Verify: Only adminfree's expenses count toward this budget

5. **Create Small Test Budget** (for Phase 5 testing)
   - [ ] Create budget:
     - **Name**: Test Alert Budget
     - **Amount**: 100
     - **Period**: Monthly
     - **Start Date**: Today
   - [ ] ✅ Verify: Created successfully
   - [ ] Note: Will use this in Phase 5 to test status changes

6. **Edit Budget**
   - [ ] Click "Edit" icon on a budget
   - [ ] Change amount to: 12000
   - [ ] Update description
   - [ ] Click "Save"
   - [ ] ✅ Verify: Changes saved
   - [ ] ✅ Verify: Updated values display

7. **Test Filters**
   - [ ] Click status filter buttons:
     - "All"
     - "On Track"
     - "Warning"
     - "Critical"
     - "Exceeded"
   - [ ] ✅ Verify: List filters correctly based on budget status
   - [ ] Toggle "Active only" checkbox
   - [ ] ✅ Verify: Shows/hides inactive budgets

8. **View Budget Details**
   - [ ] Click on a budget row to expand/view details
   - [ ] ✅ Verify: Detailed view shows:
     - Full description
     - Spending breakdown
     - Associated expenses list
     - Timeline/history

**Test as Manager/Employee** (`adminfree` or `adminfree`):

9. **Verify Read-Only Access**
   - [ ] Logout as admin
   - [ ] Login as `adminfree`
   - [ ] Go to "Budgets" tab
   - [ ] ✅ Verify: Can VIEW budgets
   - [ ] ✅ Verify: Stats display correctly
   - [ ] ✅ Verify: Budget list visible
   - [ ] ✅ Verify: NO "Create Budget" button (read-only)
   - [ ] ✅ Verify: NO Edit/Delete buttons visible
   - [ ] ✅ Verify: Can view budget details but not modify

**Expected Results**:
- ✅ Budget creation works (admin only)
- ✅ Stats calculated correctly
- ✅ Progress bars display and update
- ✅ Status colors correct (green/yellow/orange/red)
- ✅ Edit/Delete work (admin only)
- ✅ Filters work correctly
- ✅ Real-time spending calculation
- ✅ Employees/Managers have read-only access

---

### Phase 5: Test Budget Status Changes & Alerts 🎯

**Objective**: Verify budget alert thresholds trigger correctly and status colors update in real-time.

**Prerequisites**: "Test Alert Budget" created in Phase 4 with $100 limit.

**Test as Employee** (`adminfree` or `adminfree`):

1. **Check Initial State**
   - [ ] Go to "Budgets" tab
   - [ ] Find "Test Alert Budget" ($100)
   - [ ] ✅ Verify: Status is "ON TRACK" (green)
   - [ ] ✅ Verify: Progress bar at 0%
   - [ ] ✅ Verify: Remaining: $100

2. **Submit First Expense (50% Usage)**
   - [ ] Go to "Active Expenses"
   - [ ] Create expense:
     - Amount: $50
     - Vendor: Test Vendor 1
     - Category: (match budget category if set)
   - [ ] Submit expense
   - [ ] **Have admin approve it** (or if auto-approved, wait)
   - [ ] Return to "Budgets" tab
   - [ ] ✅ Verify: Progress bar now at 50%
   - [ ] ✅ Verify: Status still "ON TRACK" (green) - below 75% threshold
   - [ ] ✅ Verify: Remaining: $50

3. **Submit Second Expense (80% Usage - WARNING)**
   - [ ] Create another expense:
     - Amount: $30
     - Vendor: Test Vendor 2
   - [ ] Submit and get it approved
   - [ ] Check "Budgets" tab
   - [ ] ✅ Verify: Progress bar at 80%
   - [ ] ✅ Verify: Status changed to "WARNING" (yellow/amber badge)
   - [ ] ✅ Verify: Remaining: $20
   - [ ] ✅ Verify: Alert notification may appear

4. **Submit Third Expense (95% Usage - CRITICAL)**
   - [ ] Create expense:
     - Amount: $15
     - Vendor: Test Vendor 3
   - [ ] Submit and get approved
   - [ ] Check "Budgets" tab
   - [ ] ✅ Verify: Progress bar at 95%
   - [ ] ✅ Verify: Status changed to "CRITICAL" (orange badge)
   - [ ] ✅ Verify: Remaining: $5
   - [ ] ✅ Verify: Critical alert notification

5. **Submit Fourth Expense (105% Usage - EXCEEDED)**
   - [ ] Create expense:
     - Amount: $10
     - Vendor: Test Vendor 4
   - [ ] Submit and get approved
   - [ ] Check "Budgets" tab
   - [ ] ✅ Verify: Progress bar at 105% (may show as 100% full + indicator)
   - [ ] ✅ Verify: Status changed to "EXCEEDED" (red badge)
   - [ ] ✅ Verify: Remaining: -$5 (over budget)
   - [ ] ✅ Verify: Exceeded alert notification

6. **Verify Alert History**
   - [ ] Click on the budget to view details
   - [ ] Look for "Alerts" or "History" section
   - [ ] ✅ Verify: Alert history shows:
     - Warning alert at 80%
     - Critical alert at 95%
     - Exceeded alert at 105%
   - [ ] ✅ Verify: Timestamps recorded
   - [ ] ✅ Verify: Percentage at time of alert shown

**Expected Results**:
- ✅ Budget status updates in real-time (or after page refresh)
- ✅ Progress bar fills up correctly
- ✅ Status colors change correctly:
  - **0-74%**: Green "ON TRACK"
  - **75-89%**: Yellow/Amber "WARNING"
  - **90-99%**: Orange "CRITICAL"
  - **100%+**: Red "EXCEEDED"
- ✅ Percentage shown accurately
- ✅ Remaining amount calculates correctly (including negative for over-budget)
- ✅ Alerts triggered at correct thresholds
- ✅ Alert history recorded

---

### Phase 6: Test Notifications 🔔

**Objective**: Verify notification center displays alerts and mark-as-read functionality works.

**Test as any user**:

1. **Locate Notification Center**
   - [ ] Look for bell icon in top-right corner of dashboard
   - [ ] ✅ Verify: Bell icon visible
   - [ ] ✅ Verify: Unread count badge displayed (if notifications exist)

2. **View Notifications**
   - [ ] Click bell icon
   - [ ] ✅ Verify: Notification dropdown/panel opens
   - [ ] ✅ Verify: Shows list of notifications
   - [ ] ✅ Verify: Unread notifications highlighted/bolded
   - [ ] ✅ Verify: Notification types visible:
     - Expense approvals/rejections
     - Budget alerts
     - System notifications
   - [ ] ✅ Verify: Timestamps show (e.g., "5 minutes ago")

3. **Read Notification**
   - [ ] Click on an unread notification
   - [ ] ✅ Verify: Notification opens/expands
   - [ ] ✅ Verify: Full details displayed
   - [ ] ✅ Verify: Styling changes to show as "read"

4. **Mark as Read**
   - [ ] Find "Mark as read" button/link on notification
   - [ ] Click it
   - [ ] ✅ Verify: Notification marked as read
   - [ ] ✅ Verify: Unread count badge decreases
   - [ ] ✅ Verify: Notification moves to "Read" section (if separate)

5. **Mark All as Read**
   - [ ] Look for "Mark all as read" button
   - [ ] Click it
   - [ ] ✅ Verify: All notifications marked as read
   - [ ] ✅ Verify: Badge count goes to 0 or disappears
   - [ ] ✅ Verify: No unread notifications highlighted

6. **Notification Persistence**
   - [ ] Close notification panel
   - [ ] Refresh page
   - [ ] Open notification panel again
   - [ ] ✅ Verify: Read/unread status persists
   - [ ] ✅ Verify: Badge count accurate after refresh

7. **Test Budget Alert Notifications** (if Phase 5 completed)
   - [ ] Check for budget alert notifications from Phase 5
   - [ ] ✅ Verify: Warning, Critical, and Exceeded alerts appear
   - [ ] ✅ Verify: Clear notification text ("Budget 'Test Alert Budget' has exceeded 75% threshold")
   - [ ] ✅ Verify: Click notification navigates to budget page (if applicable)

**Expected Results**:
- ✅ Notification center visible and accessible
- ✅ Unread count badge shows correct number
- ✅ Dropdown/panel works smoothly
- ✅ Mark as read functionality works
- ✅ Notifications persist across sessions
- ✅ Budget alerts appear as notifications
- ✅ Different notification types distinguishable

---

## Test Completion Checklist

After completing all phases, verify:

- [ ] All Phase 1 tests passed (Login & Navigation)
- [ ] All Phase 2 tests passed (Recurring Expenses)
- [ ] All Phase 3 tests passed (Batch Receipt Upload)
- [ ] All Phase 4 tests passed (Budget Management)
- [ ] All Phase 5 tests passed (Budget Status Changes)
- [ ] All Phase 6 tests passed (Notifications)
- [ ] No critical bugs found
- [ ] Performance acceptable (page loads <2 seconds)
- [ ] No console errors in browser
- [ ] All user roles tested
- [ ] Documented any issues found

**Overall Testing Status**: ☐ Pass ☐ Fail ☐ Pass with Minor Issues

---

## Manual Testing Scenarios

### Scenario 1: Employee Expense Submission Flow

**Objective**: Test the complete employee expense workflow from submission to approval.

**Steps**:

1. **Login as Employee**
   - Navigate to http://localhost:5173
   - Username: `adminfree`
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
   - Username: `adminfree`
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

1. **Login as Employee** (`adminfree`)
2. **Submit Expense**
   - Amount: 5000.00
   - Vendor: Luxury Hotel
   - Category: Travel
   - Description: Weekend stay
3. **Login as Admin** (`adminfree`)
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

1. **Login as Employee** (`adminfree`)
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
   - Username: `adminfree`
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
    "username": "adminfree",
    "password": "Testme1!"
  }'
```

**Expected Response**:
```json
{
  "access_token": "<ACCESS_TOKEN>",
  "refresh_token": "<REFRESH_TOKEN>",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "email": "admin@test.com",
    "username": "adminfree",
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
  -d '{"username":"adminfree","password":"Testme1!"}' \
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
  -d '{"username":"adminfree","password":"Testme1!"}' \
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
    -d '{"username":"adminfree","password":"WrongPassword"}'
  sleep 1
done
```

**Expected**: Account locked after 5 attempts, returns 423 Locked status.

#### Test 2: Token Expiration

```bash
# Get token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"adminfree","password":"Admin123!"}' \
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
  -d '{"username":"adminfree","password":"Employee123!"}' \
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
