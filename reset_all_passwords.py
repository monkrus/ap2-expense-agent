import sqlite3
import bcrypt

conn = sqlite3.connect('backend/expenses.db')
cursor = conn.cursor()

# New password for all accounts
new_password = "AgentTest!"
hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Accounts to reset
accounts = ['admintest', 'testuser', 'emptest']

print("=" * 80)
print("RESETTING PASSWORDS")
print("=" * 80)
print(f"\nNew password for all accounts: {new_password}\n")

for username in accounts:
    # Update password and unlock account
    cursor.execute("""
        UPDATE users
        SET hashed_password = ?,
            failed_login_attempts = 0,
            locked_until = NULL,
            last_failed_login = NULL
        WHERE username = ?
    """, (hashed_password, username))

    if cursor.rowcount > 0:
        print(f"[OK] {username} - Password reset successfully")
    else:
        print(f"[FAIL] {username} - User not found")

conn.commit()

print("\n" + "=" * 80)
print("UPDATED TEST CREDENTIALS")
print("=" * 80)

# Verify the updates
cursor.execute("""
    SELECT username, email, role, is_active
    FROM users
    WHERE username IN ('admintest', 'testuser', 'emptest')
    ORDER BY role DESC, username
""")

users = cursor.fetchall()

for user in users:
    print(f"\nUsername: {user[0]}")
    print(f"  Email: {user[1]}")
    print(f"  Role: {user[2]}")
    print(f"  Password: AgentTest!")

conn.close()
