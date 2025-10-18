import sys
import uuid
sys.path.insert(0, '.')

from src.database import SessionLocal
from src.models import User, UserRole
from src.auth import AuthService

db = SessionLocal()

# Delete all existing users
users = db.query(User).all()
for user in users:
    db.delete(user)
db.commit()
print(f'Deleted {len(users)} existing users')

# Create new users with password AgentTest!
password = 'AgentTest!'
hashed = AuthService.hash_password(password)

print(f'\nCreating users with password: {password}')
print(f'Hash: {hashed}\n')

# Create admin
admin = User(
    id=str(uuid.uuid4()),
    username='admintest',
    email='admintest@example.com',
    full_name='Admin Test',
    role=UserRole.ADMIN,
    hashed_password=hashed,
    is_active=True,
    is_verified=True
)
db.add(admin)

# Create manager
manager = User(
    id=str(uuid.uuid4()),
    username='testuser',
    email='testuser@example.com',
    full_name='Test User Manager',
    role=UserRole.MANAGER,
    hashed_password=hashed,
    is_active=True,
    is_verified=True
)
db.add(manager)

# Create employee
employee = User(
    id=str(uuid.uuid4()),
    username='emptest',
    email='emptest@example.com',
    full_name='Test User Employee',
    role=UserRole.EMPLOYEE,
    hashed_password=hashed,
    is_active=True,
    is_verified=True
)
db.add(employee)

db.commit()

print('Created users successfully:')
print(f'  admintest  - Role: {admin.role.value:10} - Email: {admin.email}')
print(f'  testuser   - Role: {manager.role.value:10} - Email: {manager.email}')
print(f'  emptest    - Role: {employee.role.value:10} - Email: {employee.email}')
print(f'\nAll users have password: {password}')

# Verify password works
test_user = db.query(User).filter(User.username == 'testuser').first()
verification = AuthService.verify_password(password, test_user.hashed_password)
print(f'\nPassword verification test for testuser: {verification}')

db.close()
