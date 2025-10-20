"""
Role-Based Access Control (RBAC) system for AP2 Expense Management.

This module provides a flexible, capability-based permission system that:
- Defines granular permissions (capabilities)
- Maps roles to permissions
- Provides decorators for route protection
- Supports custom permission checks
"""

from enum import Enum
from functools import wraps
from typing import Callable, List, Optional, Set

from fastapi import HTTPException, status

from .models import UserRole


# ============================================================================
# PERMISSION DEFINITIONS
# ============================================================================


class Permission(str, Enum):
    """
    Granular permissions (capabilities) in the system.

    Naming convention: RESOURCE_ACTION
    Examples: EXPENSE_APPROVE, USER_CREATE, SYSTEM_CONFIGURE
    """

    # ===== EXPENSE PERMISSIONS =====
    EXPENSE_SUBMIT = "expense:submit"
    EXPENSE_VIEW_OWN = "expense:view_own"
    EXPENSE_VIEW_DEPARTMENT = "expense:view_department"
    EXPENSE_VIEW_ALL = "expense:view_all"
    EXPENSE_EDIT_OWN = "expense:edit_own"
    EXPENSE_EDIT_DEPARTMENT = "expense:edit_department"
    EXPENSE_EDIT_ALL = "expense:edit_all"
    EXPENSE_DELETE_OWN = "expense:delete_own"
    EXPENSE_DELETE_ALL = "expense:delete_all"
    EXPENSE_APPROVE_DEPARTMENT = "expense:approve_department"
    EXPENSE_APPROVE_ALL = "expense:approve_all"
    EXPENSE_REJECT_DEPARTMENT = "expense:reject_department"
    EXPENSE_REJECT_ALL = "expense:reject_all"
    EXPENSE_BULK_APPROVE = "expense:bulk_approve"
    EXPENSE_BULK_REJECT = "expense:bulk_reject"

    # ===== COMMENT PERMISSIONS =====
    COMMENT_CREATE = "comment:create"
    COMMENT_VIEW = "comment:view"
    COMMENT_EDIT_OWN = "comment:edit_own"
    COMMENT_DELETE_OWN = "comment:delete_own"
    COMMENT_DELETE_ANY = "comment:delete_any"

    # ===== RECEIPT PERMISSIONS =====
    RECEIPT_UPLOAD = "receipt:upload"
    RECEIPT_VIEW_OWN = "receipt:view_own"
    RECEIPT_VIEW_ALL = "receipt:view_all"
    RECEIPT_DELETE_OWN = "receipt:delete_own"
    RECEIPT_DELETE_ALL = "receipt:delete_all"

    # ===== USER PERMISSIONS =====
    USER_VIEW_OWN = "user:view_own"
    USER_VIEW_DEPARTMENT = "user:view_department"
    USER_VIEW_ALL = "user:view_all"
    USER_CREATE = "user:create"
    USER_EDIT_OWN = "user:edit_own"
    USER_EDIT_ALL = "user:edit_all"
    USER_DELETE = "user:delete"
    USER_CHANGE_ROLE = "user:change_role"
    USER_SUSPEND = "user:suspend"
    USER_UNLOCK = "user:unlock"

    # ===== REPORT PERMISSIONS =====
    REPORT_VIEW_OWN = "report:view_own"
    REPORT_VIEW_DEPARTMENT = "report:view_department"
    REPORT_VIEW_ALL = "report:view_all"
    REPORT_EXPORT = "report:export"

    # ===== AUDIT PERMISSIONS =====
    AUDIT_VIEW_OWN = "audit:view_own"
    AUDIT_VIEW_DEPARTMENT = "audit:view_department"
    AUDIT_VIEW_ALL = "audit:view_all"

    # ===== SYSTEM PERMISSIONS =====
    SYSTEM_CONFIGURE = "system:configure"
    SYSTEM_MAINTENANCE = "system:maintenance"
    SYSTEM_HEALTH = "system:health"
    SYSTEM_ANALYTICS = "system:analytics"

    # ===== ORGANIZATION PERMISSIONS =====
    ORG_CREATE = "org:create"
    ORG_VIEW = "org:view"
    ORG_EDIT = "org:edit"
    ORG_DELETE = "org:delete"
    ORG_MANAGE_MEMBERS = "org:manage_members"

    # ===== BILLING PERMISSIONS =====
    BILLING_VIEW = "billing:view"
    BILLING_MANAGE = "billing:manage"


