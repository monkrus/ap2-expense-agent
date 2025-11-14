"""
Database seeding with default test users.
These users will ALWAYS be created if they don't exist.
"""

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from .auth import AuthService
from .models import User, UserRole

# FIXED TEST USERS - DO NOT MODIFY
DEFAULT_USERS = [
    {
        "username": "admintest",
        "email": "admintest@example.com",
        "full_name": "Admin Test User",
        "role": UserRole.ADMIN,
        "password": "AgentTest!",
    },
    {
        "username": "testuser",
        "email": "testuser@example.com",
        "full_name": "Test Manager User",
        "role": UserRole.MANAGER,
        "password": "AgentTest!",
    },
    {
        "username": "emptest",
        "email": "emptest@example.com",
        "full_name": "Employee Test 1",
        "role": UserRole.EMPLOYEE,
        "password": "AgentTest!",
    },
    {
        "username": "emptest2",
        "email": "emptest2@example.com",
        "full_name": "Employee Test 2",
        "role": UserRole.EMPLOYEE,
        "password": "AgentTest!",
    },
]


def seed_default_users(db: Session, force_password_reset: bool = False) -> dict:
    """
    Seed the database with default test users.

    This function:
    - Creates users if they don't exist
    - Optionally resets passwords to default if force_password_reset=True
    - Always ensures users are active and verified

    Args:
        db: Database session
        force_password_reset: If True, reset all default users' passwords to default

    Returns:
        dict: Statistics about seeding operation
    """
    stats = {"created": 0, "updated": 0, "skipped": 0, "total": len(DEFAULT_USERS)}

    try:
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
                stats["created"] += 1

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
    Reset all default users' passwords to the default password.
    Use this if passwords need to be reset to default.
    """
    stats = seed_default_users(db, force_password_reset=True)
    print(f"[SEED] Reset passwords for {stats['updated']} users")
