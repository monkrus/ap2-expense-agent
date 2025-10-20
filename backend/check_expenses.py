import sqlite3

conn = sqlite3.connect('expenses.db')
cursor = conn.cursor()

# Get all expenses
cursor.execute('SELECT id, user_id, amount, vendor, status, date FROM expenses ORDER BY created_at DESC')
expenses = cursor.fetchall()

print('All expenses in database:')
print('-' * 80)
for i, row in enumerate(expenses, 1):
    exp_id, user_id, amount, vendor, status, date = row
    print(f'{i}. Vendor: {vendor:<20} Amount: ${amount if amount else "NULL":<10} Status: {status:<10} Date: {date}')

print(f'\nTotal: {len(expenses)} expenses')

# Get user info
cursor.execute('SELECT id, username FROM users')
users = {row[0]: row[1] for row in cursor.fetchall()}

print('\n\nExpenses by user:')
print('-' * 80)
cursor.execute('SELECT user_id, COUNT(*) FROM expenses GROUP BY user_id')
for row in cursor.fetchall():
    user_id, count = row
    username = users.get(user_id, 'Unknown')
    print(f'{username}: {count} expenses')

conn.close()
