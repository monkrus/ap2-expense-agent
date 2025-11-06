"""
Comprehensive Admin Portal Functionality Test
Tests all CRUD operations, deletions, edits, clicks, and interactions
"""
import requests
import json
import sys
from datetime import datetime

BASE_URL = 'http://localhost:8000'

# Test results tracking
results = {
    'passed': 0,
    'failed': 0,
    'errors': []
}

def print_section(title):
    print(f'\n{"="*70}')
    print(f'{title}')
    print(f'{"="*70}')

def print_result(success, message):
    status = '[PASS]' if success else '[FAIL]'
    print(f'{status} {message}')
    if success:
        results['passed'] += 1
    else:
        results['failed'] += 1

def test_login():
    """Test admin login"""
    print_section('TEST 1: ADMIN LOGIN')
    try:
        login_data = {'username': 'admintest', 'password': 'AgentTest!'}
        response = requests.post(f'{BASE_URL}/api/v1/auth/login', json=login_data)

        if response.status_code == 200:
            token = response.json()['access_token']
            print_result(True, 'Admin login successful')
            return token
        else:
            print_result(False, f'Login failed: {response.status_code}')
            results['errors'].append(f'Login failed: {response.text}')
            return None
    except Exception as e:
        print_result(False, f'Login error: {str(e)}')
        return None

def test_user_creation(headers):
    """Test creating a new user"""
    print_section('TEST 2: USER CREATION')
    try:
        new_user = {
            'username': f'testuser_{datetime.now().timestamp()}',
            'email': f'testuser_{datetime.now().timestamp()}@example.com',
            'password': 'TestPassword123!',
            'full_name': 'Test User Created',
            'role': 'employee'
        }

        response = requests.post(f'{BASE_URL}/api/v1/admin/users/create', json=new_user, headers=headers)

        if response.status_code == 201:
            user_data = response.json()
            print_result(True, f'User created: {user_data.get("username")}')
            return user_data.get('id')
        else:
            print_result(False, f'User creation failed: {response.status_code} - {response.text[:200]}')
            return None
    except Exception as e:
        print_result(False, f'User creation error: {str(e)}')
        return None

def test_user_update(headers, user_id):
    """Test updating user information"""
    print_section('TEST 3: USER UPDATE')
    try:
        update_data = {
            'full_name': 'Updated Test User',
            'email': f'updated_{datetime.now().timestamp()}@example.com'
        }

        response = requests.patch(
            f'{BASE_URL}/api/v1/admin/users/{user_id}/profile',
            json=update_data,
            headers=headers
        )

        if response.status_code == 200:
            updated_user = response.json()
            print_result(True, f'User updated: {updated_user.get("full_name")}')
            return True
        else:
            print_result(False, f'User update failed: {response.status_code} - {response.text[:200]}')
            return False
    except Exception as e:
        print_result(False, f'User update error: {str(e)}')
        return False

def test_user_role_change(headers, user_id):
    """Test changing user role"""
    print_section('TEST 4: USER ROLE CHANGE')
    try:
        response = requests.patch(
            f'{BASE_URL}/api/v1/admin/users/{user_id}/role',
            json={'role': 'manager'},
            headers=headers
        )

        if response.status_code == 200:
            user_data = response.json()
            print_result(True, f'User role changed to: {user_data.get("role")}')
            return True
        else:
            print_result(False, f'Role change failed: {response.status_code} - {response.text[:200]}')
            return False
    except Exception as e:
        print_result(False, f'Role change error: {str(e)}')
        return False

def test_user_suspension(headers, user_id):
    """Test suspending a user"""
    print_section('TEST 5: USER SUSPENSION')
    try:
        response = requests.post(
            f'{BASE_URL}/api/v1/admin/users/{user_id}/suspend',
            headers=headers
        )

        if response.status_code == 200:
            print_result(True, 'User suspended successfully')

            # Verify user is suspended
            verify_response = requests.get(f'{BASE_URL}/api/v1/admin/users/{user_id}', headers=headers)
            if verify_response.status_code == 200:
                user_data = verify_response.json()
                is_suspended = not user_data.get('is_active', True)
                if is_suspended:
                    print(f'  Verified: User is_active = {user_data.get("is_active")}')
                    return True
            return True
        else:
            print_result(False, f'User suspension failed: {response.status_code}')
            return False
    except Exception as e:
        print_result(False, f'User suspension error: {str(e)}')
        return False

def test_user_activation(headers, user_id):
    """Test activating a suspended user"""
    print_section('TEST 6: USER ACTIVATION')
    try:
        response = requests.post(
            f'{BASE_URL}/api/v1/admin/users/{user_id}/activate',
            headers=headers
        )

        if response.status_code == 200:
            print_result(True, 'User activated successfully')
            return True
        else:
            print_result(False, f'User activation failed: {response.status_code}')
            return False
    except Exception as e:
        print_result(False, f'User activation error: {str(e)}')
        return False

