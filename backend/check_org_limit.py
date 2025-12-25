#!/usr/bin/env python3
"""Check organization limit enforcement"""
import sys
sys.path.insert(0, ".")

from src.database import SessionLocal
from src.models import Organization, OrganizationMember, User
from src.billing.limit_enforcer import LimitEnforcer

db = SessionLocal()
try:
    # Find adminfree user
    user = db.query(User).filter(User.username == "adminfree").first()
    
    if not user:
        print("User 'adminfree' not found")
        sys.exit(1)
    
    # Count active organizations user is a member of
    active_orgs = (
        db.query(Organization)
        .join(OrganizationMember, Organization.id == OrganizationMember.organization_id)
        .filter(OrganizationMember.user_id == user.id)
        .filter(OrganizationMember.is_active == True)
        .filter(Organization.is_active == True)
        .all()
    )
    
    print(f"User: {user.username}")
    print(f"Active organizations: {len(active_orgs)}")
    for org in active_orgs:
        print(f"  - {org.name} ({org.slug})")
    
    # Check limit enforcer
    limit_enforcer = LimitEnforcer(db)
    limits = limit_enforcer.get_organization_limits(user.id)
    
    print(f"\nTier limits:")
    print(f"  Tier: {limits.tier_name}")
    print(f"  Max organizations: {limits.max_organizations}")
    print(f"  Current count: {len(active_orgs)}")
    print(f"  Can create more: {len(active_orgs) < limits.max_organizations if limits.max_organizations > 0 else True}")
    
    # Test limit check
    can_create = limit_enforcer.check_organization_limit(user.id, raise_error=False)
    print(f"\nLimit check result: {'✓ Can create' if can_create else '✗ Limit reached'}")
    
finally:
    db.close()
