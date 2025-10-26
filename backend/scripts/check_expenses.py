import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import SessionLocal
from src.models import Expense

db = SessionLocal()
try:
    expenses = db.query(Expense).all()
    print(f'\nTotal expenses: {len(expenses)}')
    print(f'Archived: {len([e for e in expenses if e.is_archived])}')
    print(f'Not archived: {len([e for e in expenses if not e.is_archived])}')
    print('\nFirst 10 expenses:')
    for e in expenses[:10]:
        print(f'  {e.id[:8]}... status={e.status.value:10} archived={e.is_archived}')
finally:
    db.close()
