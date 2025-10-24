# Admin Dashboard Testing Guide

**Last Updated:** October 24, 2025
**Version:** 2.0

This document provides comprehensive step-by-step testing procedures for the Admin Dashboard functionality in the Expense Management System.

## Table of Contents
1. [Login & Authentication](#1-login--authentication)
2. [Dashboard Overview](#2-dashboard-overview)
3. [Pending Approvals Tab](#3-pending-approvals-tab)
4. [All Expenses Tab](#4-all-expenses-tab)
5. [User Management Tab](#5-user-management-tab)
6. [Receipt Management](#6-receipt-management)
7. [Search, Filter & Sort](#7-search-filter--sort)
8. [Security & Permissions](#8-security--permissions)
9. [Edge Cases & Error Handling](#9-edge-cases--error-handling)
10. [Testing Checklist](#10-testing-checklist)

---

## 1. Login & Authentication

### Test 1.1: Admin Login
**Steps:**
1. Navigate to `http://localhost:5173`
2. Enter admin credentials:
   - Username: `admintest`
   - Password: `AgentTest!` ⚠️ **(One exclamation mark only)**
3. Click "Sign In"

**Expected Results:**
- ✓ Login successful
- ✓ Redirected to Admin Dashboard
- ✓ Dashboard shows: Pending Approvals, All Expenses, and User Management tabs
- ✓ Header displays "Admin Dashboard" with shield icon
- ✓ Admin role badge visible

### Test 1.2: Manager Login
**Steps:**
1. Log in with manager credentials:
   - Username: `testuser`
   - Password: `AgentTest!`

**Expected Results:**
- ✓ Login successful
- ✓ Dashboard shows: Pending Approvals and All Expenses tabs
- ✓ **User Management tab NOT visible** (admin-only)
- ✓ Header displays "Manager Dashboard"

### Test 1.3: Session Persistence
**Steps:**
1. Log in as admin
2. Refresh the page (F5)

**Expected Results:**
- ✓ Session maintained
- ✓ No re-login required
- ✓ Dashboard state preserved (tab selection, filters)

### Test 1.4: Auto-Refresh
**Steps:**
1. Log in and observe the dashboard
2. Wait 10 seconds without interaction

**Expected Results:**
- ✓ Data refreshes automatically every 10 seconds
- ✓ No loading spinner during auto-refresh
- ✓ Current tab selection maintained
- ✓ Applied filters preserved

### Test 1.5: Logout
**Steps:**
1. Click "Logout" button in top-right corner
2. Try accessing admin URL directly

**Expected Results:**
- ✓ Logged out successfully
- ✓ Redirected to login page
- ✓ Cannot access admin dashboard without login
- ✓ Session cleared

---

## 2. Dashboard Overview

### Test 2.1: Dashboard Header
**Steps:**
1. Log in as admin
2. View the header section

**Expected Results:**
- ✓ Title shows "Admin Dashboard" with shield icon
- ✓ Role badge displays "ADMIN"
- ✓ Description text visible
- ✓ Three buttons present: Change Password, Refresh, Logout
- ✓ Buttons styled correctly with icons

### Test 2.2: Tab Navigation
**Steps:**
1. Click each tab:
   - Pending Approvals
   - All Expenses
   - User Management (admin only)
2. Verify tab highlighting

**Expected Results:**
- ✓ Active tab highlighted with blue underline
- ✓ Tab icons display correctly (Clock, FileText, UserCog)
- ✓ Pending Approvals shows count badge if > 0
- ✓ Tab content changes appropriately
- ✓ URL may update (if routing implemented)

### Test 2.3: Refresh Button
**Steps:**
1. Click the "Refresh" button
2. Observe the dashboard

**Expected Results:**
- ✓ Button shows "Refreshing..." during load
- ✓ All data refreshes from server
- ✓ Current tab data reloads
- ✓ Brief loading state visible
- ✓ Button disabled during refresh

### Test 2.4: Change Password
**Steps:**
1. Click "Change Password" button
2. Enter current and new passwords
3. Submit

**Expected Results:**
- ✓ Modal appears with password form
- ✓ Form validation works (required fields, password strength)
- ✓ Success notification on successful change
- ✓ Modal closes after success
- ✓ Can still use dashboard without re-login

---

## 3. Pending Approvals Tab

### Test 3.1: View Pending Statistics
**Steps:**
1. Navigate to "Pending Approvals" tab
2. View the statistics cards

**Expected Results:**
- ✓ **Pending Requests** card shows count (blue)
- ✓ **Total Amount** card shows sum in USD format with commas
- ✓ **Employees** card shows count of unique submitters
- ✓ Statistics update in real-time
- ✓ Only shows on Pending Approvals tab (not All Expenses)

### Test 3.2: View Pending Expenses List
**Steps:**
1. Locate the expense table below statistics
2. Review the displayed information

**Expected Results:**
- ✓ Table shows columns: #, Employee, Expense ID, Status, Details, Date, Amount, Approver, Actions
- ✓ Each expense displays:
  - Row number (1, 2, 3...)
  - Employee name and email
  - Expense ID (with copy button)
  - Status badge (yellow "PENDING")
  - Category, vendor, description
  - Submission date
  - Amount formatted as currency
- ✓ Expenses sorted by date (newest first by default)
- ✓ Pagination controls if > 10 expenses

### Test 3.3: Approve Expense
**Steps:**
1. Find a pending expense
2. Click the green "Approve" button in Actions column
3. Observe the result

**Expected Results:**
- ✓ Confirmation prompt: "Approve this expense?"
- ✓ Success notification: "Expense [ID] approved successfully"
- ✓ Expense removed from Pending Approvals tab
- ✓ Pending count decreases by 1
- ✓ Total amount decreases
- ✓ Can view approved expense in "All Expenses" tab
- ✓ Approver name set to current admin

### Test 3.4: Reject Expense
**Steps:**
1. Find a pending expense
2. Click the red "Reject" button
3. Modal appears with rejection reason input
4. Enter reason: "Missing receipt"
5. Click "Reject Expense"

**Expected Results:**
- ✓ Modal appears with text area for reason
- ✓ Can enter rejection reason (optional but recommended)
- ✓ Success notification appears
- ✓ Expense removed from Pending list
- ✓ Pending count decreases
- ✓ Rejection reason stored with expense
- ✓ Can view rejected expense in All Expenses tab with reason

### Test 3.5: Copy Expense ID
**Steps:**
1. Click the copy icon next to an expense ID
2. Paste into notepad

**Expected Results:**
- ✓ Icon changes to checkmark briefly
- ✓ Full expense ID copied to clipboard
- ✓ Can paste the UUID successfully

### Test 3.6: Empty State
**Steps:**
1. Approve/reject all pending expenses
2. View the Pending Approvals tab

**Expected Results:**
- ✓ "No expenses found" message displays
- ✓ Statistics show zeros
- ✓ No errors occur
- ✓ Tab remains functional

### Test 3.7: View Receipt Count
**Steps:**
1. Find expense with uploaded receipts
2. Observe the receipt count badge

**Expected Results:**
- ✓ Badge shows count (e.g., "2 📎")
- ✓ Click badge opens receipt list modal
- ✓ Can view/download receipts
- ✓ Badge color indicates receipt presence

---

## 4. All Expenses Tab

### Test 4.1: View All Expenses
**Steps:**
1. Navigate to "All Expenses" tab
2. Review the displayed expenses

**Expected Results:**
- ✓ Shows all expenses from all users (all statuses)
- ✓ Same table format as Pending tab
- ✓ Status badges colored: Green=Approved, Red=Rejected, Yellow=Pending
- ✓ No statistics cards (only on Pending tab)
- ✓ Status filter dropdown visible
- ✓ Search bar visible
- ✓ Sort controls visible
- ✓ **Clear History button visible** (admin only, red button)

### Test 4.2: Filter by Status
**Steps:**
1. Click "Status:" dropdown
2. Select each option:
   - All Statuses
   - Pending
   - Approved
   - Rejected
3. Observe filtered results

**Expected Results:**
- ✓ "All Statuses" shows everything
- ✓ "Pending" shows only yellow-badged expenses
- ✓ "Approved" shows only green-badged expenses
- ✓ "Rejected" shows only red-badged expenses
- ✓ Expense count updates
- ✓ Filter persists during auto-refresh
- ✓ Pagination resets to page 1

### Test 4.3: View Approved Expense Details
**Steps:**
1. Filter by "Approved"
2. Find an approved expense
3. Review the information

**Expected Results:**
- ✓ Status badge shows "APPROVED" (green)
- ✓ Approver name displayed in Approver column
- ✓ Approval date/time visible
- ✓ Transaction ID shown (if available, copyable)
- ✓ No action buttons (already processed)
- ✓ Can view receipts if uploaded

### Test 4.4: View Rejected Expense Details
**Steps:**
1. Filter by "Rejected"
2. Find a rejected expense
3. Review the information

**Expected Results:**
- ✓ Status badge shows "REJECTED" (red)
- ✓ Rejection reason displayed (if provided)
- ✓ Rejecter name displayed
- ✓ Rejection date/time visible
- ✓ No action buttons
- ✓ Full details preserved

### Test 4.5: Clear Expense History (Admin Only)
**Steps:**
1. Navigate to "All Expenses" tab
2. Click the red "Clear History" button in top-right
3. Confirm first warning
4. Confirm second warning

**Expected Results:**
- ✓ First confirmation: "Are you sure you want to clear ALL expense history..."
- ✓ Second confirmation: "FINAL WARNING: This will delete ALL expense records..."
- ✓ Success message shows deletion statistics
- ✓ All expenses removed (pending, approved, rejected, withdrawn)
- ✓ All receipts and files deleted
- ✓ All comments deleted
- ✓ Audit log created
- ✓ Button disabled if no expenses
- ✓ Button only visible to admin role

### Test 4.6: Search Expenses
**Steps:**
1. Enter search query: "office"
2. Try searching:
   - By vendor: "Staples"
   - By description: "supplies"
   - By category: "Travel"
   - By employee name: "Test"
   - By expense ID: "0bb24044"
   - By amount: "125"

**Expected Results:**
- ✓ Real-time filtering as you type
- ✓ Searches across: ID, vendor, description, category, amount, status, user email, user name
- ✓ Case-insensitive search
- ✓ Partial matches work
- ✓ Clear search (X button) shows all expenses
- ✓ Pagination resets to page 1
- ✓ Search works with status filter

### Test 4.7: Copy Transaction ID
**Steps:**
1. Find an approved expense with transaction ID
2. Click copy icon next to transaction ID
3. Paste into notepad

**Expected Results:**
- ✓ Icon changes to checkmark
- ✓ Transaction ID copied to clipboard
- ✓ Can paste successfully

---

## 5. User Management Tab

### Test 5.1: Access User Management
**Steps:**
1. Log in as admin
2. Click "User Management" tab

**Expected Results:**
- ✓ User list displays
- ✓ Search bar visible at top
- ✓ "Create User" button visible (green, with Plus icon)
- ✓ Table shows columns: #, Name, Email, Username, Role, Department, Status, Actions
- ✓ All users in system displayed
- ✓ Pagination if > 10 users

### Test 5.2: View User List
**Steps:**
1. Review the user list table
2. Check each column

**Expected Results:**
- ✓ Row numbers (1, 2, 3...)
- ✓ Full names displayed
- ✓ Email addresses shown
- ✓ Usernames visible
- ✓ Role badges colored correctly (Blue=Admin, Purple=Manager, Green=Employee)
- ✓ Department displayed (or "No department")
- ✓ Status badges: Green="Active", Red="Suspended"
- ✓ Action buttons: View, Edit, Delete

### Test 5.3: Create New User
**Steps:**
1. Click "+ Create User" button
2. Fill in the form:
   - Email: `newemp@company.com`
   - Username: `newemp`
   - Full Name: `New Employee Test`
   - Password: `Test123!` (must meet requirements)
   - Role: Select "Employee"
   - Department: `Engineering`
3. Click "Create User"

**Expected Results:**
- ✓ Modal appears with empty form
- ✓ Password requirements shown:
  - At least 8 characters
  - One uppercase letter
  - One lowercase letter
  - One number
  - One special character
- ✓ Password visibility toggle works
- ✓ Role dropdown has all options (Admin, Manager, Employee, Accountant)
- ✓ User created successfully
- ✓ Success message: "User created successfully"
- ✓ User appears in list immediately
- ✓ Modal closes automatically
- ✓ New user can log in immediately

### Test 5.4: Duplicate Username/Email Prevention
**Steps:**
1. Try to create user with existing username
2. Try to create user with existing email

**Expected Results:**
- ✓ Error: "Username already taken" or "Email already registered"
- ✓ Form does not submit
- ✓ User remains on modal to correct
- ✓ Clear error message displayed

### Test 5.5: Edit User
**Steps:**
1. Click "Edit" button (pencil icon) on a user
2. Modify fields:
   - Full Name: "Updated Name Test"
   - Department: "Sales"
3. Click "Save Changes"

**Expected Results:**
- ✓ Edit modal appears pre-filled with user data
- ✓ Can edit: Full Name, Email (read-only shown), Department
- ✓ **Cannot edit**: Username (disabled field)
- ✓ Can change Role via dropdown
- ✓ Can toggle Active/Suspended status with toggle switch
- ✓ Changes save successfully
- ✓ Success message appears
- ✓ User list updates immediately
- ✓ Modal closes after save

### Test 5.6: Change User Role
**Steps:**
1. Edit a user
2. Change role from "Employee" to "Manager"
3. Save changes
4. **In another browser**: Log in as that user

**Expected Results:**
- ✓ Role updates successfully in admin view
- ✓ Role badge changes color
- ✓ User's permissions change immediately
- ✓ User sees Manager dashboard on next login
- ✓ Can approve others' expenses
- ✓ Success message: "User updated successfully"

### Test 5.7: Suspend User Account
**Steps:**
1. Click "Edit" on an active user
2. Toggle the "Active" switch to OFF
3. Click "Save Changes"
4. Observe the user list

**Expected Results:**
- ✓ Warning in modal: "Suspending this user will log them out immediately..."
- ✓ User status changes to "Suspended" (red badge)
- ✓ User row may dim or show warning color
- ✓ Success message: "User suspended. They will be logged out immediately..."
- ✓ Edit button changes to "Activate"
- ✓ User cannot log in (tested separately)

### Test 5.8: Verify Suspended User Cannot Log In
**Steps:**
1. Suspend a user account
2. **In incognito/private window**: Try to log in as suspended user
3. Attempt login

**Expected Results:**
- ✓ Login fails immediately
- ✓ Error message: "User account is inactive" or "Account suspended"
- ✓ Red error alert displayed
- ✓ User cannot access system
- ✓ No dashboard loads

### Test 5.9: Verify Logged-In User Auto-Logout on Suspension
**Steps:**
1. **Browser 1**: Log in as regular employee (keep session active)
2. **Browser 2**: Admin suspends that employee's account
3. **Back in Browser 1**: Click any button (refresh, view expense, create expense)

**Expected Results:**
- ✓ Error notification: "Your account has been suspended. Please contact your administrator."
- ✓ User automatically logged out
- ✓ Redirected to login page
- ✓ Session token cleared
- ✓ Cannot perform any actions
- ✓ Must re-login (which will fail due to suspension)

### Test 5.10: Activate Suspended User
**Steps:**
1. Find a suspended user (red "Suspended" badge)
2. Click "Edit" button
3. Toggle "Active" switch to ON
4. Click "Save Changes"
5. **In another browser**: Try logging in as that user

**Expected Results:**
- ✓ Modal shows current "Suspended" state
- ✓ Toggle to Active shows green state
- ✓ Success message: "User activated. They can now log in..."
- ✓ Status badge turns green "Active"
- ✓ User row returns to normal styling
- ✓ User can log in immediately
- ✓ Full access restored

### Test 5.11: Delete User
**Steps:**
1. Click "Delete" button (trash icon) on a user
2. Confirm deletion in modal

**Expected Results:**
- ✓ Confirmation modal appears: "Delete User"
- ✓ Warning: "Are you sure you want to delete [username]?"
- ✓ Mentions "This action cannot be undone"
- ✓ User removed from system
- ✓ Success message: "User deleted successfully"
- ✓ User list updates immediately
- ✓ Cannot delete yourself (button disabled with tooltip)

### Test 5.12: Cannot Delete Self
**Steps:**
1. Attempt to delete your own admin account
2. Check delete button state

**Expected Results:**
- ✓ Delete button disabled (grayed out)
- ✓ Tooltip on hover: "Can't delete yourself"
- ✓ Click does nothing
- ✓ Modal does not open

### Test 5.13: View User Details
**Steps:**
1. Click "View" button (eye icon) on a user
2. Review the modal information

**Expected Results:**
- ✓ Modal shows full user details
- ✓ Displays: ID, Email, Username, Full Name, Role, Department, Status
- ✓ Shows account metadata: Created At, Last Login, MFA Status, Failed Login Attempts
- ✓ Permission list for that role displayed
- ✓ Read-only display (no edit fields)
- ✓ Close button works

### Test 5.14: Search Users
**Steps:**
1. Enter search query in user search box
2. Try searching:
   - By name: "Test"
   - By email: "@gmail"
   - By username: "admin"
3. Clear search

**Expected Results:**
- ✓ Real-time filtering as you type
- ✓ Searches: Name, Email, Username
- ✓ Case-insensitive
- ✓ Partial matches work
- ✓ Clear search shows all users
- ✓ Pagination resets to page 1

---

## 6. Receipt Management

### Test 6.1: Upload Receipt to Expense
**Steps:**
1. In Pending or All Expenses tab, find an expense
2. Click "Upload" button or receipt count badge
3. Select file: `receipt.jpg` (< 5MB)
4. Click "Upload Receipt"

**Expected Results:**
- ✓ Upload modal appears
- ✓ File selector accepts: JPG, JPEG, PNG, PDF
- ✓ Upload progress bar shown
- ✓ Success notification: "Receipt uploaded successfully"
- ✓ Receipt count badge increments (+1)
- ✓ Modal closes or stays open for more uploads

### Test 6.2: Upload Multiple Receipts
**Steps:**
1. Upload first receipt
2. Upload second receipt to same expense
3. Upload third receipt
4. Check receipt count

**Expected Results:**
- ✓ Each receipt uploads independently
- ✓ Receipt count badge updates after each upload
- ✓ Final count shows correct total (e.g., "3 📎")
- ✓ All receipts stored and linked to expense
- ✓ No limit on number (within reason)

### Test 6.3: View Receipt List
**Steps:**
1. Click receipt count badge on expense (e.g., "2 📎")
2. Review the modal

**Expected Results:**
- ✓ Modal opens with receipt list
- ✓ Each receipt shows:
  - Filename
  - Upload date/time (formatted)
  - View button (eye icon)
  - Delete button (trash icon)
- ✓ Receipts sorted by upload date (newest first)
- ✓ Empty state if no receipts

### Test 6.4: View Receipt
**Steps:**
1. In receipt list modal, click "View" button
2. Receipt opens in new tab

**Expected Results:**
- ✓ Receipt opens in new browser tab
- ✓ Image displays correctly (JPG, PNG)
- ✓ PDF renders in browser viewer
- ✓ Can zoom, download from browser
- ✓ Original quality maintained
- ✓ Browser back button returns to app

### Test 6.5: Delete Receipt
**Steps:**
1. In receipt list, click "Delete" button on a receipt
2. Confirm deletion

**Expected Results:**
- ✓ Confirmation prompt: "Delete this receipt?"
- ✓ Receipt removed from list immediately
- ✓ Receipt count badge decrements (-1)
- ✓ Success notification: "Receipt deleted successfully"
- ✓ Physical file deleted from server
- ✓ Modal updates in real-time
- ✓ If last receipt deleted, count badge disappears

### Test 6.6: Receipt Upload Validation
**Steps:**
1. Try uploading:
   - File > 5MB
   - Wrong file type (.exe, .txt, .docx)
   - Corrupted image file

**Expected Results:**
- ✓ Files > 5MB rejected with error: "File too large (max 5MB)"
- ✓ Invalid file types rejected: "Invalid file type"
- ✓ Clear error messages displayed
- ✓ Upload button disabled for invalid files
- ✓ Can try again with valid file
- ✓ Modal remains open

---

## 7. Search, Filter & Sort

### Test 7.1: Expense Search (All Tabs)
**Steps:**
1. Use search box in expense tabs
2. Type: "office"
3. Try partial matches: "sta" (for Staples)
4. Try special characters

**Expected Results:**
- ✓ Real-time filtering (no submit button needed)
- ✓ Case-insensitive search
- ✓ Searches: Expense ID, Vendor, Description, Category, Amount, User Name, User Email
- ✓ Partial matches work
- ✓ No lag or delay
- ✓ Clear button (X) resets to all expenses
- ✓ Search persists during auto-refresh
- ✓ Pagination resets to page 1

### Test 7.2: Status Filter (All Expenses Tab)
**Steps:**
1. Go to "All Expenses" tab
2. Change status filter dropdown
3. Select each option

**Expected Results:**
- ✓ "All Statuses" shows everything
- ✓ "Pending" filters to only pending
- ✓ "Approved" filters to only approved
- ✓ "Rejected" filters to only rejected
- ✓ Expense count updates correctly
- ✓ Works with search query
- ✓ Persists during auto-refresh

### Test 7.3: Sort Controls
**Steps:**
1. Click sort column headers or sort dropdown
2. Test each sort option:
   - Date (Newest First / Oldest First)
   - Amount (Highest / Lowest)
   - Category (A-Z)
   - Vendor (A-Z)
   - User (A-Z)
   - Status (Pending → Approved → Rejected)

**Expected Results:**
- ✓ Click header toggles sort direction
- ✓ Arrow icons show current sort (↑ or ↓)
- ✓ Correct sort order applied
- ✓ Date: Newest shows recent dates first
- ✓ Amount: Highest shows $1000 before $100
- ✓ Category/Vendor/User: Alphabetical order
- ✓ Stable sorting (ties handled consistently)
- ✓ Works with active filters
- ✓ Sort preference saved to localStorage
- ✓ Restored on page refresh

### Test 7.4: Combined Filters
**Steps:**
1. Apply search: "office"
2. Apply status filter: "Approved"
3. Apply sort: "Highest Amount"
4. Observe results

**Expected Results:**
- ✓ All filters work together
- ✓ Results match ALL criteria (AND logic)
- ✓ Only approved expenses matching "office" shown
- ✓ Sorted by highest amount first
- ✓ Correct count displayed
- ✓ No errors or conflicts
- ✓ Clear search resets only search (filter/sort remain)

### Test 7.5: Pagination
**Steps:**
1. Create 25+ expenses
2. View pagination controls
3. Navigate pages:
   - Click "Next"
   - Click "Previous"
   - Click page numbers
   - Use first/last page buttons

**Expected Results:**
- ✓ Shows 10 expenses per page
- ✓ Page numbers display (1, 2, 3...)
- ✓ Current page highlighted (blue background)
- ✓ "Previous" button disabled on page 1
- ✓ "Next" button disabled on last page
- ✓ Page range shown: "Showing 1-10 of 25"
- ✓ Pagination resets to page 1 when filtering/searching
- ✓ Smooth transitions between pages
- ✓ No duplicate or missing expenses

---

## 8. Security & Permissions

### Test 8.1: Role-Based Access Control
**Steps:**
1. Log in as different roles:
   - Admin
   - Manager
   - Employee (use EmployeeDashboard)
2. Try accessing admin features

**Expected Results:**
- ✓ **Admin**: Can see and use all tabs (Pending, All Expenses, User Management)
- ✓ **Manager**: Can see Pending and All Expenses tabs, **cannot see User Management**
- ✓ **Employee**: Only sees EmployeeDashboard, **cannot access AdminDashboard routes**
- ✓ Direct URL access to admin routes returns 403 for non-admins
- ✓ API requests return 403/401 for unauthorized roles

### Test 8.2: Cannot Modify Own Critical Settings
**Steps:**
1. As admin, try to:
   - Delete your own account
   - Suspend yourself
   - Demote your own role

**Expected Results:**
- ✓ Delete button disabled with tooltip: "Can't delete yourself"
- ✓ Suspend yourself shows warning (allowed but risky)
- ✓ Role change from Admin to Employee works but shows warning
- ✓ Cannot lock yourself out completely

### Test 8.3: Token Expiration & Refresh
**Steps:**
1. Log in as admin
2. Wait for token to near expiration (if short-lived)
3. Perform an action (approve expense)

**Expected Results:**
- ✓ Token auto-refreshes silently
- ✓ Action completes successfully
- ✓ No re-login required
- ✓ User unaware of refresh
- ✓ If refresh fails, redirects to login with error

### Test 8.4: Session Management
**Steps:**
1. Log in on two different browsers (Chrome, Firefox)
2. Perform actions in both
3. Logout from one

**Expected Results:**
- ✓ Both sessions independent
- ✓ Logout in one doesn't affect the other
- ✓ Both can work simultaneously
- ✓ Changes in one visible in other after refresh
- ✓ Each has its own refresh token

### Test 8.5: Admin Actions Audit Trail
**Steps:**
1. Perform various actions:
   - Approve expense
   - Reject expense
   - Suspend user
   - Create user
   - Delete expense history
2. Check audit logs (backend logs or DB)

**Expected Results:**
- ✓ All admin actions logged
- ✓ Includes: User ID, Action, Timestamp, Resource, Details
- ✓ Sensitive actions specially flagged
- ✓ Cannot delete audit logs via UI
- ✓ Audit logs persist even if user deleted

---

## 9. Edge Cases & Error Handling

### Test 9.1: Network Errors
**Steps:**
1. Disconnect internet
2. Try to approve an expense
3. Reconnect internet
4. Retry action

**Expected Results:**
- ✓ Clear error message: "Network error. Please check connection."
- ✓ Action fails gracefully (no data loss)
- ✓ UI remains responsive
- ✓ Retry works when connection restored
- ✓ No browser console errors (or handled)

### Test 9.2: Concurrent Modifications
**Steps:**
1. **Browser 1**: Admin 1 views a pending expense
2. **Browser 2**: Admin 2 approves the same expense
3. **Browser 1**: Admin 1 tries to approve it

**Expected Results:**
- ✓ Admin 1 gets error: "Expense already processed" or 404
- ✓ No duplicate approval
- ✓ Data integrity maintained
- ✓ Admin 1 sees updated status after refresh

### Test 9.3: Invalid Data Entry
**Steps:**
1. In user creation form, try:
   - Empty required fields
   - Weak password: "pass"
   - Invalid email: "notanemail"
   - Username with spaces
2. In expense approval, try:
   - Approve already-approved expense
   - Delete non-existent expense

**Expected Results:**
- ✓ Validation catches errors before submission
- ✓ Clear inline error messages
- ✓ Cannot submit invalid data
- ✓ Form highlights error fields (red border)
- ✓ Backend validation as backup (400 Bad Request)
- ✓ User-friendly error messages

### Test 9.4: Large Datasets
**Steps:**
1. Create 100+ expenses
2. Create 50+ users
3. Test pagination and performance
4. Apply filters and search

**Expected Results:**
- ✓ Pagination works smoothly
- ✓ No performance degradation
- ✓ Search still fast (< 500ms)
- ✓ No browser freezing or lag
- ✓ Table renders quickly
- ✓ Auto-refresh doesn't impact performance
- ✓ Memory usage stable

### Test 9.5: File Upload Edge Cases
**Steps:**
1. Upload 0-byte file
2. Upload file with very long name (>255 chars)
3. Upload file with special characters in name
4. Upload same file twice

**Expected Results:**
- ✓ 0-byte file rejected: "File is empty"
- ✓ Long filename truncated or rejected
- ✓ Special characters sanitized
- ✓ Duplicate uploads allowed (separate records)
- ✓ No file system errors

---

## 10. Testing Checklist

### Critical Features
- [ ] Admin can log in with correct credentials
- [ ] Dashboard displays three tabs (Pending, All Expenses, User Management)
- [ ] Auto-refresh every 10 seconds works
- [ ] Approve expense workflow complete
- [ ] Reject expense with reason workflow complete
- [ ] Suspend user account works
- [ ] Suspended user cannot log in
- [ ] Logged-in suspended user auto-logs out
- [ ] Activate suspended user works
- [ ] Create new user with validation
- [ ] Duplicate username/email prevented
- [ ] Delete user works (except self)
- [ ] Upload receipt to expense
- [ ] View receipt list and download
- [ ] Delete receipt
- [ ] Clear expense history works (double confirmation)
- [ ] Search expenses across all fields
- [ ] Filter by status (pending/approved/rejected)
- [ ] Sort expenses by columns
- [ ] Pagination works correctly
- [ ] Copy expense ID and transaction ID

### Security Features
- [ ] Session persistence across page refresh
- [ ] Token auto-refresh works
- [ ] Logout clears session
- [ ] Cannot modify own critical settings (delete self)
- [ ] Role-based access control enforced
- [ ] Manager cannot access User Management
- [ ] Employee cannot access AdminDashboard
- [ ] Audit trail for admin actions

### User Experience
- [ ] Loading indicators appear during actions
- [ ] Success notifications show for actions
- [ ] Error messages clear and actionable
- [ ] Form validation works and shows errors
- [ ] Modals open and close correctly
- [ ] Buttons disable during processing
- [ ] No browser console errors
- [ ] Responsive design works (test at 1024px, 1366px, 1920px)
- [ ] Visual consistency (colors, fonts, spacing)
- [ ] Icons display correctly
- [ ] Status badges colored correctly

### Edge Cases
- [ ] Network error handling
- [ ] Concurrent modification handling
- [ ] Invalid data entry prevented
- [ ] Large dataset performance acceptable
- [ ] File upload validation works
- [ ] Empty states display correctly

---

## Test Data & Credentials

### Default System Users

All default users share the same password: **`AgentTest!`** ⚠️ **(One exclamation mark only)**

#### Admin Account
- **Username**: `admintest`
- **Password**: `AgentTest!`
- **Email**: `admintest@example.com`
- **Full Name**: Admin Test User
- **Role**: Admin
- **Permissions**: Full system access
  - View all expenses (all users)
  - Approve/reject any expense
  - Create/edit/delete/suspend users
  - Access User Management tab
  - Clear expense history
  - View all audit logs

#### Manager Account
- **Username**: `testuser`
- **Password**: `AgentTest!`
- **Email**: `testuser@example.com`
- **Full Name**: Test Manager User
- **Role**: Manager
- **Permissions**: Expense approval only
  - View all expenses (all users)
  - Approve/reject any expense
  - **Cannot** access User Management
  - **Cannot** create/modify users
  - Can view own expense history

#### Employee Accounts

**Employee 1:**
- **Username**: `emptest`
- **Password**: `AgentTest!`
- **Email**: `emptest@example.com`
- **Full Name**: Employee Test 1
- **Role**: Employee
- **Permissions**: Self-service only
  - Create own expenses
  - Edit own pending expenses
  - Withdraw own pending expenses
  - View own expense history
  - Upload receipts to own expenses
  - **Cannot** approve/reject any expenses
  - **Cannot** view other users' expenses

**Employee 2:**
- **Username**: `emptest2`
- **Password**: `AgentTest!`
- **Email**: `emptest2@example.com`
- **Full Name**: Employee Test 2
- **Role**: Employee
- **Permissions**: Same as Employee 1

### Test Scenarios Quick Reference

| Scenario | User 1 | User 2 | Purpose |
|----------|--------|--------|---------|
| Admin approves employee expense | `admintest` | `emptest` | Basic approval workflow |
| Admin suspends user | `admintest` | `emptest` | User suspension testing |
| Manager approves expense | `testuser` | `emptest2` | Manager permissions |
| Employee submits expense | `emptest` | - | Employee dashboard |
| Concurrent approval attempt | `admintest` | `testuser` | Race condition testing |
| Self-approval prevention | `admintest` | `admintest` | Security testing |

### Sample Test Expenses

Create expenses with variety for comprehensive testing:

#### Low-Value Expenses ($0-$100)
- **$10.50** - Office Supplies - Staples - "Pens and notebooks"
- **$25.00** - Meals - Subway - "Team lunch"
- **$45.99** - Software - Adobe - "Monthly subscription"
- **$89.00** - Office Supplies - Amazon - "Desk accessories"

#### Medium-Value Expenses ($100-$1,000)
- **$125.00** - Travel - Uber - "Airport transportation"
- **$250.00** - Meals - Restaurant - "Client dinner meeting"
- **$450.00** - Software - Microsoft - "Office licenses"
- **$850.00** - Office Supplies - Best Buy - "Monitor and keyboard"

#### High-Value Expenses ($1,000+)
- **$1,250.00** - Travel - Delta Airlines - "Conference flight"
- **$2,500.00** - Travel - Marriott - "Hotel 5 nights"
- **$5,000.00** - Software - Salesforce - "Annual license"

#### Date Variety
- **Past**: 30 days ago, 60 days ago, 90 days ago
- **Recent**: Yesterday, 2 days ago, last week
- **Current**: Today, this week
- **Edge**: January 1st, December 31st, month boundaries

#### Status Variety
- **Pending**: Recently submitted, awaiting approval
- **Approved**: Processed by admin/manager, has approver name
- **Rejected**: Denied with rejection reason
- **Withdrawn**: Employee cancelled (rarely used)

### Creating Additional Test Users

For comprehensive testing, create these additional users via User Management:

#### Additional Admin
- **Username**: `admin2`
- **Password**: `Test123!`
- **Email**: `admin2@company.com`
- **Full Name**: Second Admin User
- **Role**: Admin
- **Purpose**: Test concurrent admin actions

#### Additional Manager
- **Username**: `manager2`
- **Password**: `Test123!`
- **Email**: `manager2@company.com`
- **Full Name**: Second Manager User
- **Role**: Manager
- **Department**: Sales
- **Purpose**: Test manager permissions and conflicts

#### Additional Employees
- **Username**: `employee3`
- **Password**: `Test123!`
- **Email**: `employee3@company.com`
- **Full Name**: Third Employee
- **Role**: Employee
- **Department**: Engineering
- **Purpose**: Bulk expense testing

---

## 11. User/Admin Interaction Scenarios

This section covers comprehensive testing scenarios involving interactions between different user roles.

### Scenario 11.1: Employee Submits → Admin Approves
**Purpose:** Test basic expense approval workflow

**Steps:**
1. **Browser 1 (Employee)**: Log in as `emptest`
2. Submit new expense:
   - Amount: $125.50
   - Category: Office Supplies
   - Vendor: Staples
   - Description: "Printer ink and paper"
   - Date: Today
3. Upload receipt (optional)
4. Note the Expense ID
5. **Browser 2 (Admin)**: Log in as `admintest`
6. Go to "Pending Approvals" tab
7. Find the expense by Employee name or ID
8. Click "Approve"
9. **Back to Browser 1 (Employee)**: Refresh or wait for auto-refresh
10. Go to "History" tab

**Expected Results:**
- ✓ Employee sees expense in "Active" tab initially (pending status)
- ✓ Admin sees expense in "Pending Approvals" tab immediately
- ✓ Admin can view full expense details
- ✓ Approval succeeds with success notification
- ✓ Employee sees expense moved to "History" tab
- ✓ Expense shows "APPROVED" badge (green)
- ✓ Approver name shows as "Admin Test User"
- ✓ Approval timestamp recorded
- ✓ Both users can view receipt if uploaded

---

### Scenario 11.2: Employee Submits → Admin Rejects
**Purpose:** Test expense rejection workflow with reason

**Steps:**
1. **Browser 1 (Employee)**: Log in as `emptest2`
2. Submit expense:
   - Amount: $500.00
   - Category: Travel
   - Vendor: Delta Airlines
   - Description: "Personal trip" (intentionally problematic)
3. **Browser 2 (Admin)**: Log in as `admintest`
4. Find the expense in "Pending Approvals"
5. Click "Reject" button
6. Enter rejection reason: "This appears to be a personal expense, not business-related. Please review company travel policy."
7. Click "Reject Expense"
8. **Back to Browser 1 (Employee)**: Refresh
9. Check "History" tab

**Expected Results:**
- ✓ Admin sees rejection modal with text area
- ✓ Can enter detailed rejection reason
- ✓ Rejection succeeds with notification
- ✓ Employee sees expense in "History" with red "REJECTED" badge
- ✓ Rejection reason displayed to employee
- ✓ Rejecter name shown
- ✓ Employee can learn from feedback
- ✓ Expense cannot be re-submitted (must create new)

---

### Scenario 11.3: Admin Suspends Employee → Employee Auto-Logout
**Purpose:** Test immediate suspension enforcement

**Steps:**
1. **Browser 1 (Employee)**: Log in as `emptest`
2. Navigate to dashboard, leave browser open
3. **Browser 2 (Admin)**: Log in as `admintest`
4. Go to "User Management" tab
5. Find user `emptest`
6. Click "Edit"
7. Toggle "Active" switch to OFF (suspend)
8. Click "Save Changes"
9. Confirm suspension message
10. **Back to Browser 1 (Employee)**: Try any action:
    - Click "New Expense"
    - Click "Refresh"
    - Click any tab

**Expected Results:**
- ✓ Admin sees success: "User emptest suspended. They will be logged out immediately..."
- ✓ User status badge turns red "Suspended"
- ✓ **In Browser 1**: Error notification appears immediately on next action
- ✓ Error message: "Your account has been suspended. Please contact your administrator."
- ✓ Employee automatically logged out
- ✓ Redirected to login page
- ✓ Session cleared
- ✓ Cannot perform any further actions
- ✓ Attempt to log in again fails with "Account suspended" error

---

### Scenario 11.4: Admin Activates Suspended User → Employee Can Login
**Purpose:** Test suspension reversal

**Steps:**
1. **Prerequisite**: User `emptest` is suspended (from Scenario 11.3)
2. **Browser 1 (Admin)**: Log in as `admintest`
3. Go to "User Management" tab
4. Find suspended user `emptest` (red "Suspended" badge)
5. Click "Edit"
6. Toggle "Active" switch to ON
7. Click "Save Changes"
8. **Browser 2 (Employee)**: Try to log in as `emptest` with password `AgentTest!`

**Expected Results:**
- ✓ Admin sees success: "User activated. They can now log in..."
- ✓ Status badge turns green "Active"
- ✓ Warning styling removed from user row
- ✓ Employee can log in successfully immediately
- ✓ Full access restored
- ✓ Can submit expenses
- ✓ Can view expense history
- ✓ No lingering restrictions

---

### Scenario 11.5: Manager Approves Employee Expense
**Purpose:** Test manager approval permissions

**Steps:**
1. **Browser 1 (Employee)**: Log in as `emptest2`
2. Submit expense:
   - Amount: $75.00
   - Category: Meals
   - Vendor: Chipotle
   - Description: "Team lunch meeting"
3. **Browser 2 (Manager)**: Log in as `testuser`
4. Go to "Pending Approvals" tab
5. Find the expense
6. Click "Approve"
7. **Browser 1 (Employee)**: Check "History" tab

**Expected Results:**
- ✓ Manager sees expense in "Pending Approvals"
- ✓ Manager can approve expense
- ✓ Approver name shows as "Test Manager User" (not Admin)
- ✓ Employee sees approved expense with manager's name
- ✓ Manager **cannot** access User Management tab
- ✓ Manager can view "All Expenses" tab
- ✓ Manager has same approval rights as admin for expenses

---

### Scenario 11.6: Concurrent Approval Attempt (Race Condition)
**Purpose:** Test system behavior when two admins try to approve same expense

**Steps:**
1. **Prerequisite**: One pending expense exists
2. **Browser 1 (Admin 1)**: Log in as `admintest`
3. **Browser 2 (Admin 2)**: Log in as `admin2` (or `testuser` manager)
4. Both navigate to "Pending Approvals" tab
5. Both see the same expense
6. **Browser 1**: Click "Approve" first
7. **Browser 2**: Click "Approve" 2 seconds later

**Expected Results:**
- ✓ First approval succeeds (Admin 1)
- ✓ Success notification in Browser 1
- ✓ Expense disappears from Browser 1's pending list
- ✓ Second approval fails (Admin 2)
- ✓ Error in Browser 2: "Expense not found" or "Expense already processed"
- ✓ No duplicate approval created
- ✓ Data integrity maintained
- ✓ Only one approver recorded
- ✓ Browser 2 auto-refreshes and expense removed from list

---

### Scenario 11.7: Employee Edits Expense Before Admin Reviews
**Purpose:** Test real-time updates

**Steps:**
1. **Browser 1 (Employee)**: Log in as `emptest`
2. Submit expense:
   - Amount: $100.00
   - Description: "Office supplies"
3. Note the Expense ID
4. Immediately click "Edit" (while still pending)
5. Change amount to $150.00
6. Change description to "Office supplies and equipment"
7. Click "Update"
8. **Browser 2 (Admin)**: Log in as `admintest`
9. Go to "Pending Approvals"
10. Find the expense
11. Review details

**Expected Results:**
- ✓ Employee can edit pending expense
- ✓ Changes save successfully
- ✓ Admin sees **updated** details ($150.00, new description)
- ✓ No stale data shown
- ✓ Auto-refresh shows latest version
- ✓ Approval uses current data
- ✓ Edit history may be logged (if implemented)

---

### Scenario 11.8: Employee Withdraws Expense After Submission
**Purpose:** Test employee expense cancellation

**Steps:**
1. **Browser 1 (Employee)**: Log in as `emptest2`
2. Submit expense (any details)
3. Decide to cancel it
4. Click "Delete" or "Withdraw" button on pending expense
5. Confirm deletion
6. **Browser 2 (Admin)**: Log in as `admintest`
7. Check "Pending Approvals" tab

**Expected Results:**
- ✓ Employee can delete/withdraw pending expense
- ✓ Confirmation prompt appears
- ✓ Success notification: "Expense withdrawn"
- ✓ Expense removed from employee's "Active" tab
- ✓ Admin **does not** see expense in Pending list
- ✓ Expense marked as "WITHDRAWN" in database (soft delete)
- ✓ Cannot be approved after withdrawal

---

### Scenario 11.9: Admin Creates User → New User Logs In
**Purpose:** Test user creation and immediate access

**Steps:**
1. **Browser 1 (Admin)**: Log in as `admintest`
2. Go to "User Management" tab
3. Click "+ Create User"
4. Fill in form:
   - Email: `newemployee@company.com`
   - Username: `newemployee`
   - Full Name: "New Employee Test"
   - Password: `Welcome123!`
   - Role: Employee
   - Department: "Marketing"
5. Click "Create User"
6. Note the success message
7. **Browser 2 (New User)**: Immediately try logging in:
   - Username: `newemployee`
   - Password: `Welcome123!`

**Expected Results:**
- ✓ User creation succeeds
- ✓ User appears in user list immediately
- ✓ New user can log in right away (no email verification needed)
- ✓ New user sees Employee Dashboard
- ✓ New user can submit expenses
- ✓ New user's department shown as "Marketing"
- ✓ Pre-verified account (is_verified = true)

---

### Scenario 11.10: Admin Changes User Role → Permissions Update
**Purpose:** Test real-time permission changes

**Steps:**
1. **Browser 1 (Employee)**: Log in as `emptest`
2. Note you see Employee Dashboard only
3. **Browser 2 (Admin)**: Log in as `admintest`
4. Go to "User Management"
5. Find user `emptest`
6. Click "Edit"
7. Change Role from "Employee" to "Manager"
8. Click "Save Changes"
9. **Back to Browser 1**: Refresh the page or perform any action

**Expected Results:**
- ✓ Admin sees success: "User updated successfully"
- ✓ Role badge changes to "MANAGER" (purple)
- ✓ **In Browser 1**: After refresh, user sees Manager Dashboard
- ✓ "Pending Approvals" tab now visible
- ✓ Can approve other employees' expenses
- ✓ Permissions updated immediately
- ✓ Old session remains valid (no forced logout)

---

### Scenario 11.11: Multiple Employees Submit → Admin Bulk Review
**Purpose:** Test admin efficiency with multiple pending expenses

**Steps:**
1. **Browsers 1-3 (Employees)**:
   - Browser 1: Log in as `emptest`, submit expense #1
   - Browser 2: Log in as `emptest2`, submit expense #2
   - Browser 3: Create `employee3`, log in, submit expense #3
2. **Browser 4 (Admin)**: Log in as `admintest`
3. Go to "Pending Approvals" tab
4. Review statistics (should show 3 pending, 3 unique employees)
5. Use search to find specific expense
6. Approve expense #1
7. Reject expense #2 with reason
8. Approve expense #3
9. Check pending count

**Expected Results:**
- ✓ Admin sees all 3 expenses in pending list
- ✓ Statistics accurate: "3 Pending Requests", "3 Employees"
- ✓ Total amount = sum of all three
- ✓ Can search by employee name/vendor/description
- ✓ Can sort by date, amount, employee
- ✓ Each approval/rejection independent
- ✓ Pending count decreases with each action
- ✓ Employees see their individual results in real-time

---

### Scenario 11.12: Admin Deletes User with Pending Expense
**Purpose:** Test data integrity on user deletion

**Steps:**
1. **Browser 1 (Employee)**: Log in as `employee3`
2. Submit a pending expense
3. **Browser 2 (Admin)**: Log in as `admintest`
4. Go to "User Management"
5. Find user `employee3`
6. Click "Delete"
7. Confirm deletion
8. Go to "Pending Approvals" tab
9. Check if deleted user's expense still visible

**Expected Results:**
- ✓ User deletion succeeds
- ✓ User removed from user list
- ✓ **Expense data preserved** (orphaned expense)
- ✓ Expense shows deleted user's name/email as historical data
- ✓ Can still approve/reject the expense
- ✓ OR: System prevents deletion if user has pending expenses (better UX)
- ✓ Data integrity maintained

---

### Scenario 11.13: Employee Uploads Receipt → Admin Views Receipt
**Purpose:** Test receipt sharing between users

**Steps:**
1. **Browser 1 (Employee)**: Log in as `emptest`
2. Submit expense or find existing pending expense
3. Click "Upload Receipt"
4. Select file: `receipt.jpg`
5. Upload successfully
6. Note receipt count badge shows "1"
7. **Browser 2 (Admin)**: Log in as `admintest`
8. Go to "Pending Approvals"
9. Find the expense (should show receipt count "1")
10. Click receipt count badge
11. Click "View" on receipt

**Expected Results:**
- ✓ Employee upload succeeds
- ✓ Receipt count updates immediately
- ✓ Admin sees receipt count badge
- ✓ Admin can open receipt list modal
- ✓ Receipt opens in new tab for admin
- ✓ Image displays correctly
- ✓ Admin can download receipt
- ✓ Both users have equal access to receipt
- ✓ Receipt persists after approval/rejection

---

### Scenario 11.14: Admin Clears History → All Users Affected
**Purpose:** Test system-wide data clearing

**Steps:**
1. **Prerequisite**: Multiple expenses exist (pending, approved, rejected) from various employees
2. **Browser 1 (Employee)**: Log in as `emptest`, note expense count in "History" tab
3. **Browser 2 (Admin)**: Log in as `admintest`
4. Go to "All Expenses" tab
5. Click red "Clear History" button (top-right)
6. Confirm first warning
7. Confirm second warning
8. Note success message with statistics
9. **Back to Browser 1 (Employee)**: Refresh
10. Check "Active" and "History" tabs

**Expected Results:**
- ✓ Admin sees two confirmation dialogs (safety)
- ✓ Success message shows deletion stats (expenses, receipts, comments deleted)
- ✓ Admin's "All Expenses" tab shows empty
- ✓ Admin's "Pending Approvals" tab shows "0 Pending"
- ✓ **Employee sees empty "History" and "Active" tabs**
- ✓ All users' expenses cleared system-wide
- ✓ All receipts and physical files deleted
- ✓ Audit log created for admin action
- ✓ Fresh start for testing

---

### Scenario 11.15: Self-Approval Prevention (Security)
**Purpose:** Verify admin cannot approve their own expenses

**Steps:**
1. **Browser 1 (Admin as Employee)**: Log in as `admintest`
2. Submit an expense (admins can submit expenses too)
   - Amount: $200.00
   - Category: Software
   - Vendor: Adobe
   - Description: "Design software"
3. Go to "Pending Approvals" tab
4. Find your own expense
5. Try to click "Approve"

**Expected Results:**
- ✓ Admin can submit expenses like any employee
- ✓ Expense appears in "Pending Approvals"
- ✓ **Approve button disabled or shows error** when clicking
- ✓ Error message: "Cannot approve your own expense" or "Not authorized"
- ✓ Must wait for another admin/manager to approve
- ✓ Security policy enforced
- ✓ Audit trail records the attempt

---

## 12. Advanced Multi-User Scenarios

### Scenario 12.1: Three-Way Approval (Admin, Manager, Employee)
**Purpose:** Test complex approval workflows

**Steps:**
1. **Browser 1**: Employee submits expense
2. **Browser 2**: Manager reviews and approves
3. **Browser 3**: Admin views approved expense in "All Expenses"
4. All browsers stay open, observe real-time updates

**Expected Results:**
- ✓ All three users see correct data
- ✓ Auto-refresh updates all browsers
- ✓ No stale data
- ✓ Timeline of actions preserved

---

### Scenario 12.2: Concurrent User Management
**Purpose:** Test simultaneous user administration

**Steps:**
1. **Two Admin browsers**: Both edit same user simultaneously
2. Admin 1 changes name, Admin 2 changes department
3. Both click "Save"

**Expected Results:**
- ✓ Last write wins (or conflict detection)
- ✓ No data corruption
- ✓ User notified of conflict

---

### Scenario 12.3: Load Testing Simulation
**Purpose:** Test system under moderate load

**Steps:**
1. Create 10 employees
2. Each submits 5 expenses (50 total)
3. Admin reviews all 50 in one session
4. Test performance and responsiveness

**Expected Results:**
- ✓ Pagination handles large dataset
- ✓ Search remains fast
- ✓ No memory leaks
- ✓ Browser doesn't freeze

---

## Quick Test Script for Multi-User Scenarios

Use this checklist for rapid multi-user testing:

| # | Scenario | Browser 1 | Browser 2 | Pass/Fail |
|---|----------|-----------|-----------|-----------|
| 1 | Submit→Approve | `emptest` | `admintest` | [ ] |
| 2 | Submit→Reject | `emptest2` | `admintest` | [ ] |
| 3 | Suspend→Auto-logout | `emptest` | `admintest` | [ ] |
| 4 | Activate→Login | `emptest` | `admintest` | [ ] |
| 5 | Manager Approve | `emptest` | `testuser` | [ ] |
| 6 | Concurrent Approve | `admintest` | `testuser` | [ ] |
| 7 | Edit Before Review | `emptest` | `admintest` | [ ] |
| 8 | Withdraw Expense | `emptest2` | `admintest` | [ ] |
| 9 | Create→Login | `admintest` | `newuser` | [ ] |
| 10 | Role Change | `emptest` | `admintest` | [ ] |
| 11 | Bulk Review | 3× Employee | `admintest` | [ ] |
| 12 | Delete User | `employee3` | `admintest` | [ ] |
| 13 | Receipt Share | `emptest` | `admintest` | [ ] |
| 14 | Clear History | `emptest` | `admintest` | [ ] |
| 15 | Self-Approval | `admintest` | `admintest` | [ ] |

---

## Browser Compatibility

Test on multiple browsers:
- [ ] Chrome (latest version)
- [ ] Firefox (latest version)
- [ ] Edge (latest version)
- [ ] Safari (latest version, macOS only)

**Verify for each browser:**
- [ ] All features work correctly
- [ ] Layout renders properly
- [ ] No console errors
- [ ] Performance acceptable
- [ ] File upload/download works
- [ ] Notifications display correctly

---

## Reporting Issues

When reporting bugs, include:
1. **Steps to reproduce** (detailed, numbered)
2. **Expected result** (what should happen)
3. **Actual result** (what actually happened)
4. **Browser and version** (e.g., Chrome 118.0.5993)
5. **Screenshots or screen recording** (use Loom, CloudApp, etc.)
6. **Browser console errors** (F12 → Console tab, copy full error)
7. **User role** (Admin, Manager, or Employee)
8. **Date/Time** of issue occurrence
9. **Server logs** if available (check backend/logs/)

---

## Known Issues

### Current Known Issues:
1. **Auto-refresh may cause page scroll jump** if viewing bottom of long list
2. **Pagination count may be off by 1** if deleting last item on page
3. **Receipt upload progress bar** may not show for very fast uploads (<1s)
4. **Sort preference** saved globally, not per-tab

### Workarounds:
1. Manual refresh resets scroll position
2. Go to previous page or refresh to correct
3. Success notification confirms upload
4. Clear localStorage to reset sort

---

## Success Criteria

Admin Dashboard is considered fully functional if:
- ✅ All critical features (see checklist) pass
- ✅ No security vulnerabilities identified
- ✅ All user roles work correctly
- ✅ Error handling is graceful (no crashes)
- ✅ Performance acceptable (< 2s page load, < 500ms interactions)
- ✅ Works on Chrome, Firefox, Edge (Safari optional)
- ✅ Mobile responsive (optional for v1)

---

**End of Admin Dashboard Testing Guide**

**Last Updated:** October 24, 2025
**Version:** 2.0
**Tested Against:** Expense Management System v1.0
