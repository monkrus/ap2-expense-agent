import sqlite3

conn = sqlite3.connect('backend/expenses.db')
cursor = conn.cursor()

# Reset admin account - clear the lock
cursor.execute("""
    UPDATE users
    SET failed_login_attempts = 0,
        locked_until = NULL,
        last_failed_login = NULL
    WHERE username = 'admintest'
""")

# Verify the update
cursor.execute("""
    SELECT username, failed_login_attempts, locked_until, is_active
    FROM users
    WHERE username = 'admintest'
""")

result = cursor.fetchone()
if result:
    print("Admin account reset successful!")
    print(f"  Username: {result[0]}")
    print(f"  Failed Attempts: {result[1]}")
    print(f"  Locked Until: {result[2]}")
    print(f"  Is Active: {result[3]}")
    print("\nYou can now login with:")
    print("  Username: admintest")
    print("  Password: Admin123!")
else:
    print("Admin user not found")

conn.commit()
conn.close()
