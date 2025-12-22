# User Credentials - Development Environment

**Last Updated**: 2025-11-28
**Environment**: Development/Testing

---

## Password for ALL Users

**All users have the same password**: `Testme1!`

## Primary Test Users

### Admin User
- **Username**: `admintest`
- **Email**: `sergeisqa@gmail.com`
- **Role**: ADMIN (Full system access)
- **Password**: `Testme1!`
- **Permissions**: All permissions (superuser)

### Manager User
- **Username**: `testuser`
- **Email**: `naftalinka21@gmail.com`
- **Role**: MANAGER (Department management)
- **Password**: `Testme1!`
- **Permissions**:
  - Approve expenses ≤ $5,000
  - View/edit department expenses
  - View department reports
  - Manage team members

### Accountant User
- **Username**: `employee2`
- **Email**: `mutabortrim@gmail.com`
- **Role**: ACCOUNTANT (Read-only auditor)
- **Password**: `Testme1!`
- **Permissions**:
  - View all expenses (read-only)
  - View all reports
  - Audit all transactions
  - **Cannot approve** expenses (separation of duties)

### Employee Users

#### Employee 1
- **Username**: `emptest`
- **Email**: `sergeigodev@gmail.com`
- **Role**: EMPLOYEE (Basic user)
- **Password**: `Testme1!`
- **Permissions**:
  - Submit own expenses
  - View/edit own expenses
  - Upload receipts
  - View own reports

#### Employee 2
- **Username**: `emptest2`
- **Email**: `telegramtok@gmail.com`
- **Role**: EMPLOYEE (Basic user)
- **Password**: `Testme1!`
- **Permissions**: Same as Employee 1

---

## Complete User List (30 Users)

| # | Username | Email | Role | Full Name | Password |
|---|----------|-------|------|-----------|----------|
| 1 | employee2 | mutabortrim@gmail.com | accountant | Accountant User | Testme1! |
| 2 | admintest | sergeisqa@gmail.com | admin | Admin Test User | Testme1! |
| 3 | checkouttest_1764359575 | checkouttest_1764359575@test.com | employee | Checkout Test User | Testme1! |
| 4 | checkouttest_1764359587 | checkouttest_1764359587@test.com | employee | Checkout Test User | Testme1! |
| 5 | emptest | sergeigodev@gmail.com | employee | Employee Test 1 | Testme1! |
| 6 | emptest2 | telegramtok@gmail.com | employee | Employee Test 2 | Testme1! |
| 7 | freetest2 | freetest2@test.com | employee | Free Tier Test | Testme1! |
| 8 | freetest3 | freetest3@test.com | employee | Free Tier Test 3 | Testme1! |
| 9 | freetest4 | freetest4@test.com | employee | Free Tier Test 4 | Testme1! |
| 10 | freetest5 | freetest5@example.com | employee | Free Tier Test User 5 | Testme1! |
| 11 | freetest6 | freetest6@test.com | employee | N/A | Testme1! |
| 12 | freetiertest | freetiertest@test.com | employee | N/A | Testme1! |
| 13 | freetiertest2 | freetiertest2@test.com | employee | N/A | Testme1! |
| 14 | massuser1 | mass1@example.com | employee | Mass User 1 | Testme1! |
| 15 | ocrfinal | ocrfinal@test.com | employee | N/A | Testme1! |
| 16 | ocrtest | ocrtest@test.com | employee | N/A | Testme1! |
| 17 | orgtest_20251127_160315 | orgtest_20251127_160315@test.com | employee | Test User | Testme1! |
| 18 | orgtest_20251127_160330 | orgtest_20251127_160330@test.com | employee | Test User | Testme1! |
| 19 | orgtest_20251127_160348 | orgtest_20251127_160348@test.com | employee | Test User | Testme1! |
| 20 | sectest2 | sectest2@example.com | employee | Security Tester | Testme1! |
| 21 | securitytest1 | sectest1@test.com | employee | N/A | Testme1! |
| 22 | stripetest | stripetest@test.com | employee | Stripe Test User | Testme1! |
| 23 | stripetest_1764351238 | stripetest_1764351238@example.com | employee | Stripe Tester | Testme1! |
| 24 | user0_1764299500 | user0_1764299500@test.com | employee | Test User | Testme1! |
| 25 | user1_1764299502 | user1_1764299502@test.com | employee | Test User | Testme1! |
| 26 | user2_1764299504 | user2_1764299504@test.com | employee | Test User | Testme1! |
| 27 | webhook_test_1764351129 | webhook_test_1764351129@example.com | employee | Webhook Tester | Testme1! |
| 28 | webhook_test_1764351140 | webhook_test_1764351140@example.com | employee | Webhook Tester | Testme1! |
| 29 | xsstest1 | xsstest1@test.com | employee | N/A | Testme1! |
| 30 | testuser | naftalinka21@gmail.com | manager | Test Manager User | Testme1! |