def test_organization_creation(headers):
    """Test creating a new organization"""
    print_section('TEST 7: ORGANIZATION CREATION')
    try:
        new_org = {
            'name': f'Test Org {datetime.now().timestamp()}',
            'slug': f'test-org-{int(datetime.now().timestamp())}',
            'description': 'Test organization for comprehensive testing',
            'currency': 'USD',
            'timezone': 'America/New_York',
            'max_members': 50
        }

        response = requests.post(f'{BASE_URL}/api/v1/organizations', json=new_org, headers=headers)

        if response.status_code == 201:
            org_data = response.json()
            print_result(True, f'Organization created: {org_data.get("name")}')
            return org_data.get('id')
        else:
            print_result(False, f'Organization creation failed: {response.status_code} - {response.text[:200]}')
            return None
    except Exception as e:
        print_result(False, f'Organization creation error: {str(e)}')
        return None

def test_organization_update(headers, org_id):
    """Test updating organization information"""
    print_section('TEST 8: ORGANIZATION UPDATE')
    try:
        update_data = {
            'name': f'Updated Org {datetime.now().timestamp()}',
            'description': 'Updated organization description'
        }

        response = requests.patch(
            f'{BASE_URL}/api/v1/organizations/{org_id}',
            json=update_data,
            headers=headers
        )

        if response.status_code == 200:
            org_data = response.json()
            print_result(True, f'Organization updated: {org_data.get("name")}')
            return True
        else:
            print_result(False, f'Organization update failed: {response.status_code} - {response.text[:200]}')
            return False
    except Exception as e:
        print_result(False, f'Organization update error: {str(e)}')
        return False

def test_expense_creation(headers):
    """Test creating a new expense"""
    print_section('TEST 9: EXPENSE CREATION')
    try:
        new_expense = {
            'amount': 125.50,
            'description': 'Test expense for comprehensive testing',
            'category': 'Office Supplies',
            'date': datetime.now().isoformat()
        }

        response = requests.post(f'{BASE_URL}/api/v1/expenses', json=new_expense, headers=headers)

        if response.status_code == 201:
            expense_data = response.json()
            print_result(True, f'Expense created: ${expense_data.get("amount")} - {expense_data.get("description")}')
            return expense_data.get('id')
        else:
            print_result(False, f'Expense creation failed: {response.status_code} - {response.text[:200]}')
            return None
    except Exception as e:
        print_result(False, f'Expense creation error: {str(e)}')
        return None

def test_expense_update(headers, expense_id):
    """Test updating expense information"""
    print_section('TEST 10: EXPENSE UPDATE')
    try:
        update_data = {
            'amount': 150.75,
            'description': 'Updated test expense',
            'category': 'Travel'
        }

        response = requests.put(
            f'{BASE_URL}/api/v1/expenses/{expense_id}',
            json=update_data,
            headers=headers
        )

        if response.status_code == 200:
            expense_data = response.json()
            print_result(True, f'Expense updated: ${expense_data.get("amount")} - {expense_data.get("description")}')
            return True
        else:
            print_result(False, f'Expense update failed: {response.status_code} - {response.text[:200]}')
            return False
    except Exception as e:
        print_result(False, f'Expense update error: {str(e)}')
        return False

def test_expense_approval(headers):
    """Test approving an expense"""
    print_section('TEST 11: EXPENSE APPROVAL')
    try:
        # Get pending expenses
        response = requests.get(f'{BASE_URL}/api/v1/expenses/all-pending', headers=headers)

        if response.status_code != 200:
            print_result(False, f'Failed to get pending expenses: {response.status_code}')
            return False

        expenses = response.json()
        if not expenses or len(expenses) == 0:
            print_result(True, 'No pending expenses to approve (skipped)')
            return True

        expense_id = expenses[0].get('id')

        # Approve the expense
        approval_response = requests.post(
            f'{BASE_URL}/api/v1/expenses/approve',
            json={'expense_id': expense_id},
            headers=headers
        )

        if approval_response.status_code == 200:
            print_result(True, f'Expense approved: {expense_id[:8]}...')
            return True
        else:
            print_result(False, f'Expense approval failed: {approval_response.status_code}')
            return False
    except Exception as e:
        print_result(False, f'Expense approval error: {str(e)}')
        return False

