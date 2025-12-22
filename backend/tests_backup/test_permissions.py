"""
Unit tests for the RBAC permission system.

Tests cover:
- Permission checking (has_permission, has_any_permission, has_all_permissions)
- Role-permission mappings
- Expense approval logic (can_approve_expense)
- Department-based filtering
- Manager approval limits
- Self-approval prevention
"""

import pytest
from fastapi import HTTPException

from src.models import UserRole
from src.permissions import (
    Permission,
    has_permission,
    has_any_permission,
    has_all_permissions,
    get_user_permissions,
    check_permission,
    check_expense_access,
    can_approve_expense,
    ROLE_PERMISSIONS,
)


class TestBasicPermissionChecks:
    """Test basic permission checking functions"""

    def test_employee_has_own_permissions(self):
        """Employee should have permission to view their own expenses"""
        assert has_permission(UserRole.EMPLOYEE, Permission.EXPENSE_VIEW_OWN) is True
        assert has_permission(UserRole.EMPLOYEE, Permission.EXPENSE_SUBMIT) is True
        assert has_permission(UserRole.EMPLOYEE, Permission.EXPENSE_EDIT_OWN) is True

    def test_employee_cannot_approve(self):
        """Employee should NOT have approval permissions"""
        assert has_permission(UserRole.EMPLOYEE, Permission.EXPENSE_APPROVE_DEPARTMENT) is False
        assert has_permission(UserRole.EMPLOYEE, Permission.EXPENSE_APPROVE_ALL) is False

    def test_employee_cannot_view_all(self):
        """Employee should NOT be able to view all expenses"""
        assert has_permission(UserRole.EMPLOYEE, Permission.EXPENSE_VIEW_ALL) is False
        assert has_permission(UserRole.EMPLOYEE, Permission.EXPENSE_VIEW_DEPARTMENT) is False

    def test_manager_can_approve_department(self):
        """Manager should be able to approve department expenses"""
        assert has_permission(UserRole.MANAGER, Permission.EXPENSE_APPROVE_DEPARTMENT) is True
        assert has_permission(UserRole.MANAGER, Permission.EXPENSE_REJECT_DEPARTMENT) is True
        assert has_permission(UserRole.MANAGER, Permission.EXPENSE_BULK_APPROVE) is True

    def test_manager_cannot_approve_all(self):
        """Manager should NOT be able to approve all expenses (admin-only)"""
        assert has_permission(UserRole.MANAGER, Permission.EXPENSE_APPROVE_ALL) is False

    def test_manager_inherits_employee_permissions(self):
        """Manager should have all employee permissions"""
        assert has_permission(UserRole.MANAGER, Permission.EXPENSE_VIEW_OWN) is True
        assert has_permission(UserRole.MANAGER, Permission.EXPENSE_SUBMIT) is True
        assert has_permission(UserRole.MANAGER, Permission.EXPENSE_EDIT_OWN) is True

    def test_accountant_can_view_all(self):
        """Accountant should be able to view all expenses"""
        assert has_permission(UserRole.ACCOUNTANT, Permission.EXPENSE_VIEW_ALL) is True
        assert has_permission(UserRole.ACCOUNTANT, Permission.REPORT_VIEW_ALL) is True

    def test_accountant_cannot_approve(self):
        """Accountant should NOT be able to approve expenses (read-only)"""
        assert has_permission(UserRole.ACCOUNTANT, Permission.EXPENSE_APPROVE_DEPARTMENT) is False
        assert has_permission(UserRole.ACCOUNTANT, Permission.EXPENSE_APPROVE_ALL) is False

    def test_admin_has_all_permissions(self):
        """Admin should have ALL permissions"""
        for permission in Permission:
            assert has_permission(UserRole.ADMIN, permission) is True

    def test_admin_can_manage_users(self):
        """Admin should be able to manage users"""
        assert has_permission(UserRole.ADMIN, Permission.USER_CREATE) is True
        assert has_permission(UserRole.ADMIN, Permission.USER_CHANGE_ROLE) is True
        assert has_permission(UserRole.ADMIN, Permission.USER_DELETE) is True
        assert has_permission(UserRole.ADMIN, Permission.SYSTEM_CONFIGURE) is True


