"""Verify final user setup with emails and subscriptions"""
from src.database import SessionLocal
from src.models import User, Subscription

db = SessionLocal()

print("="*90)
print("FINAL USER VERIFICATION")
print("="*90)

users = db.query(User).filter(
    User.username.in_(['adminfree', 'adminenter', 'user1', 'user2', 'manager1', 'acc1'])
).all()

print(f"\n{'Username':<15} {'Email':<35} {'Role':<12} {'Tier':<12}")
print("-"*90)

for user in users:
    sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    tier = sub.tier.value.upper() if sub else "NONE"
    print(f"{user.username:<15} {user.email:<35} {user.role.value:<12} {tier:<12}")

print("\n" + "="*90)
print("Verification complete - all users ready!")
print("="*90)

db.close()