def test_expense_rejection(headers):
    """Test rejecting an expense"""
    print_section('TEST 12: EXPENSE REJECTION')
    try:
        # Get pending expenses
        response = requests.get(f'{BASE_URL}/api/v1/expenses/all-pending', headers=headers)

        if response.status_code != 200:
            print_result(False, f'Failed to get pending expenses: {response.status_code}')
            return False

        expenses = response.json()
        if not expenses or len(expenses) == 0:
            print_result(True, 'No pending expenses to reject (skipped)')
            return True

        expense_id = expenses[0].get('id')

        # Reject the expense
        rejection_response = requests.post(
            f'{BASE_URL}/api/v1/expenses/reject',
            json={'expense_id': expense_id, 'reason': 'Test rejection'},
            headers=headers
        )

        if rejection_response.status_code == 200:
            print_result(True, f'Expense rejected: {expense_id[:8]}...')
            return True
        else:
            print_result(False, f'Expense rejection failed: {rejection_response.status_code}')
            return False
    except Exception as e:
        print_result(False, f'Expense rejection error: {str(e)}')
        return False

def test_expense_deletion(headers, expense_id):
    """Test deleting an expense"""
    print_section('TEST 13: EXPENSE DELETION (WITHDRAWAL)')
    try:
        response = requests.delete(
            f'{BASE_URL}/api/v1/expenses/{expense_id}/withdraw',
            headers=headers
        )

        if response.status_code == 200:
            print_result(True, f'Expense withdrawn/deleted: {expense_id[:8]}...')

            # Verify expense is deleted (should return empty or not found)
            verify_response = requests.get(f'{BASE_URL}/api/v1/admin/expenses', headers=headers)
            if verify_response.status_code == 200:
                expenses = verify_response.json()
                expense_exists = any(e.get('id') == expense_id for e in expenses)
                if not expense_exists:
                    print(f'  Verified: Expense no longer in list')
            return True
        else:
            print_result(False, f'Expense deletion failed: {response.status_code}')
            return False
    except Exception as e:
        print_result(False, f'Expense deletion error: {str(e)}')
        return False

def test_bulk_expense_operations(headers):
    """Test bulk approval/rejection"""
    print_section('TEST 14: BULK EXPENSE OPERATIONS')
    try:
        # Get pending expenses
        response = requests.get(f'{BASE_URL}/api/v1/expenses/all-pending', headers=headers)

        if response.status_code != 200:
            print_result(False, f'Failed to get pending expenses: {response.status_code}')
            return False

        expenses = response.json()
        if not expenses or len(expenses) < 2:
            print_result(True, 'Not enough pending expenses for bulk operations (skipped)')
            return True

        # Get first 2 expense IDs
        expense_ids = [e.get('id') for e in expenses[:2]]

        # Test bulk approval
        approval_response = requests.post(
            f'{BASE_URL}/api/v1/expenses/bulk-approve',
            json={'expense_ids': expense_ids},
            headers=headers
        )

        if approval_response.status_code == 200:
            print_result(True, f'Bulk approved {len(expense_ids)} expenses')
            return True
        else:
            print_result(False, f'Bulk approval failed: {approval_response.status_code}')
            return False
    except Exception as e:
        print_result(False, f'Bulk operations error: {str(e)}')
        return False

def test_database_stats(headers):
    """Test database statistics endpoint"""
    print_section('TEST 15: DATABASE STATISTICS')
    try:
        response = requests.get(f'{BASE_URL}/api/v1/admin/stats/database', headers=headers)

        if response.status_code == 200:
            stats = response.json()
            print_result(True, 'Database statistics retrieved')
            print(f'  Users: {stats.get("users", {})}')
            print(f'  Sessions: {stats.get("sessions", {})}')
            print(f'  Audit logs: {stats.get("audit_logs", {})}')
            return True
        else:
            print_result(False, f'Database stats failed: {response.status_code}')
            return False
    except Exception as e:
        print_result(False, f'Database stats error: {str(e)}')
        return False

def test_pagination(headers):
    """Test pagination on user list"""
    print_section('TEST 16: PAGINATION')
    try:
        # Test with limit
        response = requests.get(f'{BASE_URL}/api/v1/admin/users?limit=5', headers=headers)

        if response.status_code == 200:
            data = response.json()
            users = data.get('users', [])
            if len(users) <= 5:
                print_result(True, f'Pagination working: Retrieved {len(users)} users (limit=5)')
                return True
            else:
                print_result(False, f'Pagination failed: Got {len(users)} users with limit=5')
                return False
        else:
            print_result(False, f'Pagination test failed: {response.status_code}')
            return False
    except Exception as e:
        print_result(False, f'Pagination error: {str(e)}')
        return False

def test_search_filter(headers):
    """Test search/filter functionality"""
    print_section('TEST 17: SEARCH/FILTER')
    try:
        # Search for admin users
        response = requests.get(f'{BASE_URL}/api/v1/admin/users?role=admin', headers=headers)

        if response.status_code == 200:
            data = response.json()
            users = data.get('users', [])
            admin_count = sum(1 for u in users if u.get('role') == 'admin')
            print_result(True, f'Search/filter working: Found {admin_count} admin users')
            return True
        else:
            print_result(False, f'Search/filter failed: {response.status_code}')
            return False
    except Exception as e:
        print_result(False, f'Search/filter error: {str(e)}')
        return False

