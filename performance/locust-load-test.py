"""
Locust load testing script for AP2 Expense Agent
Usage: locust -f locust-load-test.py --host=https://your-domain.com
"""

from locust import HttpUser, task, between
import json
import random
from datetime import datetime, timedelta

class ExpenseUser(HttpUser):
    """Simulates an employee using the expense management system"""

    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks

    def on_start(self):
        """Login when user starts"""
        # Register/login
        username = f"loadtest_{random.randint(1000, 9999)}@example.com"
        password = "Test123!@#"

        response = self.client.post("/api/v1/users/register", json={
            "username": username,
            "email": username,
            "password": password,
            "full_name": f"Load Test User {random.randint(1000, 9999)}",
            "organization_name": "Load Test Org"
        }, catch_response=True)

        if response.status_code == 200 or response.status_code == 409:
            # Try login
            response = self.client.post("/api/v1/users/login", json={
                "username": username,
                "password": password
            })

            if response.status_code == 200:
                self.token = response.json()["access_token"]
                self.headers = {"Authorization": f"Bearer {self.token}"}
            else:
                self.token = None
                self.headers = {}
        else:
            self.token = None
            self.headers = {}

    @task(10)
    def view_expenses(self):
        """View expense list (most common operation)"""
        if not self.token:
            return

        self.client.get("/api/v1/expenses/", headers=self.headers, name="/api/v1/expenses/ [list]")

    @task(5)
    def create_expense(self):
        """Create a new expense"""
        if not self.token:
            return

        expense = {
            "amount": round(random.uniform(10.0, 500.0), 2),
            "currency": "USD",
            "description": f"Load test expense {random.randint(1000, 9999)}",
            "category": random.choice(["travel", "meals", "supplies", "other"]),
            "merchant": f"Test Merchant {random.randint(1, 100)}",
            "transaction_date": (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat()
        }

        self.client.post("/api/v1/expenses/", json=expense, headers=self.headers, name="/api/v1/expenses/ [create]")

    @task(3)
    def view_expense_report(self):
        """View expense report"""
        if not self.token:
            return

        self.client.get("/api/v1/expenses/report", headers=self.headers, name="/api/v1/expenses/report")

    @task(2)
    def view_audit_trail(self):
        """View audit trail"""
        if not self.token:
            return

        self.client.get("/api/v1/audit/", headers=self.headers, name="/api/v1/audit/ [list]")

    @task(1)
    def view_profile(self):
        """View user profile"""
        if not self.token:
            return

        self.client.get("/api/v1/users/me", headers=self.headers, name="/api/v1/users/me")

    @task(1)
    def health_check(self):
        """Health check endpoint (simulates monitoring)"""
        self.client.get("/health", name="/health")


class AdminUser(HttpUser):
    """Simulates an admin user managing the system"""

    wait_time = between(5, 15)  # Admins are less frequent
    weight = 1  # 1 admin for every 10 regular users

    def on_start(self):
        """Login as admin"""
        response = self.client.post("/api/v1/users/login", json={
            "username": "admin@example.com",
            "password": "admin123"
        })

        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}

    @task(5)
    def view_all_expenses(self):
        """View all expenses (admin)"""
        if not self.token:
            return

        self.client.get("/api/v1/expenses/all", headers=self.headers, name="/api/v1/expenses/all")

    @task(3)
    def view_users(self):
        """View all users"""
        if not self.token:
            return

        self.client.get("/api/v1/users/", headers=self.headers, name="/api/v1/users/ [admin]")

    @task(2)
    def view_organization_stats(self):
        """View organization statistics"""
        if not self.token:
            return

        self.client.get("/api/v1/organizations/stats", headers=self.headers, name="/api/v1/organizations/stats")

    @task(1)
    def approve_expense(self):
        """Approve a random expense"""
        if not self.token:
            return

        # Get pending expenses
        response = self.client.get("/api/v1/expenses/?status=pending", headers=self.headers, name="/api/v1/expenses/?status=pending")

        if response.status_code == 200:
            expenses = response.json()
            if expenses:
                expense_id = random.choice(expenses)["id"]
                self.client.post(f"/api/v1/expenses/{expense_id}/approve", headers=self.headers, name="/api/v1/expenses/[id]/approve")


class BillingCronJob(HttpUser):
    """Simulates the billing CronJob"""

    wait_time = between(3600, 3600)  # Every hour
    weight = 0.1  # Very infrequent

    def on_start(self):
        """Login as admin for billing operations"""
        response = self.client.post("/api/v1/users/login", json={
            "username": "admin@example.com",
            "password": "admin123"
        })

        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}

    @task
    def report_usage(self):
        """Report usage to GCP"""
        if not self.token:
            return

        self.client.post("/api/v1/billing/report-usage",
            json={
                "period_start": (datetime.now() - timedelta(hours=1)).isoformat(),
                "period_end": datetime.now().isoformat()
            },
            headers=self.headers,
            name="/api/v1/billing/report-usage"
        )
