# AP2 Expense Agent - Testing Quick Reference Guide

## Test Summary

| Component | Tests | Passed | Failed | Status |
|-----------|-------|--------|--------|--------|
| Authentication | 33 | 33 | 0 | ✓ PASS |
| Expenses | 22 | 17 | 5 | ⚠ PARTIAL |
| User Management | 13 | 11 | 2 | ⚠ PARTIAL |
| Permissions | 36 | 0 | 36 | ✗ FAIL |
| Multi-Tenancy | 10 | 0 | 10 | ✗ FAIL |
| Approval Policies | 38 | 35 | 3 | ⚠ PARTIAL |
| AP2 Protocol | 22 | 22 | 0 | ✓ PASS |
| Compliance | 19 | 19 | 0 | ✓ PASS |
| Archiving | 24 | 22 | 2 | ⚠ PARTIAL |
| Billing | 15 | 15 | 0 | ✓ PASS |
| Integration | 4 | 1 | 1 | ⚠ ERROR |
| **TOTAL** | **451** | **325** | **97** | **72%** |

---

## Critical Issues (Fix Now)

### 1. Status Format Bug
**Problem**: Expenses return `'pending'` instead of `'PENDING'`
**Impact**: 6 failing tests
**Files**:
- src/models.py (Expense.status)
- src/schemas.py (response schemas)
**Fix**: Uppercase all status values

### 2. Permissions Broken
**Problem**: All permission checks failing (0/36 tests pass)
**Impact**: Cannot enforce role-based access control
**Files**:
- src/permissions.py
- All routes using permission decorators
**Fix**: Audit and re-implement permission system

### 3. Multi-Tenancy Leak
**Problem**: Organizations not filtering data properly (0/10 tests pass)
**Impact**: CRITICAL SECURITY - cross-org data visibility
**Files**:
- src/routes/expenses.py
- src/database.py
**Fix**: Add org context filtering to all queries

---

## Quick Test Commands

```bash
# Full test suite (2 minutes)
cd backend && pytest tests/ -q

# By category
pytest tests/test_auth.py              # Auth (should all pass)
pytest tests/test_api_expenses.py      # Expenses (6 failures)
pytest tests/test_permissions.py       # Permissions (36 failures)
pytest tests/test_tenant_isolation_comprehensive.py  # Multi-tenancy (9 failures)
pytest tests/test_auto_approval.py     # Policies (3 failures)
pytest tests/test_ap2_protocol.py      # AP2 Payment (should all pass)
pytest tests/integration/             # Integration (errors due to org limits)

# Specific failing test
pytest tests/test_permissions.py::TestBasicPermissionChecks -v

# With verbose output
pytest tests/test_api_expenses.py::TestExpenseAPIRoutes::test_create_expense_success -vv

# Coverage report
pytest tests/ --cov=src --cov-report=html
```

---

## Failing Tests by File

### test_api_expenses.py (5 failures)
1. `test_create_expense_success` - Status format ('pending' vs 'PENDING')
2. `test_get_expenses_list` - Response structure issue

### test_auto_approval.py (3 failures)
1. `test_simple_auto_approval` - Status format
2. `test_expense_exceeding_amount_limit_not_auto_approved` - Status format
3. `test_no_policies_results_in_manual_approval` - Status format

### test_users.py (2 failures)
1. `test_create_user_as_admin` - Status 422 validation error
2. `test_update_user_role_as_admin` - Validation error

### test_permissions.py (36 failures)
All tests failing - permission system non-functional
- Employee permission checks
- Manager approval limits
- Accountant access control
- Department filtering
- Approval authority validation

### test_tenant_isolation_comprehensive.py (9 failures)
All tests failing - multi-tenancy isolation broken
- Cross-org data visibility
- Missing org header validation
- Organization context not enforced
- Soft delete handling

