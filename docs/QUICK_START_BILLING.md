# Quick Start: Billing Implementation

## Immediate Next Steps (30 minutes)

### 1. Install Frontend Dependencies

```bash
cd frontend
npm install
```

This installs:
- `@stripe/stripe-js`
- `@stripe/react-stripe-js`

### 2. Get Stripe Test Keys

1. Go to https://dashboard.stripe.com/test/apikeys
2. Copy your **Publishable key** (starts with `pk_test_`)
3. Copy your **Secret key** (starts with `sk_test_`)

### 3. Configure Frontend

```bash
cd frontend
cp .env.example .env
```

Edit `frontend/.env`:
```env
VITE_API_URL=http://localhost:8000
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_YOUR_KEY_HERE
```

### 4. Configure Backend

Edit `backend/.env`:
```env
# Add/update these lines:
STRIPE_SECRET_KEY=sk_test_YOUR_KEY_HERE
STRIPE_PUBLISHABLE_KEY=pk_test_YOUR_KEY_HERE
```

### 5. Create Stripe Products (Test Mode)

1. Go to https://dashboard.stripe.com/test/products
2. Click **+ Add product**
3. Create 3 products:

**Starter Plan**:
- Name: Starter
- Price: $29/month
- Copy the Price ID (e.g., `price_1ABC123`)

**Professional Plan**:
- Name: Professional
- Price: $99/month
- Copy the Price ID

**Enterprise Plan**:
- Name: Enterprise
- Price: $299/month
- Copy the Price ID

4. Add price IDs to `backend/.env`:
```env
STRIPE_PRICE_ID_STARTER=price_1ABC123starter
STRIPE_PRICE_ID_PROFESSIONAL=price_1ABC123professional
STRIPE_PRICE_ID_ENTERPRISE=price_1ABC123enterprise
```

### 6. Start the Application

**Terminal 1 - Backend**:
```bash
cd backend
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend**:
```bash
cd frontend
npm run dev
```

### 7. Test Payment Flow

1. Open http://localhost:5173
2. Login with your account
3. Go to **Pricing** page
4. Click **Select Plan** on any tier
5. You'll be redirected to Stripe Checkout
6. Use test card: `4242 4242 4242 4242`
   - Expiry: Any future date
   - CVC: Any 3 digits
   - ZIP: Any 5 digits
7. Complete checkout
8. You'll be redirected back to the app
9. Go to **Billing** page - you should see your new subscription!

---

## Test Cards

| Card Number | Description |
|-------------|-------------|
| `4242 4242 4242 4242` | Success |
| `4000 0000 0000 0002` | Card declined |
| `4000 0000 0000 9995` | Insufficient funds |
| `4000 0025 0000 3155` | Requires authentication (3D Secure) |

---

## Verify Everything Works

### ✅ Backend Checks

1. **API Running**:
   ```bash
   curl http://localhost:8000/health
   # Should return: {"status":"healthy"}
   ```

2. **Payment Endpoints Available**:
   ```bash
   curl http://localhost:8000/api/payment/setup-intent \
     -H "Authorization: Bearer <TOKEN>"
   # Should return client_secret
   ```

3. **GCP Webhook Ready**:
   ```bash
   curl http://localhost:8000/api/webhooks/gcp/health
   # Should return: {"status":"healthy"}
   ```

### ✅ Frontend Checks

1. Open browser console (F12)
2. Go to http://localhost:5173/pricing
3. Check for errors - should be none
4. Look for "Stripe.js loaded" or similar
5. Click a plan - should redirect to Stripe

### ✅ Database Checks

```bash
cd backend
python
```

```python
from src.database import SessionLocal
from src.models_billing import BillingTier

db = SessionLocal()
tiers = db.query(BillingTier).all()
print(f"Found {len(tiers)} billing tiers")
for tier in tiers:
    print(f"  - {tier.tier_display_name}: ${tier.base_price}/month")
```

Should show 4 tiers: Free, Starter, Professional, Enterprise

---

## Troubleshooting

### "Stripe is not defined"

**Problem**: Frontend can't load Stripe.js

**Solution**:
1. Check `VITE_STRIPE_PUBLISHABLE_KEY` is set in `frontend/.env`
2. Restart frontend dev server: `npm run dev`
3. Clear browser cache and reload

### "Invalid API key"

**Problem**: Backend using wrong Stripe key

**Solution**:
1. Verify `STRIPE_SECRET_KEY` in `backend/.env` starts with `sk_test_`
2. Copy fresh key from https://dashboard.stripe.com/test/apikeys
3. Restart backend server

### "Price not found"

**Problem**: Stripe price IDs not configured

**Solution**:
1. Check you created products in **Test mode** (toggle in Stripe dashboard)
2. Copy price IDs from product page, not product IDs
3. Price IDs start with `price_`, not `prod_`
4. Add to `backend/.env` and restart

### Payment succeeds but subscription not showing

**Problem**: Webhook not configured or database not updated

**Solution**:
1. Check backend logs for errors
2. Verify organization has stripe_customer_id in database
3. Check OrganizationSubscription table for new record
4. Reload billing page (hard refresh: Ctrl+Shift+R)

---

## What You Should See

### Working Billing Flow

1. **Pricing Page**: 4 tiers displayed with features
2. **Click Plan**: Redirects to `checkout.stripe.com`
3. **Stripe Checkout**: Hosted payment form
4. **Complete Payment**: Redirects back to `localhost:5173/billing?session_id=...`
5. **Billing Dashboard**: Shows active subscription with tier name
6. **Usage Metrics**: Displays current usage (0 initially)
7. **Manage Payment Button**: Opens Stripe Customer Portal

### Customer Portal Should Allow

- View current subscription
- Update payment method (add/remove cards)
- View invoice history
- Cancel subscription (if enabled in Stripe settings)

---

## Next: Production Setup

Once everything works in test mode:

1. **Switch to Live Mode**:
   - Get live keys from https://dashboard.stripe.com/apikeys
   - Create live products/prices
   - Update `.env` files
   - **Important**: Activate your account (Stripe requires business verification)

2. **Configure GCP**:
   - Follow `BILLING_IMPLEMENTATION_COMPLETE.md`
   - Set up service account
   - Register webhook endpoints
   - Deploy Cloud Scheduler jobs

3. **Set Up Webhooks**:
   - Stripe webhook for subscription events
   - GCP webhooks for marketplace events
   - Configure signature verification

4. **Deploy**:
   - Cloud Run / GKE / your hosting platform
   - Set production environment variables
   - Test end-to-end flow
   - Monitor logs for first 24 hours

---

## Support

- Stripe Docs: https://stripe.com/docs
- Stripe Support: https://support.stripe.com
- Test your integration: https://stripe.com/docs/testing

**You're all set!** 🚀

Start the servers, test the payment flow, and verify everything works before moving to production.
