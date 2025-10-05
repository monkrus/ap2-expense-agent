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

from src.api import app
from src.database import get_db
from src.models import Base, User, UserRole
from src.auth import AuthService
import uuid


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
    """Create a test user"""
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
        role=UserRole.ADMIN,
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
        role=UserRole.MANAGER,
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
