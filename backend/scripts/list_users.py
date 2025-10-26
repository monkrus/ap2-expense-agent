"""
Script to list all users and their roles in the database.

This script displays:
- Username
- Email
- Role
- Active status
- Account lock status
- Organization (if applicable)
- Created and last updated timestamps

Usage:
    python list_users.py
    python list_users.py --role admin
    python list_users.py --active
    python list_users.py --locked
    python list_users.py --org "Company Name"
    python list_users.py --format json
"""

import sys
import os
import argparse
import json
from datetime import datetime
from pathlib import Path

# Add the src directory to Python path
backend_dir = Path(__file__).parent
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


def format_datetime(dt):
    """Format datetime for display"""
    if dt is None:
        return "N/A"
    if isinstance(dt, str):
        return dt
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def is_account_locked(user):
    """Check if account is currently locked"""
    if user.locked_until is None:
        return False
    if isinstance(user.locked_until, str):
        # Parse string datetime if needed
        try:
            locked_until = datetime.fromisoformat(user.locked_until.replace('Z', '+00:00'))
            return locked_until > datetime.utcnow()
        except:
            return False
    return user.locked_until > datetime.utcnow()


def list_users_table(db: Session, role_filter=None, active_only=False, locked_only=False, org_filter=None):
    """List users in table format"""
    query = db.query(User)

    # Apply filters
    if role_filter:
        query = query.filter(User.role == role_filter)
    if active_only:
        query = query.filter(User.is_active == True)
    if org_filter:
        # Assuming there's an organization relationship
        try:
            query = query.join(User.organization).filter(User.organization.has(name=org_filter))
        except:
            pass  # Skip if organization relationship doesn't exist

    users = query.all()

    if not users:
        print("No users found matching the criteria.")
        return

    # Filter locked users if requested
    if locked_only:
        users = [u for u in users if is_account_locked(u)]
        if not users:
            print("No locked users found.")
            return

    print("=" * 120)
    print(f"USERS IN DATABASE ({len(users)} total)")
    print("=" * 120)
    print()

    # Header
    print(f"{'Username':<20} {'Email':<30} {'Role':<15} {'Active':<8} {'Locked':<8} {'Created':<20}")
    print("-" * 120)

    # Rows
    for user in users:
        username = user.username[:19] if len(user.username) > 19 else user.username
        email = user.email[:29] if len(user.email) > 29 else user.email
        role = user.role.value if hasattr(user.role, 'value') else str(user.role)
        active = "Yes" if user.is_active else "No"
        locked = "Yes" if is_account_locked(user) else "No"
        created = format_datetime(user.created_at)[:19] if hasattr(user, 'created_at') else "N/A"

        print(f"{username:<20} {email:<30} {role:<15} {active:<8} {locked:<8} {created:<20}")

    print("=" * 120)
    print()


def list_users_detailed(db: Session, role_filter=None, active_only=False, locked_only=False, org_filter=None):
    """List users in detailed format"""
    query = db.query(User)

    # Apply filters
    if role_filter:
        query = query.filter(User.role == role_filter)
    if active_only:
        query = query.filter(User.is_active == True)
    if org_filter:
        try:
            query = query.join(User.organization).filter(User.organization.has(name=org_filter))
        except:
            pass

    users = query.all()

    if not users:
        print("No users found matching the criteria.")
        return

    # Filter locked users if requested
    if locked_only:
        users = [u for u in users if is_account_locked(u)]
        if not users:
            print("No locked users found.")
            return

    print("=" * 120)
    print(f"USERS IN DATABASE ({len(users)} total)")
    print("=" * 120)
    print()

    for i, user in enumerate(users, 1):
        print(f"[{i}] User Details:")
        print(f"  Username:              {user.username}")
        print(f"  Email:                 {user.email}")
        print(f"  Role:                  {user.role.value if hasattr(user.role, 'value') else str(user.role)}")
        print(f"  Active:                {user.is_active}")
        print(f"  Locked:                {is_account_locked(user)}")

        if hasattr(user, 'failed_login_attempts'):
            print(f"  Failed Login Attempts: {user.failed_login_attempts}")

        if hasattr(user, 'locked_until') and user.locked_until:
            print(f"  Locked Until:          {format_datetime(user.locked_until)}")

        if hasattr(user, 'last_failed_login') and user.last_failed_login:
            print(f"  Last Failed Login:     {format_datetime(user.last_failed_login)}")

        if hasattr(user, 'organization') and user.organization:
            try:
                print(f"  Organization:          {user.organization.name}")
            except:
                pass

        if hasattr(user, 'created_at'):
            print(f"  Created At:            {format_datetime(user.created_at)}")

        if hasattr(user, 'updated_at'):
            print(f"  Updated At:            {format_datetime(user.updated_at)}")

        print("-" * 120)

    print()


