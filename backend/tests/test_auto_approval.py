"""
End-to-End Auto-Approval Integration Tests
Tests the complete auto-approval workflow from policy creation to expense approval
"""

import uuid
from datetime import datetime
from decimal import Decimal

import pytest

from src.models import ApprovalPolicy, Expense, ExpenseStatus, OrganizationRole


class TestAutoApprovalEndToEnd:
    """Test auto-approval system end-to-end"""

    def test_simple_auto_approval(self, client, admin_org_headers, test_organization, test_admin, db_session):
        """Test basic auto-approval flow"""
        # Step 1: Create an approval policy
        policy_data = {
            "name": "Auto-approve small expenses",
            "description": "Automatically approve expenses under $50",
            "priority": 100,
            "auto_approve": True,
            "require_receipt": False,  # Don't require receipt for this test
            "notify_on_auto_approve": True,
            "max_amount_per_expense": 50.00,
            "conditions": {
                "categories": ["MEALS", "OFFICE_SUPPLIES"],
                "min_amount": 1.00
            }
        }

        response = client.post(
            "/api/v1/approval-policies",
            headers=admin_org_headers,
            json=policy_data
        )

        assert response.status_code == 201, f"Policy creation failed: {response.json()}"
        policy = response.json()
        assert policy["name"] == "Auto-approve small expenses"
        assert policy["auto_approve"] == True
        policy_id = policy["id"]

        # Step 2: Submit an expense that MATCHES the policy
        expense_data = {
            "amount": 25.00,  # Under $50 limit
            "vendor": "Coffee Shop",
            "description": "Team coffee",
            "category": "MEALS",  # In allowed categories
            "date": datetime.utcnow().isoformat(),
        }

        response = client.post(
            "/api/v1/expenses",
            headers=admin_org_headers,
            json=expense_data
        )

        assert response.status_code == 201, f"Expense creation failed: {response.json()}"
        expense = response.json()

        # Step 3: Verify expense was AUTO-APPROVED
        assert expense["auto_approved"] == True, "Expense should be auto-approved"
        assert expense["status"] == "approved", f"Status should be approved, got {expense['status']}"
        assert expense.get("auto_approved_via") == "approval_policy", "Should be approved via policy"
        assert "Auto-approved by policy" in expense.get("message", "")

    def test_expense_exceeding_amount_limit_not_auto_approved(
        self, client, admin_org_headers, test_organization, test_admin, db_session
    ):
        """Test that expenses exceeding max amount are not auto-approved"""
        # Create policy with $50 limit
        policy_data = {
            "name": "Small expense policy",
            "priority": 100,
            "auto_approve": True,
            "require_receipt": False,
            "max_amount_per_expense": 50.00,
            "conditions": {"categories": ["MEALS"]}
        }

        response = client.post(
            "/api/v1/approval-policies",
            headers=admin_org_headers,
            json=policy_data
        )
        assert response.status_code == 201

        # Submit expense OVER the limit
        expense_data = {
            "amount": 75.00,  # Over $50 limit
            "vendor": "Restaurant",
            "description": "Team lunch",
            "category": "MEALS",
            "date": datetime.utcnow().isoformat(),
        }

        response = client.post(
            "/api/v1/expenses",
            headers=admin_org_headers,
            json=expense_data
        )

        assert response.status_code == 201
        expense = response.json()

        # Should NOT be auto-approved
        assert expense["auto_approved"] == False, "Expense should NOT be auto-approved"
        assert expense["status"] == "pending", "Status should be pending"
        assert "manual approval" in expense.get("message", "").lower()

    def test_category_filtering(self, client, admin_org_headers, test_admin, db_session):
        """Test that only matching categories are auto-approved"""
        # Create policy for MEALS only
        policy_data = {
            "name": "MEALS only policy",
            "priority": 100,
            "auto_approve": True,
            "require_receipt": False,
            "max_amount_per_expense": 100.00,
            "conditions": {
                "categories": ["MEALS"]  # Only MEALS allowed
            }
        }

        response = client.post(
            "/api/v1/approval-policies",
            headers=admin_org_headers,
            json=policy_data
        )
        assert response.status_code == 201

        # Test 1: Submit MEALS expense (should auto-approve)
        response = client.post(
            "/api/v1/expenses",
            headers=admin_org_headers,
            json={
                "amount": 30.00,
                "vendor": "Coffee",
                "description": "Coffee",
                "category": "MEALS",
                "date": datetime.utcnow().isoformat(),
            }
        )
        assert response.status_code == 201
        expense = response.json()
        assert expense["auto_approved"] == True, "MEALS should be auto-approved"

        # Test 2: Submit TRAVEL expense (should NOT auto-approve)
        response = client.post(
            "/api/v1/expenses",
            headers=admin_org_headers,
            json={
                "amount": 30.00,
                "vendor": "Uber",
                "description": "Taxi",
                "category": "TRAVEL",  # Not in allowed categories
                "date": datetime.utcnow().isoformat(),
            }
        )
        assert response.status_code == 201
        expense = response.json()
        assert expense["auto_approved"] == False, "TRAVEL should NOT be auto-approved"

    def test_priority_based_policy_matching(self, client, admin_org_headers, test_admin, db_session):
        """Test that higher priority policies are checked first"""
        # Create low priority policy (priority 10)
        low_priority_policy = {
            "name": "Low priority policy",
            "priority": 10,
            "auto_approve": True,
            "require_receipt": False,
            "max_amount_per_expense": 100.00,
            "conditions": {"categories": ["MEALS"]}
        }

        response = client.post(
            "/api/v1/approval-policies",
            headers=admin_org_headers,
            json=low_priority_policy
        )
        assert response.status_code == 201
        low_policy_id = response.json()["id"]

        # Create high priority policy (priority 100) with stricter limit
        high_priority_policy = {
            "name": "High priority policy",
            "priority": 100,  # Higher priority
            "auto_approve": True,
            "require_receipt": False,
            "max_amount_per_expense": 20.00,  # Stricter limit
            "conditions": {"categories": ["MEALS"]}
        }

        response = client.post(
            "/api/v1/approval-policies",
            headers=admin_org_headers,
            json=high_priority_policy
        )
        assert response.status_code == 201
        high_policy_id = response.json()["id"]

        # Submit expense under high priority limit
        response = client.post(
            "/api/v1/expenses",
            headers=admin_org_headers,
            json={
                "amount": 15.00,  # Under $20 (high priority limit)
                "vendor": "Coffee",
                "description": "Coffee",
                "category": "MEALS",
                "date": datetime.utcnow().isoformat(),
            }
        )
        assert response.status_code == 201
        expense = response.json()

        # Should match HIGH priority policy
        assert expense["auto_approved"] == True
        assert expense.get("auto_approved_via") == "approval_policy", \
            "Should match high priority policy"

    def test_daily_limit_enforcement(self, client, admin_org_headers, test_admin, db_session):
        """Test that daily limits per user are enforced"""
        # Create policy with $100 daily limit
        policy_data = {
            "name": "Daily limit policy",
            "priority": 100,
            "auto_approve": True,
            "require_receipt": False,
            "max_amount_per_expense": 50.00,
            "daily_limit_per_user": 100.00,  # $100 per day
            "conditions": {"categories": ["MEALS"]}
        }

        response = client.post(
            "/api/v1/approval-policies",
            headers=admin_org_headers,
            json=policy_data
        )
        assert response.status_code == 201

        # Submit first expense ($40) - should auto-approve
        response = client.post(
            "/api/v1/expenses",
            headers=admin_org_headers,
            json={
                "amount": 40.00,
                "vendor": "Lunch",
                "description": "Lunch",
                "category": "MEALS",
                "date": datetime.utcnow().isoformat(),
            }
        )
        assert response.status_code == 201
        expense1 = response.json()
        assert expense1["auto_approved"] == True, "First expense should auto-approve"

        # Submit second expense ($40) - should auto-approve (total $80)
        response = client.post(
            "/api/v1/expenses",
            headers=admin_org_headers,
            json={
                "amount": 40.00,
                "vendor": "Dinner",
                "description": "Dinner",
                "category": "MEALS",
                "date": datetime.utcnow().isoformat(),
            }
        )
        assert response.status_code == 201
        expense2 = response.json()
        assert expense2["auto_approved"] == True, "Second expense should auto-approve (total $80)"

        # Submit third expense ($40) - should NOT auto-approve (would exceed $100 daily limit)
        response = client.post(
            "/api/v1/expenses",
            headers=admin_org_headers,
            json={
                "amount": 40.00,
                "vendor": "Snacks",
                "description": "Snacks",
                "category": "MEALS",
                "date": datetime.utcnow().isoformat(),
            }
        )
        assert response.status_code == 201
        expense3 = response.json()
        assert expense3["auto_approved"] == False, \
            "Third expense should NOT auto-approve (would exceed daily limit)"

    def test_policy_can_be_disabled(self, client, admin_org_headers, test_admin, db_session):
        """Test that disabled policies don't auto-approve"""
        # Create active policy
        policy_data = {
            "name": "Test policy",
            "priority": 100,
            "auto_approve": True,
            "is_active": True,
            "require_receipt": False,
            "max_amount_per_expense": 50.00,
            "conditions": {"categories": ["MEALS"]}
        }

        response = client.post(
            "/api/v1/approval-policies",
            headers=admin_org_headers,
            json=policy_data
        )
        assert response.status_code == 201
        policy_id = response.json()["id"]

        # Submit expense - should auto-approve
        response = client.post(
            "/api/v1/expenses",
            headers=admin_org_headers,
            json={
                "amount": 25.00,
                "vendor": "Coffee",
                "description": "Coffee",
                "category": "MEALS",
                "date": datetime.utcnow().isoformat(),
            }
        )
        assert response.status_code == 201
        expense1 = response.json()
        assert expense1["auto_approved"] == True

        # Disable the policy
        response = client.patch(
            f"/api/v1/approval-policies/{policy_id}",
            headers=admin_org_headers,
            json={"is_active": False}
        )
        assert response.status_code == 200

        # Submit another expense - should NOT auto-approve (policy disabled)
        response = client.post(
            "/api/v1/expenses",
            headers=admin_org_headers,
            json={
                "amount": 30.00,
                "vendor": "Tea Shop",
                "description": "Afternoon tea",
                "category": "MEALS",
                "date": datetime.utcnow().isoformat(),
            }
        )
        assert response.status_code == 201
        expense2 = response.json()
        assert expense2["auto_approved"] == False, \
            "Should NOT auto-approve when policy is disabled"

    def test_no_policies_results_in_manual_approval(self, client, admin_org_headers, test_admin, db_session):
        """Test that expenses require manual approval when no policies exist"""
        response = client.post(
            "/api/v1/expenses",
            headers=admin_org_headers,
            json={
                "amount": 10.00,
                "vendor": "Test",
                "description": "Test",
                "category": "MEALS",
                "date": datetime.utcnow().isoformat(),
            }
        )

        assert response.status_code == 201
        expense = response.json()
        assert expense["auto_approved"] == False
        assert expense["status"] == "pending"
        assert "manual approval" in expense.get("message", "").lower()


