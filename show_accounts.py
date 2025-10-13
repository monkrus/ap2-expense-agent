import sqlite3

conn = sqlite3.connect('backend/expenses.db')
cursor = conn.cursor()

print("=" * 80)
print("CURRENT USER ACCOUNTS")
print("=" * 80)

# Get all users
cursor.execute("""
    SELECT username, email, role, is_active, is_verified,
           failed_login_attempts, locked_until, created_at
    FROM users
    ORDER BY role DESC, username
""")

users = cursor.fetchall()

print(f"\nTotal users: {len(users)}\n")

for user in users:
    print(f"Username: {user[0]}")
    print(f"  Email: {user[1]}")
    print(f"  Role: {user[2]}")
    print(f"  Active: {'Yes' if user[3] else 'No'}")
    print(f"  Verified: {'Yes' if user[4] else 'No'}")
    print(f"  Failed Logins: {user[5]}")
    print(f"  Locked Until: {user[6] if user[6] else 'Not locked'}")
    print(f"  Created: {user[7]}")
    print()

print("=" * 80)
print("DEFAULT TEST PASSWORDS (from documentation)")
print("=" * 80)
print("\nADMIN:")
print("  Username: admintest")
print("  Password: Admin123!  (needs to be changed to AdminTest!)")
print("\nEMPLOYEE:")
print("  Username: emptest")
print("  Password: Employee123!")

conn.close()
