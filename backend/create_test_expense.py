from src.database import SessionLocal
from src.models import User, Expense, ExpenseStatus, Organization, OrganizationMember
from decimal import Decimal
import uuid
from datetime import datetime, UTC

db = SessionLocal()

# Find active organization
org = db.query(Organization).filter(Organization.is_active == True).first()
if not org:
    print('ERROR: No organization found')
    exit(1)

print(f'Using organization: {org.name}')

# Find a member (not admin) in this org
member = db.query(OrganizationMember).filter(
    OrganizationMember.organization_id == org.id,
    OrganizationMember.role.in_(['member', 'employee'])
).first()

if not member:
    # Use any member
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org.id
    ).first()

user = db.query(User).filter(User.id == member.user_id).first()
print(f'Creating expense for: {user.full_name} ({user.email})')

# Create PENDING expense
expense = Expense(
    id=str(uuid.uuid4()),
    user_id=user.id,
    organization_id=org.id,
    amount=Decimal('150.00'),
    vendor='Test Vendor Inc',
    category='Office Supplies',
    description='Testing admin approval workflow - Office furniture',
    status=ExpenseStatus.PENDING,
    date=datetime.now(UTC),
    created_at=datetime.now(UTC),
    updated_at=datetime.now(UTC)
)

db.add(expense)
db.commit()

print(f'\nSUCCESS: Pending expense created!')
print(f'ID: {expense.id[:8]}...')
print(f'Amount: ${expense.amount}')
print(f'Status: {expense.status.value}')
print(f'\nRefresh the Pending Approvals tab to see it!')