**Total**: 30 users
**Password**: All users share the same password: `Testme1!`

---

## Role Comparison

| Feature | ADMIN | MANAGER | ACCOUNTANT | EMPLOYEE |
|---------|-------|---------|------------|----------|
| Submit expenses | ✅ | ✅ | ✅ | ✅ |
| View own expenses | ✅ | ✅ | ✅ | ✅ |
| View department expenses | ✅ | ✅ | ❌ | ❌ |
| View all expenses | ✅ | ❌ | ✅ (read-only) | ❌ |
| Approve expenses | ✅ | ✅ (≤$5K) | ❌ | ❌ |
| Edit all expenses | ✅ | ❌ | ❌ | ❌ |
| Manage users | ✅ | ❌ | ❌ | ❌ |
| View reports (all) | ✅ | ❌ | ✅ | ❌ |
| System configuration | ✅ | ❌ | ❌ | ❌ |

---

## Testing Scenarios

### Test Expense Approval Workflow
1. Login as `emptest` → Submit expense for $100
2. Login as `testuser` (manager) → Approve expense
3. Login as `employee2` (accountant) → Verify expense appears in audit log

### Test Role Permissions
1. Login as `employee2` (accountant) → Try to approve expense (should fail)
2. Login as `emptest` → Try to view another user's expenses (should fail)
3. Login as `testuser` → Try to approve $10,000 expense (should fail, over $5K limit)

### Test Audit Trail
1. Login as `admintest` → Create new user
2. Login as `employee2` (accountant) → View audit log
3. Verify all actions are logged with timestamps

---

## Quick Login Commands (via API)

### Admin Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admintest","password":"Testme1!"}'
```

### Manager Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"Testme1!"}'
```

### Accountant Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"employee2","password":"Testme1!"}'
```

### Employee Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"emptest","password":"Testme1!"}'
```

---

## Frontend Login

**URL**: http://localhost:5173

Simply enter the username and password from the table above.

---

## Security Notes

⚠️ **IMPORTANT**:
- These credentials are for **DEVELOPMENT/TESTING ONLY**
- **NEVER use these credentials in production**
- All users use the same password for testing convenience
- Production users should have unique, strong passwords
- Enable 2FA/TOTP for production admin accounts

---

## Database Changes

Users updated on: 2025-11-28

**Changes made**:
1. Updated `admintest` email: `admintest@example.com` → `sergeisqa@gmail.com`
2. Updated `testuser` email: `testuser@example.com` → `naftalinka21@gmail.com`
3. **Created** `employee2` user with ACCOUNTANT role
4. Updated `emptest` email: `emptest@example.com` → `sergeigodev@gmail.com`
5. Updated `emptest2` email: `emptest2@example.com` → `telegramtok@gmail.com`

---

## Additional Test Users

The database also contains 24 additional test users created during various testing scenarios:
- Stripe checkout tests
- Webhook tests
- Security tests
- Organization tests

These are all EMPLOYEE role users and can be safely ignored or deleted.

---

**For Production Deployment**:
See `PRODUCTION_DEPLOYMENT_GUIDE.md` for instructions on creating production admin accounts with secure credentials.
