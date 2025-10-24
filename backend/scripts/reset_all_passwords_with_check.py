import sqlite3
import bcrypt

conn = sqlite3.connect('backend/expenses.db')
cursor = conn.cursor()

print("=" * 80)
print("DIAGNOSTIC: Checking Current User Status")
print("=" * 80)

# Check if users exist
accounts = ['admintest', 'testuser', 'emptest', 'employee2']

for username in accounts:
    cursor.execute("""
        SELECT username, email, role, is_active, failed_login_attempts, 
               locked_until, hashed_password
        FROM users
        WHERE username = ?
    """, (username,))
    
    user = cursor.fetchone()
    
    if user:
        print(f"\n[FOUND] {username}")
        print(f"  Email: {user[1]}")
        print(f"  Role: {user[2]}")
        print(f"  Active: {user[3]}")
        print(f"  Failed attempts: {user[4]}")
        print(f"  Locked until: {user[5]}")
        print(f"  Has password: {'Yes' if user[6] else 'No'}")
    else:
        print(f"\n[NOT FOUND] {username} - User does not exist in database!")

print("\n" + "=" * 80)
print("PERFORMING PASSWORD RESET")
print("=" * 80)

# New password
new_password = "AgentTest!"
hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

print(f"\nNew password: {new_password}")
print(f"Hashed password: {hashed_password[:50]}...")

for username in accounts:
    # Check if user exists first
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    if not cursor.fetchone():
        print(f"\n[SKIP] {username} - User doesn't exist, skipping")
        continue
    
    # Update password and unlock account
    cursor.execute("""
        UPDATE users
        SET hashed_password = ?,
            failed_login_attempts = 0,
            locked_until = NULL,
            last_failed_login = NULL,
            is_active = 1
        WHERE username = ?
    """, (hashed_password, username))
    
    if cursor.rowcount > 0:
        print(f"\n[SUCCESS] {username} - Password reset successfully")
    else:
        print(f"\n[ERROR] {username} - Update failed")

conn.commit()

print("\n" + "=" * 80)
print("VERIFYING PASSWORD RESET")
print("=" * 80)

# Test the password
test_password = "AgentTest!"

for username in accounts:
    cursor.execute("""
        SELECT hashed_password, is_active, locked_until
        FROM users
        WHERE username = ?
    """, (username,))
    
    result = cursor.fetchone()
    
    if result:
        stored_hash = result[0]
        is_active = result[1]
        locked_until = result[2]
        
        # Test password match
        password_match = bcrypt.checkpw(test_password.encode('utf-8'), stored_hash.encode('utf-8'))
        
        print(f"\n{username}:")
        print(f"  Password matches: {password_match}")
        print(f"  Account active: {bool(is_active)}")
        print(f"  Account locked: {locked_until is not None}")
        
        if password_match and is_active and not locked_until:
            print(f"  ✅ Should be able to login")
        else:
            print(f"  ❌ Login will fail - check issues above")

print("\n" + "=" * 80)
print("ALL USERS IN DATABASE")
print("=" * 80)

cursor.execute("SELECT username, email, role FROM users")
all_users = cursor.fetchall()

print(f"\nTotal users in database: {len(all_users)}\n")
for user in all_users:
    print(f"  - {user[0]} ({user[1]}) - {user[2]}")

conn.close()

print("\n" + "=" * 80)
print("DIAGNOSTIC COMPLETE")
print("=" * 80)