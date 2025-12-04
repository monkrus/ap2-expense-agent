# AP2 Expense Agent - API Integration Guide

Complete guide for integrating with the AP2 Expense Agent API.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Authentication](#authentication)
3. [API Endpoints Overview](#api-endpoints-overview)
4. [Common Use Cases](#common-use-cases)
5. [Webhooks](#webhooks)
6. [Error Handling](#error-handling)
7. [Rate Limits](#rate-limits)
8. [Code Examples](#code-examples)
9. [Best Practices](#best-practices)

---

## Getting Started

### Base URL

```
Production: https://your-org.ap2expense.com/api/v1
Staging:    https://staging.ap2expense.com/api/v1
```

### API Documentation

Interactive API documentation is available at:
- **Swagger UI**: `https://your-backend-url/docs`
- **ReDoc**: `https://your-backend-url/redoc`
- **OpenAPI Spec**: `https://your-backend-url/openapi.json`

### Requirements

- API key or JWT token (see [Authentication](#authentication))
- HTTPS only (TLS 1.3)
- Content-Type: `application/json`
- Organization ID (for multi-tenant operations)

---

## Authentication

### Method 1: JWT Authentication (Recommended)

**Step 1: Obtain Access Token**

```bash
curl -X POST https://your-backend-url/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@company.com",
    "password": "your_password"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Step 2: Use Access Token**

Include the token in the `Authorization` header:

```bash
curl -X GET https://your-backend-url/api/v1/expenses \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Step 3: Refresh Token (when expired)**

```bash
curl -X POST https://your-backend-url/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

### Method 2: OAuth2 (Google/GitHub)

**Google OAuth Flow:**

```bash
# Step 1: Redirect user to Google OAuth
https://your-backend-url/api/v1/oauth/google/login

# Step 2: Handle callback
# Google redirects to: /api/v1/oauth/google/callback?code=AUTH_CODE

# Step 3: Exchange code for token (handled automatically)
```

### Method 3: API Keys (Enterprise Only)

Contact support to generate API keys for server-to-server integration.

---

## API Endpoints Overview

### Authentication & Users
```
POST   /api/v1/auth/register          - Register new user
POST   /api/v1/auth/login             - Login with email/password
POST   /api/v1/auth/refresh           - Refresh access token
POST   /api/v1/auth/logout            - Logout
GET    /api/v1/users/me               - Get current user
PUT    /api/v1/users/me               - Update profile
```

### Expenses
```
POST   /api/v1/expenses               - Submit expense
GET    /api/v1/expenses               - List expenses
GET    /api/v1/expenses/{id}          - Get expense details
PUT    /api/v1/expenses/{id}          - Update expense
DELETE /api/v1/expenses/{id}          - Delete expense
POST   /api/v1/expenses/approve       - Approve expense
POST   /api/v1/expenses/reject        - Reject expense
GET    /api/v1/expenses/export        - Export expenses (CSV/PDF)
```

### Receipts
```
POST   /api/v1/expenses/{id}/receipts - Upload receipt
GET    /api/v1/expenses/{id}/receipts - List receipts
GET    /api/v1/receipts/{id}/download - Download receipt
```

### Organizations
```
POST   /api/v1/organizations          - Create organization
GET    /api/v1/organizations          - List organizations
GET    /api/v1/organizations/{id}     - Get organization
POST   /api/v1/organizations/{id}/invitations - Invite member
```

### AP2 Protocol
```
POST   /api/ap2/intent-mandate        - Create intent mandate
POST   /api/ap2/cart-mandate          - Create cart mandate
POST   /api/ap2/payment-mandate       - Create payment mandate
POST   /api/ap2/execute-payment       - Execute payment
POST   /api/ap2/complete-flow         - Complete full AP2 flow
GET    /api/ap2/mandate/{id}/status   - Get mandate status
```

### Billing
```
GET    /api/billing/subscription      - Get subscription info
POST   /api/billing/subscription      - Create subscription
PUT    /api/billing/subscription/{id} - Update subscription
GET    /api/billing/usage/monthly     - Get usage stats
```

---

## Common Use Cases

### Use Case 1: Submit Expense Programmatically

**Python Example:**

```python
import requests
import json

# Configuration
API_BASE = "https://your-backend-url/api/v1"
TOKEN = "your_jwt_token"

# Headers
headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Submit expense
expense_data = {
    "amount": 45.99,
    "vendor": "Office Depot",
    "category": "office_supplies",
    "description": "Printer paper and toner",
    "date": "2025-11-13"
}

response = requests.post(
    f"{API_BASE}/expenses",
    headers=headers,
    json=expense_data
)

if response.status_code == 201:
    expense = response.json()
    print(f"Expense created: {expense['expense']['id']}")
else:
    print(f"Error: {response.json()}")
```

**JavaScript/Node.js Example:**

```javascript
const axios = require('axios');

const API_BASE = 'https://your-backend-url/api/v1';
const TOKEN = 'your_jwt_token';

async function submitExpense() {
  try {
    const response = await axios.post(
      `${API_BASE}/expenses`,
      {
        amount: 45.99,
        vendor: 'Office Depot',
        category: 'office_supplies',
        description: 'Printer paper and toner',
        date: '2025-11-13'
      },
      {
        headers: {
          'Authorization': `Bearer ${TOKEN}`,
          'Content-Type': 'application/json'
        }
      }
    );

    console.log('Expense created:', response.data.expense.id);
  } catch (error) {
    console.error('Error:', error.response.data);
  }
}

submitExpense();
```

**cURL Example:**

```bash
curl -X POST https://your-backend-url/api/v1/expenses \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 45.99,
    "vendor": "Office Depot",
    "category": "office_supplies",
    "description": "Printer paper and toner",
    "date": "2025-11-13"
  }'
```

### Use Case 2: Upload Receipt with Expense

```python
import requests

API_BASE = "https://your-backend-url/api/v1"
TOKEN = "your_jwt_token"

headers = {
    "Authorization": f"Bearer {TOKEN}"
}

# Step 1: Create expense
expense_response = requests.post(
    f"{API_BASE}/expenses",
    headers={**headers, "Content-Type": "application/json"},
    json={
        "amount": 45.99,
        "vendor": "Office Depot",
        "category": "office_supplies",
        "description": "Supplies"
    }
)

expense_id = expense_response.json()['expense']['id']

# Step 2: Upload receipt
with open('receipt.pdf', 'rb') as receipt_file:
    files = {'file': receipt_file}
    receipt_response = requests.post(
        f"{API_BASE}/expenses/{expense_id}/receipts",
        headers=headers,
        files=files
    )

print(f"Receipt uploaded: {receipt_response.json()['receipt_id']}")
```

### Use Case 3: Fetch Expense Reports

```python
import requests
from datetime import datetime, timedelta

API_BASE = "https://your-backend-url/api/v1"
TOKEN = "your_jwt_token"

headers = {
    "Authorization": f"Bearer {TOKEN}"
}

# Get all expenses from last month
response = requests.get(
    f"{API_BASE}/expenses",
    headers=headers
)

expenses = response.json()

# Filter by date (client-side)
last_month = datetime.now() - timedelta(days=30)
recent_expenses = [
    exp for exp in expenses
    if datetime.fromisoformat(exp['date']) > last_month
]

# Export to CSV
export_response = requests.get(
    f"{API_BASE}/expenses/export?format=csv",
    headers=headers
)

with open('expenses_export.csv', 'wb') as f:
    f.write(export_response.content)
```

### Use Case 4: Approve Expenses via API

```python
import requests

API_BASE = "https://your-backend-url/api/v1"
TOKEN = "manager_jwt_token"  # Manager or admin token

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Approve single expense
approval_data = {
    "expense_id": "exp_abc123",
    "approver_id": "user_xyz789"
}

response = requests.post(
    f"{API_BASE}/expenses/approve",
    headers=headers,
    json=approval_data
)

if response.status_code == 200:
    result = response.json()
    print(f"Approved! Transaction ID: {result['result']['transaction_id']}")
```

### Use Case 5: Bulk Approve Expenses

```python
import requests

API_BASE = "https://your-backend-url/api/v1"
TOKEN = "manager_jwt_token"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Bulk approve
bulk_data = {
    "expense_ids": [
        "exp_abc123",
        "exp_def456",
        "exp_ghi789"
    ]
}

response = requests.post(
    f"{API_BASE}/expenses/bulk-approve",
    headers=headers,
    json=bulk_data
)

result = response.json()
print(f"Approved: {result['approved']}/{result['total']}")
```

---

## Webhooks

Subscribe to real-time events via webhooks.

### Available Events

```
expense.submitted       - New expense submitted
expense.approved        - Expense approved
expense.rejected        - Expense rejected
expense.updated         - Expense modified
receipt.uploaded        - Receipt uploaded
organization.created    - New organization created
subscription.updated    - Subscription changed
```

### Setting Up Webhooks

**Step 1: Configure Webhook Endpoint**

Your endpoint should accept POST requests:

```python
from flask import Flask, request
import hmac
import hashlib

app = Flask(__name__)

WEBHOOK_SECRET = "your_webhook_secret"

@app.route('/webhooks/ap2-expense', methods=['POST'])
def handle_webhook():
    # Verify signature
    signature = request.headers.get('X-AP2-Signature')
    body = request.get_data()

    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_signature):
        return 'Invalid signature', 401

    # Process event
    event = request.json

    if event['type'] == 'expense.approved':
        expense_id = event['data']['expense_id']
        # Send notification, update external system, etc.
        print(f"Expense approved: {expense_id}")

    return 'OK', 200
```

**Step 2: Register Webhook URL**

Contact support or use the admin dashboard to register your webhook URL:
- URL: `https://your-domain.com/webhooks/ap2-expense`
- Events: Select events to subscribe to
- Secret: Generate webhook secret for signature verification

### Webhook Payload Example

```json
{
  "id": "evt_abc123",
  "type": "expense.approved",
  "timestamp": "2025-11-13T19:30:00Z",
  "data": {
    "expense_id": "exp_xyz789",
    "amount": 45.99,
    "vendor": "Office Depot",
    "approver_id": "user_manager1",
    "transaction_id": "txn_stripe_abc"
  }
}
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Success |
| 201 | Created | Resource created |
| 400 | Bad Request | Invalid input |
| 401 | Unauthorized | Missing/invalid token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Duplicate/conflict |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |

### Error Response Format

```json
{
  "detail": "Error message",
  "status_code": 400,
  "error_code": "INVALID_AMOUNT",
  "field": "amount",
  "timestamp": "2025-11-13T19:30:00Z"
}
```

### Common Error Codes

| Error Code | Description | Solution |
|------------|-------------|----------|
| `INVALID_TOKEN` | JWT token expired/invalid | Refresh token |
| `INSUFFICIENT_PERMISSIONS` | User lacks permission | Check user role |
| `EXPENSE_NOT_FOUND` | Expense doesn't exist | Verify expense ID |
| `INVALID_AMOUNT` | Amount validation failed | Check amount > 0 |
| `INVALID_CATEGORY` | Unknown category | Use valid category |
| `RATE_LIMIT_EXCEEDED` | Too many requests | Slow down, retry after |
| `ORGANIZATION_NOT_FOUND` | Org doesn't exist | Check org ID |

### Retry Logic Example

```python
import requests
import time

def api_call_with_retry(url, headers, data, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=data)

            if response.status_code == 429:
                # Rate limited - wait and retry
                retry_after = int(response.headers.get('Retry-After', 60))
                time.sleep(retry_after)
                continue

            if response.status_code >= 500:
                # Server error - exponential backoff
                time.sleep(2 ** attempt)
                continue

            return response

        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)

    raise Exception("Max retries exceeded")
```

---

## Rate Limits

### Default Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| Authentication | 10 requests | 1 minute |
| Expenses (read) | 100 requests | 1 minute |
| Expenses (write) | 20 requests | 1 minute |
| AP2 Payment Mandates | 20 requests | 1 minute |
| AP2 Execute Payment | 10 requests | 1 minute |
| AP2 Complete Flow | 5 requests | 1 minute |
| Webhooks | Unlimited | - |

### Rate Limit Headers

Responses include rate limit information:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1699901234
```

### Handling Rate Limits

```python
import time

def check_rate_limit(response):
    if response.status_code == 429:
        retry_after = int(response.headers.get('Retry-After', 60))
        print(f"Rate limited. Waiting {retry_after} seconds...")
        time.sleep(retry_after)
        return True
    return False
```

---

## Code Examples

### Complete Integration Example (Python)

```python
import requests
from typing import Dict, List, Optional

class AP2ExpenseClient:
    def __init__(self, base_url: str, email: str, password: str):
        self.base_url = base_url
        self.token = None
        self.refresh_token = None
        self._login(email, password)

    def _login(self, email: str, password: str):
        """Authenticate and get token"""
        response = requests.post(
            f"{self.base_url}/auth/login",
            json={"email": email, "password": password}
        )
        response.raise_for_status()
        data = response.json()
        self.token = data['access_token']
        self.refresh_token = data['refresh_token']

    def _headers(self) -> Dict[str, str]:
        """Get authorization headers"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def submit_expense(
        self,
        amount: float,
        vendor: str,
        category: str,
        description: str,
        date: Optional[str] = None
    ) -> Dict:
        """Submit a new expense"""
        data = {
            "amount": amount,
            "vendor": vendor,
            "category": category,
            "description": description
        }
        if date:
            data["date"] = date

        response = requests.post(
            f"{self.base_url}/expenses",
            headers=self._headers(),
            json=data
        )
        response.raise_for_status()
        return response.json()

    def upload_receipt(self, expense_id: str, file_path: str) -> Dict:
        """Upload receipt for an expense"""
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(
                f"{self.base_url}/expenses/{expense_id}/receipts",
                headers={"Authorization": f"Bearer {self.token}"},
                files=files
            )
        response.raise_for_status()
        return response.json()

    def get_expenses(self, status: Optional[str] = None) -> List[Dict]:
        """List expenses, optionally filtered by status"""
        params = {"status": status} if status else {}
        response = requests.get(
            f"{self.base_url}/expenses",
            headers=self._headers(),
            params=params
        )
        response.raise_for_status()
        return response.json()

    def approve_expense(self, expense_id: str, approver_id: str) -> Dict:
        """Approve an expense"""
        response = requests.post(
            f"{self.base_url}/expenses/approve",
            headers=self._headers(),
            json={
                "expense_id": expense_id,
                "approver_id": approver_id
            }
        )
        response.raise_for_status()
        return response.json()

# Usage
client = AP2ExpenseClient(
    base_url="https://your-backend-url/api/v1",
    email="user@company.com",
    password="password123"
)

# Submit expense
expense = client.submit_expense(
    amount=45.99,
    vendor="Office Depot",
    category="office_supplies",
    description="Printer supplies"
)

# Upload receipt
client.upload_receipt(
    expense_id=expense['expense']['id'],
    file_path="receipt.pdf"
)

# List pending expenses
pending = client.get_expenses(status="pending")
print(f"Found {len(pending)} pending expenses")
```

---

## Best Practices

### 1. Security

✅ **Do:**
- Always use HTTPS
- Store tokens securely (never in code)
- Rotate API keys regularly
- Validate webhook signatures
- Use environment variables for secrets

❌ **Don't:**
- Commit tokens to git
- Share API keys
- Use HTTP
- Trust webhook data without verification

### 2. Performance

✅ **Do:**
- Implement exponential backoff for retries
- Cache responses when appropriate
- Use pagination for large lists
- Batch operations when possible
- Monitor rate limits

❌ **Don't:**
- Make unnecessary API calls
- Ignore rate limit headers
- Fetch entire datasets repeatedly

### 3. Error Handling

✅ **Do:**
- Check status codes
- Parse error responses
- Log errors for debugging
- Retry transient failures
- Handle rate limits gracefully

❌ **Don't:**
- Ignore errors
- Retry indefinitely
- Swallow exceptions

### 4. Data Validation

✅ **Do:**
- Validate input before sending
- Check required fields
- Format dates correctly (ISO 8601)
- Verify amounts are positive

❌ **Don't:**
- Send invalid data
- Assume server validation is enough

---

## Support

### API Support
- **Email**: api-support@ap2expense.com
- **Documentation**: https://docs.ap2expense.com/api
- **Status Page**: https://status.ap2expense.com

### Response Times
- Starter: 48 hours
- Professional: 24 hours
- Enterprise: 4 hours

### Additional Resources
- [User Getting Started Guide](USER_GETTING_STARTED.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [Security Documentation](../SECURITY.md)

---

**Happy Integrating!** 🚀

*Last Updated: November 2025*
*Version: 1.0*
