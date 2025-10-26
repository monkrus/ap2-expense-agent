"""
Script to verify all users have the same password by checking password hashes
"""
import sqlite3
from pathlib import Path
import bcrypt

def check_bcrypt_password(hashed_password, password):
    """Check a password hash in bcrypt format"""
    try:
        # Truncate password to 72 bytes for bcrypt compatibility
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        return bcrypt.checkpw(password_bytes, hashed_password.encode('utf-8'))
    except Exception as e:
        print(f"Error checking password: {e}")
        return False

# Database path
db_path = Path("backend/expenses.db")
if not db_path.exists():
    print(f"Error: Database not found at {db_path}")
    exit(1)

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Test password
test_password = "AgentTest!"

# Get all users with password hashes
cursor.execute("SELECT username, email, role, hashed_password FROM users")
users = cursor.fetchall()

print("=" * 80)
print("CHECKING USER LOGIN WITH PASSWORD: AgentTest!")
print("=" * 80)
print()

if not users:
    print("No users found!")
else:
    print(f"Found {len(users)} users:")
    print()
    print(f"{'Username':<20} {'Email':<30} {'Role':<15} {'Can Login':<12}")
    print("-" * 80)

    success_count = 0
    fail_count = 0

    for username, email, role, password_hash in users:
        can_login = check_bcrypt_password(password_hash, test_password)
        status = "YES" if can_login else "NO"

        print(f"{username:<20} {email:<30} {role:<15} {status:<12}")

        if can_login:
            success_count += 1
        else:
            fail_count += 1

    print()
    print("=" * 80)
    print(f"SUMMARY: {success_count}/{len(users)} users can login with password 'AgentTest!'")
    print("=" * 80)

    if fail_count > 0:
        print()
        print(f"WARNING: {fail_count} users CANNOT login with the test password!")
        print("You may need to reset their passwords.")

conn.close()
