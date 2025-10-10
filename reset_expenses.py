import sqlite3
import sys

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Connect to database
conn = sqlite3.connect('backend/expenses.db')
cursor = conn.cursor()

print("=" * 80)
print("RESETTING ALL EXPENSES")
print("=" * 80)

# Count current expenses
cursor.execute("SELECT COUNT(*) FROM expenses")
before_count = cursor.fetchone()[0]
print(f"\nExpenses before deletion: {before_count}")

# Get breakdown by user
cursor.execute("""
    SELECT u.username, COUNT(e.id) as count
    FROM expenses e
    JOIN users u ON e.user_id = u.id
    GROUP BY u.username
""")

user_breakdown = cursor.fetchall()
if user_breakdown:
    print("\nBreakdown by user:")
    for username, count in user_breakdown:
        print(f"  {username}: {count} expenses")

# Delete all expenses
cursor.execute("DELETE FROM expenses")
conn.commit()

# Verify deletion
cursor.execute("SELECT COUNT(*) FROM expenses")
after_count = cursor.fetchone()[0]

print(f"\n✓ Deleted {before_count} expenses")
print(f"✓ Expenses after deletion: {after_count}")

# Also clean up related AP2 mandate tables if they exist
print("\nCleaning up related AP2 mandate records...")

try:
    cursor.execute("DELETE FROM payment_mandates")
    payment_count = cursor.rowcount
    print(f"  ✓ Deleted {payment_count} payment mandates")
except Exception as e:
    print(f"  • Payment mandates: {e}")

try:
    cursor.execute("DELETE FROM cart_mandates")
    cart_count = cursor.rowcount
    print(f"  ✓ Deleted {cart_count} cart mandates")
except Exception as e:
    print(f"  • Cart mandates: {e}")

try:
    cursor.execute("DELETE FROM intent_mandates")
    intent_count = cursor.rowcount
    print(f"  ✓ Deleted {intent_count} intent mandates")
except Exception as e:
    print(f"  • Intent mandates: {e}")

conn.commit()

print("\n" + "=" * 80)
print("CURRENT USER STATE")
print("=" * 80)

cursor.execute("""
    SELECT username, email, role
    FROM users
    ORDER BY role DESC, username
""")

users = cursor.fetchall()
print(f"\nUsers still in system: {len(users)}\n")
for username, email, role in users:
    print(f"  {username:15} {email:30} [{role}]")

print("\n" + "=" * 80)
print("RESET COMPLETE - All expenses deleted, users preserved")
print("=" * 80)
print("\nYou can now start fresh testing!")
print("• testuser: 0 expenses")
print("• emptest: 0 expenses")
print("• admintest: can see 0 total expenses")

conn.close()
