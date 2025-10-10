import sqlite3
import sys

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Connect to database
conn = sqlite3.connect('backend/expenses.db')
cursor = conn.cursor()

print("=" * 80)
print("ADMIN USERS CHECK")
print("=" * 80)

# Check for admin users
cursor.execute("""
    SELECT id, username, email, role, created_at
    FROM users
    WHERE role IN ('ADMIN', 'MANAGER', 'ACCOUNTANT')
    ORDER BY role, username
""")

admin_users = cursor.fetchall()

if not admin_users:
    print("\n⚠️  No admin/manager/accountant users found!")
    print("\nCreating a test admin user...")

    # We'll need to create one
    print("\nPlease run the registration endpoint or create manually")
else:
    print(f"\nFound {len(admin_users)} admin-level user(s):\n")
    for user in admin_users:
        user_id, username, email, role, created_at = user
        print(f"Username: {username}")
        print(f"  Email: {email}")
        print(f"  Role: {role}")
        print(f"  ID: {user_id}")
        print(f"  Created: {created_at}")
        print()

print("=" * 80)
print("ALL USERS IN SYSTEM")
print("=" * 80)

cursor.execute("""
    SELECT username, email, role
    FROM users
    ORDER BY created_at
""")

all_users = cursor.fetchall()
print(f"\nTotal users: {len(all_users)}\n")
for username, email, role in all_users:
    print(f"  {username:20} {email:30} {role}")

conn.close()
