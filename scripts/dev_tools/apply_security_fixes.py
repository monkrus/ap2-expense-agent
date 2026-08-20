"""
Apply Critical Security Fixes to RBAC System
"""

def apply_critical_fixes():
    """Apply CRITICAL-1 and CRITICAL-2 security fixes"""

    file_path = 'backend/src/routes/organizations.py'

    # Read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if fixes already applied
    if 'SECURITY FIX (CRITICAL-2)' in content:
        print('[INFO] CRITICAL fixes already applied')
        return False

    # Define the fixes
    critical2_fix = '''
    # SECURITY FIX (CRITICAL-2): Prevent self-role modification
    if member.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify your own role. Contact another administrator.",
        )
'''

    critical1_fix = '''
    # SECURITY FIX (CRITICAL-1): Only OWNER can grant OWNER role
    if role == OrganizationRole.OWNER and user_role != OrganizationRole.OWNER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the organization OWNER can grant OWNER role to others.",
        )
'''

    # Find and replace the vulnerable section
    # Original vulnerable code block
    old_code = '''    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Member not found"
        )

    # Cannot change owner role
    if member.role == OrganizationRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot change owner role"
        )

    member.role = role'''

    # New secured code block
    new_code = '''    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Member not found"
        )
''' + critical2_fix + '''
    # Cannot change owner role
    if member.role == OrganizationRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot change owner role"
        )
''' + critical1_fix + '''
    member.role = role'''

    # Apply the fix
    if old_code in content:
        content = content.replace(old_code, new_code)

        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print('[SUCCESS] Applied CRITICAL-1 and CRITICAL-2 fixes to organizations.py')
        return True
    else:
        print('[ERROR] Could not find target code section')
        print('[INFO] File may have been modified or fixes already applied')
        return False


def apply_high2_fix():
    """Apply HIGH-2: Restrict ADMIN removal"""

    file_path = 'backend/src/routes/organizations.py'

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'SECURITY FIX (HIGH-2)' in content:
        print('[INFO] HIGH-2 fix already applied')
        return False

    high2_fix = '''
    # SECURITY FIX (HIGH-2): Only OWNER can remove ADMINs
    if member.role == OrganizationRole.ADMIN and user_role != OrganizationRole.OWNER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the organization OWNER can remove administrators.",
        )
'''

    # Find the section to modify
    old_code = '''    # Cannot remove owner
    if member.role == OrganizationRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove organization owner",
        )

    # Soft delete (deactivate)'''

    new_code = '''    # Cannot remove owner
    if member.role == OrganizationRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove organization owner",
        )
''' + high2_fix + '''
    # Soft delete (deactivate)'''

    if old_code in content:
        content = content.replace(old_code, new_code)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print('[SUCCESS] Applied HIGH-2 fix to organizations.py')
        return True
    else:
        print('[ERROR] Could not find target code for HIGH-2 fix')
        return False


def apply_high4_fix():
    """Apply HIGH-4: Remove global role checks"""

    file_path = 'backend/src/routes/expenses.py'

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'SECURITY FIX (HIGH-4)' in content:
        print('[INFO] HIGH-4 fix already applied')
        return False

    # Fix 1: ensure_expense_access function
    old_code1 = '''    # Check role-based access
    user_org_role = get_user_organization_role(user.id, org_id, db)

    # Owners, admins, and accountants can see all expenses
    if user_org_role in ["owner", "admin"] or user.role == UserRole.ACCOUNTANT:
        return expense

    # Managers can see all team expenses
    if user_org_role == "manager" or user.role == UserRole.MANAGER:
        return expense'''

    new_code1 = '''    # Check role-based access
    user_org_role = get_user_organization_role(user.id, org_id, db)

    # SECURITY FIX (HIGH-4): Only check organization roles, not global roles
    # Owners and admins can see all expenses in their organization
    if user_org_role in ["owner", "admin"]:
        return expense

    # Managers can see all team expenses in their organization
    if user_org_role == "manager":
        return expense'''

    # Fix 2: list_expenses function
    old_code2 = '''    # Role-based filtering
    user_org_role = get_user_organization_role(current_user.id, org_id, db)

    # Employees see only their own expenses
    if user_org_role in ["member", None] and current_user.role == UserRole.EMPLOYEE:
        query = query.filter(Expense.user_id == current_user.id)

    # All other roles (manager, accountant, admin, owner) see all expenses'''

    new_code2 = '''    # Role-based filtering
    user_org_role = get_user_organization_role(current_user.id, org_id, db)

    # SECURITY FIX (HIGH-4): Only use organization roles for filtering
    # Members see only their own expenses
    if user_org_role in ["member", None]:
        query = query.filter(Expense.user_id == current_user.id)

    # All other org roles (manager, admin, owner) see all expenses'''

    modified = False

    if old_code1 in content:
        content = content.replace(old_code1, new_code1)
        modified = True
        print('[SUCCESS] Applied HIGH-4 fix (part 1) to ensure_expense_access')

    if old_code2 in content:
        content = content.replace(old_code2, new_code2)
        modified = True
        print('[SUCCESS] Applied HIGH-4 fix (part 2) to list_expenses')

    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    else:
        print('[ERROR] Could not find target code for HIGH-4 fixes')
        return False


if __name__ == '__main__':
    print('=' * 70)
    print('AP2 EXPENSE AGENT - SECURITY FIXES')
    print('=' * 70)
    print()

    print('[STEP 1] Applying CRITICAL fixes to organizations.py...')
    apply_critical_fixes()
    print()

    print('[STEP 2] Applying HIGH-2 fix to organizations.py...')
    apply_high2_fix()
    print()

    print('[STEP 3] Applying HIGH-4 fixes to expenses.py...')
    apply_high4_fix()
    print()

    print('=' * 70)
    print('[COMPLETE] All security fixes applied')
    print('=' * 70)
    print()
    print('Next steps:')
    print('1. Restart the backend server')
    print('2. Run: python test_rbac_comprehensive.py')
    print('3. Review: RBAC_SECURITY_AUDIT_REPORT.md')
