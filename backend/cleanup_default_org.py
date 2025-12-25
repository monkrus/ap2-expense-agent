#!/usr/bin/env python3
"""Remove default organization from database"""
import sys
sys.path.insert(0, ".")

from src.database import SessionLocal
from src.models import Organization, OrganizationMember

db = SessionLocal()
try:
    # Find and delete default organization
    default_org = db.query(Organization).filter(
        Organization.slug == "default-org"
    ).first()
    
    if default_org:
        # Delete all memberships first
        memberships = db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == default_org.id
        ).all()
        
        for membership in memberships:
            db.delete(membership)
        
        # Delete the organization
        db.delete(default_org)
        db.commit()
        
        print(f"Deleted default organization: {default_org.name}")
        print(f"Deleted {len(memberships)} organization memberships")
    else:
        print("No default organization found")
finally:
    db.close()
