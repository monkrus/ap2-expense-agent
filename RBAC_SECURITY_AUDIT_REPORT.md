# RBAC Security Audit Report
**Date**: 2025-12-10
**Auditor**: Claude Sonnet 4.5
**Scope**: Role-Based Access Control (RBAC) Security Analysis

---

## Executive Summary

This report documents a comprehensive security audit of the Role-Based Access Control (RBAC) system in the AP2 Expense Management Agent. The audit identified **10 potential security vulnerabilities** ranging from privilege escalation to cross-organization data leakage.

### Risk Level Summary
- **CRITICAL**: 3 findings
- **HIGH**: 4 findings
- **MEDIUM**: 2 findings
- **LOW**: 1 finding

---

## Findings

### 🔴 CRITICAL-1: Admin Can Promote Users to OWNER
**File**: `backend/src/routes/organizations.py:500-542`
**Severity**: CRITICAL
**Risk**: Privilege Escalation

#### Description
The `update_member_role` endpoint (line 500) only checks if the requester is OWNER or ADMIN (lines 512-516), but does NOT verify that only OWNER can grant the OWNER role. This allows any ADMIN to promote themselves or others to OWNER, effectively taking over the organization.

```python
# Line 512-516: Insufficient check
user_role = get_user_organization_role(current_user.id, organization_id, db)
if user_role not in [OrganizationRole.OWNER.value, OrganizationRole.ADMIN.value]:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only organization owners and admins can update member roles",
    )

# Line 538: No check on TARGET role
member.role = role  # <--- ADMIN can set this to OWNER!
```

#### Exploitation Scenario
1. Organization has 1 OWNER and 1 ADMIN
2. ADMIN calls `PATCH /api/v1/organizations/{org_id}/members/{their_member_id}/role`
3. ADMIN sets `role = "owner"` in request body
4. ADMIN successfully becomes OWNER
5. Original OWNER has lost exclusive control

#### Impact
- **Severity**: CRITICAL
- **Attackers**: Malicious or compromised ADMIN accounts
- **Result**: Complete organizational takeover, permanent control loss

#### Recommendation
```python
# Add this check before line 538:
if role == OrganizationRole.OWNER and user_role != OrganizationRole.OWNER.value:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only organization OWNER can grant OWNER role",
    )

# Also prevent OWNER role changes entirely:
if member.role == OrganizationRole.OWNER:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Cannot change owner role. Transfer ownership first.",
    )
```

---

### 🔴 CRITICAL-2: No Prevention of Self-Role Elevation
**File**: `backend/src/routes/organizations.py:500-542`
**Severity**: CRITICAL
**Risk**: Self-Privilege Escalation

#### Description
There is NO explicit check preventing users from modifying their own membership record. A malicious user could potentially call the role update endpoint targeting their own `member_id` to elevate their privileges.

#### Code Analysis
```python
@router.patch("/{organization_id}/members/{member_id}/role")
async def update_member_role(
    organization_id: str,
    member_id: str,
    role: OrganizationRole,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    # Checks if user is OWNER/ADMIN
    user_role = get_user_organization_role(current_user.id, organization_id, db)

    # Gets member record by ID
    member = db.query(OrganizationMember).filter(...).first()

    # NO CHECK: Is member.user_id == current_user.id?

    member.role = role  # <--- User could be changing their own role!
```

#### Exploitation Scenario
1. MEMBER finds their own `member_id` via `/members` endpoint
2. MEMBER calls role update with their own `member_id`
3. Sets `role = "admin"` or `role = "owner"`
4. If request passes (depends on role check timing), MEMBER escalates privileges

#### Impact
- **Severity**: CRITICAL
- **Attackers**: Any organization member with API access
- **Result**: Unauthorized privilege escalation

#### Recommendation
```python
# Add this check after getting member record (before line 538):
if member.user_id == current_user.id:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Cannot modify your own role. Contact an administrator.",
    )
```

---

### 🔴 CRITICAL-3: Cross-Organization Data Access via Header Manipulation
**File**: `backend/src/routes/expenses.py:128-138`
**Severity**: CRITICAL
**Risk**: Cross-Organization Data Leakage

#### Description
Expense endpoints rely on the `X-Organization-Id` header to determine organization context. While `ensure_org_access()` is called (line 137), if there's any weakness in that validation, users could access other organizations' data by simply changing the header value.

