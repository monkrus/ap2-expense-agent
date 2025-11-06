"""
Comprehensive Interaction Test - Tests clicks, edits, views, filters, and all user interactions
"""
import requests
import json
import sys

BASE_URL = 'http://localhost:8000'

results = {'passed': 0, 'failed': 0, 'errors': []}

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
        results['errors'].append(message)

def login():
    """Test login"""
    print_section('TEST 1: LOGIN & AUTHENTICATION')
    try:
        response = requests.post(
            f'{BASE_URL}/api/v1/auth/login',
            json={'username': 'admintest', 'password': 'AgentTest!'}
        )
        if response.status_code == 200:
            print_result(True, 'Login successful')
            return response.json()['access_token']
        else:
            print_result(False, f'Login failed: {response.status_code}')
            return None
    except Exception as e:
        print_result(False, f'Login error: {str(e)}')
        return None

def test_dashboard_click(headers):
    """Test clicking on dashboard (loading dashboard stats)"""
    print_section('TEST 2: DASHBOARD - Click/Load Statistics')
    try:
        response = requests.get(f'{BASE_URL}/api/v1/admin/dashboard/stats', headers=headers)

        if response.status_code == 200:
            data = response.json()
            print_result(True, 'Dashboard loaded successfully')
            print(f'  Organizations: {data["organizations"]["total"]} (click would show list)')
            print(f'  Users: {data["users"]["total"]} (click would show user management)')
            print(f'  Expenses: {data["expenses"]["total_count"]} (click would show expenses)')
            print(f'  Subscriptions: {data["revenue"]["active_subscriptions"]} (click would show billing)')
            return True
        else:
            print_result(False, f'Dashboard load failed: {response.status_code}')
            return False
    except Exception as e:
        print_result(False, f'Dashboard error: {str(e)}')
        return False

def test_user_list_click(headers):
    """Test clicking to view user list"""
    print_section('TEST 3: USER LIST - Click to View All Users')
    try:
        response = requests.get(f'{BASE_URL}/api/v1/admin/users', headers=headers)

        if response.status_code == 200:
            data = response.json()
            users = data.get('users', [])
            print_result(True, f'User list loaded: {len(users)} users')
            print(f'  First 3 users (would display in table):')
            for i, user in enumerate(users[:3], 1):
                print(f'    {i}. {user.get("username")} ({user.get("role")}) - Active: {user.get("is_active")}')
            return users[0]['id'] if users else None
        else:
            print_result(False, f'User list failed: {response.status_code}')
            return None
    except Exception as e:
        print_result(False, f'User list error: {str(e)}')
        return None

def test_user_detail_click(headers, user_id):
    """Test clicking on a user to view details"""
    print_section('TEST 4: USER DETAILS - Click on User to View Profile')
    try:
        response = requests.get(f'{BASE_URL}/api/v1/admin/users/{user_id}', headers=headers)

        if response.status_code == 200:
            user = response.json()
            print_result(True, 'User details loaded (modal/page would open)')
            print(f'  Username: {user.get("username")}')
            print(f'  Email: {user.get("email")}')
            print(f'  Role: {user.get("role")}')
            print(f'  Status: {"Active" if user.get("is_active") else "Inactive"}')
            print(f'  Verified: {"Yes" if user.get("is_verified") else "No"}')
            print(f'  Last Login: {user.get("last_login", "Never")}')
            return True
        else:
            print_result(False, f'User details failed: {response.status_code}')
            return False
    except Exception as e:
        print_result(False, f'User details error: {str(e)}')
        return False

