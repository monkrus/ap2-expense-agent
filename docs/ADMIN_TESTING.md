# Admin Dashboard Testing Guide

This document provides comprehensive step-by-step testing procedures for all Admin dashboard functionality.

## Table of Contents
1. [Login & Authentication](#1-login--authentication)
2. [Dashboard Overview](#2-dashboard-overview)
3. [Pending Expense Requests](#3-pending-expense-requests)
4. [My Expenses (Admin's Personal Expenses)](#4-my-expenses-admins-personal-expenses)
5. [User Management](#5-user-management)
6. [Receipt Management](#6-receipt-management)
7. [Search, Filter & Sort](#7-search-filter--sort)
8. [Security & Permissions](#8-security--permissions)

---

## 1. Login & Authentication

### Test 1.1: Admin Login
**Steps:**
1. Navigate to the login page
2. Enter admin credentials:
   - Username: `admintest`
   - Password: `AgentTest!!`
3. Click "Sign In"

**Expected Results:**
- ✓ Login successful
- ✓ Redirected to Admin dashboard
- ✓ Admin interface loads with all sections visible

### Test 1.2: Session Persistence
**Steps:**
1. Log in as admin
2. Refresh the page (F5)

**Expected Results:**
- ✓ Session maintained
- ✓ No re-login required
- ✓ Dashboard state preserved

### Test 1.3: Logout
**Steps:**
1. Click logout button
2. Try accessing admin URL directly

**Expected Results:**
- ✓ Logged out successfully
- ✓ Redirected to login page
- ✓ Cannot access admin dashboard without login

---

## 2. Dashboard Overview

### Test 2.1: Statistics Cards
**Steps:**
1. Log in as admin
2. View the statistics cards at the top

**Expected Results:**
- ✓ "Total Pending" shows count of pending expenses
- ✓ "Approved This Month" shows count with green styling
- ✓ "Rejected This Month" shows count with red styling
- ✓ "Total Amount" shows sum in USD format ($X,XXX.XX)
- ✓ All statistics update in real-time

### Test 2.2: Refresh Button
**Steps:**
1. Click the "Refresh" button (↻ icon)
2. Observe the dashboard

**Expected Results:**
- ✓ All data refreshes from server
- ✓ Statistics update
- ✓ Pending requests reload
- ✓ My Expenses reload
- ✓ Brief loading indicator appears

---

## 3. Pending Expense Requests

### Test 3.1: View Pending Requests
**Steps:**
1. Locate "Pending Expense Requests" section
2. Verify it displays all pending expenses from all users

**Expected Results:**
- ✓ Section shows all pending expenses (from all employees)
- ✓ Each expense card shows:
  - Expense ID
  - Employee name (submitter)
  - Amount in USD
  - Category
  - Date
  - Description
  - Vendor
- ✓ Cards sorted by date (newest first)
- ✓ Vertical scrolling enabled (max-height: 700px)

### Test 3.2: Approve Expense
**Steps:**
1. Find a pending expense
2. Click the green "Approve" button
3. Observe the result

**Expected Results:**
- ✓ Success notification appears
- ✓ Expense removed from pending list
- ✓ Statistics update (Total Pending decreases, Approved This Month increases)
- ✓ Employee receives notification (if logged in)

### Test 3.3: Reject Expense
**Steps:**
1. Find a pending expense
2. Click the red "Reject" button
3. Enter rejection reason in modal
4. Click "Reject Expense"

**Expected Results:**
- ✓ Modal appears with text area for reason
- ✓ Success notification appears
- ✓ Expense removed from pending list
- ✓ Statistics update (Total Pending decreases, Rejected This Month increases)
- ✓ Rejection reason stored with expense

### Test 3.4: View Expense Details
**Steps:**
1. Click on an expense card to expand details
2. Review all information

**Expected Results:**
- ✓ Full expense details visible
- ✓ Transaction ID shown (if available)
- ✓ Receipt count badge visible (if receipts uploaded)
- ✓ All metadata displayed correctly

### Test 3.5: Empty State
**Steps:**
1. Approve/reject all pending expenses
2. View the pending section

**Expected Results:**
- ✓ "No pending expenses" message displays
- ✓ Section remains visible but empty
- ✓ No errors occur

---

## 4. My Expenses (Admin's Personal Expenses)

### Test 4.1: View Active Expenses
**Steps:**
1. Click "Active" tab in My Expenses section
2. Review the table

**Expected Results:**
- ✓ Shows only admin's pending expenses
- ✓ Table displays columns: #, Date, Category, Vendor, Description, Amount, Receipts, Actions
- ✓ Rows numbered (1, 2, 3...)
- ✓ Amounts formatted with commas ($1,234.56)
- ✓ Receipt count badge shown if receipts exist

### Test 4.2: View History
**Steps:**
1. Click "History" tab
2. Review approved/rejected expenses

**Expected Results:**
- ✓ Shows admin's approved and rejected expenses
- ✓ Status badges colored correctly (green=approved, red=rejected)
- ✓ Same table format as Active tab
- ✓ Actions disabled/hidden for historical expenses

### Test 4.3: Create New Expense
**Steps:**
1. Click "+ New Expense" button
2. Fill in the form:
   - Amount: `125.50`
   - Category: Select "Office Supplies"
   - Vendor: `Staples`
   - Description: `Printer ink and paper`
   - Date: Select today's date
3. Click "Submit"

**Expected Results:**
- ✓ Modal appears with form
- ✓ Form validation works (required fields)
- ✓ Amount accepts decimals (0.01 step)
- ✓ Date picker works correctly
- ✓ Success notification on submit
- ✓ New expense appears in Active tab
- ✓ Modal closes automatically
- ✓ Statistics update

### Test 4.4: Edit Expense
**Steps:**
1. Find a pending expense in Active tab
2. Click edit icon (pencil)
3. Modify fields:
   - Change amount to `150.00`
   - Change description
4. Click "Update"

**Expected Results:**
- ✓ Edit modal appears pre-filled with current data
- ✓ All fields editable
- ✓ Can only edit pending expenses
- ✓ Changes save successfully
- ✓ Table updates immediately
- ✓ Success notification appears

### Test 4.5: Delete/Withdraw Expense
**Steps:**
1. Find a pending expense
2. Click delete icon (trash)
3. Confirm deletion

**Expected Results:**
- ✓ Confirmation modal appears
- ✓ Expense removed from Active tab
- ✓ Success notification appears
- ✓ Cannot delete approved/rejected expenses

### Test 4.6: Upload Receipt
**Steps:**
1. Find an expense (pending or approved)
2. Click "Upload" button or receipt count badge
3. Select image file (JPG, PNG, PDF)
4. Click "Upload Receipt"

**Expected Results:**
- ✓ Upload modal appears
- ✓ File selector accepts images and PDFs
- ✓ Upload progress shown
- ✓ Receipt count badge updates (+1)
- ✓ Success notification appears
- ✓ Multiple receipts can be uploaded

### Test 4.7: View Receipts
**Steps:**
1. Find expense with receipts (receipt count > 0)
2. Click the receipt count badge
3. View receipt list modal

**Expected Results:**
- ✓ Modal shows all receipts for that expense
- ✓ Each receipt shows filename and upload date
- ✓ "View" button opens receipt in new tab
- ✓ "Delete" button removes receipt
- ✓ Modal updates in real-time

### Test 4.8: Search Expenses
**Steps:**
1. Type in search box: `office`
2. Observe filtered results

**Expected Results:**
- ✓ Table filters to show matching expenses
- ✓ Searches in: vendor, description, category
- ✓ Search is case-insensitive
- ✓ Results update as you type
- ✓ Clear search shows all expenses again

### Test 4.9: Filter by Category
**Steps:**
1. Click "All Categories" dropdown
2. Select "Travel"

**Expected Results:**
- ✓ Table shows only Travel expenses
- ✓ Active and History tabs both filter
- ✓ Search still works with filter active
- ✓ "All Categories" shows all expenses again

### Test 4.10: Sort Expenses
**Steps:**
1. Click "Sort by" dropdown
2. Try each sort option:
   - Newest First
   - Oldest First
   - Highest Amount
   - Lowest Amount

**Expected Results:**
- ✓ Newest First: Recent expenses at top
- ✓ Oldest First: Old expenses at top
- ✓ Highest Amount: $1000 before $100
- ✓ Lowest Amount: $10 before $100
- ✓ Sort persists when switching tabs
- ✓ Sort works with active filters

### Test 4.11: Pagination
**Steps:**
1. Create 20+ expenses
2. View pagination controls
3. Navigate pages

**Expected Results:**
- ✓ Shows 10 expenses per page
- ✓ Page numbers display correctly
- ✓ "Previous" and "Next" buttons work
- ✓ Current page highlighted
- ✓ Vertical scrolling within page
- ✓ Page resets when filtering/searching

---

## 5. User Management

### Test 5.1: Access User Management
**Steps:**
1. Click "Manage Users" tab or button
2. View user list

**Expected Results:**
- ✓ User management interface appears
- ✓ Shows all users in system
- ✓ Displays: Name, Email, Username, Role, Department, Status

### Test 5.2: Create New User
**Steps:**
1. Click "+ Create User" button
2. Fill in form:
   - Email: `newuser@company.com`
   - Username: `newuser`
   - Full Name: `New Test User`
   - Password: `Test123!`
   - Role: Select "Employee"
   - Department: `Engineering`
3. Click "Create User"

**Expected Results:**
- ✓ Modal appears with empty form
- ✓ Password validation shows requirements
- ✓ Role dropdown works
- ✓ User created successfully
- ✓ Success notification appears
- ✓ User appears in user list
- ✓ Modal closes automatically
- ✓ **Cannot create duplicate username/email**

### Test 5.3: Edit User
**Steps:**
1. Find a user
2. Click edit icon
3. Modify:
   - Full Name: `Updated Name`
   - Department: `Sales`
4. Click "Update"

**Expected Results:**
- ✓ Edit modal appears pre-filled
- ✓ Can edit: Full Name, Department
- ✓ Cannot edit: Email, Username (read-only)
- ✓ Changes save successfully
- ✓ User list updates immediately

### Test 5.4: Change User Role
**Steps:**
1. Find an employee
2. Click role dropdown or edit
3. Change role to "Manager"
4. Confirm change

**Expected Results:**
- ✓ Role updates successfully
- ✓ User's permissions change immediately
- ✓ Success notification appears
- ✓ Cannot change own role

### Test 5.5: Suspend User
**Steps:**
1. Find an active user
2. Click "Suspend" button
3. Confirm suspension

**Expected Results:**
- ✓ Confirmation modal appears
- ✓ User status changes to "Suspended"
- ✓ Status badge turns red
- ✓ User row dims/grays out
- ✓ Warning banner shows on user row
- ✓ Success message: "User suspended successfully. They will be logged out on their next action."

### Test 5.6: Verify Suspended User - Login Prevention
**Steps:**
1. Suspend a user account
2. **In incognito/private window**: Try to log in as that user

**Expected Results:**
- ✓ Login fails with error: "User account is inactive"
- ✓ Error displayed in red alert box
- ✓ User cannot access system

### Test 5.7: Verify Suspended User - Auto-Logout
**Steps:**
1. Log in as regular employee
2. **In another tab/window**: Admin suspends that employee
3. **Back in employee tab**: Click any button (view expenses, create expense, etc.)

**Expected Results:**
- ✓ Error notification: "Your account has been suspended. Please contact your administrator."
- ✓ User automatically logged out
- ✓ Page reloads to login screen
- ✓ Session cleared
- ✓ **User cannot continue working**

### Test 5.8: Activate Suspended User
**Steps:**
1. Find suspended user (red "Suspended" badge)
2. Click "Activate" button
3. Confirm activation

**Expected Results:**
- ✓ User status changes to "Active"
- ✓ Status badge turns green
- ✓ User row returns to normal styling
- ✓ Warning banner disappears
- ✓ User can log in again immediately
- ✓ Success notification appears

### Test 5.9: Delete User
**Steps:**
1. Find a user to delete
2. Click delete icon (trash)
3. Confirm deletion

**Expected Results:**
- ✓ Confirmation modal appears
- ✓ Warning about permanent deletion
- ✓ User removed from system
- ✓ Cannot delete yourself
- ✓ Cannot delete users with active expenses (optional)

### Test 5.10: Search Users
**Steps:**
1. Type in search box
2. Try searching by:
   - Name: `Test`
   - Email: `@gmail`
   - Username: `emp`

**Expected Results:**
- ✓ Filters users in real-time
- ✓ Searches all displayed fields
- ✓ Case-insensitive search

### Test 5.11: Filter Users by Role
**Steps:**
1. Click role filter dropdown
2. Select "Employee"
3. Try other roles

**Expected Results:**
- ✓ Shows only users with selected role
- ✓ "All Roles" shows everyone
- ✓ Count updates

### Test 5.12: View User Permissions
**Steps:**
1. Click "View Permissions" on a user
2. Review permission list

**Expected Results:**
- ✓ Modal shows all permissions for that role
- ✓ Permissions clearly listed
- ✓ Read-only display

---

## 6. Receipt Management

### Test 6.1: Upload Receipt to Expense
**Steps:**
1. Go to any expense (pending or approved)
2. Click "Upload" button
3. Select file: `receipt.jpg` (< 5MB)
4. Click "Upload Receipt"

**Expected Results:**
- ✓ File upload works
- ✓ Accepts: JPG, PNG, PDF
- ✓ Progress indicator shows
- ✓ Receipt count increments
- ✓ Success notification appears

### Test 6.2: Upload Multiple Receipts
**Steps:**
1. Upload first receipt
2. Upload second receipt to same expense
3. Upload third receipt

**Expected Results:**
- ✓ Each receipt uploads independently
- ✓ Receipt count badge shows correct total (e.g., "3")
- ✓ All receipts stored and linked to expense

### Test 6.3: View Receipt List
**Steps:**
1. Click receipt count badge (e.g., "2")
2. View modal with receipt list

**Expected Results:**
- ✓ Modal shows all receipts for that expense
- ✓ Each receipt shows:
  - Filename
  - Upload date/time
  - File size
- ✓ View and Delete buttons visible

### Test 6.4: View Receipt
**Steps:**
1. In receipt list, click "View" button
2. Receipt opens in new tab

**Expected Results:**
- ✓ Receipt opens in new browser tab
- ✓ Image displays correctly
- ✓ PDF renders properly
- ✓ Can download from browser

### Test 6.5: Delete Receipt
**Steps:**
1. In receipt list, click "Delete" button
2. Confirm deletion

**Expected Results:**
- ✓ Confirmation prompt appears
- ✓ Receipt removed from list
- ✓ Receipt count decrements
- ✓ Success notification appears
- ✓ Modal updates immediately

### Test 6.6: Receipt Upload Validation
**Steps:**
1. Try uploading:
   - File > 5MB
   - Wrong file type (.exe, .txt)
   - Corrupted image

**Expected Results:**
- ✓ Large files rejected with error
- ✓ Invalid file types rejected
- ✓ Clear error messages shown
- ✓ Upload button disabled for invalid files

---

## 7. Search, Filter & Sort

### Test 7.1: Global Search
**Steps:**
1. Use search box in each section
2. Type partial matches
3. Test special characters

**Expected Results:**
- ✓ Real-time filtering
- ✓ Case-insensitive
- ✓ Searches relevant fields
- ✓ No lag or delay
- ✓ Clear search resets results

### Test 7.2: Category Filter
**Steps:**
1. Test category dropdown
2. Select each category:
   - Travel
   - Meals
   - Office Supplies
   - Software
   - Other

**Expected Results:**
- ✓ Shows only selected category
- ✓ Works in both Active and History tabs
- ✓ Combines with search
- ✓ "All Categories" shows everything

### Test 7.3: Status Filter (History Tab)
**Steps:**
1. Go to History tab
2. Filter by:
   - Approved
   - Rejected
   - All

**Expected Results:**
- ✓ Shows only selected status
- ✓ Status badges match filter
- ✓ Combines with other filters

### Test 7.4: Sort Options
**Steps:**
1. Test all sort options:
   - Date (Newest/Oldest)
   - Amount (Highest/Lowest)
   - Category (A-Z)
   - Vendor (A-Z)

**Expected Results:**
- ✓ Correct sort order applied
- ✓ Stable sorting (consistent results)
- ✓ Works with filters active
- ✓ Dropdown shows current selection

### Test 7.5: Combined Filters
**Steps:**
1. Apply search: `office`
2. Apply category filter: `Office Supplies`
3. Apply sort: `Highest Amount`

**Expected Results:**
- ✓ All filters work together
- ✓ Results match all criteria
- ✓ Correct items displayed
- ✓ Proper sort order maintained

---

## 8. Security & Permissions

### Test 8.1: Admin-Only Access
**Steps:**
1. Log in as employee
2. Try to access admin features

**Expected Results:**
- ✓ Cannot see user management
- ✓ Cannot see all pending expenses (only own)
- ✓ Cannot approve others' expenses
- ✓ Admin routes return 403

### Test 8.2: Token Expiration
**Steps:**
1. Log in as admin
2. Wait for token to expire (or clear token manually)
3. Perform action

**Expected Results:**
- ✓ Token auto-refreshes
- ✓ Action completes successfully
- ✓ No re-login required
- ✓ If refresh fails, redirects to login

### Test 8.3: Session Management
**Steps:**
1. Log in on two different browsers
2. Logout from one
3. Check the other

**Expected Results:**
- ✓ Both sessions independent
- ✓ Logout in one doesn't affect other
- ✓ Both can work simultaneously

### Test 8.4: Cannot Modify Own Status
**Steps:**
1. As admin, try to:
   - Suspend yourself
   - Change your own role
   - Delete your own account

**Expected Results:**
- ✓ Actions blocked with error
- ✓ Warning message shown
- ✓ Cannot demote/remove self

### Test 8.5: Audit Trail
**Steps:**
1. Perform various actions:
   - Approve expense
   - Suspend user
   - Create expense
2. Check audit logs (if implemented)

**Expected Results:**
- ✓ All actions logged
- ✓ Includes: user, action, timestamp
- ✓ Cannot delete audit logs

---

## 9. Edge Cases & Error Handling

### Test 9.1: Network Errors
**Steps:**
1. Disconnect internet
2. Try to perform actions
3. Reconnect

**Expected Results:**
- ✓ Clear error messages
- ✓ No data loss
- ✓ Retry mechanism works
- ✓ UI remains responsive

### Test 9.2: Concurrent Modifications
**Steps:**
1. Open expense in two tabs
2. Edit in both tabs
3. Save both

**Expected Results:**
- ✓ Last save wins (or conflict detection)
- ✓ No data corruption
- ✓ User notified of conflict

### Test 9.3: Invalid Data
**Steps:**
1. Try entering:
   - Negative amounts
   - Future dates
   - Empty required fields
   - Special characters in names

**Expected Results:**
- ✓ Validation catches errors
- ✓ Clear error messages
- ✓ Cannot submit invalid data
- ✓ Form highlights errors

### Test 9.4: Large Datasets
**Steps:**
1. Create 100+ expenses
2. Create 50+ users
3. Test pagination and performance

**Expected Results:**
- ✓ Pagination works smoothly
- ✓ No performance degradation
- ✓ Search still fast
- ✓ No browser freezing

---

## 10. UI/UX Testing

### Test 10.1: Visual Consistency
**Verification Points:**
- ✓ All buttons use theme colors (indigo-600, green-600, red-600)
- ✓ Icons consistent throughout
- ✓ Spacing and padding uniform
- ✓ Fonts and sizes match design
- ✓ Status badges colored correctly (green=approved, red=rejected, yellow=pending)

### Test 10.2: Responsive Design
**Steps:**
1. Resize browser window
2. Test on different screen sizes
3. Check mobile view

**Expected Results:**
- ✓ Layout adapts to screen size
- ✓ No horizontal scrolling
- ✓ Touch-friendly on mobile
- ✓ Readable on all devices

### Test 10.3: Loading States
**Verification Points:**
- ✓ Spinners show during data fetch
- ✓ Buttons disable during processing
- ✓ "Loading..." messages clear
- ✓ No content flashing

### Test 10.4: Notifications
**Verification Points:**
- ✓ Success toasts appear (green)
- ✓ Error toasts appear (red)
- ✓ Toasts auto-dismiss after 3-5 seconds
- ✓ Multiple toasts stack properly
- ✓ Messages are clear and actionable

---

## 11. Browser Compatibility

### Test on Multiple Browsers:
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Edge (latest)
- [ ] Safari (latest)

**Verify:**
- ✓ All features work
- ✓ Layout correct
- ✓ No console errors
- ✓ Performance acceptable

---

## Testing Checklist Summary

### Critical Features
- [ ] Admin can log in
- [ ] Approve pending expenses
- [ ] Reject pending expenses with reason
- [ ] Create new expense
- [ ] Edit pending expense
- [ ] Delete pending expense
- [ ] Upload receipts
- [ ] View receipt list
- [ ] Create new user (with unique username/email)
- [ ] Edit user details
- [ ] Change user role
- [ ] Suspend user account
- [ ] Verify suspended user cannot log in
- [ ] Verify logged-in suspended user is auto-logged out
- [ ] Activate suspended user
- [ ] Delete user
- [ ] Search functionality
- [ ] Filter by category
- [ ] Sort options work
- [ ] Pagination works
- [ ] Statistics update in real-time

### Security Features
- [ ] Session persistence
- [ ] Token auto-refresh
- [ ] Logout works correctly
- [ ] Cannot modify own account critically
- [ ] Role-based access control
- [ ] Suspended users locked out immediately

### User Experience
- [ ] Loading indicators appear
- [ ] Success notifications show
- [ ] Error messages clear
- [ ] Form validation works
- [ ] No console errors
- [ ] Responsive design
- [ ] Visual consistency

---

## Known Issues to Test For

1. **Username Already Taken**: When creating a user, verify that duplicate usernames show clear error: "Username already taken"
2. **Suspended User Feedback**: Verify that suspending a user shows proper success message and visual feedback
3. **Auto-Logout**: Confirm that suspended users who are logged in get automatically logged out on their next action
4. **Receipt Count**: Ensure receipt count badge updates immediately after upload/delete
5. **Pagination Reset**: Verify pagination resets to page 1 when applying filters

---

## Reporting Issues

When reporting bugs, include:
1. **Steps to reproduce**
2. **Expected result**
3. **Actual result**
4. **Browser and version**
5. **Screenshots/recordings**
6. **Console errors** (F12 → Console tab)
7. **User role** (admin/employee)

---

## Test Data

### Sample Admin Account
- Username: `admintest`
- Password: `AgentTest!`
- Role: Admin

### Sample Test Users
Create test users with different roles:
- Employee: `testemployee` / `Test123!`
- Manager: `testmanager` / `Test123!`

### Sample Expenses
Create expenses with various:
- Categories: Travel, Meals, Office Supplies, Software
- Amounts: $10, $100, $1000, $5000
- Dates: Past, today, this month
- Statuses: Pending, Approved, Rejected

---

**End of Admin Testing Guide**

Last Updated: October 24, 2025
