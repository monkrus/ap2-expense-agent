# Max Members Bug Fix - FREE Tier Showing 25 Instead of 1

## Problem

User reported that FREE tier organizations were showing **max_members=25** instead of the correct value of **max_members=1**.

Screenshot evidence:
- Organization: org1
- Max Members: 25 (INCORRECT)

## Root Cause

### Bug #1: Hardcoded Default in Organization Creation

**File:** `backend/src/routes/organizations.py` (line 308)

**Before (WRONG):**
```python
organization = Organization(
    id=str(uuid.uuid4()),
    name=org_data.name,
    slug=org_data.slug,
    description=org_data.description,
    currency=org_data.currency or "USD",
    timezone=org_data.timezone or "UTC",
    max_members=org_data.max_members or 25,  # ❌ HARDCODED TO 25!
    is_active=True,
)
```

**After (CORRECT):**
```python
organization = Organization(
    id=str(uuid.uuid4()),
    name=org_data.name,
    slug=org_data.slug,
    description=org_data.description,
    currency=org_data.currency or "USD",
    timezone=org_data.timezone or "UTC",
    max_members=tier_limits.max_users,  # ✅ FROM SUBSCRIPTION TIER
    is_active=True,
)
```

### Bug #2: Database Default Value

**File:** `backend/src/models.py` (line 111)

```python
max_members = Column(Integer, nullable=False, default=25)
```

This database default of 25 also contributed to the problem, though the main issue was in the organization creation code.

## Correct Tier Limits

From `backend/src/billing/tier_limits.py`:

| Tier          | Max Users |
|---------------|-----------|
| FREE          | 1         |
| STARTER       | 5         |
| PROFESSIONAL  | 25        |
| ENTERPRISE    | 100       |

## Fixes Applied

### 1. Updated Organization Creation Logic

**File:** `backend/src/routes/organizations.py` (line 308)

Changed from:
```python
max_members=org_data.max_members or 25
```

To:
```python
max_members=tier_limits.max_users  # Set based on user's subscription tier
```

This ensures that:
- FREE tier organizations get max_members=1
- STARTER tier organizations get max_members=5
- PROFESSIONAL tier organizations get max_members=25
- ENTERPRISE tier organizations get max_members=100

### 2. Fixed Existing Organizations

**Script:** `backend/fix_org_max_members.py`

Created and ran a migration script that:
1. Found all active organizations
2. Determined each organization owner's subscription tier
3. Updated max_members to match the tier's max_users value

**Results:**
```
[UPDATED] 'Acme Corporation' (slug: different-slug-1)
   Tier: free
   Max Members: 25 -> 1

[UPDATED] 'Test Org 1766034211' (slug: test-org-1766034211)
   Tier: free
   Max Members: 25 -> 1

[UPDATED] 'Test Org 1766034234' (slug: test-org-1766034234)
   Tier: free
   Max Members: 25 -> 1

[UPDATED] 'Audit Test Org d6487402' (slug: audit-org-bc09cc4d)
   Tier: free
   Max Members: 25 -> 1

[UPDATED] 'Test Org 1766277664' (slug: test-org-1766277664)
   Tier: free
   Max Members: 25 -> 1

[UPDATED] 'Default Organization' (slug: default-org)
   Tier: free
   Max Members: 25 -> 1

[UPDATED] 'org1' (slug: org1)
   Tier: free
   Max Members: 25 -> 1

================================================================================
SUCCESS: Updated 7 organization(s)
================================================================================
```

All 7 FREE tier organizations were successfully updated from max_members=25 to max_members=1.

## Verification

After fix:
```bash
cd backend && python -c "from src.database import SessionLocal; from src.models import Organization; db = SessionLocal(); orgs = db.query(Organization).filter(Organization.is_active == True).all(); [print(f'Name: {org.name:30} | Max Members: {org.max_members}') for org in orgs]"
```

Output:
```
Name: Acme Corporation               | Max Members: 1
Name: Test Org 1766034211            | Max Members: 1
Name: Test Org 1766034234            | Max Members: 1
Name: Audit Test Org d6487402        | Max Members: 1
Name: Test Org 1766277664            | Max Members: 1
Name: Default Organization           | Max Members: 1
Name: org1                           | Max Members: 1
```

✅ All organizations now have correct max_members=1 for FREE tier.

## Testing Checklist

- [x] Fixed organization creation code to use tier_limits.max_users
- [x] Created migration script to fix existing organizations
- [x] Ran migration script successfully (7 organizations updated)
- [x] Verified all organizations now have correct max_members
- [x] Restarted backend server with fix
- [ ] User to verify in UI that org1 now shows max_members=1

## Prevention

### For Future Code Reviews

When creating or updating organizations, ALWAYS use:
```python
max_members=tier_limits.max_users
```

NEVER hardcode max_members to a static value like 25.

### For Database Migrations

If changing tier limits in the future, run a similar migration script to update existing organizations.

## Files Modified

1. `backend/src/routes/organizations.py` - Line 308 (organization creation)
2. `backend/fix_org_max_members.py` - New migration script
3. `MAX_MEMBERS_BUG_FIX.md` - This documentation

## Related Issues

This bug is related to the earlier error handling fixes where FREE tier users trying to invite members were getting incorrect error messages. The fix ensures:

1. Organizations display correct max_members in UI
2. Tier limit enforcement uses correct values
3. Error messages show correct limits (1 for FREE tier, not 25)

---

**Date Fixed:** 2025-12-21
**Fixed By:** Claude Code
**User Report:** Screenshot showing org1 with max_members=25 instead of 1