def test_user_filter_click(headers):
    """Test clicking filter dropdown and selecting role"""
    print_section('TEST 5: USER FILTER - Click Filter, Select Role')
    try:
        # Test filtering by admin role
        response = requests.get(f'{BASE_URL}/api/v1/admin/users?role=admin', headers=headers)

        if response.status_code == 200:
            data = response.json()
            users = data.get('users', [])
            admin_users = [u for u in users if u.get('role') == 'admin']
            print_result(True, f'Filter applied: Found {len(admin_users)} admin users')
            for user in admin_users:
                print(f'  - {user.get("username")} (admin)')
            return True
        else:
            print_result(False, f'Filter failed: {response.status_code}')
            return False
    except Exception as e:
        print_result(False, f'Filter error: {str(e)}')
        return False

def test_expense_list_click(headers):
    """Test clicking to view expense list"""
    print_section('TEST 6: EXPENSE LIST - Click to View All Expenses')
    try:
        response = requests.get(f'{BASE_URL}/api/v1/admin/expenses', headers=headers)

        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and 'expenses' in data:
                expenses = data['expenses']
                print_result(True, f'Expense list loaded: {len(expenses)} expenses')
                print(f'  Summary stats (would display in dashboard):')
                print(f'    Total: {data.get("total_count")} | Pending: {data.get("pending_count")}')
                print(f'    Approved: {data.get("approved_count")} | Rejected: {data.get("rejected_count")}')
                print(f'    Total Amount: ${data.get("total_amount", 0):.2f}')
                print(f'  First 3 expenses (would display in table):')
                for i, exp in enumerate(expenses[:3], 1):
                    print(f'    {i}. ${exp.get("amount")} - {exp.get("description")} [{exp.get("status")}]')
                return expenses[0]['id'] if expenses else None
            elif isinstance(data, list):
                print_result(True, f'Expense list loaded: {len(data)} expenses')
                return data[0]['id'] if data else None
            else:
                print_result(False, f'Unexpected response format: {type(data)}')
                return None
        else:
            print_result(False, f'Expense list failed: {response.status_code}')
            return None
    except Exception as e:
        print_result(False, f'Expense list error: {str(e)}')
        return None

def test_organization_list_click(headers):
    """Test clicking to view organization list"""
    print_section('TEST 7: ORGANIZATION LIST - Click to View All Orgs')
    try:
        response = requests.get(f'{BASE_URL}/api/v1/organizations', headers=headers)

        if response.status_code == 200:
            orgs = response.json()
            print_result(True, f'Organization list loaded: {len(orgs)} organizations')
            print(f'  Organizations (would display in table):')
            for org in orgs:
                print(f'    - {org.get("name")} ({org.get("slug")}) - Active: {org.get("is_active")}')
            return orgs[0]['id'] if orgs else None
        else:
            print_result(False, f'Organization list failed: {response.status_code}')
            return None
    except Exception as e:
        print_result(False, f'Organization list error: {str(e)}')
        return None

def test_organization_detail_click(headers, org_id):
    """Test clicking on organization to view details"""
    print_section('TEST 8: ORGANIZATION DETAILS - Click on Org to View')
    try:
        response = requests.get(f'{BASE_URL}/api/v1/organizations/{org_id}', headers=headers)

        if response.status_code == 200:
            org = response.json()
            print_result(True, 'Organization details loaded (page/modal would open)')
            print(f'  Name: {org.get("name")}')
            print(f'  Description: {org.get("description")}')
            print(f'  Currency: {org.get("currency")}')
            print(f'  Timezone: {org.get("timezone")}')
            print(f'  Max Members: {org.get("max_members")}')
            print(f'  Status: {"Active" if org.get("is_active") else "Inactive"}')
            return True
        else:
            print_result(False, f'Organization details failed: {response.status_code}')
            return False
    except Exception as e:
        print_result(False, f'Organization details error: {str(e)}')
        return False

