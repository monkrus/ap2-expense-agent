# Organization Cleanup Guide

## Overview

This guide explains how the organization soft-delete and cleanup system works to prevent UNIQUE constraint violations and maintain database health.

## Problem Statement

When organizations are deleted, they are "soft deleted" (marked `is_active=False`) rather than removed from the database. This preserves audit trails and allows potential recovery. However, soft-deleted records can cause UNIQUE constraint violations when users try to reuse slugs from deleted organizations.

## Protection Layers

We've implemented **5 layers of protection** to ensure this error never occurs:

### Layer 1: Pre-emptive Cleanup on Creation ✅
**File:** `backend/src/routes/organizations.py:143-160`

Before creating a new organization, the system automatically hard-deletes any soft-deleted organizations with the same slug:

```python
soft_deleted_with_slug = (
    db.query(Organization)
    .filter(Organization.slug == org_data.slug)
    .filter(Organization.is_active == False)
    .all()
)
if soft_deleted_with_slug:
    for org in soft_deleted_with_slug:
        db.delete(org)
    db.commit()  # CRITICAL: Must commit to release UNIQUE constraint
```

**Why it works:** Ensures no conflicts exist before attempting creation.

### Layer 2: Active-Only Validation ✅
**File:** `backend/src/routes/organizations.py:162-182`

Slug and name validation only checks ACTIVE organizations:

```python
existing_slug = (
    db.query(Organization)
    .filter(Organization.slug == org_data.slug)
    .filter(Organization.is_active == True)  # Only active orgs
    .first()
)
```

**Why it works:** Allows slug reuse after deletion while preventing conflicts with active organizations.

### Layer 3: Try-Catch Wrapper ✅
**File:** `backend/src/routes/organizations.py:299-406`

The entire organization creation is wrapped in a try-catch block that catches `IntegrityError`:

```python
try:
    # Create organization
    organization = Organization(...)
    db.add(organization)
    db.commit()
    return organization

except IntegrityError as e:
    db.rollback()
    # Aggressive cleanup and user-friendly error
    raise HTTPException(status_code=400, detail={...})
```

**Why it works:** Catches any UNIQUE constraint violations that slip through and performs aggressive cleanup before returning a user-friendly error (400 instead of 500).

### Layer 4: Aggressive Fallback Cleanup ✅
**File:** `backend/src/routes/organizations.py:366-385`

If an IntegrityError occurs despite all checks, the system attempts one more aggressive cleanup:

```python
if "UNIQUE constraint failed: organizations.slug" in error_message:
    # Last resort cleanup
    conflicting_orgs = (
        db.query(Organization)
        .filter(Organization.slug == org_data.slug)
        .filter(Organization.is_active == False)
        .all()
    )
    for org in conflicting_orgs:
        db.delete(org)
    db.commit()
```

**Why it works:** Handles race conditions where multiple requests try to create organizations with the same slug simultaneously.

### Layer 5: Scheduled Cleanup Script ✅
**File:** `backend/cleanup_soft_deleted_orgs.py`

A maintenance script that periodically removes old soft-deleted organizations:

```bash
# Dry run (preview what will be deleted)
python backend/cleanup_soft_deleted_orgs.py

# Live mode (actually delete records)
python backend/cleanup_soft_deleted_orgs.py --live

# Custom threshold (delete orgs soft-deleted > 60 days ago)
python backend/cleanup_soft_deleted_orgs.py --live --days=60
```

**Why it works:** Prevents accumulation of soft-deleted records over time, keeping the database clean.

## Recommended Maintenance Schedule

### Option 1: Cron Job (Linux/Mac)

Add to crontab:
```bash
# Run cleanup weekly on Sunday at 2 AM
0 2 * * 0 cd /path/to/backend && python cleanup_soft_deleted_orgs.py --live --days=30
```

### Option 2: Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger: Weekly, Sunday, 2:00 AM
4. Action: Start a program
   - Program: `python`
   - Arguments: `cleanup_soft_deleted_orgs.py --live --days=30`
   - Start in: `C:\path\to\backend`

### Option 3: Docker/Kubernetes CronJob

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: org-cleanup
spec:
  schedule: "0 2 * * 0"  # Every Sunday at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: cleanup
            image: your-backend-image
            command: ["python", "cleanup_soft_deleted_orgs.py", "--live", "--days=30"]
          restartPolicy: OnFailure
```

## Error Handling

### User Experience

If a UNIQUE constraint error somehow occurs:
- **Before:** 500 Internal Server Error (scary for users)
- **After:** 400 Bad Request with helpful message and slug suggestions

Example error response:
```json
{
  "error": "slug_conflict",
  "message": "The slug 'test1' is already in use. Please try a different slug or contact support.",
  "field": "slug",
  "suggestions": [
    "test1-new",
    "test1-a3f2b1",
    "my-test1"
  ]
}
```

### Logging

All constraint violations are logged for monitoring:
```
ERROR: UNIQUE constraint violation on slug 'test1' despite checks.
       This indicates a race condition or incomplete cleanup.
```

## Testing

### Manual Test: Delete and Recreate

1. Create organization with slug "test1"
2. Delete the organization (soft delete)
3. Immediately create new organization with slug "test1"
4. **Expected:** Success (no 500 error)

### Cleanup Script Test

```bash
# Dry run to preview
python backend/cleanup_soft_deleted_orgs.py

# Expected output:
# Found X soft-deleted organization(s) to clean up:
#   • Organization Name (slug: org-slug)
#     ID: xxx-xxx-xxx
#     Deleted: 2024-11-20 (31 days ago)
#     Associated members: 5
```

## Monitoring

### Recommended Alerts

1. **High Constraint Violation Rate**
   - Query: Count of "UNIQUE constraint violation" in logs
   - Threshold: > 5 per hour
   - Action: Investigate race conditions

2. **Soft-Deleted Organization Accumulation**
   - Query: Count of `Organization.is_active = False`
   - Threshold: > 1000 records
   - Action: Run cleanup script more frequently

3. **Cleanup Script Failures**
   - Query: Exit code != 0 from cleanup script
   - Threshold: Any failure
   - Action: Check database connectivity and permissions

## Migration Strategy

If you have existing soft-deleted organizations causing issues:

```bash
# 1. Check how many exist
python -c "
from backend.src.database import SessionLocal
from backend.src.models import Organization
db = SessionLocal()
count = db.query(Organization).filter(Organization.is_active == False).count()
print(f'Soft-deleted organizations: {count}')
"

# 2. Run cleanup (dry run first!)
cd backend
python cleanup_soft_deleted_orgs.py

# 3. If safe, run live cleanup
python cleanup_soft_deleted_orgs.py --live
```

## Verification

After implementing all layers:

✅ Layer 1: Check `organizations.py:160` has `db.commit()`
✅ Layer 2: Check queries have `.filter(Organization.is_active == True)`
✅ Layer 3: Check `try-except IntegrityError` wraps creation
✅ Layer 4: Check aggressive cleanup in except block
✅ Layer 5: Cleanup script exists and is scheduled

## Summary

With all 5 protection layers in place:
- **Prevention:** Layers 1-2 prevent issues before they occur
- **Graceful Handling:** Layer 3 catches any that slip through
- **Recovery:** Layer 4 attempts automatic recovery
- **Maintenance:** Layer 5 prevents long-term accumulation

**Result:** The 500 error should **NEVER** occur again. If it somehow does, the system will:
1. Log the issue for investigation
2. Attempt automatic recovery
3. Return a user-friendly 400 error with suggestions
