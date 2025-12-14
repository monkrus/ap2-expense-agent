# Regression Test Protection

This document explains how to prevent bugs from returning using regression tests.

## What Are Regression Tests?

**Regression tests** are tests that verify that bugs that were previously fixed stay fixed. They act as guardrails to ensure that future code changes don't accidentally re-introduce old bugs.

## Why Are They Important?

During development, you noticed that **if errors are fixed, they return again after the next fix**. This happens because:

1. **Code changes** can accidentally undo previous fixes
2. **Refactoring** can break working code
3. **Different developers** may not know about previous bugs
4. **Time passes** and we forget what was fixed

**Regression tests solve this problem** by creating automated checks that fail if a bug returns.

---

## How to Use This System

### Every Time You Fix a Bug

Follow these steps:

1. **Fix the bug** in the code
2. **Create a regression test** that proves it's fixed
3. **Run the test** to verify it passes
4. **Commit both** the fix and the test together

### Example Workflow

```bash
# 1. Fix the bug in the code
# (edit backend/src/routes/organizations.py)

# 2. Create a regression test
# (add test to backend/tests/test_organizations_regression.py)

# 3. Run the test
cd backend && pytest tests/test_organizations_regression.py::test_your_new_test -v

# 4. Commit together
git add backend/src/routes/organizations.py
git add backend/tests/test_organizations_regression.py
git commit -m "fix: prevent slug reuse bug + regression test"
```

---

## Current Regression Tests

### File: `backend/tests/test_organizations_regression.py`

This file contains 6 regression tests that protect against critical bugs:

#### Test #1: `test_402_error_returns_structured_json`

**Bug Fixed**: 2025-12-14
**File**: `backend/src/error_handlers.py:213-228`
**Issue**: When tier limits were exceeded, the frontend couldn't parse upgrade prompts because 402 errors were returning strings instead of JSON objects.

**What This Test Protects**:
- ✅ 402 errors return dict details as JSON
- ✅ Frontend can extract upgrade options
- ✅ Upgrade prompts work correctly

**If This Test Fails**:
❌ Users won't see upgrade prompts when hitting tier limits
❌ Frontend will show generic errors instead of helpful upgrade messages
❌ Monetization feature is broken

---

#### Test #2: `test_slug_can_be_reused_after_org_deletion`

**Bug Fixed**: 2025-12-14
**File**: `backend/src/routes/organizations.py:143-158`
**Issue**: After soft-deleting an organization, users couldn't create a new organization with the same slug because soft-deleted orgs weren't being hard-deleted.

**What This Test Protects**:
- ✅ Soft-deleted orgs are hard-deleted before slug check
- ✅ Slugs can be reused after deletion
- ✅ UNIQUE constraints still work for active orgs

**If This Test Fails**:
❌ Users get confusing "slug already taken" errors
❌ Can't reuse company names after deletion
❌ Database fills with orphaned soft-deleted records

---

#### Test #3: `test_slug_cannot_be_reused_for_active_orgs`

**Companion Test** to Test #2
**Purpose**: Ensures the slug reuse fix doesn't break normal uniqueness

**What This Test Protects**:
- ✅ Active orgs still prevent slug duplication
- ✅ Uniqueness constraints work correctly
- ✅ Error messages provide suggestions

**If This Test Fails**:
❌ Multiple active orgs can have same slug
❌ Data integrity is compromised
❌ Users see wrong organization data

---

#### Test #4: `test_billing_falls_back_to_user_subscription`

**Bug Fixed**: 2025-12-14
**File**: `backend/src/routes/billing_org.py:68-114`
**Issue**: Users with legacy user-level subscriptions couldn't access billing info when organization-level subscriptions didn't exist.

**What This Test Protects**:
- ✅ Billing API falls back to user subscriptions
- ✅ Legacy users can access billing dashboard
- ✅ Subscription data is properly mapped

**If This Test Fails**:
❌ Legacy users see "no subscription"
❌ Paid users think they're on free tier
❌ Billing dashboard is broken for old users

---

#### Test #5: `test_org_name_validation_is_case_insensitive`

**Bug Fixed**: 2025-11-27
**File**: `backend/src/routes/organizations.py:184-208`
**Issue**: Organizations could have duplicate names with different casing ("Acme Corp" vs "ACME CORP").

**What This Test Protects**:
- ✅ Name validation is case-insensitive
- ✅ Only active orgs are checked
- ✅ Error provides helpful suggestions

