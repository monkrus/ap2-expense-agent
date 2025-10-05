# Next Steps - AP2 Expense Agent

**Status**: ✅ Backend Implementation Complete
**Date**: October 5, 2025

---

## ✅ What's Been Completed

### Phase 1: Strategy & Planning
- [x] Monetization strategy with 4-tier pricing model
- [x] Google Cloud Marketplace listing strategy
- [x] Revenue projections ($57K-$286K ARR Year 1)
- [x] Go-to-market plan

### Phase 2: Database & Models
- [x] Subscription table with tier management
- [x] Usage tracking table for billing
- [x] Invoice table for monthly billing
- [x] AP2 mandate tables (Intent, Cart, Payment)
- [x] Database migrations tested and working

### Phase 3: Backend Services
- [x] **Billing System**
  - Tier limits configuration
  - Usage tracker with automatic overage calculation
  - Subscription service (create, upgrade, cancel, reactivate)

- [x] **AP2 Payment Flow**
  - Complete 3-step mandate flow
  - Cryptographic signatures
  - Stripe payment processor
  - Webhook handler for automatic sync

### Phase 4: API Routes
- [x] 11 billing/subscription endpoints
- [x] 8 AP2 payment endpoints
- [x] Stripe webhook endpoint
- [x] Complete API documentation

### Phase 5: Tools & Documentation
- [x] Stripe setup automation script
- [x] .env.example with all configurations
- [x] Comprehensive API documentation
- [x] Implementation summary
- [x] Google Cloud Marketplace manifest

---

## 🚀 Immediate Next Steps (Week 1)

### 1. Set Up Stripe Account

**Time**: 30 minutes

```bash
# 1. Create Stripe account
https://dashboard.stripe.com/register

# 2. Get API keys
https://dashboard.stripe.com/apikeys

# 3. Copy to .env
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
```

### 2. Create Stripe Products

**Time**: 15 minutes

```bash
# Run the setup script
cd backend
python scripts/setup_stripe.py

# Follow prompts to create:
# - Starter ($29/mo)
# - Professional ($99/mo)
# - Enterprise ($399/mo)

# Copy Price IDs to .env
```

### 3. Configure Webhooks

**Time**: 10 minutes

```bash
# 1. Go to Stripe Dashboard
https://dashboard.stripe.com/webhooks

# 2. Create endpoint: http://localhost:8000/webhooks/stripe

# 3. Select events:
#    - payment_intent.succeeded
#    - payment_intent.payment_failed
#    - customer.subscription.created
#    - customer.subscription.updated
#    - customer.subscription.deleted
#    - invoice.paid
#    - invoice.payment_failed

# 4. Copy webhook secret to .env
STRIPE_WEBHOOK_SECRET=whsec_...
```

### 4. Test API Endpoints

**Time**: 30 minutes

```bash
# Start the server
cd backend
uvicorn src.api:app --reload

# Test in browser
http://localhost:8000/docs

# Test endpoints:
# 1. GET /api/billing/tiers
# 2. POST /api/billing/subscription (create trial)
# 3. GET /api/billing/subscription
# 4. POST /api/billing/usage/track
# 5. GET /api/billing/usage/monthly
```

---

## 📋 Week 2-3: Frontend Integration

### Build React Components

**Priority: High**

1. **Pricing Page**
   - Display 4 tiers
   - Feature comparison table
   - "Start Free Trial" buttons
   - Stripe Checkout integration

2. **Subscription Dashboard**
   - Current plan display
   - Usage statistics with charts
   - Upgrade/downgrade buttons
   - Cancel subscription option

3. **Billing History**
   - Invoice list
   - Payment history
   - Download invoices

4. **Usage Dashboard**
   - Monthly usage charts
   - Remaining limits
   - Overage warnings
   - Usage breakdown by type

5. **AP2 Payment UI**
   - Intent mandate creation form
   - Cart review interface
   - Payment confirmation
   - Transaction history

### Frontend Files to Create

```
frontend/src/
├── pages/
│   ├── PricingPage.tsx
│   ├── SubscriptionDashboard.tsx
│   └── BillingHistory.tsx
├── components/
│   ├── PricingCard.tsx
│   ├── UsageChart.tsx
│   ├── SubscriptionStatus.tsx
│   ├── AP2PaymentFlow.tsx
│   └── InvoiceList.tsx
└── services/
    ├── billing.service.ts
    ├── subscription.service.ts
    └── ap2.service.ts
```

---

## 🔧 Week 4: Testing & Refinement

### 1. Integration Testing

```bash
# Test complete flows
1. User signs up
2. Creates subscription (trial)
3. Submits expenses
4. Uses AI categorization (track usage)
5. Executes AP2 payment
6. Upgrades tier
7. Views usage dashboard
8. Cancels subscription
```

### 2. Stripe Testing

Use test cards:
- Success: `4242 4242 4242 4242`
- Decline: `4000 0000 0000 0002`
- 3DS: `4000 0025 0000 3155`

### 3. Webhook Testing

```bash
# Install Stripe CLI
stripe listen --forward-to localhost:8000/webhooks/stripe

# Trigger test events
stripe trigger payment_intent.succeeded
stripe trigger customer.subscription.created
```

---

## ☁️ Week 5-6: Google Cloud Deployment

### 1. Create GCP Project

```bash
# Install Google Cloud SDK
# https://cloud.google.com/sdk/docs/install

# Create project
gcloud projects create ap2-expense-agent --name="AP2 Expense Management"

# Set as default
gcloud config set project ap2-expense-agent

# Enable APIs
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  storage.googleapis.com \
  secretmanager.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com
```

### 2. Set Up Cloud SQL

