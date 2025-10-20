# 🔐 Permission System Documentation

## Overview

The AP2 Expense Management system uses a **capability-based RBAC (Role-Based Access Control)** system that provides:

- ✅ Granular permissions for fine-grained control
- ✅ Flexible role definitions
- ✅ Easy-to-use decorators for route protection
- ✅ Extensible permission system
- ✅ Clear audit trails

---

## Permission Architecture

### **Core Concepts**

1. **Permissions (Capabilities)** - What can be done (e.g., `EXPENSE_APPROVE_ALL`)
2. **Roles** - Who users are (e.g., `ADMIN`, `MANAGER`, `EMPLOYEE`)
3. **Role-Permission Mapping** - Which roles have which permissions
4. **Permission Checks** - Enforcement in routes

---

## Quick Start

### **1. Check Permission in Route**

```python
from src.permissions import Permission, check_permission

@app.post("/api/v1/expenses/approve")
async def approve_expense(
    current_user: User = Depends(get_current_active_user)
):
    # Check if user can approve expenses
    check_permission(
        current_user.role,
        Permission.EXPENSE_APPROVE_ALL,
        raise_exception=True  # Raises HTTPException if denied
    )

    # ... approve logic ...
```

### **2. Use Permission Decorator**

```python
from src.permissions import require_permission, Permission

@router.get("/expenses/all")
@require_permission(Permission.EXPENSE_VIEW_ALL)
async def get_all_expenses(current_user: User = Depends(get_current_user)):
    # Only users with EXPENSE_VIEW_ALL permission can access
    return expenses
```

### **3. Check Multiple Permissions**

```python
from src.permissions import require_any_permission, Permission

@router.post("/expenses/approve")
@require_any_permission(
    Permission.EXPENSE_APPROVE_DEPARTMENT,
    Permission.EXPENSE_APPROVE_ALL
)
async def approve_expense(current_user: User = Depends(get_current_user)):
    # Managers OR Admins can approve
    return result
```

---

## Permission Reference

### **Expense Permissions**

| Permission | Employee | Manager | Accountant | Admin |
|------------|:--------:|:-------:|:----------:|:-----:|
| `EXPENSE_SUBMIT` | ✅ | ✅ | ✅ | ✅ |
| `EXPENSE_VIEW_OWN` | ✅ | ✅ | ✅ | ✅ |
| `EXPENSE_VIEW_DEPARTMENT` | ❌ | ✅ | ❌ | ✅ |
| `EXPENSE_VIEW_ALL` | ❌ | ❌ | ✅ | ✅ |
| `EXPENSE_EDIT_OWN` | ✅ | ✅ | ✅ | ✅ |
| `EXPENSE_EDIT_DEPARTMENT` | ❌ | ✅ | ❌ | ✅ |
| `EXPENSE_APPROVE_DEPARTMENT` | ❌ | ✅ | ❌ | ✅ |
| `EXPENSE_APPROVE_ALL` | ❌ | ❌ | ❌ | ✅ |
| `EXPENSE_BULK_APPROVE` | ❌ | ✅ | ❌ | ✅ |

### **User Permissions**

| Permission | Employee | Manager | Accountant | Admin |
|------------|:--------:|:-------:|:----------:|:-----:|
| `USER_VIEW_OWN` | ✅ | ✅ | ✅ | ✅ |
| `USER_VIEW_DEPARTMENT` | ❌ | ✅ | ❌ | ✅ |
| `USER_VIEW_ALL` | ❌ | ❌ | ✅ | ✅ |
| `USER_CREATE` | ❌ | ❌ | ❌ | ✅ |
| `USER_EDIT_ALL` | ❌ | ❌ | ❌ | ✅ |
| `USER_CHANGE_ROLE` | ❌ | ❌ | ❌ | ✅ |
| `USER_SUSPEND` | ❌ | ❌ | ❌ | ✅ |

### **System Permissions**

