from src.database import SessionLocal
from src.models import User, Subscription

db = SessionLocal()
users = db.query(User).all()

print(f"\nTotal users in database: {len(users)}\n")
print(f"{'Username':<15} {'Role':<12} {'Email':<25} {'Tier':<12}")
print("-"*70)

for u in users:
    sub = db.query(Subscription).filter(Subscription.user_id == u.id).first()
    tier = sub.tier.value if sub else "NONE"
    print(f"{u.username:<15} {u.role.value:<12} {u.email:<25} {tier:<12}")

db.close()
