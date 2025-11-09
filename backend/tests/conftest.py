"""
Pytest configuration and fixtures for testing
"""
import os
import pytest
import uuid
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set testing environment variable BEFORE importing app
os.environ["TESTING"] = "true"
os.environ["ENVIRONMENT"] = "test"

from src.api import app
from src.database import get_db
from src.models import (
    Base, User, UserRole, Organization, OrganizationMember,
    OrganizationRole, Expense, ExpenseStatus, ExpenseCategory
)
from src.auth import AuthService
from src.cache import cache


# ============================================================================
# Database Setup
# ============================================================================

# Test database setup - use DATABASE_URL from environment if set, otherwise SQLite
SQLALCHEMY_TEST_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///:memory:"
)

# Configure engine based on database type
if SQLALCHEMY_TEST_DATABASE_URL.startswith("postgresql"):
    # PostgreSQL configuration for CI/CD (GitHub Actions)
    engine = create_engine(
        SQLALCHEMY_TEST_DATABASE_URL,
        pool_pre_ping=True,
    )
else:
    # SQLite configuration for local development
    engine = create_engine(
        SQLALCHEMY_TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Setup test database schema once for all tests"""
    skip_init = os.getenv("SKIP_DB_INIT", "false").lower() == "true"

    if not skip_init:
        Base.metadata.create_all(bind=engine)

    yield

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
        json={"user
