"""Clean up soft-deleted organizations to free up slugs"""
import sys
sys.path.insert(0, 'C:/Users/robot/Desktop/ap2-expense-agent/backend')

from src.database import SessionLocal
from src.models import Organization

def cleanup_soft_deleted():
    db = SessionLocal()
    try:
        # Find all soft-deleted organizations
        deleted_orgs = db.query(Organization).filter(Organization.is_active == False).all()

        print(f"Found {len(deleted_orgs)} soft-deleted organizations")

        for org in deleted_orgs:
            print(f"  - Deleting: {org.name} (slug: {org.slug})")
            db.delete(org)

        db.commit()
        print(f"\n✅ Successfully deleted {len(deleted_orgs)} soft-deleted organizations")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_soft_deleted()
