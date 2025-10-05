# AP2 Expense Agent - API Documentation

**Version**: 1.0.0
**Base URL**: `http://localhost:8000` (development)
**Production**: `https://your-domain.com`

---

## Table of Contents

1. [Authentication](#authentication)
2. [Billing & Subscriptions](#billing--subscriptions)
3. [AP2 Payments](#ap2-payments)
4. [Webhooks](#webhooks)
5. [Error Codes](#error-codes)
6. [Rate Limiting](#rate-limiting)

---

## Authentication

All API endpoints (except `/health` and `/webhooks/*`) require authentication using JWT tokens.

### Get Token

**POST** `/api/auth/token`

```json
{
  "username": "user@example.com",
  "password": "your-password"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Use Token

Include in Authorization header:
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

---

## Billing & Subscriptions

### Get All Tiers

Get information about all subscription tiers.

**GET** `/api/billing/tiers`

**Response:**
```json
{
  "tiers": [
    {
      "tier": "starter",
      "name": "Starter",
      "price_monthly": 29.00,
      "max_users": 25,
      "max_expenses_per_month": 100,
      "max_ai_categorizations": 500,
      "max_ap2_transactions": 0,
      "ocr_scans_included": 100,
      "data_retention_days": 30,
      "priority_support": false,
      "custom_integrations": false,
      "sso_enabled": false
    },
    {
      "tier": "professional",
      "name": "Professional",
      "price_monthly": 99.00,
      "max_users": 100,
      "max_expenses_per_month": null,
      "max_ai_categorizations": 5000,
      "max_ap2_transactions": 100,
      "ocr_scans_included": 1000,
      "data_retention_days": 90,
      "priority_support": true,
      "custom_integrations": false,
      "sso_enabled": false
    }
  ]
}
```

### Get Tier Info

**GET** `/api/billing/tiers/{tier}`

**Parameters:**
- `tier`: `starter`, `professional`, `enterprise`, or `enterprise_plus`

### Get Subscription Status

Get current user's subscription status.

**GET** `/api/billing/subscription`

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "has_subscription": true,
  "tier": "professional",
  "tier_name": "Professional",
  "status": "active",
  "current_period_start": "2025-10-01T00:00:00Z",
  "current_period_end": "2025-11-01T00:00:00Z",
  "trial_end": null,
  "limits": {
    "max_users": 100,
    "max_expenses_per_month": null,
    "max_ai_categorizations": 5000,
    "max_ap2_transactions": 100,
    "ocr_scans_included": 1000,
    "data_retention_days": 90,
    "priority_support": true,
    "custom_integrations": false,
    "sso_enabled": false
  },
  "stripe_customer_id": "cus_123456789",
  "stripe_subscription_id": "sub_123456789"
}
```

### Create Subscription

**POST** `/api/billing/subscription`

**Headers:**
- `Authorization: Bearer <token>`

**Request:**
```json
{
  "tier": "professional",
  "trial_days": 14
}
```

**Response:**
```json
{
  "success": true,
  "subscription_id": "sub_abc123",
  "tier": "professional",
  "status": "trialing",
  "trial_end": "2025-10-19T00:00:00Z"
}
```

### Upgrade Subscription

**PUT** `/api/billing/subscription/{subscription_id}/upgrade`

**Headers:**
- `Authorization: Bearer <token>`

**Request:**
```json
{
  "new_tier": "enterprise"
}
```

**Response:**
```json
{
  "success": true,
  "subscription_id": "sub_abc123",
  "new_tier": "enterprise",
  "status": "active"
}
```

### Cancel Subscription

**DELETE** `/api/billing/subscription/{subscription_id}`

**Headers:**
- `Authorization: Bearer <token>`

**Query Parameters:**
- `immediate` (optional, default: false): Cancel immediately vs. at period end

**Response:**
```json
{
  "success": true,
  "subscription_id": "sub_abc123",
  "status": "canceled",
  "canceled_at": "2025-10-05T10:30:00Z",
  "ends_at": "2025-11-01T00:00:00Z"
}
```

### Reactivate Subscription

**POST** `/api/billing/subscription/{subscription_id}/reactivate`

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "subscription_id": "sub_abc123",
  "status": "active"
}
```

### Track Usage

Track a billable usage event.

**POST** `/api/billing/usage/track`

**Headers:**
- `Authorization: Bearer <token>`

**Request:**
```json
{
  "usage_type": "ai_categorization",
  "quantity": 1,
  "metadata": {
    "expense_id": "exp_123",
    "category": "office_supplies"
  }
}
```

**Usage Types:**
- `expense`: Expense submission
- `ai_categorization`: AI expense categorization
- `ocr_scan`: Receipt OCR scan
- `ap2_transaction`: AP2 automated payment

**Response:**
```json
{
  "success": true,
  "usage_record_id": "usage_xyz789",
  "billable": false,
  "fee": 0
}
```

### Get Monthly Usage

**GET** `/api/billing/usage/monthly`

**Headers:**
- `Authorization: Bearer <token>`

**Query Parameters:**
- `usage_type` (optional): Filter by specific usage type

**Response:**
```json
{
  "period_start": "2025-10-01T00:00:00Z",
  "period_end": "2025-10-05T12:00:00Z",
  "usage": {
    "ai_categorization": {
      "quantity": 250,
      "fees": 0,
      "count": 250
    },
    "ap2_transaction": {
      "quantity": 45,
      "fees": 0,
      "count": 45
    }
  },
  "total_overage_fees": 0
}
```

### Check Usage Limit

Check if user has exceeded tier limit for specific usage type.

**GET** `/api/billing/usage/check-limit/{usage_type}`

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "usage_type": "ai_categorization",
  "exceeded": false,
  "current_usage": 250,
  "limit": 5000,
  "unlimited": false
}
```

---

## AP2 Payments

Complete AP2 Protocol implementation for cryptographically-verified payments.

### Complete AP2 Flow (Simple)

Execute complete AP2 payment flow in one call.

**POST** `/api/ap2/complete-flow`

**Headers:**
- `Authorization: Bearer <token>`

**Request:**
```json
{
  "items": [
    {
      "id": "exp_123",
      "description": "Office supplies",
      "amount": 45.99,
      "category": "office_supplies"
    }
  ],
  "merchant": "Amazon",
  "constraints": {
    "max_amount": 100.00,
    "categories": ["office_supplies"]
  },
  "stripe_customer_id": "cus_123456789"
}
```

**Response:**
```json
{
  "intent_mandate_id": "intent_abc123",
  "cart_mandate_id": "cart_xyz789",
  "payment_mandate_id": "payment_def456",
  "payment_result": {
    "success": true,
    "payment_mandate_id": "payment_def456",
    "transaction_id": "pi_123456789",
    "amount": 45.99,
    "status": "completed"
  },
  "ap2_flow_complete": true
}
```

### Create Intent Mandate

Step 1: User authorizes AI agent to make purchases.

**POST** `/api/ap2/intent-mandate`

**Headers:**
- `Authorization: Bearer <token>`

**Request:**
```json
{
  "constraints": {
    "max_amount": 1000.00,
    "categories": ["office_supplies", "software"],
    "merchants": ["Amazon", "Microsoft"],
    "approval_required": true
  },
  "expiration_hours": 24
}
```

**Response:**
```json
{
  "success": true,
  "intent_mandate_id": "intent_abc123",
  "status": "active",
  "timestamp": "2025-10-05T10:00:00Z",
  "expiration": "2025-10-06T10:00:00Z",
  "signature": "a1b2c3d4e5f6..."
}
```

### Create Cart Mandate

Step 2: Agent builds shopping cart and gets approval.

**POST** `/api/ap2/cart-mandate`

**Headers:**
- `Authorization: Bearer <token>`

**Request:**
```json
{
  "intent_mandate_id": "intent_abc123",
  "items": [
    {
      "id": "exp_123",
      "description": "Office supplies",
      "amount": 45.99,
      "category": "office_supplies"
    }
  ],
  "merchant": "Amazon",
  "user_signature": "user_sig_xyz789"
}
```

**Response:**
```json
{
  "success": true,
  "cart_mandate_id": "cart_xyz789",
  "status": "pending",
  "total": 45.99,
  "merchant": "Amazon",
  "items_count": 1,
  "timestamp": "2025-10-05T10:05:00Z"
}
```

### Create Payment Mandate

Step 3: Prepare for payment execution.

**POST** `/api/ap2/payment-mandate`

**Headers:**
- `Authorization: Bearer <token>`

**Request:**
```json
{
  "cart_mandate_id": "cart_xyz789",
  "payment_method": "stripe"
}
```

**Response:**
```json
{
  "success": true,
  "payment_mandate_id": "payment_def456",
  "status": "pending",
  "payment_method": "stripe",
  "timestamp": "2025-10-05T10:10:00Z"
}
```

### Execute Payment

Step 4: Execute payment through Stripe.

**POST** `/api/ap2/execute-payment`

**Headers:**
- `Authorization: Bearer <token>`

**Request:**
```json
{
  "payment_mandate_id": "payment_def456",
  "stripe_customer_id": "cus_123456789"
}
```

**Response:**
```json
{
  "success": true,
  "payment_mandate_id": "payment_def456",
  "transaction_id": "pi_123456789",
  "amount": 45.99,
  "status": "completed"
}
```

### Get Mandate Status

**GET** `/api/ap2/mandate/{mandate_id}/status`

**Headers:**
- `Authorization: Bearer <token>`

**Query Parameters:**
- `mandate_type`: `intent`, `cart`, or `payment`

**Response:**
```json
{
  "id": "payment_def456",
  "type": "payment",
  "status": "completed",
  "timestamp": "2025-10-05T10:10:00Z",
  "created_at": "2025-10-05T10:10:00Z"
}
```

### Get User Mandates

Get all mandates for current user.

**GET** `/api/ap2/user/mandates`

**Headers:**
- `Authorization: Bearer <token>`

**Query Parameters:**
- `mandate_type` (optional): Filter by type (`intent`, `cart`, `payment`)
- `status_filter` (optional): Filter by status (`active`, `pending`, `completed`, `failed`)
- `limit` (default: 50): Max results

**Response:**
```json
{
  "mandates": [
    {
      "type": "payment",
      "id": "payment_def456",
      "status": "completed",
      "payment_method": "stripe",
      "timestamp": "2025-10-05T10:10:00Z",
      "created_at": "2025-10-05T10:10:00Z"
    }
  ],
  "count": 1
}
```

### Get AP2 Stats

**GET** `/api/ap2/stats`

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "intent_mandates": {
    "active": 5,
    "expired": 2
  },
  "cart_mandates": {
    "pending": 1,
    "completed": 10,
    "failed": 1
  },
  "payment_mandates": {
    "pending": 1,
    "completed": 10,
    "failed": 1
  },
  "total_amount_processed": 1234.56
}
```

---

## Webhooks

### Stripe Webhook

Receive events from Stripe.

**POST** `/webhooks/stripe`

**Headers:**
- `stripe-signature`: Webhook signature for verification

**Events Handled:**
- `payment_intent.succeeded`
- `payment_intent.payment_failed`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.paid`
- `invoice.payment_failed`

**Response:**
```json
{
  "status": "success",
  "event_type": "payment_intent.succeeded"
}
```

---

## Error Codes

| Code | Message | Description |
|------|---------|-------------|
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |

**Error Response Format:**
```json
{
  "detail": "Error message here"
}
```

---

## Rate Limiting

API endpoints are rate-limited to prevent abuse.

**Limits:**
- General endpoints: 60 requests/minute
- Auth endpoints: 5 requests/minute

**Rate Limit Headers:**
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1633024800
```

---

## Testing

### Test Cards (Stripe)

Use these test card numbers in development:

**Success:**
- `4242 4242 4242 4242`

**Decline:**
- `4000 0000 0000 0002`

**Requires Authentication:**
- `4000 0025 0000 3155`

**More test cards**: https://stripe.com/docs/testing

---

## Support

- **Documentation**: https://docs.ap2expense.com
- **API Issues**: https://github.com/monkrus/ap2-expense-agent/issues
- **Email**: support@ap2expense.com

---

**Generated**: 2025-10-05
**API Version**: 1.0.0
