import sqlite3
from datetime import datetime
import sys

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Connect to database
conn = sqlite3.connect('backend/expenses.db')
cursor = conn.cursor()

print("=" * 80)
print("CHECKING USERS: testuser and emptest")
print("=" * 80)

# Check users
cursor.execute("""
    SELECT id, username, email, role, created_at
    FROM users
    WHERE username IN ('testuser', 'emptest')
    ORDER BY username
""")

users = cursor.fetchall()
user_dict = {}

if not users:
    print("\n⚠️  WARNING: No users found with username 'testuser' or 'emptest'")
else:
    print(f"\nFound {len(users)} user(s):\n")
    for user in users:
        user_id, username, email, role, created_at = user
        user_dict[username] = user_id
        print(f"User ID: {user_id}")
        print(f"  Username: {username}")
        print(f"  Email: {email}")
        print(f"  Role: {role}")
        print(f"  Created: {created_at}")
        print()

# Check if they are different users
if len(users) == 2:
    if users[0][0] != users[1][0]:  # Different IDs
        print("✓ CONFIRMED: testuser and emptest are DIFFERENT users")
    else:
        print("✗ ERROR: testuser and emptest have the SAME user ID")
elif len(users) == 1:
    print(f"⚠️  WARNING: Only one user found: {users[0][1]}")
else:
    print("⚠️  WARNING: Expected 2 users, found different number")

print("\n" + "=" * 80)
print("CHECKING EXPENSE SYNC (User Submissions vs Admin View)")
print("=" * 80)

# Get all expenses with user information
cursor.execute("""
    SELECT
        e.id,
        e.user_id,
        u.username,
        e.description,
        e.amount,
        e.status,
        e.created_at,
        e.updated_at
    FROM expenses e
    JOIN users u ON e.user_id = u.id
    WHERE u.username IN ('testuser', 'emptest')
    ORDER BY e.created_at DESC
""")

expenses = cursor.fetchall()

if not expenses:
    print("\n⚠️  No expenses found for testuser or emptest")
else:
    print(f"\nFound {len(expenses)} expense(s):\n")

    pending_count = 0
    approved_count = 0
    rejected_count = 0

    for exp in expenses:
        exp_id, user_id, username, desc, amount, status, created, updated = exp
        print(f"Expense ID: {exp_id}")
        print(f"  User: {username} (ID: {user_id})")
        print(f"  Description: {desc}")
        print(f"  Amount: ${amount:.2f}")
        print(f"  Status: {status}")
        print(f"  Created: {created}")
        print(f"  Updated: {updated}")
        print()

        if status == 'pending':
            pending_count += 1
        elif status == 'approved':
            approved_count += 1
        elif status == 'rejected':
            rejected_count += 1

    print(f"Summary:")
    print(f"  Pending: {pending_count}")
    print(f"  Approved: {approved_count}")
    print(f"  Rejected: {rejected_count}")

print("\n" + "=" * 80)
print("CHECKING HISTORY VISIBILITY")
print("=" * 80)

# For each user, show their expense history
for username, user_id in user_dict.items():
    cursor.execute("""
        SELECT id, description, amount, status, created_at
        FROM expenses
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,))

    user_expenses = cursor.fetchall()
    print(f"\n{username}'s expense history ({len(user_expenses)} total):")

    if not user_expenses:
        print("  (No expenses)")
    else:
        for exp in user_expenses:
            print(f"  - ID {exp[0]}: {exp[1]} (${exp[2]:.2f}) - {exp[3]} - {exp[4]}")

# Check admin view (what admin should see)
print("\n" + "=" * 80)
print("ADMIN VIEW (All expenses from testuser and emptest)")
print("=" * 80)

cursor.execute("""
    SELECT
        e.id,
        u.username,
        e.description,
        e.amount,
        e.status,
        e.created_at
    FROM expenses e
    JOIN users u ON e.user_id = u.id
    WHERE u.username IN ('testuser', 'emptest')
    ORDER BY e.created_at DESC
""")

admin_view = cursor.fetchall()
print(f"\nAdmin should see {len(admin_view)} expense(s):\n")

pending_for_admin = []
for exp in admin_view:
    exp_id, username, desc, amount, status, created = exp
    print(f"  - ID {exp_id}: [{username}] {desc} (${amount:.2f}) - {status} - {created}")
    if status == 'pending':
        pending_for_admin.append((exp_id, username, desc, amount))

print(f"\n" + "=" * 80)
print("PENDING REQUESTS (What Admin Should See to Approve/Reject)")
print("=" * 80)

if pending_for_admin:
    print(f"\nAdmin has {len(pending_for_admin)} pending request(s):\n")
    for exp_id, username, desc, amount in pending_for_admin:
        print(f"  - Request ID {exp_id} from {username}: {desc} (${amount:.2f})")
else:
    print("\nNo pending requests for admin to review")

conn.close()

print("\n" + "=" * 80)
print("CHECK COMPLETE")
print("=" * 80)
