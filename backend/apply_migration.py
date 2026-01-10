"""
Apply auto_approved_via field migration
"""
from src.database import SessionLocal
from sqlalchemy import text

def apply_migration():
    db = SessionLocal()
    try:
        # Add auto_approved_via column
        db.execute(text('ALTER TABLE expenses ADD COLUMN auto_approved_via VARCHAR(50)'))
        db.commit()
        print('SUCCESS: Column auto_approved_via added to expenses table')

        # Backfill existing data
        db.execute(text("""
            UPDATE expenses
            SET auto_approved_via = 'intent_mandate'
            WHERE auto_approved = 1 AND intent_mandate_id IS NOT NULL
        """))

        db.execute(text("""
            UPDATE expenses
            SET auto_approved_via = 'approval_policy'
            WHERE auto_approved = 1 AND approval_policy_id IS NOT NULL AND intent_mandate_id IS NULL
        """))

        db.commit()
        print('SUCCESS: Backfilled existing auto-approved expenses')

        # Verify
        result = db.execute(text("""
            SELECT auto_approved, auto_approved_via, COUNT(*) as count
            FROM expenses
            GROUP BY auto_approved, auto_approved_via
        """))

        print('\nVerification - Expense counts by auto_approved status:')
        for row in result:
            print(f'  auto_approved={row[0]}, auto_approved_via={row[1]}, count={row[2]}')

    except Exception as e:
        if 'duplicate column name' in str(e).lower():
            print('INFO: Column auto_approved_via already exists')
        else:
            print(f'ERROR: {e}')
            db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    apply_migration()
