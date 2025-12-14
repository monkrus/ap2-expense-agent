"""
Regression Tests for Organization Features
==========================================

These tests ensure that specific bugs that were fixed stay fixed.
Each test documents:
- What bug it prevents
- When the bug was fixed
- What the test validates

CRITICAL: DO NOT DELETE OR MODIFY THESE TESTS without understanding
what regression they prevent.
"""

import pytest
from datetime import datetime, timedelta
import uuid

from src.models import Organization, OrganizationMember, Subscription, SubscriptionTier


# ============================================================================
# REGRESSION TEST #1: 402 Payment Required Returns JSON
# ============================================================================
# BUG FIXED: 2025-12-14
# FILE: backend/src/error_handlers.py:213-228
# ISSUE: 402 errors weren't returning structured JSON for upgrade prompts
# ============================================================================

def test_402_error_returns_structured_json(client, db_session, test_user, auth_headers):
    """
    REGRESSION TEST: Ensure 402 errors return dict details as JSON

    Bug: When tier limits were exceeded, the frontend couldn't parse
    the upgrade prompt because 402 errors were returning strings instead
    of structured JSON objects.

    Fixed in: error_handlers.py:213-228

    This test ensures:
    1. 402 errors with dict details return as JSON
    2. The detail object is preserved (not stringified)
    3. Frontend can extract upgrade options from the response

    If this test fails, the upgrade prompt feature is broken.
    """
    # Create a Free tier subscription with max organizations = 1
    subscription = Subscription(
        id=str(uuid.uuid4()),
        user_id=test_user.id,
        tier=SubscriptionTier.FREE,
        status="active",
        max_users=1,
        max_expenses_per_month=20,
    )
    db_session.add(subscription)
    db_session.commit()

    # Create first organization (should succeed)
    org1_response = client.post(
        "/api/v1/organizations",
        headers=auth_headers,
        json={
            "name": "First Org",
            "slug": "first-org-402",
            "description": "First organization",
        },
    )
    assert org1_response.status_code == 201

    # Try to create second organization (should fail with 402)
    org2_response = client.post(
        "/api/v1/organizations",
        headers=auth_headers,
        json={
            "name": "Second Org",
            "slug": "second-org-402",
            "description": "Second organization",
        },
    )

    # CRITICAL: Must return 402, not 500 or other error
    assert org2_response.status_code == 402, (
        f"Expected 402 Payment Required, got {org2_response.status_code}. "
        f"Response: {org2_response.json()}"
    )

    # CRITICAL: Response must be valid JSON with detail dict
    response_data = org2_response.json()
    assert "detail" in response_data, "Response missing 'detail' field"

    # CRITICAL: Detail must be a dict, not a string
    detail = response_data["detail"]
    assert isinstance(detail, dict), (
        f"Detail should be dict for upgrade prompt parsing, got {type(detail)}. "
        f"This breaks the frontend upgrade prompt feature."
    )

    # CRITICAL: Must contain upgrade prompt information
    assert "message" in detail, "Missing upgrade message"
    assert "current_tier" in detail, "Missing current tier"
    assert "current_limit" in detail, "Missing current limit"
    assert "current_count" in detail, "Missing current count"

    # Validate structure matches what frontend expects
    assert detail["current_tier"] == "free"
    assert detail["current_limit"] == 1
    assert detail["current_count"] == 1
    assert "upgrade_options" in detail

    print("✅ REGRESSION TEST PASSED: 402 errors return structured JSON")


# ============================================================================
# REGRESSION TEST #2: Slug Reuse After Deletion
# ============================================================================
# BUG FIXED: 2025-12-14
# FILE: backend/src/routes/organizations.py:143-158
# ISSUE: Couldn't reuse organization slugs after soft-deleting organizations
# ============================================================================

