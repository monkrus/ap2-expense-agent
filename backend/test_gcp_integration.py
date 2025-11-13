#!/usr/bin/env python3
"""
GCP Marketplace Integration Test Script

This script tests the GCP Marketplace webhook endpoints locally without requiring
a full GCP project setup. It simulates the procurement events that GCP Marketplace
would send to our application.

Usage:
    python test_gcp_integration.py --test procurement
    python test_gcp_integration.py --test usage
    python test_gcp_integration.py --test all
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Dict, Any

import requests
from colorama import init, Fore, Style

# Initialize colorama for colored output
init(autoreset=True)

# Default API base URL (update if running on different host/port)
API_BASE_URL = "http://localhost:8000"


class GCPMarketplaceTestSuite:
    """Test suite for GCP Marketplace integration"""

    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.passed = 0
        self.failed = 0

    def print_header(self, text: str):
        """Print formatted test section header"""
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}{text}")
        print(f"{Fore.CYAN}{'='*80}\n")

    def print_success(self, text: str):
        """Print success message"""
        print(f"{Fore.GREEN}✓ {text}")
        self.passed += 1

    def print_error(self, text: str):
        """Print error message"""
        print(f"{Fore.RED}✗ {text}")
        self.failed += 1

    def print_info(self, text: str):
        """Print info message"""
        print(f"{Fore.YELLOW}ℹ {text}")

    def print_summary(self):
        """Print test summary"""
        total = self.passed + self.failed
        pass_rate = (self.passed / total * 100) if total > 0 else 0

        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}Test Summary")
        print(f"{Fore.CYAN}{'='*80}")
        print(f"Total Tests: {total}")
        print(f"{Fore.GREEN}Passed: {self.passed}")
        print(f"{Fore.RED}Failed: {self.failed}")
        print(f"Pass Rate: {pass_rate:.1f}%")
        print(f"{Fore.CYAN}{'='*80}\n")

    def test_health_endpoint(self) -> bool:
        """Test basic health endpoint"""
        self.print_header("Testing Health Endpoint")

        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)

            if response.status_code == 200:
                data = response.json()
                self.print_success(f"Health endpoint responding: {data}")
                return True
            else:
                self.print_error(f"Health endpoint returned {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            self.print_error(f"Cannot connect to {self.base_url}. Is the server running?")
            self.print_info("Start the server with: uvicorn src.api:app --reload")
            return False
        except Exception as e:
            self.print_error(f"Health check failed: {e}")
            return False

    def test_procurement_webhook_approval(self):
        """Test procurement webhook with entitlement approval"""
        self.print_header("Testing Procurement Webhook - Entitlement Approval")

        payload = {
            "eventType": "ENTITLEMENT_PENDING_PLAN_CHANGE_APPROVED",
            "entitlement": {
                "id": "test-ent-" + datetime.now().strftime("%Y%m%d%H%M%S"),
                "name": "providers/test-provider/entitlements/test-ent-001",
                "account": "providers/test-provider/accounts/acc-test-001",
                "product": "products/ap2-expense-agent",
                "plan": "PROFESSIONAL",
                "state": "ENTITLEMENT_ACTIVATION_REQUESTED",
                "createTime": datetime.now(timezone.utc).isoformat(),
                "updateTime": datetime.now(timezone.utc).isoformat(),
                "usageReportingId": "test-usage-001",
                "consumers": [{
                    "project": "projects/test-customer-project"
                }]
            }
        }

        try:
            response = requests.post(
                f"{self.base_url}/api/webhooks/gcp/procurement",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )

            self.print_info(f"Response Status: {response.status_code}")
            self.print_info(f"Response Body: {response.text[:200]}")

            if response.status_code in [200, 201]:
                self.print_success("Procurement webhook accepted entitlement approval")
                return True
            else:
                self.print_error(f"Procurement webhook failed with status {response.status_code}")
                return False

        except Exception as e:
            self.print_error(f"Procurement webhook test failed: {e}")
            return False

    def test_procurement_webhook_creation(self):
        """Test procurement webhook with entitlement creation"""
        self.print_header("Testing Procurement Webhook - Entitlement Creation")

        payload = {
            "eventType": "ENTITLEMENT_CREATION_REQUESTED",
            "entitlement": {
                "id": "test-ent-create-" + datetime.now().strftime("%Y%m%d%H%M%S"),
                "name": "providers/test-provider/entitlements/test-ent-002",
                "account": "providers/test-provider/accounts/acc-test-002",
                "product": "products/ap2-expense-agent",
                "plan": "STARTER",
                "state": "ENTITLEMENT_ACTIVATION_REQUESTED",
                "createTime": datetime.now(timezone.utc).isoformat(),
                "updateTime": datetime.now(timezone.utc).isoformat()
            }
        }

        try:
            response = requests.post(
                f"{self.base_url}/api/webhooks/gcp/procurement",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )

            self.print_info(f"Response Status: {response.status_code}")

            if response.status_code in [200, 201]:
                self.print_success("Procurement webhook accepted entitlement creation")
                return True
            else:
                self.print_error(f"Procurement webhook failed with status {response.status_code}")
                return False

        except Exception as e:
            self.print_error(f"Procurement webhook test failed: {e}")
            return False

    def test_procurement_webhook_cancellation(self):
        """Test procurement webhook with entitlement cancellation"""
        self.print_header("Testing Procurement Webhook - Entitlement Cancellation")

        payload = {
            "eventType": "ENTITLEMENT_CANCELLATION_REQUESTED",
            "entitlement": {
                "id": "test-ent-cancel-" + datetime.now().strftime("%Y%m%d%H%M%S"),
                "name": "providers/test-provider/entitlements/test-ent-003",
                "account": "providers/test-provider/accounts/acc-test-003",
                "product": "products/ap2-expense-agent",
                "plan": "PROFESSIONAL",
                "state": "ENTITLEMENT_CANCELLED",
                "createTime": datetime.now(timezone.utc).isoformat(),
                "updateTime": datetime.now(timezone.utc).isoformat()
            }
        }

        try:
            response = requests.post(
                f"{self.base_url}/api/webhooks/gcp/procurement",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )

            self.print_info(f"Response Status: {response.status_code}")

            if response.status_code in [200, 201]:
                self.print_success("Procurement webhook accepted entitlement cancellation")
                return True
            else:
                self.print_error(f"Procurement webhook failed with status {response.status_code}")
                return False

        except Exception as e:
            self.print_error(f"Procurement webhook test failed: {e}")
            return False

    def test_usage_reporting_endpoint(self):
        """Test usage reporting endpoint"""
        self.print_header("Testing Usage Reporting Endpoint")

        try:
            response = requests.post(
                f"{self.base_url}/api/webhooks/gcp/report-usage",
                headers={"Content-Type": "application/json"},
                timeout=30
            )

            self.print_info(f"Response Status: {response.status_code}")
            self.print_info(f"Response Body: {response.text[:200]}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    self.print_success(f"Usage reporting completed: {data}")
                    return True
                except json.JSONDecodeError:
                    self.print_success("Usage reporting completed (no JSON response)")
                    return True
            else:
                self.print_error(f"Usage reporting failed with status {response.status_code}")
                return False

        except Exception as e:
            self.print_error(f"Usage reporting test failed: {e}")
            return False

    def test_gcp_health_endpoint(self):
        """Test GCP-specific health endpoint"""
        self.print_header("Testing GCP Health Endpoint")

        try:
            response = requests.get(
                f"{self.base_url}/api/webhooks/gcp/health",
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                self.print_success(f"GCP health endpoint responding: {data}")
                return True
            else:
                self.print_error(f"GCP health endpoint returned {response.status_code}")
                return False

        except Exception as e:
            self.print_error(f"GCP health check failed: {e}")
            return False

    def run_procurement_tests(self):
        """Run all procurement webhook tests"""
        self.test_health_endpoint()
        self.test_gcp_health_endpoint()
        self.test_procurement_webhook_creation()
        self.test_procurement_webhook_approval()
        self.test_procurement_webhook_cancellation()

    def run_usage_tests(self):
        """Run all usage reporting tests"""
        self.test_health_endpoint()
        self.test_gcp_health_endpoint()
        self.test_usage_reporting_endpoint()

    def run_all_tests(self):
        """Run complete test suite"""
        self.run_procurement_tests()
        self.run_usage_tests()


def main():
    parser = argparse.ArgumentParser(
        description="Test GCP Marketplace integration endpoints"
    )
    parser.add_argument(
        "--test",
        choices=["procurement", "usage", "all"],
        default="all",
        help="Which test suite to run"
    )
    parser.add_argument(
        "--url",
        default=API_BASE_URL,
        help=f"Base URL for the API (default: {API_BASE_URL})"
    )

    args = parser.parse_args()

    print(f"{Fore.CYAN}╔{'═'*78}╗")
    print(f"{Fore.CYAN}║{' '*78}║")
    print(f"{Fore.CYAN}║{' '*20}GCP Marketplace Integration Tests{' '*24}║")
    print(f"{Fore.CYAN}║{' '*78}║")
    print(f"{Fore.CYAN}╚{'═'*78}╝\n")

    suite = GCPMarketplaceTestSuite(base_url=args.url)

    if args.test == "procurement":
        suite.run_procurement_tests()
    elif args.test == "usage":
        suite.run_usage_tests()
    else:
        suite.run_all_tests()

    suite.print_summary()

    # Exit with appropriate code
    sys.exit(0 if suite.failed == 0 else 1)


if __name__ == "__main__":
    main()
