"""Check latest expense and notification"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from src.database import SessionLocal
from src.models import Expense, User, Notification, OrganizationMember

db = SessionLocal()

# Get latest expense
expense = db.query(Expense).order_by(Expense.created_at.desc()).first()

if not expense:
    print("No expenses found!")
    db.close()
    sys.exit(0)

print("=" * 70)
print("LATEST EXPENSE")
print("=" * 70)
print(f"Expense ID: {expense.id}")
print(f"Amount: ${expense.amount}")
print(f"Vendor: {expense.vendor}")
print(f"Organization ID: {expense.organization_id}")
print(f"Status: {expense.status}")
print(f"Created: {expense.created_at}")

user = db.query(User).filter(User.id == expense.user_id).first()
print(f"Submitted by: {user.username} (User ID: {user.id})")
print(f"Submitter role: {user.role}")

# Check who should receive notification (admins/owners in that org)
print("\n" + "=" * 70)
print("WHO SHOULD GET NOTIFICATION?")
print("=" * 70)

admin_members = db.query(OrganizationMember).filter(
    OrganizationMember.organization_id == expense.organization_id,
    OrganizationMember.is_active == True
).all()

print(f"All members in organization {expense.organization_id}:")
for member in admin_members:
    member_user = db.query(User).filter(User.id == member.user_id).first()
    print(f"  - {member_user.username} (Role: {member.role}, User Role: {member_user.role})")

# Check actual notifications
print("\n" + "=" * 70)
print("ACTUAL NOTIFICATIONS CREATED")
print("=" * 70)

notification = db.query(Notification).filter(Notification.expense_id == expense.id).first()

if notification:
    recipient = db.query(User).filter(User.id == notification.user_id).first()
    print(f"Notification sent to: {recipient.username}")
    print(f"Title: {notification.title}")
    print(f"Message: {notification.message}")
    print(f"Read: {notification.is_read}")
    print(f"Created: {notification.created_at}")
else:
    print("NO notification found for this expense!")

db.close()
