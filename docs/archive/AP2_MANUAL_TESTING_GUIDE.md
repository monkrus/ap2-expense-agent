# AP2 Manual Testing Guide

## Understanding "Used" Mandates

**Key Insight**: Mandates become "used" when a payment is **successfully executed**. Simply creating mandates does NOT count as "used".

## The AP2 Flow

```
1. Create Intent Mandate    ❌ Not used yet
2. Create Cart Mandate      ❌ Not used yet
3. Create Payment Mandate   ❌ Not used yet
4. Execute Payment          ✅ NOW IT'S USED! (if successful)
```

## Method 1: Test via Frontend (Easiest)

### Steps:

1. **Open the application**
   - Navigate to http://localhost:5173

2. **Login or Register**
   - Use credentials:
     - Username: `testuser`
     - Password: `Test123!`

3. **Navigate to AP2 Section**
   - Look for "AP2" or "Mandates" in the navigation
   - Or go directly to: http://localhost:5173/ap2

4. **Check Initial Stats**
   - Look for "Used Mandates" or "Completed Payments" count
   - Should be 0 initially

5. **Create and Execute a Mandate**
   - Click "Create Intent Mandate" or "New Mandate"
   - Fill in constraints (max amount, categories, merchant)
   - Add items to cart
   - Execute the payment

6. **Check Updated Stats**
   - Refresh the AP2 stats page
   - "Used Mandates" should increase by 1

## Method 2: Test via API (Using curl or Postman)

### Step 1: Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "Test123!"
  }'
```

Save the `access_token` from the response.

### Step 2: Check Initial Stats

```bash
curl http://localhost:8000/api/ap2/stats \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

Look for `payment_mandates.completed` count.

### Step 3: Execute Complete Flow (Quick Method)

```bash
curl -X POST http://localhost:8000/api/ap2/complete-flow \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {
        "description": "Test Item",
        "amount": 25.00,
        "category": "OFFICE_SUPPLIES"
      }
    ],
    "merchant": "Amazon",
    "constraints": {
      "max_amount": 100.00,
      "categories": ["OFFICE_SUPPLIES"]
    }
  }'
```

### Step 4: Check Updated Stats

```bash
curl http://localhost:8000/api/ap2/stats \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

The `payment_mandates.completed` count should increase.

## Method 3: Test via Python Script

Run the automated test:

```bash
cd C:\Users\robot\Desktop\ap2-expense-agent
python test_ap2_usage_demo.py
```

This script will:
1. Login
2. Show stats before payment
3. Execute a payment
4. Show stats after payment
5. Display the difference

## Method 4: Step-by-Step API Testing

For a detailed understanding, execute each step separately:

### 1. Create Intent Mandate

```bash
curl -X POST http://localhost:8000/api/ap2/intent-mandate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "constraints": {
      "max_amount": 100.00,
      "categories": ["OFFICE_SUPPLIES"]
    },
    "expiration_hours": 24
  }'
```

Save the `intent_mandate_id`.

### 2. Create Cart Mandate

```bash
curl -X POST http://localhost:8000/api/ap2/cart-mandate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "intent_mandate_id": "YOUR_INTENT_ID",
    "items": [
      {
        "id": "item-1",
        "description": "Office Chair",
        "amount": 35.00,
        "category": "OFFICE_SUPPLIES"
      }
    ],
    "merchant": "Amazon",
    "user_signature": "sig-12345"
  }'
```

Save the `cart_mandate_id`.

### 3. Create Payment Mandate

```bash
curl -X POST http://localhost:8000/api/ap2/payment-mandate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cart_mandate_id": "YOUR_CART_ID",
    "payment_method": "stripe"
  }'
```

Save the `payment_mandate_id`.

### 4. Execute Payment (THIS IS WHEN IT BECOMES "USED")

```bash
curl -X POST http://localhost:8000/api/ap2/execute-payment \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "payment_mandate_id": "YOUR_PAYMENT_ID",
    "nonce": "unique-nonce-12345",
    "timestamp": "2026-02-01T12:00:00Z"
  }'
```

**Note**: Use a unique nonce each time and current timestamp.

## Troubleshooting

### Payment Fails with "failed" Status

**Cause**: Stripe is not configured or payment processing failed.

**Solution**:
- Check if Stripe API keys are configured in backend
- For testing without Stripe, the system should still track usage
- Check backend logs for specific error messages

### "Used Mandates" Count Doesn't Increase

**Possible Reasons**:
1. Payment failed (check cart_mandate.status and payment_mandate.status)
2. Payment is still "pending" (not completed)
3. Database not updated (check backend logs)

**Fix**:
- Only **completed** payments count as "used"
- Check mandate status: `GET /api/ap2/mandate/{mandate_id}/status`

### "Tier Limit Exceeded" Error

This means you've reached the free tier limit for AP2 transactions.

**Current Limits**:
- Free Tier: 5 AP2 transactions per month
- Pro Tier: 50 AP2 transactions per month
- Enterprise Tier: Unlimited

## Viewing All Mandates

```bash
curl http://localhost:8000/api/ap2/user/mandates \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Filter options:
- `?mandate_type=intent` - Only intent mandates
- `?mandate_type=cart` - Only cart mandates
- `?mandate_type=payment` - Only payment mandates
- `?status_filter=completed` - Only completed mandates
- `?limit=10` - Limit results

## Summary

**When do mandates become "used"?**
- When `execute_payment` completes successfully ✅
- When `complete_flow` completes successfully ✅

**When do mandates NOT count as "used"?**
- When you just create an intent mandate ❌
- When you just create a cart mandate ❌
- When you just create a payment mandate ❌
- When payment fails ❌
- When payment is still pending ❌

## Test User Credentials

- **Username**: testuser
- **Password**: Test123!
- **Email**: test@example.com

## Quick Test Command

```bash
# One-line test
python test_ap2_usage_demo.py
```

This will show you the complete flow with before/after stats.
