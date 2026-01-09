"""
Comprehensive Organization Management Tests

Tests all organization functionality:
- Creation with validation
- Free tier limits (1 organization max)
- Deletion (soft delete)
- Editing
- Lifecycle flows
- Error messages
- No default organizations
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.api import app
from src.database import get_db, SessionLocal
from src.models import User, Organization, OrganizationMember, OrganizationRole, UserRole
from src.auth import AuthService
import uuid
from datetime import datetime


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def db():
    """Database session fixture"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(db: Session):
    """Create a test user"""
    user = User(
        id=str(uuid.uuid4()),
        username=f"testuser_{uuid.uuid4().hex[:8]}",
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Test User",
        role=UserRole.ADMIN,
        hashed_password=AuthService.hash_password("TestPassword123!"),
        is_active=True,
        is_verified=True,
        created_at=datetime.utcnow()
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    yield user

    # Cleanup: delete user's organizations and memberships
    memberships = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id
    ).all()
    for m in memberships:
        db.delete(m)

    orgs = db.query(Organization).join(OrganizationMember).filter(
        OrganizationMember.user_id == user.id
    ).all()
    for org in orgs:
        db.delete(org)

    db.delete(user)
    db.commit()


@pytest.fixture
def auth_headers(client, test_user):
    """Get authentication headers for test user"""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": test_user.username,
            "password": "TestPassword123!"
        }
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestOrganizationCreation:
    """Test organization creation scenarios"""

    def test_create_organization_success(self, client, auth_headers, db):
        """Test successful organization creation"""
        org_data = {
            "name": "Test Organization",
            "slug": "test-org",
            "description": "A test organization",
            "currency": "USD",
            "timezone": "UTC"
        }

        response = client.post(
            "/api/v1/organizations",
            json=org_data,
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == org_data["name"]
        assert data["slug"] == org_data["slug"]
        assert data["is_active"] is True

    def test_create_organization_slug_too_short(self, client, auth_headers):
        """Test organization creation with slug < 3 characters"""
        org_data = {
            "name": "Test",
            "slug": "ab",  # Too short
            "currency": "USD",
            "timezone": "UTC"
        }

        response = client.post(
            "/api/v1/organizations",
            json=org_data,
            headers=auth_headers
        )

        assert response.status_code == 400
        response_data = response.json()
        assert "detail" in response_data
        error_data = response_data["detail"]
        assert error_data["error"] == "slug_too_short"
        assert "Organization Name must be at least 1 character" in error_data["message"]
        assert "Organization ID must be at least 3 characters" in error_data["message"]
        assert error_data["field"] == "slug"
        assert "hint" in error_data

    def test_create_organization_invalid_slug_format(self, client, auth_headers):
        """Test organization creation with invalid slug characters"""
        org_data = {
            "name": "Test Organization",
            "slug": "Test_Org!",  # Invalid characters
            "currency": "USD",
            "timezone": "UTC"
        }

        response = client.post(
            "/api/v1/organizations",
            json=org_data,
            headers=auth_headers
        )

        assert response.status_code == 422

    def test_create_organization_duplicate_slug(self, client, auth_headers, db):
        """Test organization creation with duplicate slug"""
        # Create first organization
        org1_data = {
            "name": "First Org",
            "slug": "unique-slug",
            "currency": "USD",
            "timezone": "UTC"
        }
        response1 = client.post(
            "/api/v1/organizations",
            json=org1_data,
            headers=auth_headers
        )
        assert response1.status_code == 201

        # Try to create second org with same slug
        org2_data = {
            "name": "Second Org",
            "slug": "unique-slug",  # Duplicate!
            "currency": "USD",
            "timezone": "UTC"
        }
        response2 = client.post(
            "/api/v1/organizations",
            json=org2_data,
            headers=auth_headers
        )

        assert response2.status_code == 400
        response_data = response2.json()
        error_data = response_data["detail"]
        assert error_data["error"] == "slug_already_taken"
        assert "suggestions" in error_data
        assert len(error_data["suggestions"]) > 0

    def test_create_organization_duplicate_name(self, client, auth_headers):
        """Test organization creation with duplicate name (case-insensitive)"""
        # Create first organization
        org1_data = {
            "name": "Unique Company",
            "slug": "unique-company-1",
            "currency": "USD",
            "timezone": "UTC"
        }
        response1 = client.post(
            "/api/v1/organizations",
            json=org1_data,
            headers=auth_headers
        )
        assert response1.status_code == 201

        # Try to create org with same name (different case)
        org2_data = {
            "name": "unique company",  # Same name, different case
            "slug": "unique-company-2",
            "currency": "USD",
            "timezone": "UTC"
        }
        response2 = client.post(
            "/api/v1/organizations",
            json=org2_data,
            headers=auth_headers
        )

        assert response2.status_code == 400
        response_data = response2.json()
        error_data = response_data["detail"]
        assert error_data["error"] == "name_already_taken"
        assert "suggestions" in error_data


class TestOrganizationLimits:
    """Test free tier organization limits"""

    def test_free_tier_one_organization_limit(self, client, auth_headers, db, monkeypatch):
        """Test that free tier users can only create 1 organization

        Note: Limits are bypassed when TESTING=true, so we temporarily disable it.
        """
        # Temporarily disable testing bypass to actually test limits
        monkeypatch.delenv("TESTING", raising=False)

        # Create first organization (should succeed)
        org1_data = {
            "name": "First Organization",
            "slug": "first-org",
            "currency": "USD",
            "timezone": "UTC"
        }
        response1 = client.post(
            "/api/v1/organizations",
            json=org1_data,
            headers=auth_headers
        )
        assert response1.status_code == 201

        # Try to create second organization (should fail with 402)
        org2_data = {
            "name": "Second Organization",
            "slug": "second-org",
            "currency": "USD",
            "timezone": "UTC"
        }
        response2 = client.post(
            "/api/v1/organizations",
            json=org2_data,
            headers=auth_headers
        )

        assert response2.status_code == 402
        response_data = response2.json()
        # 402 errors have a "detail" wrapper
        assert "detail" in response_data
        error_data = response_data["detail"]
        assert error_data["error"] == "limit_exceeded"
        assert error_data["current_tier"] == "Free"
        assert error_data["current_limit"] == 1
        assert "upgrade" in error_data["message"].lower()
        assert "upgrade_options" in error_data


class TestOrganizationDeletion:
    """Test organization deletion (soft delete)"""

    def test_delete_organization_as_owner(self, client, auth_headers, db):
        """Test that owner can delete organization"""
        # Create organization
        org_data = {
            "name": "Delete Test Org",
            "slug": "delete-test",
            "currency": "USD",
            "timezone": "UTC"
        }
        create_response = client.post(
            "/api/v1/organizations",
            json=org_data,
            headers=auth_headers
        )
        assert create_response.status_code == 201
        org_id = create_response.json()["id"]

        # Delete organization
        delete_response = client.delete(
            f"/api/v1/organizations/{org_id}",
            headers=auth_headers
        )

        assert delete_response.status_code == 204

        # Verify organization is soft-deleted
        org = db.query(Organization).filter(Organization.id == org_id).first()
        assert org is not None  # Still exists in DB
        assert org.is_active is False  # But marked inactive

    def test_delete_organization_frees_slug(self, client, auth_headers, db):
        """Test that deleting org allows slug reuse"""
        # Create and delete first organization
        org1_data = {
            "name": "First Org",
            "slug": "reusable-slug",
            "currency": "USD",
            "timezone": "UTC"
        }
        create1 = client.post(
            "/api/v1/organizations",
            json=org1_data,
            headers=auth_headers
        )
        assert create1.status_code == 201
        org1_id = create1.json()["id"]

        # Delete first org
        client.delete(
            f"/api/v1/organizations/{org1_id}",
            headers=auth_headers
        )

        # Create new org with same slug (should succeed)
        org2_data = {
            "name": "Second Org",
            "slug": "reusable-slug",  # Same slug
            "currency": "USD",
            "timezone": "UTC"
        }
        create2 = client.post(
            "/api/v1/organizations",
            json=org2_data,
            headers=auth_headers
        )

        assert create2.status_code == 201


class TestOrganizationEditing:
    """Test organization update functionality"""

    def test_update_organization_as_owner(self, client, auth_headers):
        """Test that owner can update organization"""
        # Create organization
        org_data = {
            "name": "Original Name",
            "slug": "original-slug",
            "description": "Original description",
            "currency": "USD",
            "timezone": "UTC"
        }
        create_response = client.post(
            "/api/v1/organizations",
            json=org_data,
            headers=auth_headers
        )
        assert create_response.status_code == 201
        org_id = create_response.json()["id"]

        # Update organization
        update_data = {
            "name": "Updated Name",
            "description": "Updated description"
        }
        update_response = client.patch(
            f"/api/v1/organizations/{org_id}",
            json=update_data,
            headers=auth_headers
        )

        assert update_response.status_code == 200
        updated_org = update_response.json()
        assert updated_org["name"] == "Updated Name"
        assert updated_org["description"] == "Updated description"
        assert updated_org["slug"] == "original-slug"  # Slug unchanged


class TestOrganizationLifecycle:
    """Test complete organization lifecycle flows"""

    def test_create_delete_create_flow(self, client, auth_headers, db, monkeypatch):
        """Test: Create org → Delete org → Create new org

        Note: Limits are bypassed when TESTING=true, so we temporarily disable it.
        """
        # Temporarily disable testing bypass to actually test limits
        monkeypatch.delenv("TESTING", raising=False)

        # Step 1: Create first organization
        org1_data = {
            "name": "First Org",
            "slug": "first-org",
            "currency": "USD",
            "timezone": "UTC"
        }
        create1 = client.post(
            "/api/v1/organizations",
            json=org1_data,
            headers=auth_headers
        )
        assert create1.status_code == 201
        org1_id = create1.json()["id"]

        # Step 2: Verify user is at limit
        org2_data = {
            "name": "Second Org",
            "slug": "second-org",
            "currency": "USD",
            "timezone": "UTC"
        }
        limit_check = client.post(
            "/api/v1/organizations",
            json=org2_data,
            headers=auth_headers
        )
        assert limit_check.status_code == 402  # At limit

        # Step 3: Delete first organization
        delete_response = client.delete(
            f"/api/v1/organizations/{org1_id}",
            headers=auth_headers
        )
        assert delete_response.status_code == 204

        # Step 4: Create new organization (should succeed now)
        org3_data = {
            "name": "Third Org",
            "slug": "third-org",
            "currency": "USD",
            "timezone": "UTC"
        }
        create3 = client.post(
            "/api/v1/organizations",
            json=org3_data,
            headers=auth_headers
        )
        assert create3.status_code == 201


class TestNoDefaultOrganization:
    """Test that no default organizations are created"""

    def test_no_default_org_on_user_creation(self, db):
        """Test that creating a user doesn't create default organization"""
        # Create new user
        user = User(
            id=str(uuid.uuid4()),
            username=f"newuser_{uuid.uuid4().hex[:8]}",
            email=f"new_{uuid.uuid4().hex[:8]}@example.com",
            full_name="New User",
            role=UserRole.ADMIN,
            hashed_password=AuthService.hash_password("Password123!"),
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow()
        )
        db.add(user)
        db.commit()

        # Check that no organizations exist for this user
        org_count = db.query(Organization).join(OrganizationMember).filter(
            OrganizationMember.user_id == user.id,
            Organization.is_active == True
        ).count()

        assert org_count == 0, "New user should start with 0 organizations"

        # Cleanup
        db.delete(user)
        db.commit()

    def test_no_default_org_exists_globally(self, db):
        """Test that 'default-org' doesn't exist in database"""
        default_org = db.query(Organization).filter(
            Organization.slug == "default-org",
            Organization.is_active == True
        ).first()

        assert default_org is None, "No 'default-org' should exist"


class TestValidationErrorMessages:
    """Test that error messages are user-friendly"""

    def test_slug_too_short_error_message(self, client, auth_headers):
        """Test that slug validation error is clear"""
        org_data = {
            "name": "Test",
            "slug": "ab",
            "currency": "USD",
            "timezone": "UTC"
        }

        response = client.post(
            "/api/v1/organizations",
            json=org_data,
            headers=auth_headers
        )

        assert response.status_code == 400
        response_data = response.json()
        assert "detail" in response_data
        error_data = response_data["detail"]
        # Verify friendly error message format includes both rules
        assert error_data["error"] == "slug_too_short"
        assert "Organization Name must be at least 1 character" in error_data["message"]
        assert "Organization ID must be at least 3 characters" in error_data["message"]
        assert error_data["field"] == "slug"
        assert "hint" in error_data

    def test_duplicate_name_provides_suggestions(self, client, auth_headers):
        """Test that duplicate name error provides suggestions"""
        # Create first org
        org1_data = {
            "name": "Great Company",
            "slug": "great-company-1",
            "currency": "USD",
            "timezone": "UTC"
        }
        client.post("/api/v1/organizations", json=org1_data, headers=auth_headers)

        # Try duplicate name
        org2_data = {
            "name": "Great Company",
            "slug": "great-company-2",
            "currency": "USD",
            "timezone": "UTC"
        }
        response = client.post(
            "/api/v1/organizations",
            json=org2_data,
            headers=auth_headers
        )

        assert response.status_code == 400
        response_data = response.json()
        error_data = response_data["detail"]
        assert "suggestions" in error_data
        assert len(error_data["suggestions"]) > 0
        assert error_data["error"] == "name_already_taken"
