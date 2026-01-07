# AP2 Expense Agent - Test Issues and Fix Recommendations

## Issue #1: Status Format Inconsistency (6 test failures)

### Problem
Expense status values are being returned in lowercase format instead of uppercase.

**Failing Tests**:
- test_api_expenses.py::TestExpenseAPIRoutes::test_create_expense_success
- test_api_expenses.py::TestExpenseAPIRoutes::test_get_expenses_list
- test_auto_approval.py::TestAutoApprovalEndToEnd::test_simple_auto_approval
- test_auto_approval.py::TestAutoApprovalEndToEnd::test_expense_exceeding_amount_limit_not_auto_approved
- test_auto_approval.py::TestAutoApprovalEndToEnd::test_no_policies_results_in_manual_approval

### Error Examples

```python
# Test expectation
assert expense["status"] == "PENDING"

# Actual value
'pending'
```

### Root Cause
The Expense model likely defines status as a lowercase string or the serialization is converting to lowercase.

### Search Locations
```
Files to check:
- src/models.py (look for ExpenseStatus enum or status field definition)
- src/schemas.py (look for ExpenseResponse or similar schemas)
- src/routes/expenses.py (look for response building)
```

### Fix Approach

**Option 1**: Use Enum with uppercase values
```python
from enum import Enum

class ExpenseStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"

# In model
class Expense(Base):
    status: ExpenseStatus = ExpenseStatus.PENDING
```

**Option 2**: Uppercase in serialization
```python
# In schema response
class ExpenseResponse(BaseModel):
    status: str

    @field_validator('status', mode='before')
    def uppercase_status(cls, v):
        return v.upper() if v else v
```

**Option 3**: Update test to match current behavior
```python
# If lowercase is intentional
assert expense["status"] == "pending"
```

### Verification
```bash
pytest tests/test_api_expenses.py::TestExpenseAPIRoutes::test_create_expense_success -vv
pytest tests/test_auto_approval.py -v
```

---

## Issue #2: Permissions System Completely Non-Functional (36 test failures)

### Problem
All 36 permission tests are failing. The permission checking system is either not implemented or completely broken.

**Affected Test Classes**:
- TestBasicPermissionChecks (9 tests)
- TestMultiplePermissionChecks (3 tests)
- TestGetUserPermissions (1 test)
- TestCheckPermissionWithException (3 tests)
- TestExpenseAccessControl (5 tests)
- TestExpenseApprovalLogic (7 tests)
- TestDepartmentFiltering (2 tests)
- TestRolePermissionMappings (3 tests)
- TestEdgeCases (5 tests)

### Root Cause
Permission checks in the codebase are likely:
1. Not being enforced in routes
2. Using broken permission logic
3. Missing role-to-permission mapping
4. Not checking user roles correctly

### What Needs Permission Checks

```
Employee Role:
- Can create own expenses
- Can view own expenses
- Cannot approve any expenses
- Cannot view other users' expenses
- Cannot change roles

Manager Role:
- Can create own expenses
- Can view own + department expenses
- Can approve expenses up to amount limit
- Can view department members
- Cannot change roles of other managers
- Cannot approve expenses from other departments

Accountant Role:
- Can view all expenses (read-only)
- Cannot create expenses
- Cannot approve expenses
- Can export reports
- Can view all users

Admin Role:
- Full access to everything
```

### Files to Audit

```
C:\Users\robot\Desktop\ap2-expense-agent\backend\
├── src/
│   ├── permissions.py          # Main permissions logic
│   ├── decorators.py           # @require_permission decorator
│   └── routes/
│       ├── expenses.py
│       ├── users.py
│       ├── admin.py
│       └── approval_policies.py
```

### Example Fix Pattern

```python
# routes/expenses.py

from fastapi import Depends
from src.permissions import require_permission

@router.get("/expenses")
async def list_expenses(
    user: User = Depends(get_current_user),
):
    # Add permission check
    require_permission(user, "read_expenses")

    # Filter by user's organization and role
    if user.role == UserRole.ADMIN:
        expenses = db.query(Expense).all()
    elif user.role == UserRole.MANAGER:
        expenses = db.query(Expense).filter(
            Expense.department == user.department
        ).all()
    else:  # Employee/Accountant
        expenses = db.query(Expense).filter(
            Expense.user_id == user.id
        ).all()

    return expenses
```

