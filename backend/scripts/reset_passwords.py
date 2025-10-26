"""
Script to reset passwords for all users in the database.

This script allows you to:
1. Reset all users to a default password
2. Reset specific users by email or username
3. Generate random passwords for all users

Usage:
    python reset_passwords.py --default-password <password>
    python reset_passwords.py --random
    python reset_passwords.py --user <email_or_username> --password <new_password>
"""

import sys
import os
import argparse
import secrets
import string
import bcrypt
from datetime import datetime, timezone
from pathlib import Path

# Fix Windows encoding issues
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add the src directory to Python path
script_dir = Path(__file__).parent
backend_dir = script_dir.parent
src_dir = backend_dir / "src"
sys.path.insert(0, str(src_dir))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Import the User model from the src directory
import importlib.util

models_py = src_dir / "models.py"
models_pkg_init = src_dir / "models" / "__init__.py"

if models_py.exists():
    spec = importlib.util.spec_from_file_location("models", str(models_py))
    models = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(models)
    User = models.User
elif models_pkg_init.exists():
    spec = importlib.util.spec_from_file_location("models", str(models_pkg_init))
    models = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(models)
    User = models.User
else:
    # As a last resort try importing as src.models (if src is a package)
    try:
        sys.path.insert(0, str(backend_dir))
        from src.models import User  # type: ignore
    except Exception as e:
        raise ImportError("Could not import 'models' module from the src directory") from e


def hash_password(password: str) -> str:
    """Hash a password using bcrypt (same logic as AuthService)"""
    # Bcrypt has a 72-byte limit, truncate if necessary
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def generate_random_password(length: int = 16) -> str:
    """Generate a cryptographically secure random password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password


def reset_all_passwords(db: Session, password: str, random: bool = False) -> None:
    """Reset passwords for all users"""
    users = db.query(User).all()

    if not users:
        print("No users found in the database.")
        return

    print(f"\nFound {len(users)} user(s). Resetting passwords...\n")

    results = []
    for user in users:
        if random:
            new_password = generate_random_password()
        else:
            new_password = password

        # Hash and update password
        user.hashed_password = hash_password(new_password)
        user.updated_at = datetime.now(timezone.utc)

        # Reset failed login attempts
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_failed_login = None

        results.append({
            "username": user.username,
            "email": user.email,
            "password": new_password
        })

    # Commit all changes
    db.commit()

    # Display results
    print("=" * 80)
    print("PASSWORD RESET COMPLETE")
    print("=" * 80)
    print(f"\nPasswords have been reset for {len(results)} user(s):\n")

    for result in results:
        print(f"Username: {result['username']}")
        print(f"Email:    {result['email']}")
        print(f"Password: {result['password']}")
        print("-" * 80)

    print("\n⚠️  IMPORTANT: Save these credentials securely!")
    print("⚠️  Users should change their passwords after first login.\n")


def reset_user_password(db: Session, identifier: str, password: str, random: bool = False) -> None:
    """Reset password for a specific user by email or username"""
    user = db.query(User).filter(
        (User.email == identifier) | (User.username == identifier)
    ).first()

    if not user:
        print(f"❌ Error: User with email or username '{identifier}' not found.")
        return

    if random:
        new_password = generate_random_password()
    else:
        new_password = password

    # Hash and update password
    user.hashed_password = hash_password(new_password)
    user.updated_at = datetime.now(timezone.utc)

    # Reset failed login attempts
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_failed_login = None

    db.commit()

    # Display result
    print("=" * 80)
    print("PASSWORD RESET COMPLETE")
    print("=" * 80)
    print(f"\nUsername: {user.username}")
    print(f"Email:    {user.email}")
    print(f"Password: {new_password}")
    print("-" * 80)
    print("\n⚠️  IMPORTANT: Save this credential securely!")
    print("⚠️  User should change their password after login.\n")


def list_users(db: Session) -> None:
    """List all users in the database"""
    users = db.query(User).all()

    if not users:
        print("No users found in the database.")
        return

    print("=" * 80)
    print(f"USERS IN DATABASE ({len(users)} total)")
    print("=" * 80)

    for user in users:
        print(f"\nUsername: {user.username}")
        print(f"Email:    {user.email}")
        print(f"Role:     {user.role.value}")
        print(f"Active:   {user.is_active}")
        print(f"Locked:   {user.locked_until is not None and user.locked_until > datetime.now(timezone.utc)}")
        print("-" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Reset passwords for users in the expense management system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Reset all users to "AgentTest!" (default)
  python reset_passwords.py

  # Reset all users to a custom password
  python reset_passwords.py --default-password "TempPassword123!"

  # Reset all users with random passwords
  python reset_passwords.py --random

  # Reset a specific user's password
  python reset_passwords.py --user admin@example.com --password "NewPassword123!"

  # Reset a specific user with a random password
  python reset_passwords.py --user john.doe --random

  # List all users
  python reset_passwords.py --list
        """
    )

    parser.add_argument(
        "--default-password",
        type=str,
        default="AgentTest!",
        help="Default password to set for all users (default: AgentTest!)"
    )

    parser.add_argument(
        "--random",
        action="store_true",
        help="Generate random passwords for users"
    )

    parser.add_argument(
        "--user",
        type=str,
        help="Email or username of specific user to reset"
    )

    parser.add_argument(
        "--password",
        type=str,
        help="New password for specific user (use with --user)"
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List all users in the database"
    )

    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help="Path to the database file (default: auto-detect)"
    )

    args = parser.parse_args()

    # Auto-detect database path
    if args.db is None:
        # Try to find the database relative to the script location
        script_dir = Path(__file__).parent
        backend_dir = script_dir.parent
        db_path = backend_dir / "expenses.db"
    else:
        db_path = Path(args.db)

    # Check database file exists
    if not db_path.exists():
        print(f"❌ Error: Database file not found: {db_path}")
        sys.exit(1)

    # Create database session
    engine = create_engine(f"sqlite:///{db_path}")
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # List users mode
        if args.list:
            list_users(db)
            return

        # Reset specific user
        if args.user:
            if not args.password and not args.random:
                print("❌ Error: Must specify either --password or --random with --user")
                sys.exit(1)

            reset_user_password(db, args.user, args.password, args.random)
            return

        # Reset all users
        if args.default_password or args.random:
            if args.default_password and args.random:
                print("❌ Error: Cannot use both --default-password and --random")
                sys.exit(1)

            # Confirm action
            print("⚠️  WARNING: This will reset passwords for ALL users in the database!")
            confirm = input("Type 'yes' to continue: ")

            if confirm.lower() != "yes":
                print("Operation cancelled.")
                sys.exit(0)

            reset_all_passwords(db, args.default_password, args.random)
            return

        # No valid arguments
        parser.print_help()

    finally:
        db.close()


if __name__ == "__main__":
    main()
