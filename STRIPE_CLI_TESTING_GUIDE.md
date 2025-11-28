# Stripe CLI Testing Guide

## Overview
This guide helps you test Stripe webhooks locally using the Stripe CLI.

## Prerequisites
- ✅ Stripe CLI installed at `C:\Users\robot\stripe-cli\stripe.exe`
- ✅ Backend running at `http://localhost:8000`
- ✅ Stripe API keys configured in `backend/.env`

## Step-by-Step Testing

### Step 1: Authenticate Stripe CLI (First Time Only)

Open a Command Prompt and run:
```cmd
C:\Users\robot\stripe-cli\stripe.exe login
```

This will:
1. Open your browser
2. Ask you to log in to your Stripe account
3. Grant access to the Stripe CLI

### Step 2: Start the Webhook Listener

**Option A: Using the batch file (Recommended)**
```cmd
cd C:\Users\robot\Desktop\ap2-expense-agent
test-stripe-webhook.bat
```

**Option B: Manual command**
```cmd
C:\Users\robot\stripe-cli\stripe.exe listen --forward-to localhost:8000/api/payment/webhooks/stripe --print-secret
```

**Important**: Copy the webhook signing secret that appears!
```
whsec_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Add it to `backend/.env`:
```env
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Step 3: Restart Backend (After Adding Secret)

The backend needs to reload the new webhook secret:
```cmd
# Stop the backend (Ctrl+C)
# Start it again:
cd backend
.venv\Scripts\python.exe -m uvicorn src.api:app --host 127.0.0.1 --port 8000 --reload
```

### Step 4: Trigger Test Events

**Option A: Using the batch file (Recommended)**

Open a NEW Command Prompt (keep the webhook listener running):
```cmd
cd C:\Users\robot\Desktop\ap2-expense-agent
trigger-stripe-test-events.bat
```

**Option B: Manual commands**

Open a NEW Command Prompt and run:

```cmd
# Test checkout completion (most important)
C:\Users\robot\stripe-cli\stripe.exe trigger checkout.session.completed

# Test subscription created
C:\Users\robot\stripe-cli\stripe.exe trigger customer.subscription.created

# Test subscription updated
C:\Users\robot\stripe-cli\stripe.exe trigger customer.subscription.updated

# Test subscription deleted
C:\Users\robot\stripe-cli\stripe.exe trigger customer.subscription.deleted

# Test invoice paid
C:\Users\robot\stripe-cli\stripe.exe trigger invoice.paid

# Test invoice payment failed
C:\Users\robot\stripe-cli\stripe.exe trigger invoice.payment_failed
```

## What to Check

### 1. Webhook Listener Terminal
You should see:
```
→ Forwarding event to localhost:8000/api/payment/webhooks/stripe
✓ Webhook successfully received and processed
```

### 2. Backend Logs
Check for:
```
INFO: Received Stripe webhook: checkout.session.completed
INFO: Successfully processed checkout for org xxx
```

### 3. Database Changes
After `checkout.session.completed`:
```cmd
cd backend
python -c "from src.database import SessionLocal; from src.models_billing import OrganizationSubscription; db = SessionLocal(); print([s.__dict__ for s in db.query(OrganizationSubscription).all()])"
```

## Webhook Event Handlers

Your backend (`backend/src/routes/payment.py`) handles these events:

| Event | Handler | Purpose |
|-------|---------|---------|
| `checkout.session.completed` | `handle_checkout_completed()` | **CRITICAL**: Activates subscription after payment |
| `customer.subscription.created` | `handle_subscription_created()` | Logs subscription creation |
| `customer.subscription.updated` | `handle_subscription_updated()` | Updates subscription status changes |
| `customer.subscription.deleted` | `handle_subscription_deleted()` | Marks subscription as cancelled |
| `invoice.paid` | `handle_invoice_paid()` | Resets billing period, confirms payment |
| `invoice.payment_failed` | `handle_invoice_payment_failed()` | Logs failed payment for alerts |

