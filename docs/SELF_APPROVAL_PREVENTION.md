# Self-Approval Prevention

## Overview

The expense management system has **built-in protection** to prevent users from approving or rejecting their own expense requests. This applies to **ALL users**, including administrators.

## How It Works

### Core Logic

The self-approval prevention is implemented in `backend/src/permissions.py` in the `can_approve_expense()` function:

```python
def can_approve_expense(user_role: UserRole, expense_amount: float,
                        expense_user_id: str, user_id: str, ...) -> bool:
    # Cannot approve own expense
    if user_id == expense_user_id:
        return False

    # ... rest of approval logic
```

This check happens **BEFORE** any other permission checks, ensuring that no user can bypass it.

## Where It's Applied

Self-approval prevention is enforced in all expense approval/rejection endpoints:

### 1. Single Expense Approval
- **Endpoint**: `POST /api/v1/expenses/approve`
- **Code**: `backend/src/api.py:268` (`approve_expense`)
- **Check**: Lines 294-303 use `can_approve_expense()`

### 2. Single Expense Rejection
- **Endpoint**: `POST /api/v1/expenses/reject`
- **Code**: `backend/src/api.py:359` (`reject_expense`)
- **Check**: Lines 386-395 use `can_approve_expense()`

### 3. Bulk Expense Approval
- **Endpoint**: `POST /api/v1/expenses/bulk-approve`
- **Code**: `backend/src/api.py:986` (`bulk_approve_expenses`)
- **Check**: Lines 1029-1040 use `can_approve_expense()` for each expense

### 4. Bulk Expense Rejection
- **Endpoint**: `POST /api/v1/expenses/bulk-reject`
- **Code**: `backend/src/api.py:1110` (`bulk_reject_expenses`)
- **Check**: Lines 1153-1164 use `can_approve_expense()` for each expense

## Behavior By Role

### Admin (ADMIN role)
- ✅ **CAN** approve/reject expenses from ANY other user
- ✅ **CAN** approve/reject expenses of ANY amount
- ❌ **CANNOT** approve/reject their own expenses
- ✅ **CAN** perform bulk operations (excluding own expenses)

### Manager (MANAGER role)
- ✅ **CAN** approve/reject expenses from employees
- ✅ **CAN** approve expenses up to $5,000
- ⚠️  **REQUIRES** admin approval for expenses over $5,000
- ❌ **CANNOT** approve/reject their own expenses
- ✅ **CAN** perform bulk operations (excluding own expenses)

### Employee (EMPLOYEE role)
- ❌ **CANNOT** approve/reject any expenses
- ❌ **CANNOT** approve/reject their own expenses
- ❌ **CANNOT** perform bulk operations

## Testing

### Automated Test

Run the self-approval prevention test:

```bash
cd backend
../.venv/Scripts/python.exe scripts/test_self_approval_prevention.py
```

Expected output:
```
Testing Self-Approval Prevention
================================================================================

Test 1: Admin trying to approve their own expense
  [PASS] Admin self-approval blocked: True

Test 2: Admin trying to approve employee's expense
  [PASS] Admin can approve other's expense: True

Test 3: Manager trying to approve their own expense
  [PASS] Manager self-approval blocked: True

Test 4: Manager trying to approve employee's expense ($100)
  [PASS] Manager can approve other's expense: True

Test 5: Employee trying to approve another employee's expense
  [PASS] Employee cannot approve expenses: True

Test 6: Employee trying to approve their own expense
  [PASS] Employee self-approval blocked: True

================================================================================
Summary:
  - Self-approval prevention is working correctly
  - Admins and managers CANNOT approve/reject their own expenses
  - Approval permissions work correctly for other users' expenses
```

### Manual Testing

1. Login as admin (`admintest / AgentTest!`)
2. Create an expense
3. Try to approve it → Should fail with: "Not authorized to approve this expense"

## API Response

When a user tries to approve/reject their own expense, they receive:

```json
{
  "detail": "Not authorized to approve this expense"
}
```

HTTP Status: `403 Forbidden`

## Security Implications

This feature ensures:

1. **Separation of Duties**: No single person can both submit and approve an expense
2. **Audit Trail Integrity**: All approvals have a distinct approver different from the submitter
3. **Compliance**: Meets financial control requirements for approval workflows
4. **Fraud Prevention**: Prevents users from self-approving fraudulent expenses

## Implementation Details

### Permission Check Order

The `can_approve_expense()` function checks in this order:

1. **Self-approval check** (FIRST - always blocks)
   ```python
   if user_id == expense_user_id:
       return False
   ```

2. **Role-based permissions** (ADMIN can approve all)
   ```python
   if has_permission(user_role, Permission.EXPENSE_APPROVE_ALL):
       return True
   ```

3. **Department and amount limits** (MANAGER restrictions)
   ```python
   if has_permission(user_role, Permission.EXPENSE_APPROVE_DEPARTMENT):
       # Check department match
       # Check $5,000 limit
   ```

### Why It Cannot Be Bypassed

- The check compares **user IDs** (not usernames or roles)
- It happens **before** any role-based logic
- It returns `False` immediately upon detection
- There is **no override** mechanism
- Even bulk operations check each expense individually

## Edge Cases Handled

### Case 1: Admin Creates and Tries to Approve
- **Scenario**: Admin creates expense, then tries to approve it
- **Result**: ❌ Blocked - self-approval prevention applies to all roles

### Case 2: Bulk Approval Including Own Expense
- **Scenario**: Manager selects 10 expenses (including their own) for bulk approval
- **Result**: ⚠️ 9 expenses approved, 1 (their own) skipped with error message

### Case 3: Department Manager's Own Expense
- **Scenario**: Department manager's expense needs approval
- **Result**: ✅ Must be approved by admin or another manager (from different department)

## Modifying the Behavior

**⚠️ WARNING**: This is a security feature. Modifying it could compromise financial controls.

If you absolutely need to change this behavior, edit `backend/src/permissions.py:442-444`:

```python
# Cannot approve own expense
if user_id == expense_user_id:
    return False  # Change this logic carefully
```

**Recommended**: Never disable this check. Instead, implement a "delegate approval" system if needed.

## Related Documentation

- [Permissions System](./PERMISSIONS.md)
- [Expense Workflow](./EXPENSE_WORKFLOW.md)
- [Admin Testing Guide](../docs/ADMIN_TESTING.md)
