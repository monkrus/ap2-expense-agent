# Stripe Testing - Quick Start Guide

## I Just Want to Test Webhooks!

### Option 1: Automated Test (No Stripe CLI needed)
```bash
python test_stripe_complete.py
```

This will:
- ✅ Create a test user
- ✅ Create an organization
- ✅ Create 6 checkout sessions (all products)
- ✅ Test webhook endpoint
- ✅ Show you checkout URLs to complete in browser

### Option 2: Real Webhook Testing (Requires Stripe CLI)

#### Step 1: Login to Stripe CLI (One-time)
```cmd
stripe-login.bat
```
- Opens browser
- Login to Stripe
- Authorize the CLI
- Done!

#### Step 2: Start Webhook Listener
```cmd
test-stripe-webhook.bat
```
- Forwards webhooks to your backend
- **IMPORTANT**: Copy the webhook secret (whsec_...)
- Add it to `backend/.env`: `STRIPE_WEBHOOK_SECRET=whsec_...`
- Restart your backend

#### Step 3: Trigger Test Events
```cmd
trigger-stripe-test-events.bat
```
- Interactive menu
- Choose events to trigger
- Or select "Run ALL" to test everything

---

## What Each File Does

| File | Purpose |
|------|---------|
| `stripe-login.bat` | Authenticate Stripe CLI (run once) |
| `test-stripe-webhook.bat` | Start listening for webhooks |
| `trigger-stripe-test-events.bat` | Send test events to webhooks |
| `test_stripe_complete.py` | Automated testing without CLI |
| `STRIPE_TESTING_RESULTS.md` | Detailed test results report |
| `STRIPE_CLI_TESTING_GUIDE.md` | Complete documentation |

---

## Quick Commands

### Check Backend Status
```bash
curl http://localhost:8000/health
```

### Create a Checkout Session Manually
```bash
# 1. Get a token (replace username/password)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"your_user","password":"your_pass"}'

# 2. Create checkout session
curl -X POST "http://localhost:8000/api/payment/checkout-session?tier_name=starter&billing_cycle=monthly" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Check Database for Stripe Data
```bash
cd backend
python -c "from src.database import SessionLocal; from src.models import Organization; db = SessionLocal(); orgs = [o for o in db.query(Organization).all() if o.stripe_customer_id]; print(f'Organizations with Stripe: {len(orgs)}'); [print(f'{o.name}: {o.stripe_customer_id}') for o in orgs]"
```

---

## Test Results (Latest Run)

✅ **6/6 Checkout Sessions Created Successfully**

All tier/billing cycle combinations working:
- Starter Monthly ✅
- Starter Annual ✅
- Professional Monthly ✅
- Professional Annual ✅
- Enterprise Monthly ✅
- Enterprise Annual ✅

---

## Troubleshooting

### "System cannot find the path"
**Solution**: Stripe CLI path detection is automatic now. Just run the batch file again.

### "Checkout session failed: 500"
**Problem**: User doesn't have an organization
**Solution**: Use `test_stripe_complete.py` which creates everything automatically

### "Webhook signature verification failed"
**Expected**: This is normal without webhook secret configured
**Solution**: Add `STRIPE_WEBHOOK_SECRET` to `.env` and restart backend

### Backend not running
```bash
cd backend
.venv\Scripts\python.exe -m uvicorn src.api:app --host 127.0.0.1 --port 8000 --reload
```

---

## Test Card Numbers

Use these in Stripe Checkout:

| Card Number | Result |
|-------------|--------|
| 4242 4242 4242 4242 | Success |
| 4000 0000 0000 0002 | Declined |
| 4000 0000 0000 9995 | Insufficient funds |
| 4000 0025 0000 3155 | Requires authentication (3D Secure) |

Expiry: Any future date
CVC: Any 3 digits
ZIP: Any 5 digits

---

## Sample Webhook Events

These events are handled by your backend:

| Event | What it Does |
|-------|--------------|
| `checkout.session.completed` | ⭐ **MOST IMPORTANT**: Activates subscription after payment |
| `customer.subscription.created` | Logs subscription creation |
| `customer.subscription.updated` | Updates subscription status |
| `customer.subscription.deleted` | Marks subscription as cancelled |
| `invoice.paid` | Confirms payment received |
| `invoice.payment_failed` | Logs failed payment |

To trigger these events:
```cmd
trigger-stripe-test-events.bat
```

---

## Next Steps After Testing

1. ✅ Verify all tests pass
2. ✅ Test real checkout flow in browser
3. ✅ Configure production webhook in Stripe Dashboard
4. ✅ Update to production API keys
5. ✅ Deploy to production environment

---

## Need Help?

See detailed documentation:
- **Testing Results**: `STRIPE_TESTING_RESULTS.md`
- **CLI Guide**: `STRIPE_CLI_TESTING_GUIDE.md`
- **Backend Code**: `backend/src/routes/payment.py`

Or check Stripe docs:
- [Testing Webhooks](https://stripe.com/docs/webhooks/test)
- [Test Cards](https://stripe.com/docs/testing)
- [Checkout Sessions](https://stripe.com/docs/payments/checkout)