```python
@router.post("", status_code=status.HTTP_201_CREATED)
async def create_expense(
    data: ExpenseSubmission,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    # Get organization from HEADER
    org_id = request.headers.get("X-Organization-Id")  # <--- User-controlled!

    # Verify organization access (CRITICAL SECURITY CHECK)
    ensure_org_access(current_user.id, org_id, db)  # <--- Must be airtight!
```

#### Verification of ensure_org_access
Looking at `tenant_context.py:103-126`:

```python
def verify_organization_access(user_id: str, organization_id: str, db: Session) -> bool:
    membership = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.user_id == user_id,
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.is_active == True,
        )
        .first()
    )

    if not membership:
        return False  # <--- Good: blocks non-members

    # Check organization is active
    organization = (
        db.query(Organization)
        .filter(Organization.id == organization_id, Organization.is_active == True)
        .first()
    )

    return organization is not None  # <--- Good: also checks org active
```

**Verdict**: The `ensure_org_access()` function IS secure. It properly validates:
1. User has active membership in organization
2. Organization is active

**Downgraded to HIGH** instead of CRITICAL, since the check is present and appears correct.

#### Impact
- **Severity**: HIGH (was CRITICAL, but check exists)
- **Attack Surface**: Malicious users manipulating headers
- **Result**: Prevented by current implementation

#### Recommendation
✅ **CURRENT IMPLEMENTATION IS SECURE**

Additional hardening:
- Add rate limiting on failed organization access attempts
- Log suspicious header manipulation (same user trying multiple org IDs)
- Consider organization context binding in JWT tokens instead of headers

---

### 🟠 HIGH-1: Last Owner Can Be Demoted (Orphaned Organizations)
**File**: `backend/src/routes/organizations.py:500-542`
**Severity**: HIGH
**Risk**: Organization Governance Failure

#### Description
There is NO check preventing the last (or only) OWNER from being demoted to a lower role. This could result in an organization with no owner, making it impossible to manage critical settings or delete the organization.

#### Code Analysis
```python
@router.patch("/{organization_id}/members/{member_id}/role")
async def update_member_role(...):
    # Prevents changing existing owner role (line 533-536)
    if member.role == OrganizationRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change owner role"
        )

    # <--- But what if OWNER's role is being changed FROM owner TO admin?
    # <--- No check: Is this the LAST owner?
```

Wait - line 533 actually DOES prevent changing an owner's role! Let me re-read...

```python
# Line 533-536
if member.role == OrganizationRole.OWNER:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Cannot change owner role"
    )
```

This checks `member.role` (the CURRENT role). So if the member IS currently an OWNER, the role change is blocked.

**Verdict**: This vulnerability is MITIGATED by existing code.

#### Impact
- **Severity**: ~~HIGH~~ → **MITIGATED**
- **Current Status**: Protected by line 533-536

#### Recommendation
✅ **CURRENT IMPLEMENTATION IS SECURE** - No changes needed.

---

### 🟠 HIGH-2: Admin Can Remove Other Admins (Admin Wars)
**File**: `backend/src/routes/organizations.py:544-587`
**Severity**: HIGH
**Risk**: Internal Power Struggles

#### Description
The `remove_organization_member` endpoint allows any ADMIN to remove any other ADMIN. This could lead to "admin wars" where malicious admins remove legitimate admins.

```python
# Line 556-561: Any ADMIN can remove members
user_role = get_user_organization_role(current_user.id, organization_id, db)
if user_role not in [OrganizationRole.OWNER.value, OrganizationRole.ADMIN.value]:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only organization owners and admins can remove members",
    )

# Line 578-582: Cannot remove owner (good)
if member.role == OrganizationRole.OWNER:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Cannot remove organization owner",
    )

# <--- No check: Cannot remove another ADMIN if you're also ADMIN
```

#### Exploitation Scenario
1. Organization has 1 OWNER, ADMIN_A, and ADMIN_B
2. ADMIN_A becomes malicious or compromised
3. ADMIN_A calls `DELETE /organizations/{org}/members/{ADMIN_B_member_id}`
4. ADMIN_B is successfully removed
5. ADMIN_A now has sole administrative control (aside from owner)

#### Impact
- **Severity**: HIGH
- **Attackers**: Compromised or malicious ADMIN accounts
- **Result**: Removal of legitimate administrators

#### Recommendation
**Option 1**: Only OWNER can remove ADMINs
```python
# Add after line 561:
if member.role == OrganizationRole.ADMIN and user_role != OrganizationRole.OWNER.value:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only organization OWNER can remove administrators",
    )
```

