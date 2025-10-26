#!/usr/bin/env python3
"""Unarchive all expenses"""
import sys
import os
# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import SessionLocal
from src.models import Expense

db = SessionLocal()
try:
    expenses = db.query(Expense).filter(Expense.is_archived == True).all()
    print(f'Found {len(expenses)} archived expenses')

    for expense in expenses:
        expense.is_archived = False
        expense.archived_at = None
        expense.archived_by = None
        print(f'Unarchiving {expense.id[:8]}... status={expense.status.value}')

    db.commit()
    print(f'\nSuccessfully unarchived {len(expenses)} expenses')

    # Verify
    remaining = db.query(Expense).filter(Expense.is_archived == True).count()
    print(f'Remaining archived: {remaining}')

finally:
    db.close()
