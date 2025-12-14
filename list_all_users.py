"""
List all users in the database
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from src.database import SessionLocal
from src.models import User, Subscription

def list_users():
    db = SessionLocal()

    try:
        users = db.query(User).all()

        print("\n" + "="*80)
        print(f"ALL USERS - Total: {len(users)}")
        print("="*80 + "\n")

        for user in users:
            # Get subscription
            sub = db.query(Subscription).filter(
                Subscription.user_id == user.id,
                Subscription.status.in_(['active', 'trialing'])
            ).first()

            tier = sub.tier.value if sub else 'No subscription'

            print(f"Username:   {user.username}")
            print(f"Email:      {user.email}")
            print(f"Full Name:  {user.full_name or 'N/A'}")
            print(f"Role:       {user.role}")
            print(f"Tier:       {tier}")
            print(f"Active:     {user.is_active}")
            print(f"Created:    {user.created_at}")
            print("-" * 80)

    finally:
        db.close()

if __name__ == "__main__":
    list_users()