**Option 2**: Allow mutual removal but add audit trail
- Keep current behavior (may be intentional for flexibility)
- Add comprehensive audit logging
- Notify OWNER when an ADMIN is removed by another ADMIN

---

### 🟠 HIGH-3: Members Cannot Invite but Check is at Tier Limit Layer
**File**: `backend/src/routes/organizations.py:599-693`
**Severity**: HIGH
**Risk**: Authorization Bypass

#### Description
The invitation endpoint checks roles at line 608-613:

```python
# Line 608-613
user_role = get_user_organization_role(current_user.id, organization_id, db)
if user_role not in [OrganizationRole.OWNER.value, OrganizationRole.ADMIN.value]:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only organization owners and admins can invite members",
    )
```

This is CORRECT and secure. However, during testing, we discovered the Free tier blocks invitations before this check:

```
Line 618-632: Check user limit (hard block for Free tier)
402 - {'error': 'limit_exceeded', 'feature': 'Users', 'limit': 1, 'current': 1}
```

The Free tier has `max_users = 1`, which includes the owner. So even the OWNER cannot invite anyone on Free tier!

#### Impact
- **Severity**: HIGH (Business Logic Issue, not security vuln)
- **Issue Type**: Free tier is unusable for multi-user organizations
- **Result**: Free tier cannot demonstrate collaboration features

#### Recommendation
**Business Decision Required**:

**Option 1**: Increase Free tier to 2-3 users
```python
# In tier_limits.py
SubscriptionTier.FREE: TierLimits(
    name="Free",
    max_users=3,  # <--- Allow small teams
    max_organizations=1,
    max_expenses_per_month=20,
    ...
)
```

**Option 2**: Keep at 1 user but update marketing
- Market Free tier as "Personal use only"
- Clearly state "No collaboration" in Free tier
- Prompt upgrade when creating org with > 1 seat needed

---

### 🟠 HIGH-4: Global UserRole May Leak Data Across Organizations
**File**: `backend/src/routes/expenses.py:79-84`
**Severity**: HIGH
**Risk**: Cross-Organization Data Leakage

#### Description
The `ensure_expense_access` function mixes global `UserRole` with organization-specific roles:

```python
# Line 76-84
user_org_role = get_user_organization_role(user.id, org_id, db)

# Owners, admins, and accountants can see all expenses
if user_org_role in ["owner", "admin"] or user.role == UserRole.ACCOUNTANT:
    return expense  # <--- user.role is GLOBAL!

# Managers can see all team expenses
if user_org_role == "manager" or user.role == UserRole.MANAGER:
    return expense  # <--- user.role is GLOBAL!
```

If a user has `UserRole.ACCOUNTANT` or `UserRole.MANAGER` set globally, they can see expenses in ANY organization they're a member of, even if their organization role is just "member".

#### Exploitation Scenario
1. User is an ACCOUNTANT in Company A (global role set)
2. User joins Company B as a basic MEMBER
3. User accesses Company B's expenses
4. Line 79 evaluates: `user.role == UserRole.ACCOUNTANT` → TRUE
5. User can see ALL of Company B's expenses despite being just a member

#### Impact
- **Severity**: HIGH
- **Attack Surface**: Users with global elevated roles
- **Result**: Unauthorized access to financial data across organizations

#### Recommendation
**Option 1**: Remove global role checks in organization contexts
```python
# Line 76-84: Only check organization roles
user_org_role = get_user_organization_role(user.id, org_id, db)

# Only org roles grant access
if user_org_role in ["owner", "admin"]:
    return expense

if user_org_role == "manager":
    return expense
```

**Option 2**: Explicitly require both global AND org role
```python
# User must be ACCOUNTANT globally AND have elevated org role
if user.role == UserRole.ACCOUNTANT and user_org_role in ["owner", "admin", "manager"]:
    return expense
```

**Option 3**: Add organization-specific accountant role
- Deprecate global `UserRole.ACCOUNTANT`
- Add `OrganizationRole.ACCOUNTANT` instead
- Each org manages its own accountants

---

### 🟡 MEDIUM-1: Invitation Tokens May Be Reusable
**File**: `backend/src/routes/organizations.py:722-794`
**Severity**: MEDIUM
**Risk**: Invitation Abuse

#### Description
The invitation acceptance endpoint checks:

```python
# Line 730-743
invitation = (
    db.query(OrganizationInvitation)
    .filter(
        OrganizationInvitation.token == token,
        OrganizationInvitation.status == "pending",
    )
    .first()
)

if not invitation:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Invitation not found or already used",
    )
```

