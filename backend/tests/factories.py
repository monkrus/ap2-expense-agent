"""
Test Data Factories

Provides factory functions to easily create test data with specific attributes.
These factories make it easier to write comprehensive tests without repetitive setup code.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from src.auth import AuthService
from src.models import (
    Expense,
    ExpenseCategory,
    ExpenseStatus,
    Organization,
    OrganizationMember,
    OrganizationRole,
    User,
    UserRole,
)


# ============================================================================
# User Factories
# ============================================================================


def create_user(
    db_session,
    email: Optional[str] = None,
    username: Optional[str] = None,
    role: UserRole = UserRole.USER,
    password: str = "TestPass123!",
    is_active: bool = True,
    is_verified: bool = True,
    **kwargs
) -> User:
    """
    Create a test user with specified attributes.

    Args:
        db_session: Database session
        email: User email (auto-generated if None)
        username: Username (auto-generated if None)
        role: User role (default: EMPLOYEE)
        password: Plain password to hash
        is_active: Account active status
        is_verified: Email verified status
        **kwargs: Additional user attributes

    Returns:
        Created User instance
    """
    user_id = str(uuid.uuid4())
    email = email or f"user_{user_id[:8]}@test.com"
    username = username or f"user_{user_id[:8]}"

    user = User(
        id=user_id,
        email=email,
        username=username,
        full_name=kwargs.get("full_name", f"Test User {username}"),
        hashed_password=AuthService.hash_password(password),
        role=role,
        is_active=is_active,
        is_verified=is_verified,
        department_id=kwargs.get("department_id"),
        failed_login_attempts=0,
        locked_until=None,
        last_failed_login=None,
        totp_enabled=kwargs.get("totp_enabled", False),
    )
    db_session.add(user)
    db_session.flush()
    return user


def create_employee(db_session, **kwargs) -> User:
    """Create an EMPLOYEE role user"""
    return create_user(db_session, role=UserRole.USER, **kwargs)


def create_manager(db_session, department_id: str = "sales", **kwargs) -> User:
    """Create a MANAGER role user with department"""
    return create_user(db_session, role=UserRole.ADMIN, department_id=department_id, **kwargs)


def create_accountant(db_session, **kwargs) -> User:
    """Create an ACCOUNTANT role user (read-only)"""
    return create_user(db_session, role=UserRole.ADMIN, **kwargs)


def create_admin(db_session, **kwargs) -> User:
    """Create an ADMIN role user (superuser)"""
    return create_user(db_session, role=UserRole.ADMIN, **kwargs)


# ============================================================================
# Organization Factories
# ============================================================================


def create_organization(
    db_session,
    name: Optional[str] = None,
    slug: Optional[str] = None,
    is_active: bool = True,
    **kwargs
) -> Organization:
    """
    Create a test organization.

    Args:
        db_session: Database session
        name: Organization name (auto-generated if None)
        slug: Organization slug (auto-generated if None)
        is_active: Organization active status
        **kwargs: Additional organization attributes

    Returns:
        Created Organization instance
    """
    org_id = f"org_{uuid.uuid4().hex[:8]}"
    name = name or f"Test Org {org_id}"
    slug = slug or f"test-org-{uuid.uuid4().hex[:6]}"

    org = Organization(
        id=org_id,
        name=name,
        slug=slug,
        description=kwargs.get("description"),
        currency=kwargs.get("currency", "USD"),
        timezone=kwargs.get("timezone", "UTC"),
        max_members=kwargs.get("max_members", 1),
        max_expenses_per_month=kwargs.get("max_expenses_per_month"),
        is_active=is_active,
        created_at=kwargs.get("created_at", datetime.utcnow()),
    )
    db_session.add(org)
    db_session.flush()
    return org


def add_user_to_organization(
    db_session,
    user: User,
    organization: Organization,
    role: OrganizationRole = OrganizationRole.MEMBER,
    is_active: bool = True
) -> OrganizationMember:
    """
    Add a user to an organization with a specific role.

    Args:
        db_session: Database session
        user: User to add
        organization: Organization to add user to
        role: Organization role (default: MEMBER)
        is_active: Membership active status

    Returns:
        Created OrganizationMember instance
    """
    membership = OrganizationMember(
        id=str(uuid.uuid4()),
        organization_id=organization.id,
        user_id=user.id,
        role=role,
        is_active=is_active,
        joined_at=datetime.utcnow(),
    )
    db_session.add(membership)
    db_session.flush()
    return membership


def create_organization_with_owner(
    db_session,
    owner: Optional[User] = None,
    org_name: Optional[str] = None,
    **kwargs
) -> tuple[Organization, User]:
    """
    Create an organization with an owner user.

    Args:
        db_session: Database session
        owner: Existing user to make owner (creates new if None)
        org_name: Organization name
        **kwargs: Additional organization attributes

    Returns:
        Tuple of (Organization, Owner User)
    """
    if owner is None:
        owner = create_user(db_session, role=UserRole.EMPLOYEE)

    org = create_organization(db_session, name=org_name, **kwargs)
    add_user_to_organization(db_session, owner, org, OrganizationRole.OWNER)

    db_session.commit()
    db_session.refresh(org)
    db_session.refresh(owner)
    return org, owner


# ============================================================================
# Expense Factories
# ============================================================================


def create_expense(
    db_session,
    user: User,
    organization: Organization,
    amount: float = 100.0,
    status: ExpenseStatus = ExpenseStatus.PENDING,
    category: ExpenseCategory = ExpenseCategory.MEALS,
    **kwargs
) -> Expense:
    """
    Create a test expense.

    Args:
        db_session: Database session
        user: User who submitted the expense
        organization: Organization the expense belongs to
        amount: Expense amount
        status: Expense status
        category: Expense category
        **kwargs: Additional expense attributes

    Returns:
        Created Expense instance
    """
    expense = Expense(
        id=f"exp_{uuid.uuid4().hex[:8]}",
        organization_id=organization.id,
        user_id=user.id,
        amount=amount,
        vendor=kwargs.get("vendor", "Test Vendor"),
        category=category,
        description=kwargs.get("description", "Test expense"),
        status=status,
        date=kwargs.get("date", datetime.utcnow()),
        approved_by=kwargs.get("approved_by"),
        approved_at=kwargs.get("approved_at"),
        rejection_reason=kwargs.get("rejection_reason"),
        auto_approved=kwargs.get("auto_approved", False),
        created_at=kwargs.get("created_at", datetime.utcnow()),
    )
    db_session.add(expense)
    db_session.flush()
    return expense


def create_pending_expense(db_session, user: User, organization: Organization, amount: float = 100.0, **kwargs) -> Expense:
    """Create a PENDING expense"""
    return create_expense(db_session, user, organization, amount, ExpenseStatus.PENDING, **kwargs)


def create_approved_expense(db_session, user: User, organization: Organization, amount: float = 100.0, **kwargs) -> Expense:
    """Create an APPROVED expense"""
    return create_expense(db_session, user, organization, amount, ExpenseStatus.APPROVED, **kwargs)


def create_rejected_expense(db_session, user: User, organization: Organization, amount: float = 100.0, **kwargs) -> Expense:
    """Create a REJECTED expense"""
    return create_expense(db_session, user, organization, amount, ExpenseStatus.REJECTED, **kwargs)


# ============================================================================
# Complex Scenario Factories
# ============================================================================


def create_multi_tenant_scenario(
    db_session
) -> dict:
    """
    Create a complete multi-tenant test scenario with 2 organizations.

    Returns:
        Dict with all created entities:
        {
            'org1': Organization,
            'org1_owner': User (OWNER of org1),
            'org1_admin': User (ADMIN of org1),
            'org1_employee': User (MEMBER of org1),
            'org1_expense': Expense (from org1_employee),
            'org2': Organization,
            'org2_owner': User (OWNER of org2),
            'org2_expense': Expense (from org2_owner),
        }
    """
    # Organization 1 with team
    org1, org1_owner = create_organization_with_owner(db_session, org_name="Org 1")
    org1_admin = create_user(db_session, email="org1_admin@test.com")
    add_user_to_organization(db_session, org1_admin, org1, OrganizationRole.ADMIN)
    org1_employee = create_user(db_session, email="org1_emp@test.com")
    add_user_to_organization(db_session, org1_employee, org1, OrganizationRole.MEMBER)
    org1_expense = create_pending_expense(db_session, org1_employee, org1, amount=150.0)

    # Organization 2 with single owner
    org2, org2_owner = create_organization_with_owner(db_session, org_name="Org 2")
    org2_expense = create_pending_expense(db_session, org2_owner, org2, amount=250.0)

    db_session.commit()

    return {
        'org1': org1,
        'org1_owner': org1_owner,
        'org1_admin': org1_admin,
        'org1_employee': org1_employee,
        'org1_expense': org1_expense,
        'org2': org2,
        'org2_owner': org2_owner,
        'org2_expense': org2_expense,
    }


def create_manager_approval_scenario(
    db_session,
    department: str = "sales"
) -> dict:
    """
    Create a scenario for testing manager approval workflows.

    Args:
        department: Department name

    Returns:
        Dict with:
        {
            'org': Organization,
            'manager': User (MANAGER role, ADMIN org role),
            'employee_same_dept': User (EMPLOYEE, same department),
            'employee_other_dept': User (EMPLOYEE, different department),
            'expense_under_5k': Expense ($3000, from employee_same_dept),
            'expense_over_5k': Expense ($10000, from employee_same_dept),
        }
    """
    org = create_organization(db_session, name="Manager Test Org")

    # Manager in sales department
    manager = create_manager(db_session, department_id=department)
    add_user_to_organization(db_session, manager, org, OrganizationRole.ADMIN)

    # Employee in same department
    employee_same_dept = create_employee(db_session, department_id=department)
    add_user_to_organization(db_session, employee_same_dept, org, OrganizationRole.MEMBER)

    # Employee in different department
    employee_other_dept = create_employee(db_session, department_id="engineering")
    add_user_to_organization(db_session, employee_other_dept, org, OrganizationRole.MEMBER)

    # Expenses with different amounts
    expense_under_5k = create_pending_expense(db_session, employee_same_dept, org, amount=3000.0)
    expense_over_5k = create_pending_expense(db_session, employee_same_dept, org, amount=10000.0)

    db_session.commit()

    return {
        'org': org,
        'manager': manager,
        'employee_same_dept': employee_same_dept,
        'employee_other_dept': employee_other_dept,
        'expense_under_5k': expense_under_5k,
        'expense_over_5k': expense_over_5k,
    }
