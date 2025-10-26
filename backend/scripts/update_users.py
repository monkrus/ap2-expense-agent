"""
Script to update user accounts
"""

import sys
import io
from pathlib import Path

# Fix Windows encoding issues
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add the src directory to Python path
script_dir = Path(__file__).parent
backend_dir = script_dir.parent
src_dir = backend_dir / "src"
sys.path.insert(0, str(src_dir))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

# Import User model
import importlib.util
models_py = src_dir / "models.py"
spec = importlib.util.spec_from_file_location("models", str(models_py))
models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(models)
User = models.User

# Database path
db_path = backend_dir / "expenses.db"

# Create database session
engine = create_engine(f"sqlite:///{db_path}")
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

try:
    # Activate emptest user
    emptest = db.query(User).filter(User.username == "emptest").first()
    if emptest:
        emptest.is_active = True
        emptest.updated_at = datetime.now(timezone.utc)
        print(f"✓ Activated user: emptest")
    else:
        print("✗ User 'emptest' not found")

    # Rename emptest2 to employee2
    emptest2 = db.query(User).filter(User.username == "emptest2").first()
    if emptest2:
        emptest2.username = "employee2"
        emptest2.email = "employee2@example.com"
        emptest2.updated_at = datetime.now(timezone.utc)
        print(f"✓ Renamed emptest2 to employee2")
    else:
        print("✗ User 'emptest2' not found")

    # Commit changes
    db.commit()
    print("\n✓ All changes committed successfully!")

except Exception as e:
    db.rollback()
    print(f"\n✗ Error: {e}")
    sys.exit(1)
finally:
    db.close()