| Permission | Employee | Manager | Accountant | Admin |
|------------|:--------:|:-------:|:----------:|:-----:|
| `SYSTEM_CONFIGURE` | ❌ | ❌ | ❌ | ✅ |
| `SYSTEM_MAINTENANCE` | ❌ | ❌ | ❌ | ✅ |
| `SYSTEM_HEALTH` | ❌ | ❌ | ❌ | ✅ |
| `REPORT_EXPORT` | ❌ | ✅ | ✅ | ✅ |
| `BILLING_MANAGE` | ❌ | ❌ | ❌ | ✅ |

---

## Role Definitions

### **🟢 EMPLOYEE**
**Purpose:** Submit and track personal expenses

**Can:**
- Submit expenses
- View/edit/delete own expenses
- Upload receipts
- Add comments to own expenses
- View own reports

**Cannot:**
- Approve/reject expenses
- View other users' expenses
- Access admin features

---

### **🟡 MANAGER**
**Purpose:** Oversee department expenses and approvals

**Can:**
- All employee permissions
- Approve/reject department expenses (up to $5,000)
- View department expenses
- Bulk approve/reject
- View department reports
- Export reports

**Cannot:**
- Manage users
- Access system settings
- Approve expenses over $5,000
- View other departments (future feature)

**Approval Limit:** $5,000 per expense

---

### **🔵 ACCOUNTANT**
**Purpose:** Financial oversight and reporting

**Can:**
- View all expenses (read-only)
- View all reports
- Export financial data
- View audit logs
- Access billing information

**Cannot:**
- Approve/reject expenses (optional)
- Manage users
- Access system settings

---

### **🔴 ADMIN**
**Purpose:** System administration

**Can:**
- **Everything** - all permissions
- Manage users (create, suspend, delete, change roles)
- Configure system settings
- Perform database maintenance
- Approve expenses of any amount
- Access all data

---

## Usage Examples

### **Example 1: Basic Permission Check**

```python
from src.permissions import has_permission, Permission

def some_business_logic(current_user: User):
    # Check if user can view all expenses
    if has_permission(current_user.role, Permission.EXPENSE_VIEW_ALL):
        expenses = get_all_expenses()
    else:
        expenses = get_user_expenses(current_user.id)

    return expenses
```

### **Example 2: Conditional Logic Based on Role**

```python
from src.permissions import has_permission, Permission

@app.get("/expenses")
async def get_expenses(current_user: User = Depends(get_current_user)):
    # Employees see own expenses
    if has_permission(current_user.role, Permission.EXPENSE_VIEW_OWN) and \
       not has_permission(current_user.role, Permission.EXPENSE_VIEW_ALL):
        return get_user_expenses(current_user.id)

    # Managers see department expenses
    elif has_permission(current_user.role, Permission.EXPENSE_VIEW_DEPARTMENT):
        return get_department_expenses(current_user.department_id)

    # Admins/Accountants see all expenses
    elif has_permission(current_user.role, Permission.EXPENSE_VIEW_ALL):
        return get_all_expenses()

    else:
        raise HTTPException(403, "Access denied")
```

### **Example 3: Complex Approval Logic**

```python
from src.permissions import can_approve_expense

@app.post("/expenses/approve")
async def approve_expense(
    expense_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()

    # Check if user can approve this specific expense
    if can_approve_expense(
        user_role=current_user.role,
        expense_amount=expense.amount,
        expense_user_id=expense.user_id,
        user_id=current_user.id
    ):
        # Approve the expense
        expense.status = ExpenseStatus.APPROVED
        db.commit()
        return {"success": True}
```

### **Example 4: Using Decorators**

```python
from src.permissions import (
    require_permission,
    require_any_permission,
    Permission
)

# Single permission required
@router.delete("/users/{user_id}")
@require_permission(Permission.USER_DELETE)
async def delete_user(user_id: str, current_user: User = Depends(get_current_user)):
    # Only admins can delete users
    delete_user_from_db(user_id)

# Any of the permissions required
@router.get("/reports/export")
@require_any_permission(
    Permission.REPORT_VIEW_DEPARTMENT,
    Permission.REPORT_VIEW_ALL
)
async def export_report(current_user: User = Depends(get_current_user)):
    # Managers or Admins/Accountants can export
    return generate_report()
```

---

## Advanced Features