class TestMultiplePermissionChecks:
    """Test has_any_permission and has_all_permissions functions"""

    def test_has_any_permission_manager(self):
        """Manager should have at least one approval permission"""
        assert has_any_permission(
            UserRole.MANAGER,
            [Permission.EXPENSE_APPROVE_DEPARTMENT, Permission.EXPENSE_APPROVE_ALL]
        ) is True

    def test_has_any_permission_employee(self):
        """Employee should NOT have any approval permissions"""
        assert has_any_permission(
            UserRole.EMPLOYEE,
            [Permission.EXPENSE_APPROVE_DEPARTMENT, Permission.EXPENSE_APPROVE_ALL]
        ) is False

    def test_has_all_permissions_admin(self):
        """Admin should have all specified permissions"""
        assert has_all_permissions(
            UserRole.ADMIN,
            [Permission.EXPENSE_APPROVE_ALL, Permission.USER_CREATE, Permission.SYSTEM_CONFIGURE]
        ) is True

    def test_has_all_permissions_manager_fails(self):
        """Manager should NOT have all admin permissions"""
        assert has_all_permissions(
            UserRole.MANAGER,
            [Permission.EXPENSE_APPROVE_ALL, Permission.USER_CREATE]
        ) is False


class TestGetUserPermissions:
    """Test get_user_permissions function"""

    def test_get_employee_permissions(self):
        """Get all employee permissions"""
        perms = get_user_permissions(UserRole.EMPLOYEE)
        assert Permission.EXPENSE_VIEW_OWN in perms
        assert Permission.EXPENSE_SUBMIT in perms
        assert Permission.EXPENSE_APPROVE_DEPARTMENT not in perms

    def test_get_admin_permissions(self):
        """Admin should have all permissions"""
        perms = get_user_permissions(UserRole.ADMIN)
        assert len(perms) == len(list(Permission))


class TestCheckPermissionWithException:
    """Test check_permission function that raises exceptions"""

    def test_check_permission_success(self):
        """Should return True when permission granted"""
        result = check_permission(
            UserRole.MANAGER,
            Permission.EXPENSE_APPROVE_DEPARTMENT,
            raise_exception=True
        )
        assert result is True

    def test_check_permission_failure_raises(self):
        """Should raise HTTPException when permission denied"""
        with pytest.raises(HTTPException) as exc_info:
            check_permission(
                UserRole.EMPLOYEE,
                Permission.EXPENSE_APPROVE_DEPARTMENT,
                raise_exception=True
            )
        assert exc_info.value.status_code == 403
        assert "Permission denied" in exc_info.value.detail

    def test_check_permission_failure_no_raise(self):
        """Should return False when raise_exception=False"""
        result = check_permission(
            UserRole.EMPLOYEE,
            Permission.EXPENSE_APPROVE_DEPARTMENT,
            raise_exception=False
        )
        assert result is False


class TestExpenseAccessControl:
    """Test check_expense_access function"""

    def test_employee_can_access_own_expense(self):
        """Employee should be able to access their own expense"""
        result = check_expense_access(
            user_role=UserRole.EMPLOYEE,
            user_id="user123",
            expense_user_id="user123"
        )
        assert result is True

    def test_employee_cannot_access_others_expense(self):
        """Employee should NOT be able to access other users' expenses"""
        with pytest.raises(HTTPException) as exc_info:
            check_expense_access(
                user_role=UserRole.EMPLOYEE,
                user_id="user123",
                expense_user_id="user456"
            )
        assert exc_info.value.status_code == 403

    def test_manager_can_access_department_expense_same_dept(self):
        """Manager should be able to access expenses from their department"""
        result = check_expense_access(
            user_role=UserRole.MANAGER,
            user_id="manager123",
            expense_user_id="employee456",
            user_department_id="sales",
            expense_owner_department_id="sales"
        )
        assert result is True

    def test_manager_cannot_access_different_department(self):
        """Manager should NOT be able to access expenses from other departments"""
        with pytest.raises(HTTPException) as exc_info:
            check_expense_access(
                user_role=UserRole.MANAGER,
                user_id="manager123",
                expense_user_id="employee456",
                user_department_id="sales",
                expense_owner_department_id="engineering"
            )
        assert exc_info.value.status_code == 403
        assert "department" in exc_info.value.detail.lower()

    def test_admin_can_access_any_expense(self):
        """Admin should be able to access ANY expense"""
        result = check_expense_access(
            user_role=UserRole.ADMIN,
            user_id="admin123",
            expense_user_id="employee456",
            user_department_id="engineering",
            expense_owner_department_id="sales"
        )
        assert result is True

    def test_accountant_can_access_any_expense(self):
        """Accountant should be able to access ANY expense (read-only)"""
        result = check_expense_access(
            user_role=UserRole.ACCOUNTANT,
            user_id="accountant123",
            expense_user_id="employee456"
        )
        assert result is True


