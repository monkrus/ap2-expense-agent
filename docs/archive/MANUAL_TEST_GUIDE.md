# Manual Test Guide - AP2 Expense Agent

## Test Status
- ✅ Backend running on: http://localhost:8000
- ✅ Frontend running on: http://localhost:5173
- ✅ Users created: 2 (adminfree, user1)

## Test Credentials

### Admin User (Free Tier)
- **Username**: `adminfree`
- **Email**: admin@example.com
- **Password**: `Passowrd123!`
- **Role**: ADMIN
- **Organization**: adminfree's Organization

### Regular User
- **Username**: `user1`
- **Email**: user1@example.com
- **Password**: `Passowrd123!`
- **Role**: USER
- **Organization**: user1's Organization

---

## Test Checklist

### 1. Authentication Tests

#### Test 1.1: Login as Admin
- [ ] Navigate to http://localhost:5173
- [ ] Enter username: `adminfree`
- [ ] Enter password: `Passowrd123!`
- [ ] Click Login
- [ ] **Expected**: Successfully logged in, redirected to dashboard

#### Test 1.2: Login as Regular User
- [ ] Logout from admin account
- [ ] Enter username: `user1`
- [ ] Enter password: `Passowrd123!`
- [ ] Click Login
- [ ] **Expected**: Successfully logged in, redirected to dashboard

---

### 2. Dashboard Tests

#### Test 2.1: View Dashboard (as adminfree)
- [ ] Login as `adminfree`
- [ ] Check dashboard displays correctly
- [ ] Verify organization name shows "adminfree's Organization"
- [ ] **Expected**: Dashboard loads without errors

#### Test 2.2: View Dashboard (as user1)
- [ ] Login as `user1`
- [ ] Check dashboard displays correctly
- [ ] Verify organization name shows "user1's Organization"
- [ ] **Expected**: Dashboard loads without errors

---

### 3. Expense Creation Tests

#### Test 3.1: Create New Expense (as user1)
- [ ] Login as `user1`
- [ ] Navigate to "Submit Expense" or "New Expense"
- [ ] Fill in expense details:
  - Amount: $50.00
  - Vendor: Amazon
  - Category: OFFICE_SUPPLIES
  - Description: Test expense - office supplies
- [ ] Submit expense
- [ ] **Expected**: Expense created successfully

#### Test 3.2: View Expenses List
- [ ] Navigate to Expenses list
- [ ] Verify the newly created expense appears
- [ ] Check expense status (PENDING/APPROVED)
- [ ] **Expected**: Expense visible in list

---

### 4. Admin Tests

#### Test 4.1: Admin Dashboard Access
- [ ] Login as `adminfree`
- [ ] Look for admin-specific features (user management, settings, etc.)
- [ ] **Expected**: Admin has access to additional features

---

### 5. Billing/Usage Tests

#### Test 5.1: Check Usage Metrics
- [ ] Login as `adminfree`
- [ ] Look for billing or usage section
- [ ] Verify user count shows: 2 active users
- [ ] Check expense count
- [ ] **Expected**: Metrics reflect current usage

---

### 6. API Health Check

#### Test 6.1: Backend Health
Open in browser or run:
```bash
curl http://localhost:8000/health
```
- [ ] **Expected**: Returns {"status": "healthy"} or similar

#### Test 6.2: API Documentation
- [ ] Navigate to http://localhost:8000/docs
- [ ] **Expected**: Swagger/OpenAPI documentation loads

---

## Current Database State

**Users**: 2
- adminfree (ADMIN)
- user1 (USER)

**Organizations**: 2
- adminfree's Organization
- user1's Organization

**Expenses**: 0 (clean state - create some during testing!)

---

## Quick API Tests (Optional)

### Login API Test (adminfree)
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=adminfree&password=Passowrd123!"
```

### Login API Test (user1)
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user1&password=Passowrd123!"
```

---

## Notes

- Both users are on **Free Tier** (max 2 users)
- Both users are **verified** and **active**
- Each user has their own organization
- Database has been cleared and freshly populated
- Password is intentionally spelled: `Passowrd123!` (note the typo)

---

## Test Results

Record your findings here:

| Test | Status | Notes |
|------|--------|-------|
| 1.1 Login Admin | ⬜ | |
| 1.2 Login User1 | ⬜ | |
| 2.1 Admin Dashboard | ⬜ | |
| 2.2 User Dashboard | ⬜ | |
| 3.1 Create Expense | ⬜ | |
| 3.2 View Expenses | ⬜ | |
| 4.1 Admin Features | ⬜ | |
| 5.1 Usage Metrics | ⬜ | |
| 6.1 API Health | ⬜ | |
| 6.2 API Docs | ⬜ | |

---

## Quick Start Testing

1. Open browser: http://localhost:5173
2. Login as `adminfree` / `Passowrd123!`
3. Explore the dashboard
4. Logout and login as `user1` / `Passowrd123!`
5. Create a test expense
6. Check billing/usage metrics

**Happy Testing!** 🚀
