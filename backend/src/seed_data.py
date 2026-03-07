"""
Database seeding with a default admin user.
This user will ALWAYS be created if it doesn't exist.
"""

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from .auth import AuthService
from .models import Organization, OrganizationMember, OrganizationRole, User, UserRole

# FIXED DEFAULT USERS - DO NOT MODIFY
DEFAULT_USERS = [
    {
        "username": "adminfree",
        "email": "adminfree@example.com",
        "full_name": "Admin Free",
        "role": UserRole.ADMIN,
        "password": "Testme1!",
    },
    {
        "username": "admintest",
        "email": "admintest@example.com",
        "full_name": "Admin Test",
        "role": UserRole.ADMIN,
        "password": "Testme1!",
    },
    {
        "username": "emptest",
        "email": "emptest@example.com",
        "full_name": "Employee Test",
        "role": UserRole.EMPLOYEE,
        "password": "Testme1!",
    },
    {
        "username": "managertest",
        "email": "managertest@example.com",
        "full_name": "Manager Test",
        "role": UserRole.MANAGER,
        "password": "Testme1!",
    },
]


def seed_default_users(db: Session, force_password_reset: bool = False) -> dict:
    """
    Seed the database with the default admin user.

    This function:
    - Creates users if they don't exist
    - Optionally resets passwords to default if force_password_reset=True
    - Always ensures users are active and verified

    Args:
        db: Database session
        force_password_reset: If True, reset the default user's password to default

    Returns:
        dict: Statistics about seeding operation
    """
    stats = {"created": 0, "updated": 0, "skipped": 0, "total": len(DEFAULT_USERS)}

    try:
        seeded_users = []
        for user_data in DEFAULT_USERS:
            # Check if user exists
            existing_user = (
                db.query(User).filter(User.username == user_data["username"]).first()
            )

            if existing_user:
                # User exists - optionally reset password
                if force_password_reset:
                    existing_user.hashed_password = AuthService.hash_password(
                        user_data["password"]
                    )
                    existing_user.failed_login_attempts = 0
                    existing_user.locked_until = None
                    existing_user.last_failed_login = None
                    existing_user.is_active = True
                    existing_user.is_verified = True
                    stats["updated"] += 1
                else:
                    stats["skipped"] += 1
                seeded_users.append(existing_user)
            else:
                # Create new user - StringEnum type decorator handles enum conversion automatically
                new_user = User(
                    id=str(uuid.uuid4()),
                    username=user_data["username"],
                    email=user_data["email"],
                    full_name=user_data["full_name"],
                    role=user_data[
                        "role"
                    ],  # Can pass enum or string, StringEnum handles it
                    hashed_password=AuthService.hash_password(user_data["password"]),
                    is_active=True,
                    is_verified=True,
                    failed_login_attempts=0,
                    created_at=datetime.utcnow(),
                )
                db.add(new_user)
                db.flush()
                seeded_users.append(new_user)
                stats["created"] += 1

        # Seed a default test organization and add users to it
        _seed_default_org(db, seeded_users)

        db.commit()
        return stats

    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to seed default users: {str(e)}")


DEFAULT_ORG_NAME = "Test Organization"


def _seed_default_org(db: Session, users: list) -> None:
    """Create a default test organization and add all seeded users to it."""
    if not users:
        return

    # Check if org already exists
    existing_org = db.query(Organization).filter(
        Organization.name == DEFAULT_ORG_NAME
    ).first()

    if not existing_org:
        org = Organization(
            id=str(uuid.uuid4()),
            name=DEFAULT_ORG_NAME,
            slug="test-organization",
            max_members=10,
        )
        db.add(org)
        db.flush()
    else:
        org = existing_org

    # Add each user to the org if not already a member
    for user in users:
        existing_member = db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.user_id == user.id,
        ).first()
        if not existing_member:
            if user.username in ("adminfree", "admintest"):
                role = OrganizationRole.OWNER
            elif user.username == "managertest":
                role = OrganizationRole.ADMIN
            else:
                role = OrganizationRole.MEMBER
            member = OrganizationMember(
                id=str(uuid.uuid4()),
                organization_id=org.id,
                user_id=user.id,
                role=role,
                is_active=True,
            )
            db.add(member)

        # Set department for manager seed user
        if user.username == "managertest" and not user.department_id:
            user.department_id = "engineering"


def ensure_default_users_exist(db: Session) -> None:
    """
    Ensures default users exist in the database.
    Called automatically on application startup.

    SAFEGUARD for Google Cloud Marketplace:
    - In PRODUCTION or when DISABLE_DEFAULT_ADMIN=true, this does NOT create
      the default admin user. This allows the first registered user (after
      marketplace purchase) to become the admin.
    - In DEVELOPMENT/TESTING, it creates a default admin for convenience.
    """
    import os
    from .config import settings

    # Skip default user creation in production or when explicitly disabled
    # This ensures first registered user becomes admin (marketplace safeguard)
    is_production = settings.environment == "production"
    disable_default_admin = os.getenv("DISABLE_DEFAULT_ADMIN", "false").lower() == "true"

    if is_production or disable_default_admin:
        print("[SEED] Skipping default admin creation (production/marketplace mode)")
        print("[SEED] First registered user will be granted ADMIN role")
        return

    # Development/testing mode: create default admin for convenience
    stats = seed_default_users(db, force_password_reset=False)

    if stats["created"] > 0:
        print(f"[SEED] Created {stats['created']} default users (dev mode)")
    if stats["updated"] > 0:
        print(f"[SEED] Updated {stats['updated']} default users")
    if stats["created"] == 0 and stats["updated"] == 0:
        print(f"[SEED] All {stats['total']} default users already exist")


def reset_default_users_passwords(db: Session) -> None:
    """
    Reset the default user's password to the default password.
    Use this if passwords need to be reset to default.
    """
    stats = seed_default_users(db, force_password_reset=True)
    print(f"[SEED] Reset passwords for {stats['updated']} users")
