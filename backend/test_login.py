import sys
sys.path.insert(0, '.')
from src.database import SessionLocal
from src.models import User
from src.auth import AuthService

db = SessionLocal()
user = db.query(User).filter(User.username == 'testuser').first()

if user:
    print(f'User found: {user.username}')
    print(f'Hash in DB: {user.hashed_password[:60]}...')

    # Test password verification
    password = 'AgentTest!'
    result = AuthService.verify_password(password, user.hashed_password)
    print(f'Password "{password}" verification: {result}')
else:
    print('User not found')

db.close()