### integration/test_expense_workflow.py (3 errors)
1. `test_complete_expense_workflow` - Org limit error in fixture
2. `test_expense_rejection_workflow` - Org limit error in fixture
3. `test_user_deletion_cleanup` - Org limit error in fixture
(One additional test with wrong status code)

---

## Root Causes

### Status Format
**File**: C:\Users\robot\Desktop\ap2-expense-agent\backend\src\models.py
**Line**: Expense model status field
**Current**: Returns `pending`, `approved`, `rejected` (lowercase)
**Expected**: Returns `PENDING`, `APPROVED`, `REJECTED` (uppercase)

### Permissions
**Files**: src/permissions.py, all route files
**Issue**: Permission checks not implemented or broken
**Need**: Audit decorator usage, role checking logic

### Multi-Tenancy
**Files**: src/routes/expenses.py, src/database.py
**Issue**: Missing organization context in WHERE clauses
**Need**: Add `organization_id` filters to all user data queries

---

## Test Data Requirements

The test suite creates data dynamically:
- Users are created per test
- Expenses are created per test
- Organizations are created per test
- Clean-up happens after each test

For testing database state (7 approved, 3 rejected, 7 pending):
- Need separate integration test with persistent data
- Or database snapshot verification test

---

## Next Steps

1. **Immediate** (30 min)
   - Fix status format to uppercase
   - Re-run 6 failing tests

2. **Urgent** (2-4 hours)
   - Fix multi-tenancy isolation
   - Add org context to all queries
   - Re-run 10 tenant tests

3. **Important** (3-6 hours)
   - Fix permissions system
   - Re-run 36 permission tests

4. **Follow-up** (1-2 hours)
   - Fix user creation validation
   - Fix integration test fixtures

---

## Test Infrastructure

**Framework**: pytest 8.4.2
**Database**: SQLite (in-memory for tests)
**HTTP Client**: TestClient (FastAPI)
**Test Discovery**: tests/conftest.py

**Key Fixtures**:
- `client` - FastAPI test client
- `db_session` - Test database session
- `test_user` - Pre-created test user
- `test_admin` - Pre-created admin user
- `auth_headers` - Bearer token headers

**Configuration**: backend/pytest.ini

---

## Files to Review

Essential files for fixing issues:

```
C:\Users\robot\Desktop\ap2-expense-agent\backend\src\
├── models.py              # Expense model status field
├── schemas.py             # Response schemas
├── permissions.py         # Permission system (BROKEN)
├── routes/
│   ├── expenses.py        # Multi-tenancy issue here
│   ├── auth.py
│   └── admin.py           # User creation validation
└── database.py            # Query context
```

---

## Performance Metrics

- **Total execution time**: 86.91 seconds
- **Average per test**: 0.19 seconds
- **Slowest categories**:
  - Integration tests (~25s)
  - Permission tests (~15s)
  - Tenant isolation tests (~10s)

---

## Debugging Tips

1. **View single test output**
   ```bash
   pytest tests/test_api_expenses.py::TestExpenseAPIRoutes::test_create_expense_success -vv
   ```

2. **See full error details**
   ```bash
   pytest tests/test_permissions.py -vv --tb=long
   ```

3. **Run with print statements**
   ```bash
   pytest tests/test_api_expenses.py -s
   ```

4. **Generate coverage report**
   ```bash
   pytest tests/ --cov=src --cov-report=html
   # Open htmlcov/index.html
   ```

5. **Run specific test class**
   ```bash
   pytest tests/test_permissions.py::TestBasicPermissionChecks -v
   ```

---

## Status Legend

| Symbol | Meaning |
|--------|---------|
| ✓ | All tests passing - fully functional |
| ⚠ | Some tests failing - partial functionality |
| ✗ | All tests failing - critical issue |
| ~ | Tests skipped - feature not yet implemented |

---

Last Updated: January 6, 2026
Report Location: C:\Users\robot\Desktop\ap2-expense-agent\COMPREHENSIVE_E2E_TEST_REPORT.md