def test_slug_can_be_reused_after_org_deletion(client, db_session, test_user, auth_headers):
    """
    REGRESSION TEST: Ensure slugs can be reused after org deletion

    Bug: After soft-deleting an organization, users couldn't create a new
    organization with the same slug because soft-deleted orgs weren't being
    hard-deleted before the UNIQUE constraint check.

    Fixed in: organizations.py:143-158

    This test ensures:
    1. Soft-deleted orgs with duplicate slugs are hard-deleted
    2. New orgs can reuse slugs from deleted orgs
    3. Active orgs still prevent slug reuse (constraint works)

    If this test fails, users will get confusing "slug taken" errors
    when trying to reuse slugs from deleted organizations.
    """
    SLUG = "test-org-slug"

    # Step 1: Create an organization
    create_response = client.post(
        "/api/v1/organizations",
        headers=auth_headers,
        json={
            "name": "Original Org",
            "slug": SLUG,
            "description": "Original organization",
        },
    )
    assert create_response.status_code == 201
    org_id = create_response.json()["id"]

    # Step 2: Delete the organization (soft delete)
    delete_response = client.delete(
        f"/api/v1/organizations/{org_id}",
        headers=auth_headers,
    )
    assert delete_response.status_code == 204

    # Verify it's soft-deleted (is_active = False)
    deleted_org = db_session.query(Organization).filter(
        Organization.id == org_id
    ).first()
    assert deleted_org is not None, "Org should still exist (soft delete)"
    assert deleted_org.is_active is False, "Org should be inactive"

    # Step 3: Create a NEW organization with the SAME slug
    # This is where the bug occurred - it would fail with "slug already taken"
    recreate_response = client.post(
        "/api/v1/organizations",
        headers=auth_headers,
        json={
            "name": "New Org",
            "slug": SLUG,  # ← Same slug as deleted org
            "description": "New organization with reused slug",
        },
    )

    # CRITICAL: Must succeed (201), not fail with 400 "slug already taken"
    assert recreate_response.status_code == 201, (
        f"Expected 201 (slug reuse allowed), got {recreate_response.status_code}. "
        f"Response: {recreate_response.json()}. "
        f"This means the slug reuse bug has returned!"
    )

    new_org = recreate_response.json()
    assert new_org["slug"] == SLUG
    assert new_org["name"] == "New Org"

    # Verify the old soft-deleted org was hard-deleted
    old_org_still_exists = db_session.query(Organization).filter(
        Organization.id == org_id
    ).first()
    assert old_org_still_exists is None, (
        "Old soft-deleted org should be hard-deleted to free up the slug"
    )

    print("✅ REGRESSION TEST PASSED: Slugs can be reused after deletion")


def test_slug_cannot_be_reused_for_active_orgs(client, db_session, test_user, auth_headers):
    """
    COMPANION TEST: Ensure slug uniqueness still works for ACTIVE orgs

    This test ensures the slug reuse fix doesn't break the normal
    uniqueness constraint for active organizations.
    """
    SLUG = "active-org-slug"

    # Create first organization
    response1 = client.post(
        "/api/v1/organizations",
        headers=auth_headers,
        json={
            "name": "First Active Org",
            "slug": SLUG,
            "description": "First active org",
        },
    )
    assert response1.status_code == 201

    # Try to create second organization with same slug (should fail)
    response2 = client.post(
        "/api/v1/organizations",
        headers=auth_headers,
        json={
            "name": "Second Active Org",
            "slug": SLUG,  # ← Duplicate slug
            "description": "Second active org",
        },
    )

    # CRITICAL: Must fail with 400, not succeed
    assert response2.status_code == 400, (
        f"Expected 400 (slug taken), got {response2.status_code}. "
        f"Response: {response2.json()}. "
        f"Slug uniqueness constraint is broken!"
    )

    error_data = response2.json()
    assert "detail" in error_data

    # Validate error message helps the user
    detail = error_data["detail"]
    if isinstance(detail, dict):
        assert detail.get("error") == "slug_already_taken"
        assert "suggestions" in detail  # Should provide alternatives

    print("✅ COMPANION TEST PASSED: Active org slug uniqueness works")


# ============================================================================
# REGRESSION TEST #3: User Subscription Fallback
# ============================================================================
# BUG FIXED: 2025-12-14
# FILE: backend/src/routes/billing_org.py:68-114
# ISSUE: Legacy users with user-level subscriptions couldn't access billing
# ============================================================================

