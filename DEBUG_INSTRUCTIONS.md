# Debug Instructions - Pending Filter Issue

## Current State
- Backend and frontend both have debug logging enabled
- Backend is reloading with new logging
- There's 1 pending expense in the database (Printer, $100 from emptest)

## Steps to Debug

### 1. Open Browser Developer Tools
- Press **F12** to open Developer Console
- Go to the **Console** tab

### 2. Login as Admin
- Go to http://localhost:5174
- Login as `admin@test.com`

### 3. Test "Pending Approvals" Tab
- Click on "Pending Approvals" tab
- **Expected**: You should see the Printer expense
- **Check Console**: You should see logs like:
  ```
  [AdminDashboard] Render - activeTab: pending
  [AdminDashboard] Render - pendingExpenses: 1
  [AdminDashboard] Render - currentExpenses: 1
  ```

### 4. Test "All Expenses" Tab with Pending Filter
- Click on "All Expenses" tab
- Select "Pending" from the dropdown filter
- **Expected**: You should see the same Printer expense
- **Check Console**: You should see logs like:
  ```
  [AdminDashboard] Fetching all expenses with statusFilter: pending
  [AdminDashboard] Sending filter value to API: pending
  [AdminDashboard] API Response: {expenses: [...], ...}
  [AdminDashboard] Setting allExpenses with 1 items
  [AdminDashboard] Render - activeTab: all
  [AdminDashboard] Render - statusFilter: pending
  [AdminDashboard] Render - allExpenses: 1
  [AdminDashboard] Render - currentExpenses: 1
  ```

### 5. Check Network Tab
- Go to **Network** tab in Developer Tools
- Click "All Expenses" → Select "Pending"
- Find the request to `/api/v1/expenses/all?status=pending`
- Click on it and check the **Response** tab
- **Expected**: Should show 1 expense in the JSON response

### 6. Check Backend Logs
Look at the terminal where backend is running for logs like:
```
INFO: [get_all_expenses] Called with status filter: pending
INFO: [get_all_expenses] Filtering by status enum: ExpenseStatus.PENDING
INFO: [get_all_expenses] Found 1 expenses
```

## What to Look For

### If Console Shows:
- `allExpenses: 0` but API returns 1 expense → **Frontend state issue**
- `allExpenses: 1` but you don't see it on screen → **Rendering issue**
- API error in Network tab → **Backend permission or auth issue**
- No API call in Network tab → **Frontend not calling API**

### Common Issues:
1. **Cache**: Try hard refresh (Ctrl+Shift+R)
2. **Auth**: Token might have expired, try logging out and back in
3. **State**: Frontend state not updating, check console logs
4. **Filter**: Check if statusFilter value is correct in console

## Report Back

Please share:
1. What you see in the Console tab (copy the [AdminDashboard] logs)
2. What you see in Network tab for the `/expenses/all?status=pending` request
3. Whether you can see the expense or not
4. Any errors in the console (red text)

This will help me pinpoint exactly where the issue is!
