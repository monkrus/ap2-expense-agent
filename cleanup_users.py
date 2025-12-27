"""
Cleanup Script: Delete all users except adminfree and emp1
Then ensure emp1 is in adminfree's organization
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from src.database import SessionLocal
from src.models import (
    User, Organization, OrganizationMember, Expense, Notification,
    IntentMandate, OrganizationInvitation, ExpenseComment, OrganizationRole
)
import uuid

db = SessionLocal()

print("=" * 70)
print("USER CLEANUP - KEEP ONLY adminfree AND emp1")
print("=" * 70)

# Get all users
all_users = db.query(User).all()
print(f"\n[INFO] Found {len(all_users)} total users")

# Find adminfree and emp1
adminfree = db.query(User).filter(User.username == 'adminfree').first()
emp1 = db.query(User).filter(User.username == 'emp1').first()

if not adminfree:
    print("[ERROR] adminfree user not found!")
    db.close()
    sys.exit(1)

if not emp1:
    print("[ERROR] emp1 user not found!")
    db.close()
    sys.exit(1)

print(f"\n[KEEP] adminfree (ID: {adminfree.id})")
print(f"[KEEP] emp1 (ID: {emp1.id})")

# Find users to delete
users_to_delete = [u for u in all_users if u.username not in ['adminfree', 'emp1']]
print(f"\n[DELETE] {len(users_to_delete)} users will be deleted:")
for user in users_to_delete:
    print(f"  - {user.username} (ID: {user.id}, Role: {user.role})")

if len(users_to_delete) == 0:
    print("\n[INFO] No users to delete. Only adminfree and emp1 exist.")
else:
    print(f"\n[WARNING] About to delete {len(users_to_delete)} users and ALL their data!")
    print("Press Enter to continue or Ctrl+C to cancel...")
    # Auto-continue for script execution
    # input()

    # Delete each user with proper cascade
    for user in users_to_delete:
        try:
            user_id = user.id
            username = user.username

            # Delete in correct order (similar to admin delete endpoint)

            # 1. Delete AP2 mandates
            db.query(IntentMandate).filter(IntentMandate.user_id == user_id).delete(synchronize_session=False)

            # 2. Update expenses where user is approver/archiver
            db.query(Expense).filter(Expense.approved_by == user_id).update(
                {"approved_by": None}, synchronize_session=False
            )
            db.query(Expense).filter(Expense.archived_by == user_id).update(
                {"archived_by": None}, synchronize_session=False
            )

            # 3. Delete comments
            db.query(ExpenseComment).filter(ExpenseComment.user_id == user_id).delete(synchronize_session=False)

            # 4. Delete expenses created by user
            db.query(Expense).filter(Expense.user_id == user_id).delete(synchronize_session=False)

            # 5. Delete organization invitations
            db.query(OrganizationInvitation).filter(
                OrganizationInvitation.invited_by == user_id
            ).delete(synchronize_session=False)

            # 6. Delete organization memberships
            db.query(OrganizationMember).filter(
                OrganizationMember.user_id == user_id
            ).delete(synchronize_session=False)

            # 7. Delete notifications
            db.query(Notification).filter(Notification.user_id == user_id).delete(synchronize_session=False)

            # 8. Delete the user
            db.delete(user)
            db.commit()

            print(f"  [OK] Deleted {username}")

        except Exception as e:
            db.rollback()
            print(f"  [FAIL] Error deleting {username}: {str(e)}")

# Now ensure emp1 is in adminfree's organization
print("\n" + "=" * 70)
print("ENSURING emp1 IS IN adminfree'S ORGANIZATION")
print("=" * 70)

# Get adminfree's organization
adminfree_membership = db.query(OrganizationMember).filter(
    OrganizationMember.user_id == adminfree.id,
    OrganizationMember.is_active == True
).first()

if not adminfree_membership:
    print("[ERROR] adminfree has no organization membership!")
    db.close()
    sys.exit(1)

adminfree_org = db.query(Organization).filter(
    Organization.id == adminfree_membership.organization_id
).first()

print(f"\n[INFO] adminfree's organization: {adminfree_org.name} (ID: {adminfree_org.id})")

# Check if emp1 is already in this organization
emp1_membership = db.query(OrganizationMember).filter(
    OrganizationMember.user_id == emp1.id,
    OrganizationMember.organization_id == adminfree_org.id,
    OrganizationMember.is_active == True
).first()

if emp1_membership:
    print(f"[OK] emp1 is already a member of {adminfree_org.name}")
    print(f"     Role: {emp1_membership.role}")
else:
    # Remove emp1 from all other organizations
    db.query(OrganizationMember).filter(
        OrganizationMember.user_id == emp1.id
    ).delete(synchronize_session=False)

    # Add emp1 to adminfree's organization
    new_membership = OrganizationMember(
        id=str(uuid.uuid4()),
        organization_id=adminfree_org.id,
        user_id=emp1.id,
        role=OrganizationRole.MEMBER,
        is_active=True
    )
    db.add(new_membership)
    db.commit()

    print(f"[OK] Added emp1 to {adminfree_org.name} as MEMBER")

# Clean up orphaned organizations (organizations with no members)
print("\n" + "=" * 70)
print("CLEANING UP ORPHANED ORGANIZATIONS")
print("=" * 70)

all_orgs = db.query(Organization).filter(Organization.is_active == True).all()
for org in all_orgs:
    member_count = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org.id,
        OrganizationMember.is_active == True
    ).count()

    if member_count == 0:
        print(f"[DELETE] Orphaned organization: {org.name} (ID: {org.id})")
        org.is_active = False
        db.commit()

print("\n" + "=" * 70)
print("CLEANUP COMPLETE!")
print("=" * 70)

# Final summary
remaining_users = db.query(User).all()
print(f"\nRemaining users: {len(remaining_users)}")
for user in remaining_users:
    print(f"  - {user.username} (Role: {user.role})")
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.is_active == True
    ).first()
    if membership:
        org = db.query(Organization).filter(Organization.id == membership.organization_id).first()
        print(f"    Organization: {org.name} (Org Role: {membership.role})")

print("\n[SUCCESS] Now when emp1 submits expenses, adminfree will receive notifications!")
print("=" * 70)

db.close()
