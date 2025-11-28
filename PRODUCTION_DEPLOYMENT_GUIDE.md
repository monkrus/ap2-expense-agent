# Production Deployment Guide - AP2 Expense Agent

**Last Updated**: 2025-11-28
**Target Platform**: Google Cloud Run + GCP Marketplace
**Status**: Ready for Production Deployment

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Google Cloud Setup](#google-cloud-setup)
3. [Stripe Production Configuration](#stripe-production-configuration)
4. [Environment Secrets Configuration](#environment-secrets-configuration)
5. [Database Migration](#database-migration)
6. [Deployment Steps](#deployment-steps)
7. [Post-Deployment Verification](#post-deployment-verification)
8. [Rollback Procedures](#rollback-procedures)
9. [Monitoring & Alerts](#monitoring--alerts)

---

## Pre-Deployment Checklist

### ✅ Code & Testing
- [ ] All tests passing (`pytest` + `npm test`)
- [ ] Security audit completed (SECURITY_AUDIT_REPORT_FINAL.md)
- [ ] Dependency vulnerabilities addressed (DEPENDENCY_AUDIT_REPORT.md)
- [ ] Code review completed
- [ ] Git main branch is clean and up-to-date

### ✅ Infrastructure
- [ ] GCP project created
- [ ] Billing enabled on GCP project
- [ ] Cloud Run API enabled
- [ ] Cloud SQL API enabled (if using Cloud SQL)
- [ ] Secret Manager API enabled
- [ ] Container Registry API enabled

### ✅ Secrets Prepared
- [ ] Production database credentials
- [ ] JWT secret keys (generated)
- [ ] Stripe production API keys
- [ ] Stripe webhook signing secret
- [ ] GCP service account credentials
- [ ] (Optional) Email service credentials

### ✅ Domain & SSL
- [ ] Domain name purchased and verified
- [ ] DNS records ready to update
- [ ] SSL certificate (managed by GCP or custom)

---

## Google Cloud Setup

### 1. Create GCP Project

```bash
# Set project ID (must be globally unique)
export GCP_PROJECT_ID="ap2-expense-prod"
export GCP_REGION="us-central1"

# Create project
gcloud projects create $GCP_PROJECT_ID --name="AP2 Expense Management"

# Set as active project
gcloud config set project $GCP_PROJECT_ID

# Enable billing (replace BILLING_ACCOUNT_ID)
gcloud beta billing projects link $GCP_PROJECT_ID \
  --billing-account=BILLING_ACCOUNT_ID
```

### 2. Enable Required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  containerregistry.googleapis.com \
  cloudresourcemanager.googleapis.com \
  compute.googleapis.com \
  servicenetworking.googleapis.com
```

### 3. Create Service Account

```bash
# Create service account for Cloud Run
gcloud iam service-accounts create ap2-expense-backend \
  --display-name="AP2 Expense Backend Service Account"

# Grant necessary permissions
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:ap2-expense-backend@$GCP_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:ap2-expense-backend@$GCP_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 4. Set Up Database (Cloud SQL PostgreSQL)

```bash
# Create Cloud SQL instance
gcloud sql instances create ap2-expense-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=$GCP_REGION \
  --root-password="CHANGE_THIS_SECURE_PASSWORD"

# Create database
gcloud sql databases create ap2_expense \
  --instance=ap2-expense-db

# Create database user
gcloud sql users create ap2user \
  --instance=ap2-expense-db \
  --password="CHANGE_THIS_SECURE_PASSWORD"
```

**Production Recommendation**: Use `db-n1-standard-1` or higher for production workloads.

### 5. Create Secrets in Secret Manager

```bash
# Database URL
echo -n "postgresql://ap2user:YOUR_DB_PASSWORD@/ap2_expense?host=/cloudsql/$GCP_PROJECT_ID:$GCP_REGION:ap2-expense-db" | \
  gcloud secrets create database-url --data-file=-

# JWT Secret (generate random 64-byte key)
openssl rand -hex 64 | gcloud secrets create jwt-secret --data-file=-

# Stripe Secret Key (production)
echo -n "sk_live_YOUR_STRIPE_SECRET_KEY" | \
  gcloud secrets create stripe-secret-key --data-file=-

# Stripe Publishable Key (production)
echo -n "pk_live_YOUR_STRIPE_PUBLISHABLE_KEY" | \
  gcloud secrets create stripe-publishable-key --data-file=-

# Stripe Webhook Secret (will be generated after deploying)
echo -n "whsec_YOUR_WEBHOOK_SECRET" | \
  gcloud secrets create stripe-webhook-secret --data-file=-
```

### 6. Grant Secret Access to Service Account

```bash
# Grant access to all secrets
for secret in database-url jwt-secret stripe-secret-key stripe-publishable-key stripe-webhook-secret; do
  gcloud secrets add-iam-policy-binding $secret \
    --member="serviceAccount:ap2-expense-backend@$GCP_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
done
```

---

## Stripe Production Configuration

### 1. Switch to Production Mode in Stripe Dashboard

1. Log in to [Stripe Dashboard](https://dashboard.stripe.com)
2. Toggle "View test data" OFF (top right)
3. Navigate to **Developers** → **API keys**
4. Copy **Publishable key** and **Secret key**
5. Store in GCP Secret Manager (done in step above)

### 2. Create Production Pricing

Navigate to **Products** → **Create product** and create 6 products:

#### Starter Tier
- **Product Name**: AP2 Expense - Starter
- **Monthly Price**: $29/month
- **Annual Price**: $290/year (save ~16%)

#### Professional Tier
- **Product Name**: AP2 Expense - Professional
- **Monthly Price**: $99/month
- **Annual Price**: $990/year (save ~16%)

#### Enterprise Tier
- **Product Name**: AP2 Expense - Enterprise
- **Monthly Price**: $399/month
- **Annual Price**: $3,990/year (save ~16%)

**Important**: Copy all 6 price IDs (e.g., `price_xxxxx`) for environment configuration.

### 3. Configure Production Webhook Endpoint

**CRITICAL**: This must be done AFTER deploying the backend to get the Cloud Run URL.

1. Deploy backend first (see [Deployment Steps](#deployment-steps))
2. Get backend URL: `https://ap2-expense-backend-xxxxx-uc.a.run.app`
3. Go to **Developers** → **Webhooks**
4. Click **+ Add endpoint**
5. **Endpoint URL**: `https://YOUR_BACKEND_URL/api/payment/webhooks/stripe`
6. **Events to send**:
   - ✅ `checkout.session.completed`
   - ✅ `customer.subscription.created`
   - ✅ `customer.subscription.updated`
   - ✅ `customer.subscription.deleted`
   - ✅ `invoice.paid`
   - ✅ `invoice.payment_failed`
7. Click **Add endpoint**
8. **Copy the Signing Secret** (`whsec_...`)
9. Update Secret Manager:
   ```bash
   echo -n "whsec_YOUR_ACTUAL_WEBHOOK_SECRET" | \
     gcloud secrets versions add stripe-webhook-secret --data-file=-
   ```

---

## Environment Secrets Configuration

Create a `.env.production` file locally (DO NOT commit to git):

```env
# ============================================================================
# Production Environment Configuration
# ============================================================================

ENVIRONMENT=production
DEBUG=False

# ============================================================================
# Database (Cloud SQL)
# ============================================================================

# This will be injected from Secret Manager
# DATABASE_URL=postgresql://ap2user:password@/ap2_expense?host=/cloudsql/PROJECT:REGION:INSTANCE

# ============================================================================
# Security & Authentication
# ============================================================================

# Generated from Secret Manager
# JWT_SECRET=...
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60
REFRESH_TOKEN_EXPIRATION_DAYS=30

# ============================================================================
# Stripe Production Configuration
# ============================================================================

ENABLE_BILLING=True
# STRIPE_SECRET_KEY=sk_live_... (from Secret Manager)
# STRIPE_PUBLISHABLE_KEY=pk_live_... (from Secret Manager)
# STRIPE_WEBHOOK_SECRET=whsec_... (from Secret Manager)

# Production Price IDs (update after creating Stripe products)
STRIPE_PRICE_ID_STARTER_MONTHLY=price_xxxxx
STRIPE_PRICE_ID_STARTER_ANNUAL=price_xxxxx
STRIPE_PRICE_ID_PROFESSIONAL_MONTHLY=price_xxxxx
STRIPE_PRICE_ID_PROFESSIONAL_ANNUAL=price_xxxxx
STRIPE_PRICE_ID_ENTERPRISE_MONTHLY=price_xxxxx
STRIPE_PRICE_ID_ENTERPRISE_ANNUAL=price_xxxxx

# ============================================================================
# CORS
# ============================================================================

# Update with actual frontend URL after deployment
CORS_ORIGINS=https://your-actual-domain.com,https://ap2-expense-frontend-xxxxx-uc.a.run.app

# ============================================================================
# Google Cloud Marketplace (Optional - for GCP Marketplace integration)
# ============================================================================

GCP_PROJECT_ID=ap2-expense-prod
ENABLE_GCP_MARKETPLACE=false  # Set to true when ready for marketplace
GCP_USAGE_REPORTING_ENABLED=false

# ============================================================================
# Frontend URL
# ============================================================================

FRONTEND_URL=https://your-actual-domain.com

# ============================================================================
# Email Configuration (Optional)
# ============================================================================

SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=noreply@your-domain.com
# SMTP_PASSWORD=... (from Secret Manager if needed)
SMTP_FROM_EMAIL=noreply@your-domain.com

# ============================================================================
# Data Retention
# ============================================================================

AUDIT_LOG_RETENTION_DAYS=365
SESSION_RETENTION_DAYS=90
REVOKED_TOKEN_RETENTION_DAYS=30
```

---

## Database Migration

### 1. Connect to Cloud SQL

```bash
# Install Cloud SQL Proxy
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.0.0/cloud-sql-proxy.linux.amd64
chmod +x cloud-sql-proxy

# Start proxy
./cloud-sql-proxy $GCP_PROJECT_ID:$GCP_REGION:ap2-expense-db &
```

### 2. Run Alembic Migrations

```bash
cd backend

# Set database URL for migration
export DATABASE_URL="postgresql://ap2user:YOUR_PASSWORD@127.0.0.1:5432/ap2_expense"

# Run migrations
alembic upgrade head

# Verify tables created
psql $DATABASE_URL -c "\dt"
```

### 3. Seed Initial Data (Optional)

```bash
# Seed subscription tiers
python seed_tiers_quick.py
```

---

## Deployment Steps

### Option 1: Deploy via GitHub Actions (Recommended)

1. **Set GitHub Secrets**:
   - Go to GitHub repository → Settings → Secrets and variables → Actions
   - Add secrets:
     - `GCP_PROJECT_ID`: Your GCP project ID
     - `GCP_WORKLOAD_IDENTITY_PROVIDER`: Workload identity provider
     - `GCP_SERVICE_ACCOUNT`: Service account email
     - `CODECOV_TOKEN`: (optional) For code coverage

2. **Trigger Deployment**:
   ```bash
   git checkout main
   git pull
   git push  # Pushes to main trigger deployment automatically
   ```

3. **Monitor Deployment**:
   - Go to GitHub Actions tab
   - Watch "Deploy to Production" workflow
   - Check for successful completion

### Option 2: Manual Deployment via gcloud

#### Deploy Backend

```bash
cd backend

# Build Docker image
docker build -t gcr.io/$GCP_PROJECT_ID/ap2-expense-backend:latest .

# Push to Container Registry
docker push gcr.io/$GCP_PROJECT_ID/ap2-expense-backend:latest

# Deploy to Cloud Run
gcloud run deploy ap2-expense-backend \
  --image gcr.io/$GCP_PROJECT_ID/ap2-expense-backend:latest \
  --region $GCP_REGION \
  --platform managed \
  --allow-unauthenticated \
  --service-account ap2-expense-backend@$GCP_PROJECT_ID.iam.gserviceaccount.com \
  --add-cloudsql-instances $GCP_PROJECT_ID:$GCP_REGION:ap2-expense-db \
  --min-instances 1 \
  --max-instances 10 \
  --memory 2Gi \
  --cpu 2 \
  --port 8000 \
  --timeout 300 \
  --set-secrets=DATABASE_URL=database-url:latest,\
JWT_SECRET=jwt-secret:latest,\
STRIPE_SECRET_KEY=stripe-secret-key:latest,\
STRIPE_PUBLISHABLE_KEY=stripe-publishable-key:latest,\
STRIPE_WEBHOOK_SECRET=stripe-webhook-secret:latest \
  --set-env-vars ENVIRONMENT=production,\
STRIPE_PRICE_ID_STARTER_MONTHLY=price_xxxxx,\
STRIPE_PRICE_ID_STARTER_ANNUAL=price_xxxxx,\
STRIPE_PRICE_ID_PROFESSIONAL_MONTHLY=price_xxxxx,\
STRIPE_PRICE_ID_PROFESSIONAL_ANNUAL=price_xxxxx,\
STRIPE_PRICE_ID_ENTERPRISE_MONTHLY=price_xxxxx,\
STRIPE_PRICE_ID_ENTERPRISE_ANNUAL=price_xxxxx

# Get backend URL
BACKEND_URL=$(gcloud run services describe ap2-expense-backend \
  --region $GCP_REGION \
  --format="value(status.url)")

echo "Backend URL: $BACKEND_URL"
```

#### Deploy Frontend

```bash
cd frontend

# Create production environment file
echo "VITE_API_URL=$BACKEND_URL/api/v1" > .env.production
echo "VITE_STRIPE_PUBLISHABLE_KEY=pk_live_YOUR_KEY" >> .env.production

# Build Docker image
docker build -t gcr.io/$GCP_PROJECT_ID/ap2-expense-frontend:latest .

# Push to Container Registry
docker push gcr.io/$GCP_PROJECT_ID/ap2-expense-frontend:latest

# Deploy to Cloud Run
gcloud run deploy ap2-expense-frontend \
  --image gcr.io/$GCP_PROJECT_ID/ap2-expense-frontend:latest \
  --region $GCP_REGION \
  --platform managed \
  --allow-unauthenticated \
  --min-instances 1 \
  --max-instances 5 \
  --memory 512Mi \
  --cpu 1 \
  --port 80 \
  --timeout 60

# Get frontend URL
FRONTEND_URL=$(gcloud run services describe ap2-expense-frontend \
  --region $GCP_REGION \
  --format="value(status.url)")

echo "Frontend URL: $FRONTEND_URL"
```

---

## Post-Deployment Verification

### 1. Health Checks

```bash
# Backend health
curl https://YOUR_BACKEND_URL/health

# Expected: {"status":"healthy","service":"AP2 Expense Management Agent"}

# API docs (should be disabled in production)
curl https://YOUR_BACKEND_URL/docs
# Should return 404 or redirect (for security)
```

### 2. Test User Registration

```bash
curl -X POST "https://YOUR_BACKEND_URL/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testprod",
    "password": "SecurePass123!",
    "email": "test@yourdomain.com",
    "full_name": "Production Test"
  }'
```

### 3. Test Stripe Checkout Flow

1. Open frontend URL in browser
2. Register a test account
3. Create an organization
4. Navigate to billing/pricing page
5. Select a plan
6. Complete checkout with Stripe test card: `4242 4242 4242 4242`
7. Verify webhook received in Stripe Dashboard
8. Verify subscription activated in application

### 4. Verify Webhook Endpoint

```bash
# Check webhook endpoint responds
curl -X POST "https://YOUR_BACKEND_URL/api/payment/webhooks/stripe" \
  -H "Content-Type: application/json" \
  -d '{"test": true}'

# Should return 200 (even though signature is invalid)
```

### 5. Check Logs

```bash
# Backend logs
gcloud run services logs read ap2-expense-backend \
  --region $GCP_REGION \
  --limit 50

# Frontend logs
gcloud run services logs read ap2-expense-frontend \
  --region $GCP_REGION \
  --limit 50
```

### 6. Database Verification

```bash
# Connect to Cloud SQL
./cloud-sql-proxy $GCP_PROJECT_ID:$GCP_REGION:ap2-expense-db &

# Connect via psql
psql "postgresql://ap2user:PASSWORD@127.0.0.1:5432/ap2_expense"

# Check tables
\dt

# Check billing events
SELECT * FROM billing_events ORDER BY occurred_at DESC LIMIT 10;

# Check subscriptions
SELECT * FROM organization_subscriptions;
```

---

## Rollback Procedures

### Quick Rollback (to previous version)

```bash
# List revisions
gcloud run revisions list --service=ap2-expense-backend --region=$GCP_REGION

# Rollback to specific revision
gcloud run services update-traffic ap2-expense-backend \
  --to-revisions=REVISION_NAME=100 \
  --region=$GCP_REGION
```

### Emergency Rollback (via GitHub)

1. Go to GitHub Actions
2. Find successful previous deployment
3. Click "Re-run jobs"
4. Or revert the commit and push

---

## Monitoring & Alerts

### 1. Set Up Cloud Monitoring Dashboard

```bash
# View metrics in GCP Console
https://console.cloud.google.com/run/detail/$GCP_REGION/ap2-expense-backend/metrics
```

**Key Metrics to Monitor**:
- Request count
- Request latency (p50, p95, p99)
- Error rate
- Instance count
- CPU utilization
- Memory utilization
- Billing event processing rate

### 2. Configure Alerts

Create alerts for:
- **High error rate** (> 5% of requests)
- **High latency** (p95 > 2 seconds)
- **Failed payments** (`invoice.payment_failed` events)
- **Webhook failures** (check Stripe Dashboard)
- **Database connection errors**
- **High memory usage** (> 80%)

### 3. Set Up Log-Based Alerts

```bash
# Alert on critical errors
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="Backend Critical Errors" \
  --condition-display-name="Error rate > 1%" \
  --condition-threshold-value=0.01 \
  --condition-threshold-duration=60s
```

### 4. Uptime Checks

```bash
# Create uptime check
gcloud monitoring uptime create ap2-expense-health \
  --resource-type=uptime-url \
  --host=YOUR_BACKEND_URL \
  --path=/health \
  --check-interval=60s
```

---

## Custom Domain Setup (Optional)

### 1. Map Custom Domain to Cloud Run

```bash
# Map domain to backend
gcloud beta run domain-mappings create \
  --service ap2-expense-backend \
  --domain api.your-domain.com \
  --region $GCP_REGION

# Map domain to frontend
gcloud beta run domain-mappings create \
  --service ap2-expense-frontend \
  --domain app.your-domain.com \
  --region $GCP_REGION
```

### 2. Update DNS Records

Add DNS records as shown by gcloud output (usually CNAME or A records).

### 3. Update Environment Variables

```bash
# Update CORS origins
gcloud run services update ap2-expense-backend \
  --update-env-vars CORS_ORIGINS=https://app.your-domain.com \
  --region $GCP_REGION
```

---

## Security Hardening

### 1. Enable Cloud Armor (DDoS Protection)

Already configured in `k8s/ingress.yaml` for Kubernetes deployments.

For Cloud Run, consider using Cloud Load Balancer + Cloud Armor.

### 2. Set Up VPC Connector (Optional)

For private database connections:

```bash
# Create VPC connector
gcloud compute networks vpc-access connectors create ap2-expense-connector \
  --region=$GCP_REGION \
  --network=default \
  --range=10.8.0.0/28

# Update Cloud Run to use connector
gcloud run services update ap2-expense-backend \
  --vpc-connector=ap2-expense-connector \
  --region=$GCP_REGION
```

### 3. Review IAM Permissions

```bash
# List service account permissions
gcloud projects get-iam-policy $GCP_PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:ap2-expense-backend*"
```

---

## Troubleshooting

### Backend Won't Start

```bash
# Check logs
gcloud run services logs read ap2-expense-backend --region=$GCP_REGION --limit=100

# Common issues:
# 1. Database connection failed → Check Cloud SQL instance is running
# 2. Secret access denied → Verify service account has secretAccessor role
# 3. Missing env vars → Check deployment command includes all required vars
```

### Webhooks Not Receiving Events

1. Check Stripe Dashboard → Webhooks → View logs
2. Verify webhook URL is correct (should be `https://YOUR_URL/api/payment/webhooks/stripe`)
3. Check backend logs for webhook processing errors
4. Verify webhook secret is correct in Secret Manager

### Database Connection Issues

```bash
# Test Cloud SQL connection
gcloud sql connect ap2-expense-db --user=ap2user

# Check Cloud SQL instance status
gcloud sql instances describe ap2-expense-db
```

---

## Cost Optimization

### Estimated Monthly Costs (us-central1)

**Cloud Run (Backend)**:
- 1 instance min, 10 max: ~$20-100/month

**Cloud Run (Frontend)**:
- 1 instance min, 5 max: ~$10-50/month

**Cloud SQL (db-f1-micro)**:
- ~$7.67/month

**Secret Manager**:
- ~$0.30/month (6 secrets)

**Network Egress**:
- Variable, ~$0.12/GB

**Total Estimated**: ~$40-160/month (depends on traffic)

### Cost Optimization Tips

1. **Use Cloud Run min instances = 0** for low-traffic periods
2. **Upgrade to committed use contracts** for 30-50% discount
3. **Use Cloud CDN** for static assets (frontend)
4. **Monitor cold start times** - balance cost vs. performance
5. **Set up budget alerts** in GCP Console

---

## Support & Maintenance

### Regular Maintenance Tasks

**Weekly**:
- [ ] Review error logs
- [ ] Check webhook delivery success rate
- [ ] Monitor failed payments

**Monthly**:
- [ ] Review and rotate secrets
- [ ] Update dependencies (security patches)
- [ ] Review cost optimization opportunities
- [ ] Backup database

**Quarterly**:
- [ ] Security audit
- [ ] Performance optimization review
- [ ] Disaster recovery drill

---

## Emergency Contacts

- **GCP Support**: [Cloud Console Support](https://console.cloud.google.com/support)
- **Stripe Support**: [Stripe Dashboard Support](https://dashboard.stripe.com/support)
- **On-Call Engineer**: [Your contact info]

---

**Deployment Checklist**: Use `PRODUCTION_DEPLOYMENT_CHECKLIST.md` for step-by-step deployment verification.

**Next Steps**: After deployment, configure Stripe production webhook endpoint and test end-to-end checkout flow.