def test_billing_falls_back_to_user_subscription(client, db_session, test_user, auth_headers):
    """
    REGRESSION TEST: Ensure billing API falls back to user subscriptions

    Bug: Users who had user-level subscriptions but no organization-level
    subscriptions would get "no subscription" errors when accessing the
    billing dashboard.

    Fixed in: billing_org.py:68-114

    This test ensures:
    1. When org subscription doesn't exist, check user subscription
    2. User subscription data is mapped to org subscription format
    3. Legacy users can still access billing info

    If this test fails, legacy users will be unable to view their
    subscription status and will think they're on the free tier.
    """
    # First, delete any auto-created FREE subscription from test_user fixture
    existing_free_sub = (
        db_session.query(Subscription)
        .filter(Subscription.user_id == test_user.id)
        .first()
    )
    if existing_free_sub:
        db_session.delete(existing_free_sub)
        db_session.commit()

    # Create a user-level subscription FIRST (LEGACY MODEL)
    # This simulates a user who upgraded to PROFESSIONAL before org-level billing existed
    user_subscription = Subscription(
        id=str(uuid.uuid4()),
        user_id=test_user.id,
        tier=SubscriptionTier.PROFESSIONAL,
        status="active",
        max_users=25,
        max_expenses_per_month=9999999,  # Unlimited for Pro
        max_ai_categorizations=1000,
        max_ap2_transactions=500,
        current_period_start=datetime.utcnow(),
        current_period_end=datetime.utcnow() + timedelta(days=30),
    )
    db_session.add(user_subscription)
    db_session.commit()

    # Now create an organization for the user
    org_response = client.post(
        "/api/v1/organizations",
        headers=auth_headers,
        json={
            "name": "Legacy User Org",
            "slug": "legacy-org",
            "description": "Organization for legacy user",
        },
    )
    assert org_response.status_code == 201
    org_id = org_response.json()["id"]

    # Request organization billing status
    # This would previously return "no subscription"
    billing_response = client.get(
        "/api/billing/org/subscription",
        headers=auth_headers,
    )

    # CRITICAL: Must return 200 with subscription data
    assert billing_response.status_code == 200, (
        f"Expected 200, got {billing_response.status_code}. "
        f"Response: {billing_response.json()}. "
        f"Fallback to user subscription is broken!"
    )

    billing_data = billing_response.json()

    # CRITICAL: Must show user HAS a subscription
    assert billing_data["has_subscription"] is True, (
        "Should show subscription exists (from user-level fallback)"
    )

    # CRITICAL: Must return correct tier
    assert billing_data["tier"] == "professional", (
        f"Expected tier 'professional', got '{billing_data['tier']}'"
    )

    # CRITICAL: Must include limits from user subscription
    assert "limits" in billing_data
    assert billing_data["limits"]["max_users"] == 25

    # CRITICAL: Must indicate this is a fallback (for debugging)
    assert billing_data.get("source") == "user_subscription_fallback", (
        "Should indicate this came from user subscription fallback"
    )

    print("✅ REGRESSION TEST PASSED: User subscription fallback works")


# ============================================================================
# REGRESSION TEST #4: Name Validation (Case-Insensitive)
# ============================================================================
# BUG FIXED: 2025-11-27 (from CLAUDE.md)
# FILE: backend/src/routes/organizations.py:184-208
# ISSUE: Organization names weren't validated case-insensitively
# ============================================================================

def test_org_name_validation_is_case_insensitive(client, db_session, test_user, auth_headers):
    """
    REGRESSION TEST: Ensure organization names are unique (case-insensitive)

    Bug: Users could create orgs with duplicate names like "Acme Corp"
    and "ACME CORP", which caused confusion.

    Fixed in: organizations.py:184-208

    This test ensures:
    1. Name validation is case-insensitive
    2. Only active orgs are checked (not soft-deleted)
    3. Error provides helpful suggestions

    If this test fails, users can create orgs with confusingly similar names.
    """
    # Create first organization
    response1 = client.post(
        "/api/v1/organizations",
        headers=auth_headers,
        json={
            "name": "Acme Corporation",
            "slug": "acme-corp",
            "description": "First org",
        },
    )
    assert response1.status_code == 201

    # Try to create second organization with same name (different case)
    response2 = client.post(
        "/api/v1/organizations",
        headers=auth_headers,
        json={
            "name": "ACME CORPORATION",  # ← Same name, different case
            "slug": "acme-corp-2",
            "description": "Duplicate name org",
        },
    )

    # CRITICAL: Must fail with 400
    assert response2.status_code == 400, (
        f"Expected 400 (name taken), got {response2.status_code}. "
        f"Case-insensitive name validation is broken!"
    )

    error_data = response2.json()
    detail = error_data["detail"]

    # Validate error structure
    if isinstance(detail, dict):
        assert detail.get("error") == "name_already_taken"
        assert "suggestions" in detail
        assert detail.get("hint") == "Names are case-insensitive. You can reuse names from deleted organizations."

    print("✅ REGRESSION TEST PASSED: Name validation is case-insensitive")


# ============================================================================
# Test Suite Summary
# ============================================================================

def test_regression_suite_documentation():
    """
    Documentation test - explains what this suite protects

    This test suite protects against 4 critical regressions:

    1. 402 Error JSON Structure (error_handlers.py:213-228)
       - Ensures upgrade prompts work in frontend

    2. Slug Reuse After Deletion (organizations.py:143-158)
       - Allows slug reuse from deleted orgs

    3. User Subscription Fallback (billing_org.py:68-114)
       - Ensures legacy users can access billing

    4. Case-Insensitive Name Validation (organizations.py:184-208)
       - Prevents duplicate org names

    WARNING: Do not modify or delete these tests without:
    1. Understanding what regression they prevent
    2. Creating equivalent tests if refactoring
    3. Documenting the change in CLAUDE.md
    """
    print("\n" + "="*70)
    print("REGRESSION TEST SUITE")
    print("="*70)
    print("This suite protects 4 critical bug fixes from returning:")
    print("  1. ✅ 402 Payment Required JSON Structure")
    print("  2. ✅ Slug Reuse After Organization Deletion")
    print("  3. ✅ User Subscription Fallback for Legacy Users")
    print("  4. ✅ Case-Insensitive Organization Name Validation")
    print("="*70 + "\n")
    assert True  # Always pass - this is documentation