class TestExpenseApprovalLogic:
    """Test can_approve_expense function with various scenarios"""

    def test_cannot_approve_own_expense(self):
        """Users should NOT be able to approve their own expenses"""
        result = can_approve_expense(
            user_role=UserRole.MANAGER,
            expense_amount=100.00,
            expense_user_id="user123",
            user_id="user123"
        )
        assert result is False

    def test_admin_can_approve_any_amount(self):
        """Admin should be able to approve expenses of any amount"""
        result = can_approve_expense(
            user_role=UserRole.ADMIN,
            expense_amount=10000.00,
            expense_user_id="employee123",
            user_id="admin456"
        )
        assert result is True

    def test_manager_can_approve_under_limit(self):
        """Manager should be able to approve expenses under $5,000"""
        result = can_approve_expense(
            user_role=UserRole.MANAGER,
            expense_amount=4999.99,
            expense_user_id="employee123",
            user_id="manager456"
        )
        assert result is True

    def test_manager_can_approve_exactly_limit(self):
        """Manager should be able to approve expenses exactly at $5,000"""
        result = can_approve_expense(
            user_role=UserRole.MANAGER,
            expense_amount=5000.00,
            expense_user_id="employee123",
            user_id="manager456"
        )
        assert result is True

    def test_manager_cannot_approve_over_limit(self):
        """Manager should NOT be able to approve expenses over $5,000"""
        with pytest.raises(HTTPException) as exc_info:
            can_approve_expense(
                user_role=UserRole.MANAGER,
                expense_amount=5000.01,
                expense_user_id="employee123",
                user_id="manager456"
            )
        assert exc_info.value.status_code == 403
        assert "5000" in exc_info.value.detail
        assert "admin approval" in exc_info.value.detail.lower()

    def test_employee_cannot_approve_any(self):
        """Employee should NOT be able to approve any expenses"""
        result = can_approve_expense(
            user_role=UserRole.EMPLOYEE,
            expense_amount=100.00,
            expense_user_id="employee123",
            user_id="employee456"
        )
        assert result is False

    def test_manager_same_department(self):
        """Manager should be able to approve expenses from their department"""
        result = can_approve_expense(
            user_role=UserRole.MANAGER,
            expense_amount=1000.00,
            expense_user_id="employee123",
            user_id="manager456",
            user_department_id="sales",
            expense_owner_department_id="sales"
        )
        assert result is True

    def test_manager_different_department(self):
        """Manager should NOT be able to approve expenses from other departments"""
        with pytest.raises(HTTPException) as exc_info:
            can_approve_expense(
                user_role=UserRole.MANAGER,
                expense_amount=1000.00,
                expense_user_id="employee123",
                user_id="manager456",
                user_department_id="sales",
                expense_owner_department_id="engineering"
            )
        assert exc_info.value.status_code == 403
        assert "department" in exc_info.value.detail.lower()