# ============================================================================
# ROLE-TO-PERMISSION MAPPINGS
# ============================================================================

# Define employee permissions first
_EMPLOYEE_PERMISSIONS = {
    # Expenses - Own only
    Permission.EXPENSE_SUBMIT,
    Permission.EXPENSE_VIEW_OWN,
    Permission.EXPENSE_EDIT_OWN,
    Permission.EXPENSE_DELETE_OWN,

    # Comments
    Permission.COMMENT_CREATE,
    Permission.COMMENT_VIEW,
    Permission.COMMENT_EDIT_OWN,
    Permission.COMMENT_DELETE_OWN,

    # Receipts
    Permission.RECEIPT_UPLOAD,
    Permission.RECEIPT_VIEW_OWN,
    Permission.RECEIPT_DELETE_OWN,

    # Users
    Permission.USER_VIEW_OWN,
    Permission.USER_EDIT_OWN,

    # Reports
    Permission.REPORT_VIEW_OWN,

    # Audit
    Permission.AUDIT_VIEW_OWN,
}

ROLE_PERMISSIONS: dict[UserRole, Set[Permission]] = {

    # ===== EMPLOYEE ROLE =====
    UserRole.EMPLOYEE: _EMPLOYEE_PERMISSIONS,

    # ===== MANAGER ROLE =====
    UserRole.MANAGER: {
        # All employee permissions
        *_EMPLOYEE_PERMISSIONS,

        # Expenses - View all, approve/edit department only (with $5K limit)
        Permission.EXPENSE_VIEW_ALL,  # Can VIEW all expenses for visibility
        Permission.EXPENSE_VIEW_DEPARTMENT,
        Permission.EXPENSE_EDIT_DEPARTMENT,
        Permission.EXPENSE_APPROVE_DEPARTMENT,  # But can only APPROVE ≤ $5,000
        Permission.EXPENSE_REJECT_DEPARTMENT,
        Permission.EXPENSE_BULK_APPROVE,
        Permission.EXPENSE_BULK_REJECT,

        # Receipts - Department
        Permission.RECEIPT_VIEW_ALL,

        # Users - Department
        Permission.USER_VIEW_DEPARTMENT,

        # Reports - Department
        Permission.REPORT_VIEW_DEPARTMENT,
        Permission.REPORT_EXPORT,

        # Audit - Department
        Permission.AUDIT_VIEW_DEPARTMENT,
    },

    # ===== ADMIN ROLE =====
    UserRole.ADMIN: {
        # All permissions (superuser)
        *[p for p in Permission],
    },
}


# ============================================================================
# PERMISSION CHECKER FUNCTIONS
# ============================================================================


def has_permission(user_role: UserRole, permission: Permission) -> bool:
    """
    Check if a user role has a specific permission.

    Args:
        user_role: The user's role (EMPLOYEE, MANAGER, etc.)
        permission: The permission to check

    Returns:
        True if the role has the permission, False otherwise
    """
    return permission in ROLE_PERMISSIONS.get(user_role, set())


def has_any_permission(user_role: UserRole, permissions: List[Permission]) -> bool:
    """
    Check if a user role has ANY of the specified permissions.

    Args:
        user_role: The user's role
        permissions: List of permissions to check

    Returns:
        True if the role has at least one permission, False otherwise
    """
    user_permissions = ROLE_PERMISSIONS.get(user_role, set())
    return any(p in user_permissions for p in permissions)


def has_all_permissions(user_role: UserRole, permissions: List[Permission]) -> bool:
    """
    Check if a user role has ALL of the specified permissions.

    Args:
        user_role: The user's role
        permissions: List of permissions to check

    Returns:
        True if the role has all permissions, False otherwise
    """
    user_permissions = ROLE_PERMISSIONS.get(user_role, set())
    return all(p in user_permissions for p in permissions)


def get_user_permissions(user_role: UserRole) -> Set[Permission]:
    """
    Get all permissions for a user role.

    Args:
        user_role: The user's role

    Returns:
        Set of all permissions for the role
    """
    return ROLE_PERMISSIONS.get(user_role, set())


# ============================================================================
# PERMISSION DECORATORS
# ============================================================================


