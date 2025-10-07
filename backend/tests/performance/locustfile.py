"""
Performance Testing with Locust
Load testing for AP2 Expense Agent API
"""

from locust import HttpUser, task, between, SequentialTaskSet
import json
import random
import uuid


class UserBehavior(SequentialTaskSet):
    """Sequential user behavior simulation"""

    def on_start(self):
        """Setup: Login and get authentication token"""
        # Register and login
        self.user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        self.email = f"{self.user_id}@example.com"
        self.organization_id = None
        self.expense_ids = []

        # Register user
        register_payload = {
            "email": self.email,
            "password": "TestPassword123!",
            "full_name": "Load Test User",
            "username": self.user_id
        }

        response = self.client.post(
            "/api/v1/auth/register",
            json=register_payload,
            name="/api/v1/auth/register"
        )

        if response.status_code == 201:
            # Login
            login_payload = {
                "username": self.user_id,
                "password": "TestPassword123!"
            }

            response = self.client.post(
                "/api/v1/auth/login",
                json=login_payload,
                name="/api/v1/auth/login"
            )

            if response.status_code == 200:
                data = response.json()
                self.token = data["access_token"]
                self.headers = {
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json"
                }

                # Create organization
                org_payload = {
                    "name": f"Test Org {self.user_id}",
                    "slug": f"test-org-{self.user_id}",
                    "domain": f"testorg{self.user_id}.com"
                }

                response = self.client.post(
                    "/api/v1/organizations",
                    json=org_payload,
                    headers=self.headers,
                    name="/api/v1/organizations [create]"
                )

                if response.status_code == 201:
                    self.organization_id = response.json()["id"]
                    self.headers["X-Organization-Id"] = self.organization_id

    @task(10)
    def create_expense(self):
        """Create a new expense (most common operation)"""
        if not hasattr(self, 'headers') or not self.organization_id:
            return

        expense_data = {
            "amount": round(random.uniform(10.0, 500.0), 2),
            "currency": random.choice(["USD", "EUR", "GBP"]),
            "description": f"Test expense {uuid.uuid4().hex[:8]}",
            "category": random.choice(["meals", "transport", "accommodation", "office_supplies"]),
            "merchant": f"Merchant {random.randint(1, 100)}",
            "expense_date": "2025-10-06T12:00:00Z"
        }

        response = self.client.post(
            "/api/v1/expenses",
            json=expense_data,
            headers=self.headers,
            name="/api/v1/expenses [create]"
        )

        if response.status_code == 201:
            expense_id = response.json()["id"]
            self.expense_ids.append(expense_id)

    @task(15)
    def list_expenses(self):
        """List expenses (most frequently accessed)"""
        if not hasattr(self, 'headers') or not self.organization_id:
            return

        params = {
            "limit": random.choice([10, 20, 50]),
            "offset": 0
        }

        self.client.get(
            "/api/v1/expenses",
            params=params,
            headers=self.headers,
            name="/api/v1/expenses [list]"
        )

    @task(5)
    def get_expense_detail(self):
        """Get specific expense details"""
        if not hasattr(self, 'headers') or not self.expense_ids:
            return

        expense_id = random.choice(self.expense_ids)

        self.client.get(
            f"/api/v1/expenses/{expense_id}",
            headers=self.headers,
            name="/api/v1/expenses/{id} [get]"
        )

    @task(3)
    def update_expense(self):
        """Update an expense"""
        if not hasattr(self, 'headers') or not self.expense_ids:
            return

        expense_id = random.choice(self.expense_ids)

        update_data = {
            "amount": round(random.uniform(10.0, 500.0), 2),
            "description": f"Updated expense {uuid.uuid4().hex[:8]}"
        }

        self.client.patch(
            f"/api/v1/expenses/{expense_id}",
            json=update_data,
            headers=self.headers,
            name="/api/v1/expenses/{id} [update]"
        )

    @task(5)
    def search_expenses(self):
        """Search expenses with filters"""
        if not hasattr(self, 'headers') or not self.organization_id:
            return

        params = {
            "category": random.choice(["meals", "transport", "accommodation"]),
            "min_amount": 10.0,
            "max_amount": 200.0
        }

        self.client.get(
            "/api/v1/expenses/search",
            params=params,
            headers=self.headers,
            name="/api/v1/expenses/search"
        )

    @task(2)
    def get_organization_members(self):
        """Get organization members list"""
        if not hasattr(self, 'headers') or not self.organization_id:
            return

        self.client.get(
            f"/api/v1/organizations/{self.organization_id}/members",
            headers=self.headers,
            name="/api/v1/organizations/{id}/members"
        )

    @task(1)
    def health_check(self):
        """Health check endpoint"""
        self.client.get(
            "/health",
            name="/health"
        )

    @task(1)
    def metrics_check(self):
        """Metrics endpoint"""
        self.client.get(
            "/metrics",
            name="/metrics"
        )


