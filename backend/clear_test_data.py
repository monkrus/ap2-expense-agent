"""
Clear test data and keep only production-ready data.

This script:
1. Deletes all usage metrics from before today
2. Deletes all expenses from before today
3. Keeps database structure intact
4. Preserves users, organizations, and tier configuration
"""

import os
from datetime import datetime
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv('DATABASE_URL', 'sqlite:///./expense_agent.db')
engine = create_engine(db_url)

def clear_old_data():
    """Clear test data from before today"""

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_str = today.strftime('%Y-%m-%d 00:00:00')

    print(f"Clearing data from before: {today_str}")
    print("=" * 60)

    with engine.begin() as conn:
        # Count what we're about to delete
        result = conn.execute(text("""
            SELECT COUNT(*) as count FROM usage_metrics
            WHERE created_at < :today
        """), {"today": today_str})
        usage_count = result.fetchone()[0]

        result = conn.execute(text("""
            SELECT COUNT(*) as count FROM expenses
            WHERE created_at < :today
        """), {"today": today_str})
        expense_count = result.fetchone()[0]

        print(f"\nData to be deleted:")
        print(f"  - {usage_count} usage metrics")
        print(f"  - {expense_count} expenses")

        if usage_count == 0 and expense_count == 0:
            print("\n[OK] No old data to clean. Database is already clean.")
            return

        # Confirm deletion
        response = input("\nProceed with deletion? (yes/no): ")
        if response.lower() != 'yes':
            print("Cancelled.")
            return

        # Delete old usage metrics
        result = conn.execute(text("""
            DELETE FROM usage_metrics
            WHERE created_at < :today
        """), {"today": today_str})
        print(f"\n[OK] Deleted {usage_count} usage metrics")

        # Delete old expenses (including receipts via cascade)
        result = conn.execute(text("""
            DELETE FROM expenses
            WHERE created_at < :today
        """), {"today": today_str})
        print(f"[OK] Deleted {expense_count} expenses")

        # Show what remains
        print("\n" + "=" * 60)
        print("Remaining data:")

        result = conn.execute(text("""
            SELECT COUNT(*) as count FROM usage_metrics
        """))
        print(f"  - {result.fetchone()[0]} usage metrics (today)")

        result = conn.execute(text("""
            SELECT COUNT(*) as count FROM expenses
        """))
        print(f"  - {result.fetchone()[0]} expenses (today)")

        result = conn.execute(text("""
            SELECT COUNT(*) as count FROM users
        """))
        print(f"  - {result.fetchone()[0]} users (preserved)")

        result = conn.execute(text("""
            SELECT COUNT(*) as count FROM organizations
        """))
        print(f"  - {result.fetchone()[0]} organizations (preserved)")

        print("\n[OK] Database cleaned successfully!")
        print("\nNote: All users, organizations, and tier configurations were preserved.")

if __name__ == "__main__":
    try:
        clear_old_data()
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
