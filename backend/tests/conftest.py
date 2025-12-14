"""
Pytest configuration and fixtures for testing
"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set testing environment variable BEFORE importing app
os.environ["TESTING"] = "true"

import uuid
from datetime import datetime, timedelta

from src.api import app
from src.auth import AuthService
from src.cache import cache
from src.database import get_db
from src.models import (
    Base,
    Expense,
    Organization,
    OrganizationMember,
    OrganizationRole,
    User,
    UserRole,
)
# Ensure all models (including approval policies) are registered on the metadata
import src.models_approval  # noqa: F401

# Test database setup (in-memory SQLite)
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database override"""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    """Create a test user with default organization"""
    from src.models import Organization, OrganizationMember, OrganizationRole

    user = User(
        id=str(uuid.uuid4()),
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        hashed_password=AuthService.hash_password("TestPass123!"),
        role=UserRole.EMPLOYEE,
        is_active=True,
        is_verified=True,
        failed_login_attempts=0,
        locked_until=None,
        last_failed_login=None,
    )
    db_session.add(user)
    db_session.flush()

    # Create default organization for user
    org = Organization(
        id=f"org_{uuid.uuid4().hex[:8]}",
        name="Test Organization",
        slug=f"test-org-{uuid.uuid4().hex[:6]}",
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db_session.add(org)
    db_session.flush()

    # Add user as member
    membership = OrganizationMember(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        user_id=user.id,
        role=OrganizationRole.MEMBER,
        is_active=True,
        joined_at=datetime.utcnow(),
    )
    db_session.add(membership)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_admin(db_session):
    """Create a test admin user with default organization"""
    from src.models import Organization, OrganizationMember, OrganizationRole

    admin = User(
        id=str(uuid.uuid4()),
        email="admin@example.com",
        username="admin",
        full_name="Admin User",
        hashed_password=AuthService.hash_password("AdminPass123!"),
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
        failed_login_attempts=0,
        locked_until=None,
        last_failed_login=None,
    )
    db_session.add(admin)
    db_session.flush()

    # Create default organization for admin
    org = Organization(
        id=f"org_{uuid.uuid4().hex[:8]}",
        name="Admin Organization",
        slug=f"admin-org-{uuid.uuid4().hex[:6]}",
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db_session.add(org)
    db_session.flush()

    # Add admin as owner
    membership = OrganizationMember(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        user_id=admin.id,
        role=OrganizationRole.OWNER,
        is_active=True,
        joined_at=datetime.utcnow(),
    )
    db_session.add(membership)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture
def test_manager(db_session):
    """Create a test manager user with default organization"""
    from src.models import Organization, OrganizationMember, OrganizationRole

    manager = User(
        id=str(uuid.uuid4()),
        email="manager@example.com",
        username="manager",
        full_name="Manager User",
        hashed_password=AuthService.hash_password("ManagerPass123!"),
        role=UserRole.MANAGER,
        is_active=True,
        is_verified=True,
        failed_login_attempts=0,
        locked_until=None,
        last_failed_login=None,
    )
    db_session.add(manager)
    db_session.flush()

    # Create default organization for manager
    org = Organization(
        id=f"org_{uuid.uuid4().hex[:8]}",
        name="Manager Organization",
        slug=f"manager-org-{uuid.uuid4().hex[:6]}",
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db_session.add(org)
    db_session.flush()

    # Add manager as admin
    membership = OrganizationMember(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        user_id=manager.id,
        role=OrganizationRole.ADMIN,
        is_active=True,
        joined_at=datetime.utcnow(),
    )
    db_session.add(membership)
    db_session.commit()
    db_session.refresh(manager)
    return manager


@pytest.fixture
def auth_headers(client, test_user):
    """Get authentication headers for test user"""
    response = client.post(
        "/api/v1/auth/login", json={"username": "testuser", "password": "TestPass123!"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(client, test_admin):
    """Get authentication headers for admin user"""
    response = client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "AdminPass123!"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def manager_headers(client, test_manager):
    """Get authentication headers for manager user"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "manager", "password": "ManagerPass123!"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# Organization Fixtures (Multi-Tenancy)
# ============================================================================


@pytest.fixture
def test_organization(db_session):
    """Create a test organization"""
    org = Organization(
        id=f"org_{uuid.uuid4().hex[:8]}",
        name="Test Organization",
        slug="test-org",
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


@pytest.fixture
def second_organization(db_session):
    """Create a second test organization for multi-tenant testing"""
    org = Organization(
        id=f"org_{uuid.uuid4().hex[:8]}",
        name="Second Organization",
        slug="second-org",
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


@pytest.fixture
def user_with_organization(db_session, test_user, test_organization):
    """Add test user to test organization"""
    member = OrganizationMember(
        id=f"member_{uuid.uuid4().hex[:8]}",
        organization_id=test_organization.id,
        user_id=test_user.id,
        role=OrganizationRole.MEMBER,
        joined_at=datetime.utcnow(),
    )
    db_session.add(member)
    db_session.commit()
    return test_user


@pytest.fixture
def admin_with_organization(db_session, test_admin, test_organization):
    """Add admin user to test organization"""
    member = OrganizationMember(
        id=f"member_{uuid.uuid4().hex[:8]}",
        organization_id=test_organization.id,
        user_id=test_admin.id,
        role=OrganizationRole.ADMIN,
        joined_at=datetime.utcnow(),
    )
    db_session.add(member)
    db_session.commit()
    return test_admin


@pytest.fixture
def second_org_user(db_session, second_organization):
    """Create a user in a different organization for tenant isolation testing"""
    user = User(
        id=str(uuid.uuid4()),
        email="otheruser@example.com",
        username="otheruser",
        full_name="Other User",
        hashed_password=AuthService.hash_password("OtherPass123!"),
        role=UserRole.EMPLOYEE,
        is_active=True,
        is_verified=True,
        failed_login_attempts=0,
        locked_until=None,
        last_failed_login=None,
    )
    db_session.add(user)
    db_session.flush()

    # Add user to second organization
    member = OrganizationMember(
        id=f"member_{uuid.uuid4().hex[:8]}",
        organization_id=second_organization.id,
        user_id=user.id,
        role=OrganizationRole.MEMBER,
        joined_at=datetime.utcnow(),
    )
    db_session.add(member)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def org_headers(test_user, auth_headers, db_session):
    """Create headers with organization context (test_user's organization)"""
    from src.models import OrganizationMember

    # Get test_user's organization
    membership = (
        db_session.query(OrganizationMember)
        .filter(OrganizationMember.user_id == test_user.id)
        .first()
    )

    return {**auth_headers, "X-Organization-Id": membership.organization_id}


@pytest.fixture
def admin_org_headers(test_organization, admin_headers):
    """Create admin headers with organization context"""
    return {**admin_headers, "X-Organization-Id": test_organization.id}


@pytest.fixture
def second_org_headers(client, second_organization, second_org_user):
    """Create headers for second organization user"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "otheruser", "password": "OtherPass123!"},
    )
    token = response.json()["access_token"]
    return {
        "Authorization": f"Bearer {token}",
        "X-Organization-Id": second_organization.id,
    }


# ============================================================================
# Expense Fixtures
# ============================================================================


@pytest.fixture
def test_expense(db_session, test_user):
    """Create a test expense"""
    from src.models import OrganizationMember

    # Get user's organization
    membership = (
        db_session.query(OrganizationMember)
        .filter(OrganizationMember.user_id == test_user.id)
        .first()
    )

    expense = Expense(
        id=f"exp_{uuid.uuid4().hex[:8]}",
        organization_id=membership.organization_id,
        user_id=test_user.id,
        amount=150.00,
        description="Test expense",
        category="meals",
        status="pending",
        vendor="Test Merchant",
        date=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )
    db_session.add(expense)
    db_session.commit()
    db_session.refresh(expense)
    return expense


@pytest.fixture
def manager_org_employee(db_session, test_manager):
    """Create an employee in the manager's organization"""
    from src.models import OrganizationMember, OrganizationRole

    # Get manager's organization
    manager_membership = (
        db_session.query(OrganizationMember)
        .filter(OrganizationMember.user_id == test_manager.id)
        .first()
    )

    # Create employee in same organization
    employee = User(
        id=str(uuid.uuid4()),
        email="manager_org_emp@example.com",
        username="manager_org_emp",
        full_name="Manager Org Employee",
        hashed_password=AuthService.hash_password("EmpPass123!"),
        role=UserRole.EMPLOYEE,
        is_active=True,
        is_verified=True,
        failed_login_attempts=0,
        locked_until=None,
        last_failed_login=None,
    )
    db_session.add(employee)
    db_session.flush()

    # Add to manager's organization
    membership = OrganizationMember(
        id=str(uuid.uuid4()),
        organization_id=manager_membership.organization_id,
        user_id=employee.id,
        role=OrganizationRole.MEMBER,
        is_active=True,
        joined_at=datetime.utcnow(),
    )
    db_session.add(membership)
    db_session.commit()
    db_session.refresh(employee)
    return employee


@pytest.fixture
def manager_expense(db_session, test_manager, manager_org_employee):
    """Create a test expense from employee in manager's organization"""
    from src.models import OrganizationMember

    # Get manager's organization
    membership = (
        db_session.query(OrganizationMember)
        .filter(OrganizationMember.user_id == manager_org_employee.id)
        .first()
    )

    expense = Expense(
        id=f"exp_{uuid.uuid4().hex[:8]}",
        organization_id=membership.organization_id,
        user_id=manager_org_employee.id,  # Employee's expense, not manager's
        amount=200.00,
        description="Employee expense for approval",
        category="meals",
        status="pending",
        vendor="Test Merchant",
        date=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )
    db_session.add(expense)
    db_session.commit()
    db_session.refresh(expense)
    return expense


@pytest.fixture
def multiple_expenses(db_session, test_user):
    """Create multiple test expenses"""
    from src.models import OrganizationMember

    # Get user's organization
    membership = (
        db_session.query(OrganizationMember)
        .filter(OrganizationMember.user_id == test_user.id)
        .first()
    )

    expenses = []
    for i in range(5):
        expense = Expense(
            id=f"exp_{uuid.uuid4().hex[:8]}",
            organization_id=membership.organization_id,
            user_id=test_user.id,
            amount=100.00 + (i * 50),
            description=f"Test expense {i+1}",
            category="meals" if i % 2 == 0 else "transport",
            status="pending",
            vendor=f"Merchant {i+1}",
            date=datetime.utcnow() - timedelta(days=i),
            created_at=datetime.utcnow(),
        )
        db_session.add(expense)
        expenses.append(expense)
    db_session.commit()
    return expenses


@pytest.fixture
def sample_expense_data():
    """Sample expense data for testing"""
    return {
        "amount": 150.00,
        "description": "Test business lunch",
        "category": "meals",
        "date": datetime.utcnow().isoformat(),
        "vendor": "Test Restaurant",
        "receipt_url": "https://example.com/receipt.pdf",
        # organization_id comes from user context, not request data
    }


# ============================================================================
# Cache Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def cleanup_cache():
    """Clean up cache after each test"""
    yield
    if cache.available:
        try:
            cache.redis_client.flushdb()
        except:
            pass


# ============================================================================
# Additional Fixtures for New Tests
# ============================================================================


@pytest.fixture
def employee_headers(auth_headers):
    """Alias for employee authentication headers"""
    return auth_headers


@pytest.fixture
def sample_user(db_session):
    """Factory fixture to create users with specific attributes"""

    def _create_user(email=None, role=UserRole.EMPLOYEE, **kwargs):
        email = email or f"user_{uuid.uuid4().hex[:8]}@test.com"
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            username=email.split("@")[0],
            full_name=kwargs.get("full_name", "Test User"),
            hashed_password=AuthService.hash_password(
                kwargs.get("password", "TestPass123!")
            ),
            role=role,
            is_active=kwargs.get("is_active", True),
            is_verified=kwargs.get("is_verified", True),
            failed_login_attempts=0,
            locked_until=None,
            last_failed_login=None,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _create_user


@pytest.fixture
def sample_expense(db_session, test_user, test_organization):
    """Factory fixture to create expenses with specific attributes"""
    from src.models import ExpenseCategory, ExpenseStatus

    def _create_expense(user=None, status=ExpenseStatus.PENDING, **kwargs):
        user = user or test_user
        expense = Expense(
            id=f"exp_{uuid.uuid4().hex[:8]}",
            organization_id=kwargs.get("organization_id", test_organization.id),
            user_id=user.id,
            amount=kwargs.get("amount", 100.00),
            vendor=kwargs.get("vendor", "Test Vendor"),
            category=kwargs.get("category", ExpenseCategory.TRAVEL),
            description=kwargs.get("description", "Test expense"),
            status=status,
            date=kwargs.get("date", datetime.utcnow()),
            created_at=datetime.utcnow(),
        )
        db_session.add(expense)
        db_session.commit()
        db_session.refresh(expense)
        return expense

    return _create_expense