class TestDepartmentFiltering:
    """Test department-based filtering for managers"""

    def test_manager_no_departments_set_backward_compat(self):
        """When departments not set, should allow access (backward compatibility)"""
        result = check_expense_access(
            user_role=UserRole.MANAGER,
            user_id="manager123",
            expense_user_id="employee456",
            user_department_id=None,
            expense_owner_department_id=None
        )
        assert result is True

    def test_manager_partial_department_info_backward_compat(self):
        """When only one department is set, should allow access (backward compatibility)"""
        result = check_expense_access(
            user_role=UserRole.MANAGER,
            user_id="manager123",
            expense_user_id="employee456",
            user_department_id="sales",
            expense_owner_department_id=None
        )
        assert result is True

    def test_admin_ignores_department_restrictions(self):
        """Admin should bypass all department restrictions"""
        result = can_approve_expense(
            user_role=UserRole.ADMIN,
            expense_amount=10000.00,
            expense_user_id="employee123",
            user_id="admin456",
            user_department_id="engineering",
            expense_owner_department_id="sales"
        )
        assert result is True


class TestRolePermissionMappings:
    """Test that role-permission mappings are correctly defined"""

    def test_all_roles_have_mappings(self):
        """All user roles should have permission mappings"""
        for role in UserRole:
            assert role in ROLE_PERMISSIONS

    def test_employee_permission_count(self):
        """Employee should have exactly the expected permissions"""
        employee_perms = ROLE_PERMISSIONS[UserRole.EMPLOYEE]
        # Should have own permissions but not department or all
        assert Permission.EXPENSE_VIEW_OWN in employee_perms
        assert Permission.EXPENSE_VIEW_DEPARTMENT not in employee_perms
        assert Permission.EXPENSE_VIEW_ALL not in employee_perms

    def test_manager_includes_employee_perms(self):
        """Manager permissions should include all employee permissions"""
        employee_perms = ROLE_PERMISSIONS[UserRole.EMPLOYEE]
        manager_perms = ROLE_PERMISSIONS[UserRole.MANAGER]

        # All employee permissions should be in manager permissions
        for perm in employee_perms:
            assert perm in manager_perms

    def test_accountant_includes_employee_perms(self):
        """Accountant permissions should include all employee permissions"""
        employee_perms = ROLE_PERMISSIONS[UserRole.EMPLOYEE]
        accountant_perms = ROLE_PERMISSIONS[UserRole.ACCOUNTANT]

        # All employee permissions should be in accountant permissions
        for perm in employee_perms:
            assert perm in accountant_perms

    def test_admin_has_all_permissions(self):
        """Admin should have every single permission"""
        admin_perms = ROLE_PERMISSIONS[UserRole.ADMIN]
        all_permissions = set(Permission)

        assert admin_perms == all_permissions


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_manager_approval_boundary_values(self):
        """Test manager approval at exact boundary values"""
        # Just under limit
        assert can_approve_expense(
            UserRole.MANAGER, 4999.99, "emp1", "mgr1"
        ) is True

        # Exactly at limit
        assert can_approve_expense(
            UserRole.MANAGER, 5000.00, "emp1", "mgr1"
        ) is True

        # Just over limit
        with pytest.raises(HTTPException):
            can_approve_expense(
                UserRole.MANAGER, 5000.01, "emp1", "mgr1"
            )

    def test_zero_amount_expense(self):
        """Manager should be able to approve zero amount expenses"""
        result = can_approve_expense(
            user_role=UserRole.MANAGER,
            expense_amount=0.00,
            expense_user_id="employee123",
            user_id="manager456"
        )
        assert result is True

    def test_negative_amount_expense(self):
        """Manager should be able to approve negative amounts (refunds)"""
        result = can_approve_expense(
            user_role=UserRole.MANAGER,
            expense_amount=-100.00,
            expense_user_id="employee123",
            user_id="manager456"
        )
        assert result is True

    def test_very_large_amount_requires_admin(self):
        """Very large amounts should require admin approval"""
        with pytest.raises(HTTPException) as exc_info:
            can_approve_expense(
                user_role=UserRole.MANAGER,
                expense_amount=1000000.00,
                expense_user_id="employee123",
                user_id="manager456"
            )
        assert exc_info.value.status_code == 403
