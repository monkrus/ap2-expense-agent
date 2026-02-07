"""
Setup test user for AP2 testing
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from src.database import SessionLocal, engine
from src.models import Base, User, Organization, OrganizationMember
from passlib.context import CryptContext
import uuid
from datetime import datetime

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def setup_test_user():
    """Create test user for AP2 testing"""
    db = SessionLocal()

    try:
        # Check if user already exists
        existing_user = db.query(User).filter_by(username="testuser").first()
        if existing_user:
            print("Test user 'testuser' already exists")
            print("   Username: testuser")
            print("   Password: Test123!")
            return

        # Create organization
        org = Organization(
            id=str(uuid.uuid4()),
            name="Test Organization",
            slug="test-org",
            created_at=datetime.utcnow()
        )
        db.add(org)
        db.flush()

        # Create user
        password = "Test123!"
        user = User(
            id=str(uuid.uuid4()),
            username="testuser",
            email="test@example.com",
            password_hash=pwd_context.hash(password),
            role="employee",
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(user)
        db.flush()

        # Add user to organization
        membership = OrganizationMember(
            id=str(uuid.uuid4()),
            organization_id=org.id,
            user_id=user.id,
            role="member",
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(membership)

        db.commit()

        print("Test user created successfully!")
        print("   Username: testuser")
        print("   Password: Test123!")
        print("   Email: test@example.com")
        print("   Organization: Test Organization")

    except Exception as e:
        db.rollback()
        print(f"ERROR: Error creating test user: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    setup_test_user()