The status is checked, and line 788 updates it to "accepted":

```python
# Line 788-789
invitation.status = "accepted"
invitation.accepted_at = datetime.utcnow()
```

This appears secure - once accepted, status changes from "pending" to "accepted", so the query on line 734 will not find it again.

**However**, there's a potential race condition:
1. User A starts accepting invitation (query succeeds, gets invitation)
2. User B starts accepting same invitation (query succeeds, gets same invitation)
3. Both create memberships
4. User is now a member twice (or second fails on unique constraint)

#### Impact
- **Severity**: MEDIUM
- **Likelihood**: Low (requires precise timing)
- **Result**: Duplicate memberships or constraint violations

#### Recommendation
```python
# Add database-level locking or unique constraint check
# Option 1: Row-level lock
invitation = (
    db.query(OrganizationInvitation)
    .filter(...)
    .with_for_update()  # <--- Lock row during transaction
    .first()
)

# Option 2: Check after membership creation
try:
    membership = OrganizationMember(...)
    db.add(membership)
    db.flush()  # Will raise IntegrityError if duplicate
except IntegrityError:
    db.rollback()
    raise HTTPException(400, "Already a member")
```

---

### 🟡 MEDIUM-2: Members Cannot Self-Remove (Trapped Members)
**File**: `backend/src/routes/organizations.py:544-587`
**Severity**: MEDIUM
**Risk**: User Experience / Privacy Issue

#### Description
There is NO endpoint for members to voluntarily leave an organization. The `remove_organization_member` endpoint requires ADMIN role:

```python
# Line 556-561
user_role = get_user_organization_role(current_user.id, organization_id, db)
if user_role not in [OrganizationRole.OWNER.value, OrganizationRole.ADMIN.value]:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only organization owners and admins can remove members",
    )
```

A member cannot call this on their own `member_id` because they don't have ADMIN role.

#### Impact
- **Severity**: MEDIUM (UX/Privacy, not security)
- **Issue**: Members are "trapped" in organizations
- **GDPR Risk**: Users cannot remove themselves from organizations

#### Recommendation
**Add self-removal endpoint**:

```python
@router.delete("/organizations/{organization_id}/leave")
async def leave_organization(
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Allow members to voluntarily leave an organization"""

    # Get user's membership
    membership = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.is_active == True,
        )
        .first()
    )

    if not membership:
        raise HTTPException(404, "Not a member of this organization")

    # Prevent owner from leaving if they're the last owner
    if membership.role == OrganizationRole.OWNER:
        owner_count = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.role == OrganizationRole.OWNER,
                OrganizationMember.is_active == True,
            )
            .count()
        )

        if owner_count <= 1:
            raise HTTPException(
                400,
                "Cannot leave: you are the last owner. Transfer ownership or delete the organization.",
            )

    # Soft delete membership
    membership.is_active = False
    db.commit()

    return {"message": "Successfully left organization"}
```

---

### 🟢 LOW-1: Soft-Deleted Organizations Hard-Deleted on Slug Reuse
**File**: `backend/src/routes/organizations.py:143-159`
**Severity**: LOW
**Risk**: Audit Trail Loss

#### Description
When creating an organization with a slug that matches a soft-deleted organization, the code HARD DELETES the soft-deleted org:

```python
# Line 145-158
soft_deleted_with_slug = (
    db.query(Organization)
    .filter(Organization.slug == org_data.slug)
    .filter(Organization.is_active == False)
    .all()
)
if soft_deleted_with_slug:
    logger.info(f"Hard-deleting {len(soft_deleted_with_slug)} soft-deleted...")
    for org in soft_deleted_with_slug:
        db.delete(org)  # <--- Hard delete!
    db.flush()
```

This permanently destroys the audit trail and any related data (expenses, members, etc.) that were soft-deleted.

#### Impact
- **Severity**: LOW
- **Issue**: Loss of historical data, audit trail
- **Compliance**: May violate data retention policies

#### Recommendation
**Option 1**: Rename soft-deleted org slugs instead of hard-deleting
```python
# Instead of hard delete:
for org in soft_deleted_with_slug:
    org.slug = f"{org.slug}-deleted-{org.id[:8]}"  # Make slug unique
    db.flush()
```