def require_permission(permission: Permission):
    """
    Decorator to require a specific permission for a route.

    Usage:
        @router.get("/expenses/all")
        @require_permission(Permission.EXPENSE_VIEW_ALL)
        async def get_all_expenses(current_user: User = Depends(get_current_user)):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current_user from kwargs
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            # Check permission
            if not has_permission(current_user.role, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission.value} required"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_any_permission(*permissions: Permission):
    """
    Decorator to require ANY of the specified permissions.

    Usage:
        @require_any_permission(
            Permission.EXPENSE_APPROVE_DEPARTMENT,
            Permission.EXPENSE_APPROVE_ALL
        )
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            if not has_any_permission(current_user.role, list(permissions)):
                perms_str = ", ".join([p.value for p in permissions])
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: one of [{perms_str}] required"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_all_permissions(*permissions: Permission):
    """
    Decorator to require ALL of the specified permissions.

    Usage:
        @require_all_permissions(
            Permission.EXPENSE_VIEW_ALL,
            Permission.REPORT_EXPORT
        )
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            if not has_all_permissions(current_user.role, list(permissions)):
                perms_str = ", ".join([p.value for p in permissions])
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: all of [{perms_str}] required"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


# ============================================================================
# HELPER FUNCTIONS FOR ROUTES
# ============================================================================


def check_permission(user_role: UserRole, permission: Permission,
                     raise_exception: bool = True) -> bool:
    """
    Check permission and optionally raise HTTPException.

    Args:
        user_role: The user's role
        permission: The permission to check
        raise_exception: If True, raises HTTPException on failure

    Returns:
        True if permission granted, False otherwise

    Raises:
        HTTPException: If permission denied and raise_exception=True
    """
    has_perm = has_permission(user_role, permission)

    if not has_perm and raise_exception:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {permission.value} required"
        )

    return has_perm


def check_expense_access(user_role: UserRole, user_id: str,
                         expense_user_id: str, user_department_id: Optional[str] = None,
                         expense_owner_department_id: Optional[str] = None) -> bool:
    """
    Check if user can access an expense based on role and ownership.

    Args:
        user_role: The user's role
        user_id: The current user's ID
        expense_user_id: The ID of the expense owner
        user_department_id: The current user's department ID (optional)
        expense_owner_department_id: The expense owner's department ID (optional)

    Returns:
        True if user can access the expense

    Raises:
        HTTPException: If access denied
    """
    # All expenses (admin/accountant) - check first to bypass department restrictions
    if has_permission(user_role, Permission.EXPENSE_VIEW_ALL):
        return True

    # Own expense
    if user_id == expense_user_id:
        if has_permission(user_role, Permission.EXPENSE_VIEW_OWN):
            return True

    # Department expenses (manager)
    if has_permission(user_role, Permission.EXPENSE_VIEW_DEPARTMENT):
        # Check if user and expense owner are in the same department
        if user_department_id and expense_owner_department_id:
            if user_department_id == expense_owner_department_id:
                return True
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only view expenses from your department"
                )
        # If departments not set, allow access (backward compatibility)
        return True

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You don't have permission to access this expense"
    )


def can_approve_expense(user_role: UserRole, expense_amount: float,
                        expense_user_id: str, user_id: str,
                        user_department_id: Optional[str] = None,
                        expense_owner_department_id: Optional[str] = None) -> bool:
    """
    Check if user can approve an expense with advanced logic.

    Args:
        user_role: The user's role
        expense_amount: The expense amount
        expense_user_id: The expense owner's ID
        user_id: The current user's ID
        user_department_id: The current user's department ID (optional)
        expense_owner_department_id: The expense owner's department ID (optional)

    Returns:
        True if user can approve the expense
    """
    # Cannot approve own expense
    if user_id == expense_user_id:
        return False

    # Admin can approve all
    if has_permission(user_role, Permission.EXPENSE_APPROVE_ALL):
        return True

    # Manager can approve department expenses (with optional amount limit)
    if has_permission(user_role, Permission.EXPENSE_APPROVE_DEPARTMENT):
        # Check department match if departments are set
        if user_department_id and expense_owner_department_id:
            if user_department_id != expense_owner_department_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only approve expenses from your department"
                )

        # Check amount limit for managers
        MANAGER_APPROVAL_LIMIT = 5000.00
        if expense_amount <= MANAGER_APPROVAL_LIMIT:
            return True
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Expenses over ${MANAGER_APPROVAL_LIMIT} require admin approval"
            )

    return False
