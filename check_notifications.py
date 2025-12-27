"""Check notifications in database"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from src.database import SessionLocal
from src.models import Notification, User, OrganizationMember

db = SessionLocal()

print("=" * 70)
print("CHECKING NOTIFICATIONS")
print("=" * 70)

# Check total notifications
notifications = db.query(Notification).all()
print(f"\n[INFO] Total notifications in database: {len(notifications)}")

if len(notifications) > 0:
    print("\nRecent notifications:")
    for n in notifications[-10:]:
        user = db.query(User).filter(User.id == n.user_id).first()
        username = user.username if user else "Unknown"
        print(f"  - {n.notification_type}: {n.title}")
        print(f"    To: {username} (ID: {n.user_id})")
        print(f"    Read: {n.is_read}")
        print(f"    Created: {n.created_at}")
        print()

# Check organization members with admin roles
print("\n" + "=" * 70)
print("ADMIN/MANAGER MEMBERS IN ORGANIZATIONS")
print("=" * 70)

admin_members = db.query(OrganizationMember).filter(
    OrganizationMember.role.in_(["admin", "owner", "manager"]),
    OrganizationMember.is_active == True
).all()

print(f"\n[INFO] Total admin/manager/owner members: {len(admin_members)}")

for member in admin_members:
    user = db.query(User).filter(User.id == member.user_id).first()
    username = user.username if user else "Unknown"
    print(f"  - {username} (Role: {member.role}, Org: {member.organization_id})")

db.close()