```bash
# Create PostgreSQL instance
gcloud sql instances create ap2-db \
  --database-version=POSTGRES_15 \
  --tier=db-custom-2-8192 \
  --region=us-central1 \
  --backup \
  --enable-bin-log

# Create database
gcloud sql databases create expenses --instance=ap2-db

# Create user
gcloud sql users create ap2user \
  --instance=ap2-db \
  --password=SECURE_PASSWORD_HERE
```

### 3. Store Secrets

```bash
# Store Stripe keys
echo -n "sk_live_..." | gcloud secrets create stripe-secret-key --data-file=-
echo -n "pk_live_..." | gcloud secrets create stripe-publishable-key --data-file=-
echo -n "whsec_..." | gcloud secrets create stripe-webhook-secret --data-file=-

# Store JWT secret
python -c "import secrets; print(secrets.token_urlsafe(32))" | \
  gcloud secrets create jwt-secret --data-file=-
```

### 4. Deploy to Cloud Run

```bash
# Build and deploy backend
gcloud run deploy ap2-expense-backend \
  --source backend/ \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars DATABASE_URL=postgresql://... \
  --set-secrets STRIPE_SECRET_KEY=stripe-secret-key:latest

# Build and deploy frontend
gcloud run deploy ap2-expense-frontend \
  --source frontend/ \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated
```

### 5. Configure Domain

```bash
# Map custom domain
gcloud run domain-mappings create --service=ap2-expense-backend \
  --domain=api.ap2expense.com \
  --region=us-central1
```

---

## 📊 Week 7-8: Google Cloud Marketplace

### 1. Prepare Listing Materials

**Required Assets:**
- [x] Logo (512x512 PNG) - Create
- [x] Icon (128x128 PNG) - Create
- [x] Screenshots (5 images) - Create
  - Dashboard overview
  - AP2 payment flow
  - Receipt OCR
  - Analytics
  - Admin panel
- [x] Demo video (2-3 minutes) - Create
- [x] Product listing copy - ✅ Done

### 2. Submit to Marketplace

```bash
# 1. Go to Cloud Marketplace Producer Portal
https://console.cloud.google.com/producer-portal

# 2. Create new product listing
# 3. Upload manifest: marketplace/gcp-marketplace-manifest.yaml
# 4. Upload assets
# 5. Submit for review (2-4 weeks approval)
```

### 3. Beta Testing

- Recruit 5-10 beta customers
- Offer 3 months free
- Collect feedback
- Iterate on features

---

## 🎯 Success Metrics

### Technical KPIs
- [ ] API response time <100ms average
- [ ] 99.9% uptime SLA
- [ ] Zero payment processing errors
- [ ] 100% webhook delivery rate

### Business KPIs
- [ ] 10 beta customers (Month 1)
- [ ] 50 paying customers (Month 6)
- [ ] $5,000 MRR (Month 6)
- [ ] 90%+ customer satisfaction
- [ ] <5% monthly churn

---

## 📝 Checklist Before Launch

### Development
- [x] Database migrations working
- [x] API routes implemented
- [x] AP2 protocol integration
- [x] Stripe integration
- [x] Webhook handlers
- [ ] Frontend UI complete
- [ ] Integration tests passing
- [ ] Load testing completed

### Security
- [ ] JWT secrets rotated
- [ ] HTTPS enforced
- [ ] Rate limiting configured
- [ ] SQL injection testing
- [ ] XSS prevention verified
- [ ] CORS properly configured
- [ ] Webhook signature verification working

### Stripe Setup
- [ ] Live mode API keys
- [ ] Products created
- [ ] Prices configured
- [ ] Webhooks configured
- [ ] Test payments successful
- [ ] Refund flow tested

### GCP Setup
- [ ] Cloud SQL running
- [ ] Cloud Run deployed
- [ ] Secrets configured
- [ ] Monitoring enabled
- [ ] Logging configured
- [ ] Backups automated
- [ ] Custom domain mapped

### Marketplace
- [ ] Listing created
- [ ] Assets uploaded
- [ ] Pricing configured
- [ ] Terms of service
- [ ] Privacy policy
- [ ] Support documentation
- [ ] Beta testing complete
- [ ] Google approval received

---

## 💡 Quick Commands Reference

### Development

```bash
# Start backend
cd backend
uvicorn src.api:app --reload

# Start frontend
cd frontend
npm run dev

# Run migrations
cd backend
alembic upgrade head

# Create new migration
alembic revision -m "Description"

# Run tests
pytest tests/ -v

# Setup Stripe
python scripts/setup_stripe.py
```

### Deployment

```bash
# Deploy backend
gcloud run deploy ap2-expense-backend --source backend/

# Deploy frontend
gcloud run deploy ap2-expense-frontend --source frontend/

# View logs
gcloud run services logs read ap2-expense-backend --limit=100

# Run migration in production
gcloud run jobs execute migrate-db
```

---

## 📞 Support Resources

- **Documentation**: See IMPLEMENTATION_SUMMARY.md, API_DOCUMENTATION.md
- **Monetization**: See MONETIZATION_STRATEGY.md
- **GCP Marketplace**: See marketplace/gcp-marketplace-manifest.yaml
- **Stripe Docs**: https://stripe.com/docs
- **GCP Docs**: https://cloud.google.com/run/docs
- **AP2 Protocol**: https://github.com/google-agentic-commerce/AP2

---

## 🎉 You're Ready!

All backend infrastructure is complete. Now it's time to:

1. ✅ Set up Stripe (15 min)
2. ✅ Test the API (30 min)
3. 🎨 Build the frontend (2-3 weeks)
4. ☁️ Deploy to GCP (1 week)
5. 🚀 Launch on Marketplace (submit + 2-4 week approval)

**Target Launch Date**: 8 weeks from now

**Good luck!** 🚀