## Testing Real Checkout Flow

### 1. Get an Authentication Token

Create a test user:
```cmd
curl -X POST "http://localhost:8000/api/v1/auth/register" ^
  -H "Content-Type: application/json" ^
  -d "{\"username\":\"stripetest\",\"password\":\"Test1234!\",\"email\":\"stripe@test.com\",\"full_name\":\"Stripe Test\"}"
```

Login:
```cmd
curl -X POST "http://localhost:8000/api/v1/auth/login" ^
  -H "Content-Type: application/json" ^
  -d "{\"username\":\"stripetest\",\"password\":\"Test1234!\"}"
```

Copy the `access_token` from the response.

### 2. Create a Checkout Session

```cmd
set TOKEN=your_access_token_here

curl -X POST "http://localhost:8000/api/payment/checkout-session?tier_name=starter&billing_cycle=monthly" ^
  -H "Authorization: Bearer %TOKEN%"
```

Response:
```json
{
  "session_id": "cs_test_xxxxx",
  "url": "https://checkout.stripe.com/c/pay/xxxxx",
  "billing_cycle": "monthly"
}
```

### 3. Complete Checkout in Stripe

Open the `url` in your browser and use test card:
- Card: `4242 4242 4242 4242`
- Expiry: Any future date
- CVC: Any 3 digits
- ZIP: Any 5 digits

### 4. Webhook is Triggered Automatically

Stripe will send `checkout.session.completed` event to your webhook listener, which forwards it to your backend!

## Troubleshooting

### "Connection refused" in webhook listener
**Problem**: Backend not running
**Solution**: Start backend at `http://localhost:8000`

### "Webhook signature verification failed"
**Problem**: Wrong or missing `STRIPE_WEBHOOK_SECRET`
**Solution**:
1. Copy secret from webhook listener
2. Add to `backend/.env`
3. Restart backend

### "Organization not found" in logs
**Problem**: Test event uses fake organization IDs
**Solution**: This is expected for `stripe trigger` commands. Real checkout sessions will have correct organization IDs.

### Webhook not reaching backend
**Problem**: Firewall or wrong port
**Solution**:
- Check backend is at `localhost:8000` (not 127.0.0.1)
- Check firewall allows local connections
- Try: `curl http://localhost:8000/docs`

## Checking Results

### View All Billing Events
```cmd
cd backend
python -c "from src.database import SessionLocal; from src.models_billing import BillingEvent; db = SessionLocal(); events = db.query(BillingEvent).order_by(BillingEvent.timestamp.desc()).limit(10).all(); [print(f'{e.timestamp} | {e.event_type} | {e.status}') for e in events]"
```

### View Active Subscriptions
```cmd
cd backend
python -c "from src.database import SessionLocal; from src.models_billing import OrganizationSubscription; db = SessionLocal(); subs = db.query(OrganizationSubscription).filter(OrganizationSubscription.status == 'active').all(); [print(f'Org: {s.organization_id} | Tier: {s.tier_name} | Status: {s.status}') for s in subs]"
```

## Next Steps

After verifying local webhooks work:

1. **Production Setup**: Configure real webhook endpoint in Stripe Dashboard
2. **Webhook Endpoint**: `https://yourdomain.com/api/payment/webhooks/stripe`
3. **Events to Listen For**:
   - ✅ `checkout.session.completed`
   - ✅ `customer.subscription.created`
   - ✅ `customer.subscription.updated`
   - ✅ `customer.subscription.deleted`
   - ✅ `invoice.paid`
   - ✅ `invoice.payment_failed`

## References

- [Stripe CLI Docs](https://stripe.com/docs/stripe-cli)
- [Stripe Webhooks Guide](https://stripe.com/docs/webhooks)
- [Stripe Test Cards](https://stripe.com/docs/testing)