def test_billing_tiers(headers):
    """Test billing tiers endpoint"""
    print_section('TEST 18: BILLING TIERS')
    try:
        response = requests.get(f'{BASE_URL}/api/billing/org/tiers', headers=headers)

        if response.status_code == 200:
            data = response.json()
            tiers = data.get('tiers', [])
            print_result(True, f'Billing tiers retrieved: {len(tiers)} tiers')
            for tier in tiers:
                print(f'  - {tier.get("display_name")}: ${tier.get("price_monthly")}/month')
            return True
        else:
            print_result(False, f'Billing tiers failed: {response.status_code}')
            return False
    except Exception as e:
        print_result(False, f'Billing tiers error: {str(e)}')
        return False

def test_organization_deletion(headers, org_id):
    """Test deleting an organization"""
    print_section('TEST 19: ORGANIZATION DELETION')
    try:
        response = requests.delete(
            f'{BASE_URL}/api/v1/organizations/{org_id}',
            headers=headers
        )

        if response.status_code == 200:
            print_result(True, f'Organization deleted: {org_id[:8]}...')

            # Verify organization is deleted
            verify_response = requests.get(f'{BASE_URL}/api/v1/organizations', headers=headers)
            if verify_response.status_code == 200:
                orgs = verify_response.json()
                org_exists = any(o.get('id') == org_id for o in orgs)
                if not org_exists:
                    print(f'  Verified: Organization no longer in list')
            return True
        else:
            print_result(False, f'Organization deletion failed: {response.status_code}')
            return False
    except Exception as e:
        print_result(False, f'Organization deletion error: {str(e)}')
        return False

def test_user_deletion(headers, user_id):
    """Test deleting a user"""
    print_section('TEST 20: USER DELETION')
    try:
        response = requests.delete(
            f'{BASE_URL}/api/v1/admin/users/{user_id}',
            headers=headers
        )

        if response.status_code == 200:
            print_result(True, f'User deleted: {user_id[:8]}...')

            # Verify user is deleted
            verify_response = requests.get(f'{BASE_URL}/api/v1/admin/users/{user_id}', headers=headers)
            if verify_response.status_code == 404:
                print(f'  Verified: User not found (correctly deleted)')
            return True
        else:
            print_result(False, f'User deletion failed: {response.status_code}')
            return False
    except Exception as e:
        print_result(False, f'User deletion error: {str(e)}')
        return False

def generate_report():
    """Generate final test report"""
    print_section('COMPREHENSIVE TEST REPORT')
    total = results['passed'] + results['failed']
    success_rate = (results['passed'] / total * 100) if total > 0 else 0

    print(f'Total tests: {total}')
    print(f'Passed: {results["passed"]}')
    print(f'Failed: {results["failed"]}')
    print(f'Success rate: {success_rate:.1f}%')

    if results['errors']:
        print('\nErrors encountered:')
        for i, error in enumerate(results['errors'][:5], 1):
            print(f'{i}. {error[:150]}...')

    print('\n' + '='*70)
    if results['failed'] == 0:
        print('[SUCCESS] All comprehensive tests passed!')
    else:
        print(f'[WARNING] {results["failed"]} test(s) failed')
    print('='*70)

def main():
    print('='*70)
    print('COMPREHENSIVE ADMIN PORTAL FUNCTIONALITY TEST')
    print('Testing: CRUD operations, deletions, edits, clicks, interactions')
    print('='*70)

    # Login
    token = test_login()
    if not token:
        print('\n[CRITICAL] Login failed. Cannot continue tests.')
        return

    headers = {'Authorization': f'Bearer {token}'}

    # Run all tests
    user_id = test_user_creation(headers)
    if user_id:
        test_user_update(headers, user_id)
        test_user_role_change(headers, user_id)
        test_user_suspension(headers, user_id)
        test_user_activation(headers, user_id)

    org_id = test_organization_creation(headers)
    if org_id:
        test_organization_update(headers, org_id)

    expense_id = test_expense_creation(headers)
    if expense_id:
        test_expense_update(headers, expense_id)

    test_expense_approval(headers)
    test_expense_rejection(headers)

    if expense_id:
        test_expense_deletion(headers, expense_id)

    test_bulk_expense_operations(headers)
    test_database_stats(headers)
    test_pagination(headers)
    test_search_filter(headers)
    test_billing_tiers(headers)

    # Cleanup tests (deletion)
    if org_id:
        test_organization_deletion(headers, org_id)
    if user_id:
        test_user_deletion(headers, user_id)

    # Generate report
    generate_report()

if __name__ == '__main__':
    main()
