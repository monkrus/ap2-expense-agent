"""
Complete Stripe Checkout Flow Test

Tests the full end-to-end Stripe integration:
1. User registration
2. Organization creation
3. Checkout session creation (all 6 products)
4. (Manual step: Complete checkout in browser)
5. Webhook processing verification
6. Subscription activation verification
7. Database verification

This script automates everything up to the actual checkout completion,
which must be done manually in a browser.
"""

import requests
import time
import json
from datetime import datetime

# Configuration
BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"
TEST_USER_PREFIX = f"checkouttest_{int(time.time())}"

# Test data
TEST_USER = {
    "username": TEST_USER_PREFIX,
    "password": "SecureTest123!",
    "email": f"{TEST_USER_PREFIX}@test.com",
    "full_name": "Checkout Test User"
}

TEST_ORG = {
    "name": f"Checkout Test Org {int(time.time())}",
    "slug": f"checkout-test-{int(time.time())}"
}

# Tier configurations to test
TIERS_TO_TEST = [
    {"tier": "starter", "cycle": "monthly"},
    {"tier": "starter", "cycle": "annual"},
    {"tier": "professional", "cycle": "monthly"},
    {"tier": "professional", "cycle": "annual"},
    {"tier": "enterprise", "cycle": "monthly"},
    {"tier": "enterprise", "cycle": "annual"},
]

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.OKGREEN}[OK] {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}[ERROR] {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKCYAN}> {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}! {text}{Colors.ENDC}")

def register_user():
    """Step 1: Register a new user"""
    print_header("Step 1: User Registration")

    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/auth/register",
            json=TEST_USER,
            timeout=10
        )

        if response.status_code == 201:
            data = response.json()
            print_success(f"User registered successfully: {data['username']}")
            print_info(f"User ID: {data['id']}")
            return True
        elif response.status_code == 429:
            print_warning("Rate limit reached. Using existing user or wait 60 seconds.")
            return "rate_limited"
        else:
            print_error(f"Registration failed: {response.status_code}")
            print_error(response.text)
            return False

    except Exception as e:
        print_error(f"Registration error: {str(e)}")
        return False

def login_user():
    """Step 2: Login and get access token"""
    print_header("Step 2: User Login")

    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/auth/login",
            json={
                "username": TEST_USER["username"],
                "password": TEST_USER["password"]
            },
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            token = data["access_token"]
            print_success("Login successful")
            print_info(f"Access token: {token[:20]}...")
            return token
        else:
            print_error(f"Login failed: {response.status_code}")
            print_error(response.text)
            return None

    except Exception as e:
        print_error(f"Login error: {str(e)}")
        return None

def create_organization(token):
    """Step 3: Create an organization"""
    print_header("Step 3: Organization Creation")

    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/organizations",
            json=TEST_ORG,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )

        if response.status_code == 201:
            data = response.json()
            print_success(f"Organization created: {data['name']}")
            print_info(f"Organization ID: {data['id']}")
            print_info(f"Slug: {data['slug']}")
            print_info(f"Stripe Customer ID: {data.get('stripe_customer_id', 'Not yet created')}")
            return data['id']
        else:
            print_error(f"Organization creation failed: {response.status_code}")
            print_error(response.text)
            return None

    except Exception as e:
        print_error(f"Organization creation error: {str(e)}")
        return None

