"""Update email addresses for test users"""
from src.database import SessionLocal
from src.models import User

db = SessionLocal()

# Email assignments
email_updates = {
    "adminfree": "mutabortrim@gmail.com",
    "adminenter": "sergeisqa@gmail.com",
    "user1": "naftalinka21@gmail.com",
    "user2": "telegramtok@gmail.com",
    "manager1": "sergeigodev@gmail.com",
    "acc1": "churchofsearchmeme@gmail.com",
}

print("="*80)
print("Updating User Email Addresses")
print("="*80)

updated_count = 0

for username, new_email in email_updates.items():
    user = db.query(User).filter(User.username == username).first()

    if not user:
        print(f"\nWARNING: User '{username}' not found - skipping")
        continue

    old_email = user.email
    user.email = new_email
    updated_count += 1

    print(f"\nUpdated: {username}")
    print(f"  Old email: {old_email}")
    print(f"  New email: {new_email}")

db.commit()

print("\n" + "="*80)
print(f"SUCCESS: {updated_count} email addresses updated!")
print("="*80)

# Print final summary
print("\nFINAL USER LIST:")
print("="*80)
print(f"{'Username':<15} {'Email':<35} {'Role':<12}")
print("-"*80)

for username in email_updates.keys():
    user = db.query(User).filter(User.username == username).first()
    if user:
        print(f"{user.username:<15} {user.email:<35} {user.role.value:<12}")

db.close()

print("\n" + "="*80)
print("All users ready with updated emails!")
print("Password for all users: Testme!")
print("="*80)
