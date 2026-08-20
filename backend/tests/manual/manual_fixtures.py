"""
Test Fixtures for Role-Based Testing
Provides reusable test data and helper functions to avoid tier limit issues.

Usage:
    from test_fixtures import TestFixtures

    fixtures = TestFixtures()
    fixtures.setup()  # Login all users once

    # Use fixtures in tests
    employee_token = fixtures.get_token("employee")
    org_id = fixtures.get_org_id()
"""

import time
from dataclasses import dataclass
from typing import Dict, Optional

import requests

# Configuration
BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"

# Test users (reuse existing test users)
TEST_USERS = {
    "employee": {"username": "emptest", "password": "Emptest123!", "role": "EMPLOYEE"},
    "employee2": {
        "username": "emptest2",
        "password": "Emptest2123!",
        "role": "EMPLOYEE",
    },
    "manager": {"username": "testuser", "password": "TestUser123!", "role": "MANAGER"},
    "accountant": {
        "username": "employee2",
        "password": "Employee2123!",
        "role": "ACCOUNTANT",
    },
    "admin": {"username": "admintest", "password": "AdminTest123!", "role": "ADMIN"},
}


@dataclass
class UserFixture:
    """User authentication fixture"""

    username: str
    password: str
    role: str
    token: Optional[str] = None
    user_id: Optional[str] = None
    email: Optional[str] = None


class TestFixtures:
    """Centralized test fixtures to avoid tier limits"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.api_base = f"{base_url}{API_PREFIX}"
        self.users: Dict[str, UserFixture] = {}
        self.org_id: Optional[str] = None
        self._setup_complete = False

    def setup(self) -> bool:
        """
        One-time setup: Login all users and get organization.
        Call this once at the start of your test suite.
        """
        if self._setup_complete:
            print("[FIXTURES] Already set up, skipping...")
            return True

        print("[FIXTURES] Setting up test fixtures...")

        # Login all users with rate limit handling
        for role_key, user_info in TEST_USERS.items():
            user = UserFixture(
                username=user_info["username"],
                password=user_info["password"],
                role=user_info["role"],
            )

            success = self._login_user(user)
            if not success:
                print(f"[FIXTURES] Failed to login {user.username}")
                return False

            self.users[role_key] = user
            time.sleep(0.2)  # Avoid rate limiting

        # Get organization from admin user
        success = self._get_organization()
        if not success:
            print("[FIXTURES] Failed to get organization")
            return False

        self._setup_complete = True
        print(f"[FIXTURES] Setup complete! Org: {self.org_id}")
        return True

    def _login_user(self, user: UserFixture, max_retries: int = 3) -> bool:
        """Login a single user with retry logic"""
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.api_base}/auth/login",
                    json={"username": user.username, "password": user.password},
                    timeout=10,
                )

                if response.status_code == 200:
                    data = response.json()
                    user.token = data["access_token"]
                    user.user_id = data.get("user", {}).get("id")
                    user.email = data.get("user", {}).get("email")
                    print(f"[FIXTURES] ✓ {user.username} logged in")
                    return True
                elif response.status_code == 429:  # Rate limited
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 2
                        print(f"[FIXTURES] Rate limited, waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                else:
                    print(f"[FIXTURES] Login failed: {response.status_code}")
                    return False
            except Exception as e:
                print(f"[FIXTURES] Login error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return False

        return False

    def _get_organization(self) -> bool:
        """Get existing organization for tests"""
        admin = self.users.get("admin")
        if not admin or not admin.token:
            return False

        try:
            response = requests.get(
                f"{self.api_base}/organizations",
                headers={"Authorization": f"Bearer {admin.token}"},
                timeout=10,
            )

            if response.status_code == 200:
                orgs = response.json()
                if orgs and len(orgs) > 0:
                    self.org_id = orgs[0]["id"]
                    print(f"[FIXTURES] ✓ Using org: {orgs[0]['name']}")
                    return True

            print(f"[FIXTURES] No organization found")
            return False
        except Exception as e:
            print(f"[FIXTURES] Error getting org: {e}")
            return False

    def get_token(self, role: str) -> Optional[str]:
        """Get authentication token for a role"""
        user = self.users.get(role)
        return user.token if user else None

    def get_user_id(self, role: str) -> Optional[str]:
        """Get user ID for a role"""
        user = self.users.get(role)
        return user.user_id if user else None

    def get_org_id(self) -> Optional[str]:
        """Get organization ID"""
        return self.org_id

    def get_headers(self, role: str, include_org: bool = True) -> Dict[str, str]:
        """Get HTTP headers for a role"""
        token = self.get_token(role)
        if not token:
            return {}

        headers = {"Authorization": f"Bearer {token}"}
        if include_org and self.org_id:
            headers["X-Organization-Id"] = self.org_id

        return headers

    def teardown(self):
        """Cleanup fixtures (currently no cleanup needed)"""
        print("[FIXTURES] Teardown complete")


# Singleton instance for shared use across tests
_fixtures_instance = None


def get_fixtures() -> TestFixtures:
    """Get or create the global fixtures instance"""
    global _fixtures_instance
    if _fixtures_instance is None:
        _fixtures_instance = TestFixtures()
    return _fixtures_instance


# Valid expense categories (from backend validation)
VALID_CATEGORIES = ["TRAVEL", "MEALS", "SOFTWARE", "OFFICE_SUPPLIES", "OTHER"]


def create_expense_data(**overrides) -> dict:
    """
    Create valid expense data with sensible defaults.

    Args:
        **overrides: Override default values

    Returns:
        dict: Valid expense data

    Example:
        expense = create_expense_data(amount=100.00, category="TRAVEL")
    """
    from datetime import datetime

    defaults = {
        "amount": 50.00,
        "vendor": "Test Vendor",
        "category": "OTHER",
        "description": "Test expense",
        "date": datetime.now().strftime("%Y-%m-%d"),
    }

    defaults.update(overrides)
    return defaults


# Tier limit information (for documentation purposes)
TIER_LIMITS = {
    "FREE": {
        "daily_expenses": 10,
        "monthly_expenses": 20,
        "max_orgs": 1,
        "max_users": 1,
        "features": ["basic_expenses", "simple_reports"],
    },
    "STARTER": {
        "daily_expenses": 50,
        "monthly_expenses": 200,
        "max_orgs": 3,
        "max_users": 5,
        "features": [
            "basic_expenses",
            "simple_reports",
            "receipt_upload",
            "approval_workflow",
        ],
    },
    "PROFESSIONAL": {
        "daily_expenses": "unlimited",
        "monthly_expenses": "unlimited",
        "max_orgs": 10,
        "max_users": 25,
        "features": ["all_features"],
    },
    "ENTERPRISE": {
        "daily_expenses": "unlimited",
        "monthly_expenses": "unlimited",
        "max_orgs": 25,
        "max_users": 100,
        "features": ["all_features", "priority_support", "custom_integrations"],
    },
}


def is_tier_limit_error(response: requests.Response) -> bool:
    """
    Check if a response is a tier limit error (402).

    Args:
        response: HTTP response object

    Returns:
        bool: True if this is a tier limit error
    """
    return response.status_code == 402


def get_tier_limit_message(response: requests.Response) -> Optional[str]:
    """
    Extract tier limit message from error response.

    Args:
        response: HTTP response object

    Returns:
        str or None: Tier limit message if found
    """
    if response.status_code == 402:
        try:
            data = response.json()
            detail = data.get("detail", "")
            if isinstance(detail, str):
                return detail
            elif isinstance(detail, dict):
                return detail.get("message", str(detail))
        except:
            pass
    return None
