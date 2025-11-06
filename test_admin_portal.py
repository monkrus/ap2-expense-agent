"""
Comprehensive Admin Portal Test Suite
Tests all admin functionality including dashboard, user management, expenses, billing, etc.
"""
import requests
import json
import sys

# Base URL
BASE_URL = 'http://localhost:8000'

def print_section(title):
    print(f'\n{"="*60}')
    print(f'{title}')
    print(f'{"="*60}')

def print_result(success, message):
    status = '[PASS]' if success else '[FAIL]'
    print(f'{status} {message}')

# Results tracking
results = {
    'passed': 0,
    'failed': 0,
    'errors': []
}

def test_login():
    """Test admin login"""
    print_section('TEST 1: ADMIN LOGIN')
    try:
        login_data = {'username': 'admintest', 'password': 'AgentTest!'}
        response = requests.post(f'{BASE_URL}/api/v1/auth/login', json=login_data)

        if response.status_code == 200:
            token = response.json()['access_token']
            user_data = response.json()
            print_result(True, 'Admin login successful')
            print(f'  User: {user_data.get("username")}')
            print(f'  Role: {user_data.get("role")}')
            results['passed'] += 1
            return token
        else:
            print_result(False, f'Login failed with status {response.status_code}')
            results['failed'] += 1
            results['errors'].append(f'Login failed: {response.text}')
            return None
    except Exception as e:
        print_result(False, f'Login error: {str(e)}')
        results['failed'] += 1
        results['errors'].append(f'Login exception: {str(e)}')
        return None

def test_dashboard_stats(headers):
    """Test dashboard statistics"""
    print_section('TEST 2: DASHBOARD STATISTICS')
    try:
        response = requests.get(f'{BASE_URL}/api/v1/admin/dashboard/stats', headers=headers)

        if response.status_code == 200:
            data = response.json()
            print_result(True, 'Dashboard stats loaded')
            print(f'  Total users: {data.get("total_users", 0)}')
            print(f'  Active users (30d): {data.get("active_users_30d", 0)}')
            print(f'  New users (7d): {data.get("new_users_7d", 0)}')
            print(f'  Total organizations: {data.get("total_organizations", 0)}')
            print(f'  Active organizations: {data.get("active_organizations", 0)}')
            print(f'  Total expenses: {data.get("total_expenses", 0)}')
            print(f'  Total expense amount: ${data.get("total_expense_amount", 0):.2f}')
            print(f'  Expenses this month: {data.get("expenses_this_month", 0)}')
            print(f'  Active subscriptions: {data.get("active_subscriptions", 0)}')
            results['passed'] += 1
            return True
        else:
            print_result(False, f'Dashboard stats failed: {response.status_code}')
            print(f'  Response: {response.text[:200]}')
            results['failed'] += 1
            results['errors'].append(f'Dashboard stats failed: {response.text}')
            return False
    except Exception as e:
        print_result(False, f'Dashboard stats error: {str(e)}')
        results['failed'] += 1
        results['errors'].append(f'Dashboard stats exception: {str(e)}')
        return False

def test_user_list(headers):
    """Test user listing"""
    print_section('TEST 3: USER MANAGEMENT - LIST USERS')
    try:
        response = requests.get(f'{BASE_URL}/api/v1/admin/users', headers=headers)

        if response.status_code == 200:
            data = response.json()
            users = data.get('users', [])
            print_result(True, f'User list loaded: {len(users)} users found')

            # Show first 5 users
            for i, user in enumerate(users[:5]):
                print(f'  {i+1}. {user.get("username")} - {user.get("email")} ({user.get("role")})')

            results['passed'] += 1
            return True, users
        else:
            print_result(False, f'User list failed: {response.status_code}')
            results['failed'] += 1
            results['errors'].append(f'User list failed: {response.text}')
            return False, []
    except Exception as e:
        print_result(False, f'User list error: {str(e)}')
        results['failed'] += 1
        results['errors'].append(f'User list exception: {str(e)}')
        return False, []

def test_user_details(headers, user_id):
    """Test getting user details"""
    print_section('TEST 4: USER MANAGEMENT - GET USER DETAILS')
    try:
        response = requests.get(f'{BASE_URL}/api/v1/admin/users/{user_id}', headers=headers)

        if response.status_code == 200:
            user = response.json()
            print_result(True, 'User details loaded')
            print(f'  ID: {user.get("id")}')
            print(f'  Username: {user.get("username")}')
            print(f'  Email: {user.get("email")}')
            print(f'  Role: {user.get("role")}')
            print(f'  Active: {user.get("is_active")}')
            print(f'  Verified: {user.get("is_verified")}')
            results['passed'] += 1
            return True
        else:
            print_result(False, f'User details failed: {response.status_code}')
            results['failed'] += 1
            return False
    except Exception as e:
        print_result(False, f'User details error: {str(e)}')
        results['failed'] += 1
        return False

def test_expenses_list(headers):
    """Test expense listing"""
    print_section('TEST 5: EXPENSE MANAGEMENT - LIST EXPENSES')
    try:
        response = requests.get(f'{BASE_URL}/api/v1/admin/expenses', headers=headers)

        if response.status_code == 200:
            data = response.json()
            expenses = data if isinstance(data, list) else data.get('expenses', [])
            print_result(True, f'Expense list loaded: {len(expenses)} expenses found')

            # Show first 5 expenses
            for i, expense in enumerate(expenses[:5]):
                print(f'  {i+1}. ${expense.get("amount", 0):.2f} - {expense.get("description", "N/A")} ({expense.get("status", "unknown")})')

            results['passed'] += 1
            return True, expenses
        else:
            print_result(False, f'Expense list failed: {response.status_code}')
            results['failed'] += 1
            results['errors'].append(f'Expense list failed: {response.text}')
            return False, []
    except Exception as e:
        print_result(False, f'Expense list error: {str(e)}')
        results['failed'] += 1
        results['errors'].append(f'Expense list exception: {str(e)}')
        return False, []