def list_users_json(db: Session, role_filter=None, active_only=False, locked_only=False, org_filter=None):
    """List users in JSON format"""
    query = db.query(User)

    # Apply filters
    if role_filter:
        query = query.filter(User.role == role_filter)
    if active_only:
        query = query.filter(User.is_active == True)
    if org_filter:
        try:
            query = query.join(User.organization).filter(User.organization.has(name=org_filter))
        except:
            pass

    users = query.all()

    # Filter locked users if requested
    if locked_only:
        users = [u for u in users if is_account_locked(u)]

    users_data = []
    for user in users:
        user_dict = {
            "username": user.username,
            "email": user.email,
            "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
            "is_active": user.is_active,
            "is_locked": is_account_locked(user),
        }

        if hasattr(user, 'failed_login_attempts'):
            user_dict["failed_login_attempts"] = user.failed_login_attempts

        if hasattr(user, 'locked_until') and user.locked_until:
            user_dict["locked_until"] = format_datetime(user.locked_until)

        if hasattr(user, 'organization') and user.organization:
            try:
                user_dict["organization"] = user.organization.name
            except:
                pass

        if hasattr(user, 'created_at'):
            user_dict["created_at"] = format_datetime(user.created_at)

        if hasattr(user, 'updated_at'):
            user_dict["updated_at"] = format_datetime(user.updated_at)

        users_data.append(user_dict)

    result = {
        "total": len(users_data),
        "users": users_data
    }

    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="List all users and their roles in the expense management system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all users in table format
  python list_users.py

  # List all users in detailed format
  python list_users.py --detailed

  # List only admin users
  python list_users.py --role admin

  # List only active users
  python list_users.py --active

  # List only locked users
  python list_users.py --locked

  # List users from a specific organization
  python list_users.py --org "Acme Corp"

  # Export users to JSON
  python list_users.py --format json

  # Combine filters
  python list_users.py --role user --active --format detailed
        """
    )

    parser.add_argument(
        "--role",
        type=str,
        choices=["admin", "manager", "user"],
        help="Filter by role (admin, manager, or user)"
    )

    parser.add_argument(
        "--active",
        action="store_true",
        help="Show only active users"
    )

    parser.add_argument(
        "--locked",
        action="store_true",
        help="Show only locked users"
    )

    parser.add_argument(
        "--org",
        type=str,
        help="Filter by organization name"
    )

    parser.add_argument(
        "--format",
        type=str,
        choices=["table", "detailed", "json"],
        default="table",
        help="Output format (table, detailed, or json)"
    )

    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed information (shortcut for --format detailed)"
    )

    parser.add_argument(
        "--db",
        type=str,
        default="backend/expenses.db",
        help="Path to the database file (default: backend/expenses.db)"
    )

    args = parser.parse_args()

    # Check database file exists
    db_path = args.db
    if not os.path.exists(db_path):
        print(f"Error: Database file not found: {db_path}")
        sys.exit(1)

    # Determine output format
    output_format = args.format
    if args.detailed:
        output_format = "detailed"

    # Create database session
    engine = create_engine(f"sqlite:///{db_path}")
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        if output_format == "json":
            list_users_json(db, args.role, args.active, args.locked, args.org)
        elif output_format == "detailed":
            list_users_detailed(db, args.role, args.active, args.locked, args.org)
        else:
            list_users_table(db, args.role, args.active, args.locked, args.org)
    finally:
        db.close()


if __name__ == "__main__":
    main()