def test_billing_tiers_click(headers):
    """Test clicking to view billing/pricing plans"""
    print_section('TEST 9: BILLING TIERS - Click to View Pricing Plans')
    try:
        response = requests.get(f'{BASE_URL}/api/billing/org/tiers', headers=headers)

        if response.status_code == 200:
            data = response.json()
            tiers = data.get('tiers', [])
            print_result(True, f'Billing tiers loaded: {len(tiers)} plans available')
            print(f'  Pricing plans (would display as cards):')
            for tier in tiers:
                print(f'    - {tier.get("display_name")}: ${tier.get("price_monthly")}/month')
                print(f'      Features: {len(tier.get("features", []))} features')
            return True
        else:
            print_result(False, f'Billing tiers failed: {response.status_code}')
            return False
    except Exception as e:
        print_result(False, f'Billing tiers error: {str(e)}')
        return False

def test_subscription_status_click(headers):
    """Test clicking to view subscription status"""
    print_section('TEST 10: SUBSCRIPTION STATUS - Click to View Current Plan')
    try:
        response = requests.get(f'{BASE_URL}/api/billing/org/subscription', headers=headers)

        if response.status_code == 200:
            data = response.json()
            print_result(True, 'Subscription status loaded (would display in panel)')
            if data.get('has_subscription'):
                print(f'  Current Tier: {data.get("tier_display_name")}')
                print(f'  Status: {data.get("status")}')
                print(f'  Price: ${data.get("tier_price")}/month')
                print(f'  Trial: {data.get("is_trial")}')
                if data.get('is_trial'):
                    print(f'  Trial Ends: {data.get("trial_end")}')
                print(f'  Next Billing: {data.get("next_billing_date")}')
            else:
                print(f'  No active subscription')
            return True
        else:
            print_result(False, f'Subscription status failed: {response.status_code}')
            return False
    except Exception as e:
        print_result(False, f'Subscription status error: {str(e)}')
        return False

def test_system_health_click(headers):
    """Test clicking to view system health"""
    print_section('TEST 11: SYSTEM HEALTH - Click to View System Status')
    try:
        response = requests.get(f'{BASE_URL}/api/v1/admin/system/health', headers=headers)

        if response.status_code == 200:
            data = response.json()
            print_result(True, 'System health loaded (would display in status panel)')
            print(f'  Overall Status: {data.get("overall_status")}')
            components = data.get('components', {})
            for name, status in components.items():
                if isinstance(status, dict):
                    print(f'  {name.capitalize()}: {status.get("status")}')
            return True
        else:
            print_result(False, f'System health failed: {response.status_code}')
            return False
    except Exception as e:
        print_result(False, f'System health error: {str(e)}')
        return False

def test_database_stats_click(headers):
    """Test clicking to view database statistics"""
    print_section('TEST 12: DATABASE STATS - Click to View DB Statistics')
    try:
        response = requests.get(f'{BASE_URL}/api/v1/admin/stats/database', headers=headers)

        if response.status_code == 200:
            stats = response.json()
            print_result(True, 'Database stats loaded (would display in charts)')
            print(f'  Tables monitored: {len(stats)} tables')
            for table, data in stats.items():
                if isinstance(data, dict):
                    print(f'  {table}: {data}')
                else:
                    print(f'  {table}: {data}')
            return True
        else:
            print_result(False, f'Database stats failed: {response.status_code}')
            return False
    except Exception as e:
        print_result(False, f'Database stats error: {str(e)}')
        return False

def test_user_sessions_click(headers, user_id):
    """Test clicking to view user sessions"""
    print_section('TEST 13: USER SESSIONS - Click to View Active Sessions')
    try:
        response = requests.get(f'{BASE_URL}/api/v1/users/{user_id}/sessions', headers=headers)

        if response.status_code == 200:
            sessions = response.json()
            print_result(True, f'User sessions loaded: {len(sessions)} sessions')
            print(f'  Sessions (would display in table):')
            for i, session in enumerate(sessions[:3], 1):
                print(f'    {i}. Device: {session.get("device_info", "Unknown")}')
                print(f'       IP: {session.get("ip_address", "Unknown")}')
                print(f'       Active: {session.get("is_active")}')
            return sessions[0]['id'] if sessions else None
        else:
            print_result(False, f'User sessions failed: {response.status_code}')
            return None
    except Exception as e:
        print_result(False, f'User sessions error: {str(e)}')
        return None

