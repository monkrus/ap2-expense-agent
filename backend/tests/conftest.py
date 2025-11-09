"""
Pytest configuration and fixtures for testing
"""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import uuid

# Set testing environment variable BEFORE importing app
os.environ["TESTING"] = "true"
os.environ["ENVIRONMENT"] = "test"

from src.api import app
from src.database import get_db
from src.models import Base, User, UserRole, Organization, OrganizationMember, OrganizationRole, Expense, ExpenseStatus, ExpenseCategory
from src.auth import AuthService
from src.cache import cache


# Use PostgreSQL for tests (matches CI environment)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://test_user:test_password@localhost:5432/test_db"
)

# Create test engine
engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Setup test database schema once for all tests"""
    # Skip creating tables if migrations already ran (CI environment)
    # The SKIP_DB_INIT env var is set in CI to use alembic migrations
    skip_init = os.getenv("SKIP_DB_INIT", "false").lower() == "true"

    if not skip_init:
        # Create all tables (for local development without migrations)
        Base.metadata.create_all(bind=engine)

    yield

    # Clean up after tests (only if we created the tables)
    if not skip_init:
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test with transaction rollback"""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


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


# ============================================================================
# User Fixtures
# ============================================================================

@pytest.fixture
def test_user(db_session):
    """Create a test user"""
    user = User(
        id=str(uuid.uuid4()),
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        hashed_password=AuthService.hash_password("TestPass123!"),
        role=UserRole.EMPLOYEE.value,
        is_active=True,
        is_verified=True,
        failed_login_attempts=0,
        locked_until=None,
        last_failed_login=None
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_admin(db_session):
    """Create a test admin user"""
    admin = User(
        id=str(uuid.uuid4()),
        email="admin@example.com",
        username="admin",
        full_name="Admin User",
        hashed_password=AuthService.hash_password("AdminPass123!"),
        role=UserRole.ADMIN.value,
        is_active=True,
        is_verified=True,
        failed_login_attempts=0,
        locked_until=None,
        last_failed_login=None
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture
def test_manager(db_session):
    """Create a test manager user"""
    manager = User(
        id=str(uuid.uuid4()),
        email="manager@example.com",
        username="manager",
        full_name="Manager User",
        hashed_password=AuthService.hash_password("ManagerPass123!"),
        role=UserRole.MANAGER.value,
        is_active=True,
        is_verified=True,
        failed_login_attempts=0,
        locked_until=None,
        last_failed_login=None
    )
    db_session.add(manager)
    db_session.commit()
    db_session.refresh(manager)
    return manager


@pytest.fixture
def auth_headers(client, test_user):
    """Get authentication headers for test user"""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "TestPass123!"
        }
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(client, test_admin):
    """Get authentication headers for admin user"""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "admin",
            "password": "AdminPass123!"
        }
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def manager_headers(client, test_manager):
    """Get authentication headers for manager user"""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "manager",
            "password": "ManagerPass123!"
        }
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
        description="Test organization for unit testing",
        currency="USD",
        timezone="UTC",
        max_members=25,
        is_active=True,
        created_at=datetime.utcnow()
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
        description="Second test organization for multi-tenant testing",
        currency="USD",
        timezone="UTC",
        max_members=25,
        is_active=True,
        created_at=datetime.utcnow()
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
        joined_at=datetime.utcnow()
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
        joined_at=datetime.utcnow()
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
        role=UserRole.EMPLOYEE.value,
        is_active=True,
        is_verified=True,
        failed_login_attempts=0,
        locked_until=None,
        last_failed_login=None
    )
    db_session.add(user)
    db_session.flush()

    # Add user to second organization
    member = OrganizationMember(
        id=f"member_{uuid.uuid4().hex[:8]}",
        organization_id=second_organization.id,
        user_id=user.id,
        role=OrganizationRole.MEMBER,
        joined_at=datetime.utcnow()
    )
    db_session.add(member)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def org_headers(user_with_organization, test_organization, auth_headers):
    """Create headers with organization context"""
    return {
        **auth_headers,
        "X-Organization-Id": test_organization.id
    }


