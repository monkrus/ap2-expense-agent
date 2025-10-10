from src.database import SessionLocal, engine
from src.models import Expense, ExpenseStatus, User
from sqlalchemy import select

db = SessionLocal()

try:
    # Get user IDs for testuser and emptest
    testuser = db.query(User).filter(User.username == 'testuser').first()
    emptest = db.query(User).filter(User.username == 'emptest').first()

    user_ids = []
    if testuser:
        user_ids.append(testuser.id)
        print(f'Found testuser: {testuser.id}')
    if emptest:
        user_ids.append(emptest.id)
        print(f'Found emptest: {emptest.id}')

    if not user_ids:
        print('No users found')
    else:
        # Delete all pending expenses for these users
        deleted = db.query(Expense).filter(
            Expense.user_id.in_(user_ids),
            Expense.status == ExpenseStatus.PENDING
        ).delete(synchronize_session=False)

        db.commit()
        print(f'\nDeleted {deleted} pending expenses')

        # Show remaining expenses
        remaining = db.query(Expense).filter(Expense.user_id.in_(user_ids)).all()
        print(f'\nRemaining expenses for testuser and emptest: {len(remaining)}')
        for exp in remaining:
            print(f'  - {exp.id}: {exp.status.value} ${exp.amount} {exp.vendor}')

except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()
