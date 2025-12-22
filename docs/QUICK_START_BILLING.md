# Quick Start: Marketplace Billing

This app uses Google Cloud Marketplace for subscription billing. There is no
direct Stripe checkout flow for plan upgrades.

## 1. Configure Backend (Marketplace)

Set these in `backend/.env` (values are examples):

```env
ENABLE_GCP_MARKETPLACE=true
GCP_PROJECT_ID=your-gcp-project-id
GCP_PROVIDER_ID=your-provider-id
GCP_SERVICE_ACCOUNT_PATH=/path/to/service-account.json
GCP_WEBHOOK_SECRET=your-webhook-secret
GCP_WEBHOOK_AUDIENCE=your-webhook-audience
GCP_USAGE_REPORTING_ENABLED=true
```

For full Marketplace setup details, see `docs/MARKETPLACE_READINESS_FINAL.md`
and `marketplace/gcp-marketplace-manifest.yaml`.

## 2. Seed Billing Tiers

```bash
cd backend
python scripts/seed_billing_tiers.py
```

Ensure your Marketplace SKU map is set for metering (env or config):

```env
GCP_MARKETPLACE_SKU_MAP={"expenses":{"unit":"expense","sku":"SKU_EXP"},"ai_categorizations":{"unit":"ai_categorization","sku":"SKU_AI"},"ap2_transactions":{"unit":"ap2_transaction","sku":"SKU_AP2"}}
```

## 3. Configure Frontend Marketplace Links

Set the Marketplace listing URL so upgrade/manage buttons open the listing:

```env
VITE_GCP_MARKETPLACE_URL=https://console.cloud.google.com/marketplace/product/your-project/your-product
```

## 4. Start the App

Backend:

```bash
cd backend
uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## 5. Verify Marketplace Billing

Once your org has an active entitlement:

- `GET /api/billing/org/subscription` returns `active` or `trialing`.
- `GET /api/billing/org/usage/monthly` returns usage with limits.
- Pricing and Billing pages open the Marketplace listing for upgrades.

## Local Development (No Marketplace)

For local development without Marketplace, set:

```env
ENABLE_GCP_MARKETPLACE=false
```

Usage tracking will still work, but subscriptions are not required.