def test_organizations(headers):
    """Test organization listing"""
    print_section('TEST 6: ORGANIZATION MANAGEMENT')
    try:
        response = requests.get(f'{BASE_URL}/api/v1/organizations', headers=headers)

        if response.status_code == 200:
            orgs = response.json()
            print_result(True, f'Organization list loaded: {len(orgs)} organizations')

            for i, org in enumerate(orgs[:5]):
                print(f'  {i+1}. {org.get("name")} - {"Active" if org.get("is_active") else "Inactive"}')

            results['passed'] += 1
            return True
        else:
            print_result(False, f'Organization list failed: {response.status_code}')
            results['failed'] += 1
            return False
    except Exception as e:
        print_result(False, f'Organization list error: {str(e)}')
        results['failed'] += 1
        return False

def test_billing_tiers(headers):
    """Test billing tiers"""
    print_section('TEST 7: BILLING - TIERS')
    try:
        response = requests.get(f'{BASE_URL}/api/billing/org/tiers', headers=headers)

        if response.status_code == 200:
            data = response.json()
            tiers = data.get('tiers', [])
            print_result(True, f'Billing tiers loaded: {len(tiers)} tiers')

            for tier in tiers:
                print(f'  - {tier.get("display_name", tier.get("tier"))} - ${tier.get("price_monthly", 0)}/month')

            results['passed'] += 1
            return True
        else:
            print_result(False, f'Billing tiers failed: {response.status_code}')
            results['failed'] += 1
            return False
    except Exception as e:
        print_result(False, f'Billing tiers error: {str(e)}')
        results['failed'] += 1
        return False

def test_subscription_status(headers):
    """Test subscription status"""
    print_section('TEST 8: BILLING - SUBSCRIPTION STATUS')
    try:
        response = requests.get(f'{BASE_URL}/api/billing/org/subscription', headers=headers)

        if response.status_code == 200:
            data = response.json()
            print_result(True, 'Subscription status loaded')
            print(f'  Has subscription: {data.get("has_subscription", False)}')
            if data.get('has_subscription'):
                print(f'  Tier: {data.get("tier", "N/A")}')
                print(f'  Status: {data.get("status", "N/A")}')
            results['passed'] += 1
            return True
        else:
            print_result(False, f'Subscription status failed: {response.status_code}')
            results['failed'] += 1
            return False
    except Exception as e:
        print_result(False, f'Subscription status error: {str(e)}')
        results['failed'] += 1
        return False

def test_system_health(headers):
    """Test system health"""
    print_section('TEST 9: SYSTEM HEALTH')
    try:
        response = requests.get(f'{BASE_URL}/api/v1/admin/system/health', headers=headers)

        if response.status_code == 200:
            data = response.json()
            print_result(True, 'System health check passed')
            print(f'  Status: {data.get("status", "unknown")}')
            print(f'  Database: {data.get("database", "unknown")}')
            results['passed'] += 1
            return True
        else:
            print_result(False, f'System health failed: {response.status_code}')
            results['failed'] += 1
            return False
    except Exception as e:
        print_result(False, f'System health error: {str(e)}')
        results['failed'] += 1
        return False

def test_database_stats(headers):
    """Test database statistics"""
    print_section('TEST 10: DATABASE STATISTICS')
    try:
        response = requests.get(f'{BASE_URL}/api/v1/admin/stats/database', headers=headers)

        if response.status_code == 200:
            data = response.json()
            print_result(True, 'Database stats loaded')
            for table, count in data.items():
                print(f'  {table}: {count}')
            results['passed'] += 1
            return True
        else:
            print_result(False, f'Database stats failed: {response.status_code}')
            results['failed'] += 1
            return False
    except Exception as e:
        print_result(False, f'Database stats error: {str(e)}')
        results['failed'] += 1
        return False

def generate_report():
    """Generate final test report"""
    print_section('TEST REPORT SUMMARY')
    total = results['passed'] + results['failed']
    success_rate = (results['passed'] / total * 100) if total > 0 else 0

    print(f'Total tests: {total}')
    print(f'Passed: {results["passed"]}')
    print(f'Failed: {results["failed"]}')
    print(f'Success rate: {success_rate:.1f}%')

    if results['errors']:
        print('\nErrors encountered:')
        for i, error in enumerate(results['errors'], 1):
            print(f'{i}. {error[:100]}...')

    print('\n' + '='*60)
    if results['failed'] == 0:
        print('[SUCCESS] All tests passed!')
    else:
        print(f'[WARNING] {results["failed"]} test(s) failed')
    print('='*60)

def main():
    print('='*60)
    print('ADMIN PORTAL COMPREHENSIVE TEST SUITE')
    print('='*60)

    # Test login
    token = test_login()
    if not token:
        print('\n[CRITICAL] Login failed. Cannot continue tests.')
        return

    headers = {'Authorization': f'Bearer {token}'}

    # Run all tests
    test_dashboard_stats(headers)
    success, users = test_user_list(headers)
    if success and users:
        test_user_details(headers, users[0]['id'])

    test_expenses_list(headers)
    test_organizations(headers)
    test_billing_tiers(headers)
    test_subscription_status(headers)
    test_system_health(headers)
    test_database_stats(headers)

    # Generate report
    generate_report()

if __name__ == '__main__':
    main()