@pytest.fixture
def admin_org_headers(test_organization, admin_headers):
    """Create admin headers with organization context"""
    return {
        **admin_headers,
        "X-Organization-Id": test_organization.id
    }


@pytest.fixture
def second_org_headers(client, second_organization, second_org_user):
    """Create headers for second organization user"""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "otheruser",
            "password": "OtherPass123!"
        }
    )
    token = response.json()["access_token"]
    return {
        "Authorization": f"Bearer {token}",
        "X-Organization-Id": second_organization.id
    }


# ============================================================================
# Expense Fixtures
# ============================================================================

@pytest.fixture
def test_expense(db_session, test_organization, test_user):
    """Create a test expense"""
    expense = Expense(
        id=f"exp_{uuid.uuid4().hex[:8]}",
        organization_id=test_organization.id,
        user_id=test_user.id,
        amount=150.00,
        vendor="Test Merchant",
        description="Test expense",
        category=ExpenseCategory.MEALS,
        status=ExpenseStatus.PENDING,
        date=datetime.utcnow(),
        created_at=datetime.utcnow()
    )
    db_session.add(expense)
    db_session.commit()
    db_session.refresh(expense)
    return expense


@pytest.fixture
def multiple_expenses(db_session, test_organization, test_user):
    """Create multiple test expenses"""
    expenses = []
    for i in range(5):
        expense = Expense(
            id=f"exp_{uuid.uuid4().hex[:8]}",
            organization_id=test_organization.id,
            user_id=test_user.id,
            amount=100.00 + (i * 50),
            vendor=f"Merchant {i+1}",
            description=f"Test expense {i+1}",
            category=ExpenseCategory.MEALS if i % 2 == 0 else ExpenseCategory.TRAVEL,
            status=ExpenseStatus.PENDING,
            date=datetime.utcnow() - timedelta(days=i),
            created_at=datetime.utcnow()
        )
        db_session.add(expense)
        expenses.append(expense)
    db_session.commit()
    return expenses


@pytest.fixture
def sample_expense_data(test_organization):
    """Sample expense data for testing"""
    return {
        "amount": 150.00,
        "vendor": "Test Restaurant",
        "description": "Test business lunch",
        "category": "Meals",
        "date": datetime.utcnow().isoformat(),
        "organization_id": test_organization.id
    }


# ============================================================================
# Factory Fixtures
# ============================================================================

@pytest.fixture
def sample_user(db_session):
    """Factory fixture to create users with specific attributes"""
    def _create_user(email=None, role=UserRole.EMPLOYEE, **kwargs):
        email = email or f"user_{uuid.uuid4().hex[:8]}@test.com"
        # Handle both UserRole enum and string values
        role_value = role.value if hasattr(role, 'value') else role
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            username=email.split('@')[0],
            full_name=kwargs.get('full_name', 'Test User'),
            hashed_password=AuthService.hash_password(kwargs.get('password', 'TestPass123!')),
            role=role_value,
            is_active=kwargs.get('is_active', True),
            is_verified=kwargs.get('is_verified', True),
            failed_login_attempts=0,
            locked_until=None,
            last_failed_login=None
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    return _create_user


@pytest.fixture
def sample_expense(db_session, test_user, test_organization):
    """Factory fixture to create expenses with specific attributes"""
    def _create_expense(user=None, status=ExpenseStatus.PENDING, **kwargs):
        user = user or test_user
        expense = Expense(
            id=f"exp_{uuid.uuid4().hex[:8]}",
            organization_id=kwargs.get('organization_id', test_organization.id),
            user_id=user.id,
            amount=kwargs.get('amount', 100.00),
            vendor=kwargs.get('vendor', 'Test Vendor'),
            category=kwargs.get('category', ExpenseCategory.TRAVEL),
            description=kwargs.get('description', 'Test expense'),
            status=status,
            date=kwargs.get('date', datetime.utcnow()),
            created_at=datetime.utcnow()
        )
        db_session.add(expense)
        db_session.commit()
        db_session.refresh(expense)
        return expense
    return _create_expense


# ============================================================================
# Convenience Fixtures
# ============================================================================

@pytest.fixture
def employee_headers(auth_headers):
    """Alias for employee authentication headers"""
    return auth_headers


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
