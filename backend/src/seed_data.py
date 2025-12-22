"""
Database seeding with a default admin user.
This user will ALWAYS be created if it doesn't exist.
"""

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from .auth import AuthService
from .models import Organization, OrganizationMember, OrganizationRole, User, UserRole

# FIXED DEFAULT USER - DO NOT MODIFY
DEFAULT_USERS = [
    {
        "username": "adminfree",
        "email": "adminfree@example.com",
        "full_name": "Admin Free",
        "role": UserRole.ADMIN,
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

        default_org = (
            db.query(Organization)
            .filter(Organization.slug == "default-org")
            .first()
        )
        if not default_org:
            default_org = Organization(
                id=str(uuid.uuid4()),
                name="Default Organization",
                slug="default-org",
                is_active=True,
                created_at=datetime.utcnow(),
            )
            db.add(default_org)
            db.flush()

        role_mapping = {
            UserRole.ADMIN: OrganizationRole.OWNER,
            UserRole.MANAGER: OrganizationRole.MANAGER,
        }

        for user in seeded_users:
            membership = (
                db.query(OrganizationMember)
                .filter(
                    OrganizationMember.user_id == user.id,
                    OrganizationMember.organization_id == default_org.id,
                )
                .first()
            )
            if membership:
                if not membership.is_active:
                    membership.is_active = True
                continue

            org_role = role_mapping.get(user.role, OrganizationRole.MEMBER)
            membership = OrganizationMember(
                id=str(uuid.uuid4()),
                organization_id=default_org.id,
                user_id=user.id,
                role=org_role,
                is_active=True,
                joined_at=datetime.utcnow(),
            )
            db.add(membership)

        db.commit()
        return stats

    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to seed default users: {str(e)}")


def ensure_default_users_exist(db: Session) -> None:
    """
    Ensures default users exist in the database.
    Called automatically on application startup.
    """
    stats = seed_default_users(db, force_password_reset=False)

    if stats["created"] > 0:
        print(f"[SEED] Created {stats['created']} default users")
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
