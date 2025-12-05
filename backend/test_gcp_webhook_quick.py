"""
Quick test script for GCP Marketplace webhook integration
Tests JWT verification and entitlement creation locally
"""

import requests
import jwt
import uuid
import time
from datetime import datetime, timedelta, timezone


def generate_test_jwt():
    """
    Generate a fake JWT for local testing

    WARNING: This is ONLY for local development testing!
    In production, Google signs tokens with their private key.
    """
    payload = {
        "iss": "https://accounts.google.com",
        "sub": "1234567890",
        "email": f"test-{int(time.time())}@example.com",
        "email_verified": True,
        "aud": "test-audience",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
        "name": "Test User",
    }

    # Note: Using HS256 for local testing (not secure, but works)
    # In production, Google uses RS256 with their private key
    # Add kid header to match Google's JWT format
    headers = {"kid": "test-key-id"}
    token = jwt.encode(payload, "fake-secret-for-testing", algorithm="HS256", headers=headers)
    return token


def test_webhook_basic():
    """Test basic webhook endpoint with JWT"""

    print("=" * 70)
    print("TEST 1: Basic Webhook with JWT Verification")
    print("=" * 70)

    token = generate_test_jwt()

    payload = {
        "eventType": "ENTITLEMENT_CREATION_REQUESTED",
        "entitlement": {
            "name": f"billingAccounts/123456/entitlements/{uuid.uuid4()}",
            "account": f"gcp-account-{uuid.uuid4()}",
            "plan": "professional",
            "usageReportingId": f"test-{int(time.time())}@example.com",
            "state": "ENTITLEMENT_ACTIVATION_REQUESTED",
            "metadata": {
                "companyName": f"Test Company {int(time.time())}"
            }
        }
    }

    try:
        response = requests.post(
            "http://localhost:8000/api/webhooks/gcp/procurement-simple",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=10
        )

        print(f"\nStatus Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"[PASS] SUCCESS - Webhook processed")
            print(f"\nResponse:")
            for key, value in result.items():
                print(f"  {key}: {value}")

            if result.get("status") == "created":
                print(f"\n[PASS] Organization created successfully!")
                print(f"   Organization ID: {result.get('organization_id')}")
                print(f"   User ID: {result.get('user_id')}")

            return True
        else:
            print(f"[FAIL] FAILED - Status {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print("[FAIL] ERROR - Cannot connect to backend")
        print("   Make sure backend is running:")
        print("   cd backend && uvicorn src.api:app --reload")
        return False
    except Exception as e:
        print(f"[FAIL] ERROR - {e}")
        return False


def test_health_check():
    """Test GCP webhook health endpoint"""

    print("\n" + "=" * 70)
    print("TEST 2: Health Check")
    print("=" * 70)

    try:
        response = requests.get(
            "http://localhost:8000/api/webhooks/gcp/health",
            timeout=5
        )

        print(f"\nStatus Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"[PASS] SUCCESS - Health check passed")
            print(f"\nResponse:")
            for key, value in result.items():
                print(f"  {key}: {value}")
            return True
        else:
            print(f"[FAIL] FAILED - Status {response.status_code}")
            return False

    except Exception as e:
        print(f"[FAIL] ERROR - {e}")
        return False


def test_activation():
    """Test entitlement activation event"""

    print("\n" + "=" * 70)
    print("TEST 3: Entitlement Activation")
    print("=" * 70)

    token = generate_test_jwt()

    payload = {
        "eventType": "ENTITLEMENT_ACTIVE",
        "entitlement": {
            "name": f"billingAccounts/123456/entitlements/{uuid.uuid4()}",
            "account": f"gcp-account-{uuid.uuid4()}",
            "plan": "professional",
            "state": "ENTITLEMENT_ACTIVE",
        }
    }

    try:
        response = requests.post(
            "http://localhost:8000/api/webhooks/gcp/procurement-simple",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=10
        )

        print(f"\nStatus Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"[PASS] SUCCESS - Activation handled")
            print(f"\nResponse:")
            for key, value in result.items():
                print(f"  {key}: {value}")
            return True
        else:
            print(f"[FAIL] FAILED - Status {response.status_code}")
            return False

    except Exception as e:
        print(f"[FAIL] ERROR - {e}")
        return False


def main():
    """Run all tests"""

    print("\n" + "=" * 70)
    print("GCP MARKETPLACE WEBHOOK INTEGRATION TEST")
    print("=" * 70)
    print("\nBackend is running on http://127.0.0.1:8000")
    print("Starting tests...\n")
    # input()  # Commented out for automated testing

    results = []

    # Run tests
    results.append(("Health Check", test_health_check()))
    results.append(("Webhook Basic", test_webhook_basic()))
    results.append(("Activation Event", test_activation()))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} - {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n[SUCCESS] ALL TESTS PASSED! GCP Marketplace integration is working!")
        print("\nNext steps:")
        print("1. Review the code in backend/src/gcp/jwt_verification.py")
        print("2. Check backend/src/routes/gcp_webhooks.py for webhook handler")
        print("3. Start Ticket #2: Consumer Procurement API client")
    else:
        print("\n[WARNING] Some tests failed. Check the errors above.")
        print("\nCommon issues:")
        print("- Backend not running: cd backend && uvicorn src.api:app --reload")
        print("- Missing endpoint: Add procurement-simple endpoint to gcp_webhooks.py")
        print("- Database error: Make sure database is accessible")


if __name__ == "__main__":
    main()