### Verification Steps
```bash
# Start with simple tests
pytest tests/test_permissions.py::TestBasicPermissionChecks::test_employee_cannot_view_all -vv

# Run all permission tests to verify fix
pytest tests/test_permissions.py -v
```

---

## Issue #3: Multi-Tenancy Isolation Broken (10 test failures) - SECURITY ISSUE

### Problem
Organizations are not being filtered in queries, allowing cross-organization data leakage.

**Affected Tests**:
- test_tenant_isolation.py::test_list_expenses_only_shows_own_organization
- test_tenant_isolation_comprehensive.py::test_SEC_ISO_001 through test_SEC_ISO_009

### Security Impact
- **HIGH**: User A can potentially view User B's expenses if they manipulate the organization_id header
- **HIGH**: SQL injection vulnerability if organization_id is not properly validated
- **CRITICAL**: Soft-deleted organization data might still be accessible

### Root Cause
Queries are not filtering by `organization_id` in WHERE clauses.

### Example of the Problem

```python
# WRONG - Returns all expenses for all organizations
@router.get("/expenses")
async def list_expenses(user: User = Depends(get_current_user)):
    expenses = db.query(Expense).all()  # Missing organization filter!
    return expenses

# CORRECT
@router.get("/expenses")
async def list_expenses(user: User = Depends(get_current_user)):
    # First get user's organization
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id
    ).first()

    if not membership or not membership.organization.is_active:
        raise HTTPException(status_code=403, detail="Not a member of any organization")

    # Filter expenses by organization
    expenses = db.query(Expense).filter(
        Expense.organization_id == membership.organization_id,
        Expense.is_deleted == False  # Also filter soft-deleted
    ).all()

    return expenses
```

### Files to Fix

```
All query operations in:
- src/routes/expenses.py (ALL queries)
- src/routes/approval_policies.py (ALL queries)
- src/routes/users.py (List users)
- src/routes/organizations.py (Organization members)
- src/repository.py (Data access layer)
```

### Fix Checklist

```
[ ] Add organization context extraction to every route
[ ] Validate X-Organization-Id header
[ ] Filter ALL database queries with organization_id
[ ] Filter soft-deleted organizations
[ ] Filter soft-deleted organization members
[ ] Prevent SQL injection in org_id filters
[ ] Add tests for cross-org access denial
```

### Example Implementation

```python
from src.dependencies import get_organization_context

@router.get("/expenses")
async def list_expenses(
    user: User = Depends(get_current_user),
    org_context: Organization = Depends(get_organization_context)
):
    # org_context.id is already validated and belongs to user
    expenses = db.query(Expense).filter(
        Expense.organization_id == org_context.id,
        Expense.is_deleted == False
    ).all()
    return expenses
```

### Verification
```bash
# Test cross-org access denial
pytest tests/test_tenant_isolation_comprehensive.py::TestCrossOrgDataLeakage -vv

# Run entire tenant isolation suite
pytest tests/test_tenant_isolation_comprehensive.py -v
```

---

## Issue #4: User Creation Validation Error (2 test failures)

### Problem
POST /api/v1/admin/users/create returns 422 (Unprocessable Entity) instead of 201 (Created).

**Failing Tests**:
- test_users.py::TestUserManagement::test_create_user_as_admin
- test_users.py::TestUserManagement::test_update_user_role_as_admin

### Error Response
```
Status: 422
Body: Validation error (likely missing required field or type mismatch)
```

### Likely Causes
1. Request payload missing required field
2. Field type mismatch (string vs int, etc.)
3. Invalid enum value
4. Validation schema issue

### Debugging Steps

```bash
# Run test with verbose output to see actual error
pytest tests/test_users.py::TestUserManagement::test_create_user_as_admin -vv

# Look for validation error details in output
```

### Files to Check

```
- src/routes/admin.py (POST /api/v1/admin/users/create)
- src/schemas.py (UserCreate schema)
- Look for Pydantic validation decorators
```

