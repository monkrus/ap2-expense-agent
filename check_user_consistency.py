"""
Diagnostic script to verify user consistency between database and API
"""
import requests
import sys
import io

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API_BASE_URL = "http://localhost:8000"

def check_user_consistency():
    """Check if users in database match users shown in admin panel"""

    print("=" * 70)
    print("USER CONSISTENCY CHECK")
    print("=" * 70)

    # Step 1: Login as admin
    print("\n[1] Logging in as admin...")
    admin_login = requests.post(
        f"{API_BASE_URL}/api/v1/auth/login",
        json={"username": "admintest", "password": "AgentTest!"}
    )

    if admin_login.status_code != 200:
        print(f"   ❌ Admin login failed: {admin_login.status_code}")
        return False

    admin_data = admin_login.json()
    admin_token = admin_data["access_token"]
    print(f"   ✅ Admin logged in successfully")

    # Step 2: Get ALL users from API (no filters)
    print("\n[2] Fetching all users from API...")
    headers = {"Authorization": f"Bearer {admin_token}"}

    all_users = []
    page = 1
    per_page = 50

    while True:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/admin/users?page={page}&per_page={per_page}",
            headers=headers
        )

        if response.status_code != 200:
            print(f"   ❌ Failed to fetch users: {response.status_code}")
            return False

        data = response.json()
        users = data.get("users", [])
        all_users.extend(users)

        pagination = data.get("pagination", {})
        total_pages = pagination.get("pages", 1)

        print(f"   → Fetched page {page}/{total_pages} ({len(users)} users)")

        if page >= total_pages:
            break
        page += 1

    print(f"\n   ✅ Total users fetched from API: {len(all_users)}")

    # Step 3: Display all users
    print("\n[3] User List:")
    print("   " + "-" * 66)
    print(f"   {'ID':<36} {'Username':<15} {'Role':<10} {'Active'}")
    print("   " + "-" * 66)

    for user in all_users:
        status = "✅ Yes" if user.get('is_active') else "❌ No"
        print(f"   {user['id']:<36} {user['username']:<15} {user['role']:<10} {status}")

    print("   " + "-" * 66)

    # Step 4: Statistics
    print("\n[4] Statistics:")
    print(f"   Total users: {len(all_users)}")
    print(f"   Active users: {sum(1 for u in all_users if u.get('is_active'))}")
    print(f"   Suspended users: {sum(1 for u in all_users if not u.get('is_active'))}")
    print(f"   Admins: {sum(1 for u in all_users if u.get('role') == 'admin')}")
    print(f"   Managers: {sum(1 for u in all_users if u.get('role') == 'manager')}")
    print(f"   Employees: {sum(1 for u in all_users if u.get('role') == 'employee')}")

    # Step 5: Check for default test users
    print("\n[5] Default Test Users Check:")
    expected_users = ['admintest', 'testuser', 'emptest', 'emptest2']
    found_users = [u['username'] for u in all_users]

    for expected in expected_users:
        if expected in found_users:
            user_data = next(u for u in all_users if u['username'] == expected)
            status = "Active" if user_data.get('is_active') else "SUSPENDED"
            print(f"   ✅ {expected:<15} - Found ({status})")
        else:
            print(f"   ❌ {expected:<15} - NOT FOUND")

    # Step 6: Check for unexpected/extra users
    print("\n[6] Additional Users (not in default set):")
    extra_users = [u for u in all_users if u['username'] not in expected_users]
    if extra_users:
        for user in extra_users:
            status = "Active" if user.get('is_active') else "SUSPENDED"
            print(f"   • {user['username']:<15} ({user['role']}, {status})")
    else:
        print(f"   → No additional users found")

    # Step 7: Check database stats endpoint
    print("\n[7] Database Statistics from Backend:")
    try:
        stats_response = requests.get(
            f"{API_BASE_URL}/api/v1/admin/stats/database",
            headers=headers
        )

        if stats_response.status_code == 200:
            stats = stats_response.json()
            user_stats = stats.get("users", {})
            print(f"   Total in DB: {user_stats.get('total', 'N/A')}")
            print(f"   Active in DB: {user_stats.get('active', 'N/A')}")
            print(f"   Verified in DB: {user_stats.get('verified', 'N/A')}")
            print(f"   Locked in DB: {user_stats.get('locked', 'N/A')}")

            # Compare with API results
            api_total = len(all_users)
            db_total = user_stats.get('total', 0)

            if api_total == db_total:
                print(f"\n   ✅ API user count matches database count ({api_total})")
            else:
                print(f"\n   ⚠️  MISMATCH: API shows {api_total} users, DB has {db_total}")
        else:
            print(f"   ⚠️  Could not fetch database stats: {stats_response.status_code}")
    except Exception as e:
        print(f"   ⚠️  Error fetching database stats: {e}")

    print("\n" + "=" * 70)
    print("CONSISTENCY CHECK COMPLETE")
    print("=" * 70)

    return True

if __name__ == "__main__":
    try:
        check_user_consistency()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
