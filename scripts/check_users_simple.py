"""
Simple script to check users in database
"""
import sqlite3
from pathlib import Path

# Database path
db_path = Path("backend/expenses.db")
if not db_path.exists():
    print(f"Error: Database not found at {db_path}")
    exit(1)

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all users
cursor.execute("SELECT username, email, role, is_active FROM users")
users = cursor.fetchall()

print("=" * 80)
print("USERS IN DATABASE")
print("=" * 80)
print()

if not users:
    print("No users found!")
else:
    print(f"Found {len(users)} users:")
    print()
    print(f"{'Username':<20} {'Email':<30} {'Role':<15} {'Active':<8}")
    print("-" * 80)
    for username, email, role, is_active in users:
        active_str = "Yes" if is_active else "No"
        print(f"{username:<20} {email:<30} {role:<15} {active_str:<8}")

conn.close()
