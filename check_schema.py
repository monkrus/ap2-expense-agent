import sqlite3

conn = sqlite3.connect('backend/expenses.db')
cursor = conn.cursor()

# Get table schema
cursor.execute("PRAGMA table_info(users)")
columns = cursor.fetchall()

print("Users table schema:")
for col in columns:
    print(f"  {col[1]} ({col[2]})")

# Check admin user
cursor.execute("SELECT * FROM users WHERE username = 'admintest'")
result = cursor.fetchone()

if result:
    print("\nAdmin user found:")
    cursor.execute("PRAGMA table_info(users)")
    columns = cursor.fetchall()
    for i, col in enumerate(columns):
        print(f"  {col[1]}: {result[i]}")
else:
    print("\nAdmin user not found")

conn.close()