### Example Problem & Fix

```python
# WRONG - schema might require department but test doesn't provide it
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    department: str  # Required but test doesn't provide
    role: UserRole

# CORRECT - make department optional
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    department: Optional[str] = None
    role: UserRole
```

### Verification
```bash
pytest tests/test_users.py::TestUserManagement::test_create_user_as_admin -vv
```

---

## Issue #5: Integration Test Fixture Failures (3 error, 1 failure)

### Problem
Integration tests fail during fixture setup with 402 Payment Required error.

**Affected Tests**:
- test_expense_workflow.py::test_complete_expense_workflow (ERROR)
- test_expense_workflow.py::test_expense_rejection_workflow (ERROR)
- test_expense_workflow.py::test_user_deletion_cleanup (ERROR)

### Root Cause
Free tier users are limited to 1 organization. When fixture creates a new user and tries to create an organization, it hits the limit because the user already has an auto-created organization from registration.

### Error Message
```
[ORG_LIMIT_EXCEEDED] Organization limit reached (1/1), tier=free
HTTP 402: Organizations limit exceeded: 1/1
```

### Solution Options

**Option 1**: Use paid tier in fixtures
```python
# In conftest.py
@pytest.fixture
def integration_test_user(db_session):
    user = User(...)
    org_membership = OrganizationMember(...)

    # Set tier to Professional (unlimited orgs)
    org_membership.organization.tier = "professional"

    db_session.commit()
    return user
```

**Option 2**: Skip organization creation in fixture
```python
# Use the auto-created organization from registration
@pytest.fixture
def organization(client, user):
    # Don't create a new one, use user's existing one
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id
    ).first()
    return membership.organization
```

**Option 3**: Bypass tier limits in test environment
```python
# In test settings
if TESTING:
    TIER_ENFORCEMENT_ENABLED = False
```

### Verification
```bash
pytest tests/integration/test_expense_workflow.py -v
```

---

## Fix Priority & Time Estimates

| Issue | Priority | Est. Time | Impact | Files |
|-------|----------|-----------|--------|-------|
| Status Format | HIGH | 30 min | 6 tests | models.py, schemas.py |
| User Creation | HIGH | 1 hour | 2 tests | routes/admin.py, schemas.py |
| Multi-Tenancy | CRITICAL | 2-4 hrs | 10 tests | ALL routes, database.py |
| Permissions | CRITICAL | 3-6 hrs | 36 tests | permissions.py, ALL routes |
| Integration | MEDIUM | 1 hour | 3 tests | conftest.py |

---

## Testing Workflow

### After Each Fix

```bash
# 1. Run affected tests
pytest tests/test_api_expenses.py -v

# 2. Run related tests
pytest tests/test_auto_approval.py -v

# 3. Run full suite to check for regressions
pytest tests/ -q

# 4. Check coverage
pytest tests/ --cov=src --cov-report=term-missing
```

### Expected After All Fixes

```
Final Status: 400+ tests passing
Failures: Only pre-existing known limitations
Coverage: 85%+
```

---

## Commands to Run Tests

```bash
# cd to backend directory first
cd C:\Users\robot\Desktop\ap2-expense-agent\backend

# Test Status Format Fix
pytest tests/test_api_expenses.py tests/test_auto_approval.py -v

# Test Permissions Fix
pytest tests/test_permissions.py -v

# Test Multi-Tenancy Fix
pytest tests/test_tenant_isolation_comprehensive.py -v

# Test User Creation Fix
pytest tests/test_users.py -v

# Test Integration Fixture Fix
pytest tests/integration/ -v

# Full Suite
pytest tests/ -q
```

---

## Additional Notes

1. **Status Format Bug**: Quickest fix, should take 30 minutes
2. **Permissions**: Most complex, requires understanding entire permission model
3. **Multi-Tenancy**: Security critical, must be fixed before any production deployment
4. **User Creation**: Likely quick fix, just validation schema issue
5. **Integration Tests**: Lowest priority, only affects test environment

All issues should be addressed before the application goes to production.

---

Last Updated: January 6, 2026