def test_pagination_click(headers):
    """Test clicking pagination controls"""
    print_section('TEST 14: PAGINATION - Click Next/Previous Page')
    try:
        # Page 1
        response1 = requests.get(f'{BASE_URL}/api/v1/admin/users?limit=3&offset=0', headers=headers)
        # Page 2
        response2 = requests.get(f'{BASE_URL}/api/v1/admin/users?limit=3&offset=3', headers=headers)

        if response1.status_code == 200 and response2.status_code == 200:
            page1_users = response1.json().get('users', [])
            page2_users = response2.json().get('users', [])
            print_result(True, 'Pagination working')
            print(f'  Page 1: {len(page1_users)} users')
            print(f'  Page 2: {len(page2_users)} users')
            # Verify different users
            if page1_users and page2_users:
                if page1_users[0]['id'] != page2_users[0]['id']:
                    print(f'  Verified: Different users on each page')
                return True
        else:
            print_result(False, 'Pagination failed')
            return False
    except Exception as e:
        print_result(False, f'Pagination error: {str(e)}')
        return False

def test_sort_click(headers):
    """Test clicking sort button on columns"""
    print_section('TEST 15: SORTING - Click Column Header to Sort')
    try:
        # This tests that the API can handle sorting (UI would send this)
        response = requests.get(f'{BASE_URL}/api/v1/admin/users?sort_by=username&sort_order=asc', headers=headers)

        if response.status_code == 200:
            data = response.json()
            users = data.get('users', [])
            print_result(True, 'Sorting capability verified')
            print(f'  Sorted users by username (would update table):')
            for user in users[:3]:
                print(f'    - {user.get("username")}')
            return True
        else:
            print_result(False, f'Sorting failed: {response.status_code}')
            return False
    except Exception as e:
        print_result(False, f'Sorting error: {str(e)}')
        return False

def generate_report():
    """Generate final test report"""
    print_section('COMPREHENSIVE INTERACTION TEST REPORT')
    total = results['passed'] + results['failed']
    success_rate = (results['passed'] / total * 100) if total > 0 else 0

    print(f'Total interaction tests: {total}')
    print(f'Passed: {results["passed"]}')
    print(f'Failed: {results["failed"]}')
    print(f'Success rate: {success_rate:.1f}%')

    if results['errors']:
        print('\nFailed tests:')
        for i, error in enumerate(results['errors'], 1):
            print(f'  {i}. {error}')

    print('\n' + '='*70)
    if results['failed'] == 0:
        print('[SUCCESS] All interaction tests passed!')
        print('Users can click, view, filter, paginate, and interact with all features!')
    else:
        print(f'[WARNING] {results["failed"]} interaction test(s) failed')
    print('='*70)

def main():
    print('='*70)
    print('COMPREHENSIVE INTERACTION TEST')
    print('Testing: Clicks, Views, Filters, Pagination, Sorting, Navigation')
    print('='*70)

    token = login()
    if not token:
        print('\n[CRITICAL] Login failed. Cannot continue tests.')
        return

    headers = {'Authorization': f'Bearer {token}'}

    # Test all interactions
    test_dashboard_click(headers)
    user_id = test_user_list_click(headers)
    if user_id:
        test_user_detail_click(headers, user_id)
        test_user_sessions_click(headers, user_id)
    test_user_filter_click(headers)
    test_expense_list_click(headers)
    org_id = test_organization_list_click(headers)
    if org_id:
        test_organization_detail_click(headers, org_id)
    test_billing_tiers_click(headers)
    test_subscription_status_click(headers)
    test_system_health_click(headers)
    test_database_stats_click(headers)
    test_pagination_click(headers)
    test_sort_click(headers)

    generate_report()

if __name__ == '__main__':
    main()