class TestApprovalPolicyAPI:
    """Test approval policy CRUD operations"""

    def test_create_approval_policy_as_admin(self, client, admin_org_headers):
        """Test that admins can create approval policies"""
        policy_data = {
            "name": "Test Policy",
            "description": "Test description",
            "priority": 50,
            "auto_approve": True,
            "require_receipt": True,
            "notify_on_auto_approve": True,
            "max_amount_per_expense": 100.00,
            "daily_limit_per_user": 500.00,
            "conditions": {
                "categories": ["MEALS", "TRAVEL"],
                "min_amount": 5.00
            }
        }

        response = client.post(
            "/api/v1/approval-policies",
            headers=admin_org_headers,
            json=policy_data
        )

        assert response.status_code == 201
        policy = response.json()
        assert policy["name"] == "Test Policy"
        assert policy["auto_approve"] == True
        assert policy["priority"] == 50
        assert "id" in policy

    def test_list_approval_policies(self, client, admin_org_headers):
        """Test listing approval policies"""
        # Create a policy first
        policy_data = {
            "name": "Test Policy",
            "priority": 100,
            "auto_approve": True,
            "require_receipt": False,
            "max_amount_per_expense": 50.00
        }

        create_response = client.post(
            "/api/v1/approval-policies",
            headers=admin_org_headers,
            json=policy_data
        )
        assert create_response.status_code == 201

        # List policies
        response = client.get(
            "/api/v1/approval-policies",
            headers=admin_org_headers
        )

        assert response.status_code == 200
        policies = response.json()
        assert isinstance(policies, list)
        assert len(policies) >= 1
        assert policies[0]["name"] == "Test Policy"

    def test_update_approval_policy(self, client, admin_org_headers):
        """Test updating an approval policy"""
        # Create policy
        policy_data = {
            "name": "Original Name",
            "priority": 100,
            "auto_approve": True,
            "require_receipt": False,
            "max_amount_per_expense": 50.00
        }

        create_response = client.post(
            "/api/v1/approval-policies",
            headers=admin_org_headers,
            json=policy_data
        )
        assert create_response.status_code == 201
        policy_id = create_response.json()["id"]

        # Update policy
        update_data = {
            "name": "Updated Name",
            "max_amount_per_expense": 75.00
        }

        update_response = client.patch(
            f"/api/v1/approval-policies/{policy_id}",
            headers=admin_org_headers,
            json=update_data
        )

        assert update_response.status_code == 200
        updated_policy = update_response.json()
        assert updated_policy["name"] == "Updated Name"
        assert updated_policy["limits"]["max_amount_per_expense"] == 75.00

    def test_delete_approval_policy(self, client, admin_org_headers):
        """Test deleting an approval policy"""
        # Create policy
        policy_data = {
            "name": "To Delete",
            "priority": 100,
            "auto_approve": True,
            "require_receipt": False,
            "max_amount_per_expense": 50.00
        }

        create_response = client.post(
            "/api/v1/approval-policies",
            headers=admin_org_headers,
            json=policy_data
        )
        assert create_response.status_code == 201
        policy_id = create_response.json()["id"]

        # Delete policy
        delete_response = client.delete(
            f"/api/v1/approval-policies/{policy_id}",
            headers=admin_org_headers
        )

        assert delete_response.status_code == 204 or delete_response.status_code == 200

        # Verify it's gone
        get_response = client.get(
            f"/api/v1/approval-policies/{policy_id}",
            headers=admin_org_headers
        )
        assert get_response.status_code == 404
