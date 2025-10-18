"""
Test API endpoints to verify pending expense visibility
"""
import sqlite3

conn = sqlite3.connect('backend/expenses.db')
cursor = conn.cursor()

print("=" * 80)
print("SIMULATING ADMIN API CALLS")
print("=" * 80)

# Simulate /api/v1/expenses/all-pending endpoint
print("\n1. GET /api/v1/expenses/all-pending")
print("-" * 80)

cursor.execute("""
    SELECT
        e.id,
        e.user_id,
        u.username,
        u.email as user_email,
        u.full_name as user_name,
        e.amount,
        e.vendor,
        e.category,
        e.description,
        e.status,
        e.date,
        e.created_at
    FROM expenses e
    JOIN users u ON e.user_id = u.id
    WHERE e.status = 'PENDING'
    ORDER BY e.created_at DESC
""")

pending_expenses = cursor.fetchall()

if pending_expenses:
    print(f"Found {len(pending_expenses)} pending expense(s):\n")
    for exp in pending_expenses:
        exp_id, user_id, username, user_email, user_name, amount, vendor, category, desc, status, date, created = exp
        print(f"  ID: {exp_id}")
        print(f"  User: {username} ({user_email})")
        print(f"  Amount: ${amount}")
        print(f"  Description: {desc}")
        print(f"  Status: {status}")
        print(f"  Created: {created}")
        print()
else:
    print("No pending expenses found")

# Simulate /api/v1/expenses/all?status=pending endpoint
print("\n2. GET /api/v1/expenses/all?status=pending")
print("-" * 80)

cursor.execute("""
    SELECT
        e.id,
        e.user_id,
        u.username,
        u.email as user_email,
        u.full_name as user_name,
        e.amount,
        e.vendor,
        e.category,
        e.description,
        e.status,
        e.date,
        e.created_at,
        e.approved_at,
        e.approved_by,
        e.transaction_id,
        e.rejection_reason
    FROM expenses e
    JOIN users u ON e.user_id = u.id
    WHERE e.status = 'PENDING'
      AND e.status != 'WITHDRAWN'
    ORDER BY e.created_at DESC
""")

all_pending = cursor.fetchall()

if all_pending:
    print(f"Found {len(all_pending)} expense(s) with status=pending:\n")
    for exp in all_pending:
        exp_id = exp[0]
        username = exp[2]
        user_email = exp[3]
        amount = exp[5]
        desc = exp[8]
        status = exp[9]
        created = exp[11]
        print(f"  ID: {exp_id}")
        print(f"  User: {username} ({user_email})")
        print(f"  Amount: ${amount}")
        print(f"  Description: {desc}")
        print(f"  Status: {status}")
        print(f"  Created: {created}")
        print()
else:
    print("No expenses found with pending status")

# Check for case sensitivity issues
print("\n3. CHECKING FOR CASE SENSITIVITY ISSUES")
print("-" * 80)

cursor.execute("SELECT DISTINCT status FROM expenses")
statuses = cursor.fetchall()

print(f"Unique statuses in database:")
for (status,) in statuses:
    print(f"  - '{status}' (type: {type(status).__name__})")

print("\n" + "=" * 80)
print("DIAGNOSIS")
print("=" * 80)

if len(pending_expenses) > 0 and len(all_pending) > 0:
    if len(pending_expenses) == len(all_pending):
        print("\n✓ BOTH endpoints should return the SAME data")
        print(f"  - /all-pending: {len(pending_expenses)} expenses")
        print(f"  - /all?status=pending: {len(all_pending)} expenses")
        print("\nIf you're seeing different results in the UI:")
        print("  1. Check browser console for errors")
        print("  2. Check network tab to see actual API responses")
        print("  3. Hard refresh the page (Ctrl+Shift+R)")
    else:
        print(f"\n⚠️  MISMATCH DETECTED:")
        print(f"  - /all-pending: {len(pending_expenses)} expenses")
        print(f"  - /all?status=pending: {len(all_pending)} expenses")
elif len(pending_expenses) == 0 and len(all_pending) == 0:
    print("\n✓ No pending expenses in database - both endpoints should show empty")
else:
    print(f"\n⚠️  UNEXPECTED STATE:")
    print(f"  - /all-pending: {len(pending_expenses)} expenses")
    print(f"  - /all?status=pending: {len(all_pending)} expenses")

conn.close()
