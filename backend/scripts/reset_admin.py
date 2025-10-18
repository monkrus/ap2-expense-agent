from src.database import SessionLocal
from src.models import User

db = SessionLocal()
try:
    admin = db.query(User).filter(User.username == 'admintest').first()
    if admin:
        admin.is_locked = False
        admin.failed_login_attempts = 0
        db.commit()
        print(f'✓ Admin account unlocked: {admin.username}')
        print(f'  - is_locked: {admin.is_locked}')
        print(f'  - failed_attempts: {admin.failed_login_attempts}')
    else:
        print('✗ Admin user not found')
finally:
    db.close()