**If This Test Fails**:
❌ Duplicate org names allowed
❌ Users confused by similar names
❌ Data quality problems

---

#### Test #6: `test_regression_suite_documentation`

**Purpose**: Documents what the test suite protects against

**What This Test Does**:
- ✅ Always passes (documentation test)
- ✅ Prints summary of protected regressions
- ✅ Serves as reminder to maintain tests

---

## Running Regression Tests

### Run All Regression Tests

```bash
cd backend
pytest tests/test_organizations_regression.py -v
```

**Expected Output**:
```
✓ test_402_error_returns_structured_json PASSED
✓ test_slug_can_be_reused_after_org_deletion PASSED
✓ test_slug_cannot_be_reused_for_active_orgs PASSED
✓ test_billing_falls_back_to_user_subscription PASSED
✓ test_org_name_validation_is_case_insensitive PASSED
✓ test_regression_suite_documentation PASSED

6 passed in 2.24s
```

### Run a Specific Test

```bash
cd backend
pytest tests/test_organizations_regression.py::test_402_error_returns_structured_json -v
```

### Run Before Every Commit

```bash
# Add to your git pre-commit hook
cd backend && pytest tests/test_organizations_regression.py
```

---

## How to Add New Regression Tests

### Template

```python
def test_your_bug_description(client, db_session, test_user, auth_headers):
    """
    REGRESSION TEST: Short description of what this prevents

    Bug: Explain what was broken before the fix

    Fixed in: file.py:line_numbers

    This test ensures:
    1. First protection
    2. Second protection
    3. Third protection

    If this test fails, [explain impact on users]
    """
    # Arrange: Set up the conditions that trigger the bug

    # Act: Perform the action that used to fail

    # Assert: Verify the bug is fixed
    assert expected_result, (
        f"Detailed error message explaining what broke. "
        f"This helps future developers understand the issue."
    )
```

### Best Practices

1. **Clear Documentation**: Explain WHAT bug, WHEN fixed, WHERE in code
2. **Descriptive Assertions**: Error messages should explain impact
3. **Self-Contained**: Test should work independently
4. **Fast**: Should run in < 1 second
5. **Deterministic**: Same result every time

---

## Integration with CI/CD

### GitHub Actions

```yaml
# .github/workflows/test.yml
- name: Run Regression Tests
  run: |
    cd backend
    pytest tests/test_organizations_regression.py -v
```

### Pre-Commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash
cd backend
pytest tests/test_organizations_regression.py
if [ $? -ne 0 ]; then
    echo "❌ Regression tests failed! Fix them before committing."
    exit 1
fi
```

---

## Maintenance

### ⚠️ NEVER Delete Regression Tests

Regression tests should **NEVER** be deleted unless:

1. ✅ The feature they test has been completely removed
2. ✅ The test has been replaced with equivalent or better coverage
3. ✅ You understand what regression you're exposing

### ⚠️ If a Regression Test Fails

1. **DO NOT** just delete the test or mark it as skipped
2. **DO** investigate why it's failing
3. **DO** fix the code that broke, not the test
4. **DO** update the test if requirements legitimately changed

### Updating Tests

If requirements change:

```python
# OLD (before requirement change)
assert response.status_code == 400

# NEW (after requirement change)
# DOCUMENTED: Changed from 400 to 422 for Pydantic validation (2025-12-15)
assert response.status_code == 422
```

---

## FAQ

### Q: How many regression tests should I write?

**A**: One per bug fix. If you fixed 3 bugs, create 3 regression tests.

### Q: Should I write tests for small bugs?

**A**: Yes! Small bugs can have big impacts. Even one-line fixes deserve tests.

### Q: What if my bug fix touches multiple files?

**A**: Create one comprehensive test that verifies the entire fix works end-to-end.

### Q: How do I know if I need a regression test?

**A**: Ask: "Would I want to know immediately if this bug came back?" If yes, write the test.

### Q: Can regression tests slow down development?

**A**: No! They **speed up** development by catching bugs early, before they reach users.

---

## Summary

✅ **Create regression tests for every bug fix**
✅ **Run tests before committing**
✅ **Never delete regression tests without understanding impact**
✅ **Document what each test protects against**
✅ **Use clear, descriptive test names and error messages**

**Remember**: A bug that has a regression test can only happen once. Without a test, it can happen again and again.
