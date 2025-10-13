import sqlite3

# Connect to the database
conn = sqlite3.connect('backend/expenses.db')
cursor = conn.cursor()

# Reset admin account
cursor.execute("""
    UPDATE users
    SET is_locked = 0,
        failed_login_attempts = 0
    WHERE username = 'admintest'
""")

# Verify the update
cursor.execute("""
    SELECT username, is_locked, failed_login_attempts
    FROM users
    WHERE username = 'admintest'
""")

result = cursor.fetchone()
if result:
    print(f"✓ Admin account reset successful!")
    print(f"  Username: {result[0]}")
    print(f"  Is Locked: {result[1]}")
    print(f"  Failed Attempts: {result[2]}")
else:
    print("✗ Admin user not found")

conn.commit()
conn.close()
