import sqlite3
import bcrypt

conn = sqlite3.connect('backend/expenses.db')
cursor = conn.cursor()

print("=" * 80)
print("CURRENT USER ACCOUNTS")
print("=" * 80)

# Get all users
cursor.execute("""
    SELECT username, email, role, is_active, is_verified,
           failed_login_attempts, locked_until
    FROM users
    ORDER BY role, username
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
    print()

print("=" * 80)
print("RESETTING ADMIN PASSWORD")
print("=" * 80)

# Hash the new password
new_password = "AdminTest!"
hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Update admin password and unlock account
cursor.execute("""
    UPDATE users
    SET hashed_password = ?,
        failed_login_attempts = 0,
        locked_until = NULL,
        last_failed_login = NULL
    WHERE username = 'admintest'
""", (hashed_password,))

conn.commit()

print(f"\nAdmin password reset to: {new_password}")
print("Account unlocked and ready to use!")

print("\n" + "=" * 80)
print("TEST CREDENTIALS")
print("=" * 80)
print("\nADMIN ACCOUNT:")
print("  Username: admintest")
print("  Password: AdminTest!")
print("\nEMPLOYEE ACCOUNT (if exists):")
print("  Username: emptest")
print("  Password: Employee123!")

conn.close()