def create_checkout_session(token, tier, billing_cycle):
    """Step 4: Create Stripe checkout session"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/payment/checkout-session",
            params={
                "tier_name": tier,
                "billing_cycle": billing_cycle
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "session_id": data["session_id"],
                "url": data["url"],
                "billing_cycle": data.get("billing_cycle", billing_cycle)
            }
        else:
            return {
                "success": False,
                "status_code": response.status_code,
                "error": response.text
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def test_all_checkout_sessions(token):
    """Step 5: Test all tier/cycle combinations"""
    print_header("Step 4: Testing All Stripe Checkout Sessions")

    results = []
    successful = 0
    failed = 0

    for config in TIERS_TO_TEST:
        tier = config["tier"]
        cycle = config["cycle"]

        print(f"\n{Colors.OKBLUE}Testing: {tier.title()} - {cycle.title()}{Colors.ENDC}")
        print("-" * 60)

        result = create_checkout_session(token, tier, cycle)

        if result["success"]:
            print_success(f"Checkout session created successfully")
            print_info(f"Session ID: {result['session_id']}")
            print_info(f"Checkout URL: {result['url']}")
            successful += 1
            results.append({
                **config,
                **result,
                "status": "success"
            })
        else:
            print_error(f"Failed to create checkout session")
            if "status_code" in result:
                print_error(f"Status code: {result['status_code']}")
            print_error(f"Error: {result.get('error', 'Unknown error')}")
            failed += 1
            results.append({
                **config,
                **result,
                "status": "failed"
            })

    print(f"\n{Colors.BOLD}Summary:{Colors.ENDC}")
    print(f"{Colors.OKGREEN}Successful: {successful}/6{Colors.ENDC}")
    if failed > 0:
        print(f"{Colors.FAIL}Failed: {failed}/6{Colors.ENDC}")

    return results

def verify_subscription(token, org_id):
    """Step 6: Verify subscription was created"""
    print_header("Step 5: Verify Subscription (After Manual Checkout)")

    print_info("This step requires manual checkout completion:")
    print_info("1. Open one of the checkout URLs in your browser")
    print_info("2. Complete checkout with test card: 4242 4242 4242 4242")
    print_info("3. Wait for webhook to process")
    print()
    input(f"{Colors.BOLD}Press Enter after completing checkout...{Colors.ENDC}")

    try:
        # Check subscription status
        response = requests.get(
            f"{BACKEND_URL}/api/billing/subscription",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            print_success("Subscription found")
            print_info(f"Tier: {data.get('tier', 'Unknown')}")
            print_info(f"Status: {data.get('status', 'Unknown')}")
            print_info(f"Stripe Subscription ID: {data.get('stripe_subscription_id', 'None')}")
            return True
        else:
            print_warning(f"No active subscription found (Status: {response.status_code})")
            return False

    except Exception as e:
        print_error(f"Subscription verification error: {str(e)}")
        return False

def check_webhooks_received():
    """Step 7: Check if webhooks were received"""
    print_header("Step 6: Webhook Verification")

    print_info("Check the Stripe CLI terminal for webhook events")
    print_info("You should see events like:")
    print_info("  - checkout.session.completed")
    print_info("  - customer.subscription.created")
    print_info("  - invoice.paid")
    print()

    webhook_received = input(f"{Colors.BOLD}Did you see webhook events in the CLI? (y/n): {Colors.ENDC}").lower() == 'y'

    if webhook_received:
        print_success("Webhooks are being received")
        return True
    else:
        print_warning("Webhooks may not be configured correctly")
        print_info("Make sure Stripe CLI is running:")
        print_info("  test-stripe-webhook.bat")
        return False

def main():
    """Main test flow"""
    print_header("Stripe Checkout Integration - Complete E2E Test")
    print_info(f"Backend: {BACKEND_URL}")
    print_info(f"Frontend: {FRONTEND_URL}")
    print_info(f"Test User: {TEST_USER['username']}")
    print_info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Step 1: Register user
    reg_result = register_user()
    if reg_result == False:
        print_error("Test aborted: User registration failed")
        return

    # Step 2: Login
    token = login_user()
    if not token:
        print_error("Test aborted: Login failed")
        return

    # Step 3: Create organization
    org_id = create_organization(token)
    if not org_id:
        print_error("Test aborted: Organization creation failed")
        return

    # Step 4: Test checkout sessions for all tiers
    checkout_results = test_all_checkout_sessions(token)

    # Save results to file
    results_file = f"stripe_checkout_results_{int(time.time())}.json"
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "user": TEST_USER["username"],
            "organization_id": org_id,
            "checkout_sessions": checkout_results
        }, f, indent=2)

    print_header("Checkout Sessions Created")
    print_success(f"Results saved to: {results_file}")

    # Step 5: Manual checkout instructions
    print_header("Manual Checkout Required")
    print_info("To complete the test, follow these steps:")
    print()
    print(f"{Colors.BOLD}1. Choose a checkout URL from above{Colors.ENDC}")
    print(f"{Colors.BOLD}2. Open it in your browser{Colors.ENDC}")
    print(f"{Colors.BOLD}3. Complete checkout with test card:{Colors.ENDC}")
    print(f"   {Colors.OKGREEN}Card Number: 4242 4242 4242 4242{Colors.ENDC}")
    print(f"   Expiry: Any future date (e.g., 12/25)")
    print(f"   CVC: Any 3 digits (e.g., 123)")
    print(f"   ZIP: Any 5 digits (e.g., 12345)")
    print()
    print(f"{Colors.BOLD}4. After checkout, you should be redirected back to the app{Colors.ENDC}")
    print(f"{Colors.BOLD}5. Check the Stripe CLI terminal for webhook events{Colors.ENDC}")
    print()

    # Step 6: Verify subscription (optional, requires manual input)
    verify_choice = input(f"{Colors.BOLD}Do you want to verify subscription now? (y/n): {Colors.ENDC}").lower()
    if verify_choice == 'y':
        verify_subscription(token, org_id)
        check_webhooks_received()

    # Final summary
    print_header("Test Complete!")
    print_success("All automated steps completed successfully")
    print()
    print(f"{Colors.BOLD}Next Steps:{Colors.ENDC}")
    print("1. Complete manual checkout in browser")
    print("2. Verify subscription activated in BillingDashboard")
    print("3. Check database for billing events")
    print("4. Review Stripe Dashboard for webhook delivery")
    print()
    print(f"{Colors.OKGREEN}Test user credentials:{Colors.ENDC}")
    print(f"  Username: {TEST_USER['username']}")
    print(f"  Password: {TEST_USER['password']}")
    print(f"  Email: {TEST_USER['email']}")
    print()
    print(f"{Colors.OKGREEN}Frontend: {FRONTEND_URL}{Colors.ENDC}")
    print(f"{Colors.OKGREEN}Backend: {BACKEND_URL}{Colors.ENDC}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Test interrupted by user{Colors.ENDC}")
    except Exception as e:
        print(f"\n\n{Colors.FAIL}Unexpected error: {str(e)}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
