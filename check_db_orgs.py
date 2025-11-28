"""Check what's in the database"""
import sys
sys.path.insert(0, 'C:\\Users\\robot\\Desktop\\ap2-expense-agent\\backend')

from src.database import SessionLocal
from src.models import Organization

db = SessionLocal()

print("All organizations in database:")
print("="*80)

all_orgs = db.query(Organization).filter(Organization.slug == "debug-test").all()
for org in all_orgs:
    print(f"ID: {org.id}")
    print(f"  Name: {org.name}")
    print(f"  Slug: {org.slug}")
    print(f"  Active: {org.is_active}")
    print()

db.close()