### **Manager Approval Limits**

Managers have a $5,000 approval limit per expense:

```python
MANAGER_APPROVAL_LIMIT = 5000.00

# In can_approve_expense():
if user_role == UserRole.MANAGER:
    if expense_amount > MANAGER_APPROVAL_LIMIT:
        raise HTTPException(
            403,
            f"Expenses over ${MANAGER_APPROVAL_LIMIT} require admin approval"
        )
```

### **Department Scoping (Future)**

When implemented, managers will only see their department:

```python
# TODO: Add department filtering
if user_role == UserRole.MANAGER:
    expenses = db.query(Expense).filter(
        Expense.department_id == current_user.department_id
    ).all()
```

---

## Adding New Permissions

### **Step 1: Define Permission**

```python
# In src/permissions.py
class Permission(str, Enum):
    # ... existing permissions ...

    # New permission
    EXPENSE_EXPORT_PDF = "expense:export_pdf"
```

### **Step 2: Add to Role Mapping**

```python
ROLE_PERMISSIONS: dict[UserRole, Set[Permission]] = {
    UserRole.MANAGER: {
        # ... existing permissions ...
        Permission.EXPENSE_EXPORT_PDF,  # Add here
    },
}
```

### **Step 3: Use in Route**

```python
@router.get("/expenses/{expense_id}/export/pdf")
@require_permission(Permission.EXPENSE_EXPORT_PDF)
async def export_expense_pdf(expense_id: str):
    return generate_pdf(expense_id)
```

---

## Migration Guide

### **Migrating Old Code**

**Before (role-based check):**
```python
if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
    raise HTTPException(403, "Not authorized")
```

**After (permission-based check):**
```python
from src.permissions import check_permission, Permission

check_permission(
    current_user.role,
    Permission.EXPENSE_APPROVE_DEPARTMENT,
    raise_exception=True
)
```

**Why better?**
- ✅ More readable - clear what permission is needed
- ✅ More maintainable - permissions defined in one place
- ✅ More flexible - easy to add new roles without changing code
- ✅ Better audit - clear permission denied messages

---

## Testing Permissions

```python
from src.permissions import has_permission, Permission, UserRole

def test_manager_can_approve_department():
    assert has_permission(
        UserRole.MANAGER,
        Permission.EXPENSE_APPROVE_DEPARTMENT
    ) == True

def test_employee_cannot_approve():
    assert has_permission(
        UserRole.EMPLOYEE,
        Permission.EXPENSE_APPROVE_DEPARTMENT
    ) == False

def test_admin_has_all_permissions():
    for permission in Permission:
        assert has_permission(UserRole.ADMIN, permission) == True
```

---

## Best Practices

### **✅ DO:**
- Use permissions, not roles in route logic
- Use decorators for simple checks
- Use helper functions for complex logic
- Document permission requirements
- Test permission checks

### **❌ DON'T:**
- Hardcode role checks (`if role == "admin"`)
- Mix permission and role checks
- Grant permissions without justification
- Forget to update documentation

---

## Permission Naming Convention

**Format:** `RESOURCE_ACTION_SCOPE`

**Examples:**
- `EXPENSE_VIEW_OWN` - View own expenses
- `EXPENSE_VIEW_DEPARTMENT` - View department expenses
- `EXPENSE_VIEW_ALL` - View all expenses
- `USER_CREATE` - Create users
- `SYSTEM_CONFIGURE` - Configure system

**Scopes:**
- `OWN` - User's own resources
- `DEPARTMENT` - Department/team resources
- `ALL` - All resources (company-wide)
- (no scope) - General action

---

## Future Enhancements

1. **Department-based filtering** - Restrict managers to their department
2. **Custom approval workflows** - Multi-level approvals
3. **Time-based permissions** - Temporary elevated access
4. **Resource-level permissions** - Per-expense permissions
5. **Permission inheritance** - Hierarchical roles
6. **Dynamic permissions** - Runtime permission grants

---

## Support

For questions or issues:
1. Check this documentation
2. Review `src/permissions.py` for implementation details
3. Test with different roles to understand behavior
4. Contact system administrator for permission changes