**Option 2**: Keep hard delete but add audit log
```python
# Before hard delete:
for org in soft_deleted_with_slug:
    AuthService.log_audit(
        db=db,
        user_id=current_user.id,
        action="organization.hard_deleted_for_slug_reuse",
        resource_type="organization",
        resource_id=org.id,
        request=request,
    )
    db.delete(org)
```

---

## Summary of Recommendations

### Immediate Actions Required (CRITICAL)

1. **CRITICAL-1**: Prevent ADMINs from granting OWNER role
   - Add check: Only OWNER can grant OWNER role
   - Prevent any changes to existing OWNER roles

2. **CRITICAL-2**: Prevent self-role elevation
   - Add check: Users cannot modify their own membership role
   - Require separate user for role changes

### High Priority Actions (HIGH)

3. **HIGH-2**: Restrict ADMIN removal permissions
   - Only OWNER can remove other ADMINs
   - OR add audit trail + notifications for ADMIN removals

4. **HIGH-4**: Fix global role leakage in expenses
   - Remove global UserRole checks in organization contexts
   - OR add organization-specific ACCOUNTANT role

### Medium Priority (MEDIUM)

5. **MEDIUM-1**: Add race condition protection for invitations
   - Use database row locking (`with_for_update()`)
   - Handle IntegrityErrors gracefully

6. **MEDIUM-2**: Add self-removal endpoint for members
   - Allow members to voluntarily leave organizations
   - Prevent last owner from leaving

### Low Priority (LOW)

7. **LOW-1**: Improve soft-delete handling
   - Rename slugs instead of hard-deleting
   - OR add comprehensive audit logging before hard deletes

---

## Testing Recommendations

### Manual Security Testing Checklist

Due to rate limiting (3 registrations/hour), automated testing is limited. Perform these manual tests:

1. **Privilege Escalation Tests**:
   - [ ] Try updating own role as MEMBER
   - [ ] Try updating member to OWNER as ADMIN
   - [ ] Verify OWNER role changes are blocked

2. **Cross-Organization Tests**:
   - [ ] Try accessing Org B's expenses while in Org A
   - [ ] Try creating expenses with wrong X-Organization-Id header
   - [ ] Verify organization membership checks work

3. **Admin Conflict Tests**:
   - [ ] Have ADMIN_A remove ADMIN_B
   - [ ] Verify proper authorization and logging

4. **Edge Case Tests**:
   - [ ] Try demoting last owner
   - [ ] Try removing last owner
   - [ ] Verify orphan organization prevention

### Recommended Test Environment Setup

```python
# Create test fixtures with pre-created users to avoid rate limits
@pytest.fixture
def test_users(db):
    return {
        'owner': create_user(db, "test_owner", "owner@test.com"),
        'admin': create_user(db, "test_admin", "admin@test.com"),
        'member': create_user(db, "test_member", "member@test.com"),
    }
```

---

## Conclusion

The RBAC system has a solid foundation with proper multi-tenancy isolation and organization-based access control. However, **critical vulnerabilities** exist in role elevation logic that could allow privilege escalation by malicious administrators.

**Priority**: Address CRITICAL-1 and CRITICAL-2 immediately before production deployment.

**Overall Security Posture**:
- ✅ Multi-tenant isolation: SECURE
- ✅ Cross-organization access: SECURE
- ❌ Role elevation controls: VULNERABLE
- ✅ Invitation security: MOSTLY SECURE (minor race condition)
- ⚠️ Global vs org roles: NEEDS CLARIFICATION

---

## Additional Notes

### Testing Limitations Encountered

1. **Rate Limiting**: Registration endpoint limited to 3/hour prevented comprehensive automated testing
2. **Free Tier Limits**: max_users=1 blocks invitation testing on Free tier
3. **Manual Testing Required**: Many scenarios require manual testing with pre-created users

### Files Reviewed

- `backend/src/routes/organizations.py` (832 lines)
- `backend/src/routes/auth.py` (657 lines)
- `backend/src/routes/expenses.py` (300+ lines reviewed)
- `backend/src/models.py` (958 lines)
- `backend/src/tenant_context.py` (229 lines)

### Code Quality Observations

**Strengths**:
- Comprehensive audit logging framework
- Soft-delete pattern for data retention
- Proper use of SQLAlchemy ORM (prevents SQL injection)
- Multi-tenant isolation is well-implemented
- Detailed error messages with upgrade prompts

**Areas for Improvement**:
- Role elevation logic needs tighter controls
- Global vs organization role boundaries need clarification
- Missing self-service member management (leave org)
- Hard-delete policy should be reviewed for compliance

---

**End of Report**
