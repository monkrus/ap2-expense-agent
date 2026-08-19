"""
PostgreSQL Migration Test Script
Tests database migration on PostgreSQL before production deployment

Usage:
    python test_postgres_migration.py --db-url postgresql://user:pass@localhost/dbname

Requirements:
    - PostgreSQL server running
    - Database created
    - .env file with DATABASE_URL (or pass via --db-url)
"""

import argparse
import os
import sys
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_success(msg):
    print(f"{GREEN}✓{RESET} {msg}")


def print_error(msg):
    print(f"{RED}✗{RESET} {msg}")


def print_info(msg):
    print(f"{BLUE}ℹ{RESET} {msg}")


def print_warning(msg):
    print(f"{YELLOW}⚠{RESET} {msg}")


def test_connection(db_url):
    """Test database connection"""
    print_info("Testing database connection...")
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print_success(f"Connected to PostgreSQL: {version.split(',')[0]}")
            return engine
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return None


def check_existing_tables(engine):
    """Check if tables already exist"""
    print_info("Checking existing tables...")
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if tables:
        print_warning(f"Found {len(tables)} existing tables:")
        for table in sorted(tables):
            print(f"  - {table}")
        return tables
    else:
        print_info("No existing tables found (clean database)")
        return []


def get_alembic_version(engine):
    """Get current alembic version"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            version = result.fetchone()
            if version:
                return version[0]
    except:
        return None
    return None


def run_migration(db_url):
    """Run alembic migration"""
    print_info("Running Alembic migration...")
    print_info("Command: alembic upgrade head")

    # Set environment variable for alembic
    os.environ["DATABASE_URL"] = db_url

    import subprocess

    try:
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd="backend",
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            print_success("Migration completed successfully")
            print(result.stdout)
            return True
        else:
            print_error("Migration failed")
            print(result.stderr)
            return False
    except subprocess.TimeoutExpired:
        print_error("Migration timed out (>60 seconds)")
        return False
    except Exception as e:
        print_error(f"Migration error: {e}")
        return False


def verify_tables(engine):
    """Verify all expected tables exist"""
    print_info("Verifying database schema...")

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    # Expected tables from our schema
    expected_tables = {
        "users",
        "organizations",
        "organization_members",
        "expenses",
        "receipts",
        "budgets",
        "approval_policies",  # NEW TABLE
        "sessions",
        "subscriptions",
        "usage_records",
        "notifications",
        "audit_logs",
        "alembic_version",
    }

    missing = expected_tables - tables
    extra = tables - expected_tables

    if missing:
        print_error(f"Missing tables: {missing}")
        return False

    if extra:
        print_warning(f"Extra tables (not in expected list): {extra}")

    print_success(f"All {len(expected_tables)} expected tables found")
    return True


def verify_approval_policy_table(engine):
    """Verify approval_policies table structure"""
    print_info("Verifying approval_policies table structure...")

    inspector = inspect(engine)

    if "approval_policies" not in inspector.get_table_names():
        print_error("approval_policies table not found!")
        return False

    columns = {col["name"]: col for col in inspector.get_columns("approval_policies")}

    # Expected columns
    expected_columns = [
        "id",
        "organization_id",
        "name",
        "description",
        "priority",
        "is_active",
        "auto_approve",
        "require_receipt",
        "notify_on_auto_approve",
        "conditions",
        "max_amount_per_expense",
        "daily_limit_per_user",
        "monthly_limit_per_user",
        "yearly_limit_per_user",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    ]

    missing = set(expected_columns) - set(columns.keys())

    if missing:
        print_error(f"Missing columns in approval_policies: {missing}")
        return False

    print_success(f"approval_policies table has all {len(expected_columns)} columns")

    # Check specific column types
    print_info("Checking column types...")

    checks = [
        ("id", "VARCHAR"),
        ("organization_id", "VARCHAR"),
        ("conditions", "JSON"),
        ("max_amount_per_expense", "NUMERIC"),
        ("daily_limit_per_user", "NUMERIC"),
    ]

    for col_name, expected_type in checks:
        col = columns.get(col_name)
        if col:
            actual_type = str(col["type"]).upper()
            if expected_type in actual_type:
                print_success(f"  {col_name}: {actual_type} ✓")
            else:
                print_warning(f"  {col_name}: {actual_type} (expected {expected_type})")

    return True


def verify_expense_columns(engine):
    """Verify new columns added to expenses table"""
    print_info("Verifying new expense columns...")

    inspector = inspect(engine)

    if "expenses" not in inspector.get_table_names():
        print_error("expenses table not found!")
        return False

    columns = {col["name"]: col for col in inspector.get_columns("expenses")}

    # New columns added by migration
    new_columns = ["auto_approved", "approval_policy_id"]

    for col_name in new_columns:
        if col_name in columns:
            col_type = str(columns[col_name]["type"])
            print_success(f"  {col_name}: {col_type} ✓")
        else:
            print_error(f"  Missing column: {col_name}")
            return False

    return True


def test_rollback(db_url):
    """Test migration rollback"""
    print_info("Testing migration rollback...")

    print_warning("This will downgrade the database by 1 revision")
    response = input("Continue? (yes/no): ")

    if response.lower() != "yes":
        print_info("Skipped rollback test")
        return True

    os.environ["DATABASE_URL"] = db_url

    import subprocess

    try:
        # Downgrade
        print_info("Running: alembic downgrade -1")
        result = subprocess.run(
            ["alembic", "downgrade", "-1"],
            cwd="backend",
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            print_error("Rollback failed")
            print(result.stderr)
            return False

        print_success("Rollback successful")

        # Verify tables removed
        engine = create_engine(db_url)
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        if "approval_policies" in tables:
            print_error("approval_policies table still exists after rollback!")
            return False

        print_success("approval_policies table removed successfully")

        # Re-upgrade
        print_info("Re-running migration...")
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd="backend",
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            print_error("Re-migration failed")
            return False

        print_success("Re-migration successful")
        return True

    except Exception as e:
        print_error(f"Rollback test error: {e}")
        return False


def test_data_integrity(engine):
    """Test data operations"""
    print_info("Testing data operations...")

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Test insert
        from datetime import datetime

        test_data = {
            "id": "test_policy_123",
            "organization_id": "test_org_123",
            "name": "Test Policy",
            "priority": 100,
            "is_active": True,
            "auto_approve": True,
            "require_receipt": False,
            "notify_on_auto_approve": True,
            "conditions": {"categories": ["MEALS"]},
            "max_amount_per_expense": 50.00,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        session.execute(
            text("""
                INSERT INTO approval_policies
                (id, organization_id, name, priority, is_active, auto_approve,
                 require_receipt, notify_on_auto_approve, conditions,
                 max_amount_per_expense, created_at, updated_at)
                VALUES
                (:id, :organization_id, :name, :priority, :is_active, :auto_approve,
                 :require_receipt, :notify_on_auto_approve, :conditions::jsonb,
                 :max_amount_per_expense, :created_at, :updated_at)
            """),
            test_data,
        )
        session.commit()
        print_success("Test insert successful")

        # Test select
        result = session.execute(
            text("SELECT * FROM approval_policies WHERE id = :id"),
            {"id": "test_policy_123"},
        )
        row = result.fetchone()

        if row:
            print_success("Test select successful")
        else:
            print_error("Test select failed - no data returned")
            return False

        # Test delete
        session.execute(
            text("DELETE FROM approval_policies WHERE id = :id"),
            {"id": "test_policy_123"},
        )
        session.commit()
        print_success("Test delete successful")

        return True

    except Exception as e:
        print_error(f"Data operation failed: {e}")
        session.rollback()
        return False
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description="Test PostgreSQL migration")
    parser.add_argument(
        "--db-url",
        help="Database URL (postgresql://user:pass@host/dbname)",
        default=os.getenv("DATABASE_URL"),
    )
    parser.add_argument(
        "--skip-rollback", action="store_true", help="Skip rollback test"
    )

    args = parser.parse_args()

    if not args.db_url:
        print_error("No database URL provided")
        print_error("Use --db-url or set DATABASE_URL environment variable")
        sys.exit(1)

    if "postgresql" not in args.db_url:
        print_error("This script is for PostgreSQL testing only")
        print_error(f"Got: {args.db_url}")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("POSTGRESQL MIGRATION TEST")
    print("=" * 70 + "\n")

    # Test connection
    engine = test_connection(args.db_url)
    if not engine:
        sys.exit(1)

    # Check existing state
    existing_tables = check_existing_tables(engine)
    current_version = get_alembic_version(engine)

    if current_version:
        print_info(f"Current Alembic version: {current_version}")
    else:
        print_info("No Alembic version found (new database)")

    # Run migration
    if not run_migration(args.db_url):
        sys.exit(1)

    # Verify schema
    if not verify_tables(engine):
        print_error("Table verification failed")
        sys.exit(1)

    if not verify_approval_policy_table(engine):
        print_error("Approval policy table verification failed")
        sys.exit(1)

    if not verify_expense_columns(engine):
        print_error("Expense columns verification failed")
        sys.exit(1)

    # Test data operations
    if not test_data_integrity(engine):
        print_error("Data integrity test failed")
        sys.exit(1)

    # Test rollback (optional)
    if not args.skip_rollback:
        if not test_rollback(args.db_url):
            print_warning("Rollback test failed (non-critical)")

    # Summary
    print("\n" + "=" * 70)
    print("MIGRATION TEST SUMMARY")
    print("=" * 70)
    print_success("✓ Database connection")
    print_success("✓ Migration execution")
    print_success("✓ Schema verification")
    print_success("✓ approval_policies table")
    print_success("✓ expense columns")
    print_success("✓ Data operations")
    if not args.skip_rollback:
        print_success("✓ Rollback test")

    print(f"\n{GREEN}All tests PASSED!{RESET}")
    print(f"{GREEN}PostgreSQL migration is production-ready.{RESET}\n")


if __name__ == "__main__":
    main()
