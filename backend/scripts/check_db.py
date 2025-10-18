import sqlite3

conn = sqlite3.connect('backend/expenses.db')
cursor = conn.cursor()

print("Recent expenses:")
cursor.execute("""
    SELECT id, user_id, vendor, amount, status, created_at
    FROM expenses
    ORDER BY created_at DESC
    LIMIT 5
""")

for row in cursor.fetchall():
    print(f"  ID: {row[0]}")
    print(f"  User: {row[1]}")
    print(f"  Vendor: {row[2]}")
    print(f"  Amount: ${row[3]}")
    print(f"  Status: {row[4]}")
    print(f"  Created: {row[5]}")
    print()

conn.close()
