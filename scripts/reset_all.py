"""
Automated script to reset all passwords to Testme1! without prompts
"""
import sys
from pathlib import Path

# Add the src directory to Python path
script_dir = Path(__file__).parent
backend_dir = script_dir / "backend"
src_dir = backend_dir / "src"
sys.path.insert(0, str(src_dir))

import bcrypt
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import the User model
import importlib.util

models_py = src_dir / "models.py"
spec = importlib.util.spec_from_file_location("models", str(models_py))
models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(models)
User = models.User

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

# Database path
db_path = backend_dir / "expenses.db"
if not db_path.exists():
    print(f"Error: Database not found at {db_path}")
    sys.exit(1)

# Create database session
engine = create_engine(f"sqlite:///{db_path}")
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# Password to set
test_password = "Testme1!"

try:
    users = db.query(User).all()

    if not users:
        print("No users found in database!")
        sys.exit(0)

    print(f"Resetting passwords for {len(users)} users to: {test_password}")
    print()

    for user in users:
        # Hash and update password
        user.hashed_password = hash_password(test_password)
        user.updated_at = datetime.now(timezone.utc)

        # Reset failed login attempts
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_failed_login = None

        print(f"Reset password for: {user.username} ({user.email})")

    # Commit all changes
    db.commit()

    print()
    print("=" * 80)
    print(f"SUCCESS: All {len(users)} user passwords have been reset to: {test_password}")
    print("=" * 80)

finally:
    db.close()