class WebsiteUser(HttpUser):
    """Simulated user with realistic behavior"""
    tasks = [UserBehavior]
    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks

    # Realistic user weight distribution
    weight = 1


class BurstUser(HttpUser):
    """Simulated user with burst traffic patterns"""
    tasks = [UserBehavior]
    wait_time = between(0.1, 1)  # More aggressive, faster requests
    weight = 1


class ReadHeavyUser(SequentialTaskSet):
    """User that primarily reads data (reports, dashboards)"""

    def on_start(self):
        """Setup authentication"""
        self.user_id = f"read_user_{uuid.uuid4().hex[:8]}"
        self.email = f"{self.user_id}@example.com"
        self.organization_id = None

        # Register and login (simplified for brevity)
        register_payload = {
            "email": self.email,
            "password": "TestPassword123!",
            "full_name": "Read Heavy User",
            "username": self.user_id
        }

        response = self.client.post("/api/v1/auth/register", json=register_payload)
        if response.status_code == 201:
            login_payload = {"username": self.user_id, "password": "TestPassword123!"}
            response = self.client.post("/api/v1/auth/login", json=login_payload)

            if response.status_code == 200:
                self.token = response.json()["access_token"]
                self.headers = {"Authorization": f"Bearer {self.token}"}

                # Create organization
                org_payload = {
                    "name": f"Read Org {self.user_id}",
                    "slug": f"read-org-{self.user_id}",
                    "domain": f"readorg{self.user_id}.com"
                }
                response = self.client.post("/api/v1/organizations", json=org_payload, headers=self.headers)
                if response.status_code == 201:
                    self.organization_id = response.json()["id"]
                    self.headers["X-Organization-Id"] = self.organization_id

    @task(20)
    def list_expenses_readonly(self):
        """Frequent expense listing"""
        if not hasattr(self, 'headers'):
            return
        self.client.get("/api/v1/expenses", params={"limit": 50}, headers=self.headers)

    @task(5)
    def get_reports(self):
        """Get expense reports"""
        if not hasattr(self, 'headers'):
            return
        self.client.get("/api/v1/expenses/reports", headers=self.headers)

    @task(1)
    def create_minimal_expense(self):
        """Occasional expense creation"""
        if not hasattr(self, 'headers'):
            return

        expense_data = {
            "amount": 50.00,
            "currency": "USD",
            "description": "Quick expense",
            "category": "meals",
            "merchant": "Test Merchant"
        }
        self.client.post("/api/v1/expenses", json=expense_data, headers=self.headers)


class ReportViewerUser(HttpUser):
    """User primarily viewing reports and dashboards"""
    tasks = [ReadHeavyUser]
    wait_time = between(2, 8)  # Slower, more deliberate browsing
    weight = 2


# Performance test scenarios

class SpikeTestUser(HttpUser):
    """Simulate traffic spikes"""
    tasks = [UserBehavior]
    wait_time = between(0.1, 0.5)  # Very aggressive
    weight = 1


class SoakTestUser(HttpUser):
    """Long-running stability test"""
    tasks = [UserBehavior]
    wait_time = between(5, 15)  # Slow and steady
    weight = 1
