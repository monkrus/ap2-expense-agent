import bcrypt
import sqlite3

conn = sqlite3.connect('expenses.db')
cursor = conn.cursor()

# Get all users
cursor.execute('SELECT id, username FROM users')
users = cursor.fetchall()

# Set password with exclamation mark
password = 'AgentTest!'  # No escaping issues in a Python file!

for user_id, username in users:
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    cursor.execute(
        'UPDATE users SET hashed_password = ?, failed_login_attempts = 0, locked_until = NULL WHERE id = ?',
        (hashed, user_id)
    )
    print(f'Updated {username}')

conn.commit()
print(f'\nAll {len(users)} users now have password: {password}')
conn.close()
