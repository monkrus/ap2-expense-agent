"""Clean up all soft-deleted organizations to allow testing"""
import sys
sys.path.insert(0, 'C:\\Users\\robot\\Desktop\\ap2-expense-agent\\backend')

from src.database import SessionLocal
from src.models import Organization

db = SessionLocal()

# Find all soft-deleted organizations
deleted_orgs = db.query(Organization).filter(Organization.is_active == False).all()

print(f"Found {len(deleted_orgs)} soft-deleted organizations")

for org in deleted_orgs:
    print(f"Permanently deleting: {org.name} (slug: {org.slug}, id: {org.id})")
    db.delete(org)

db.commit()
print("\nAll soft-deleted organizations have been permanently removed")
print("You can now test organization creation without slug conflicts")

db.close()
