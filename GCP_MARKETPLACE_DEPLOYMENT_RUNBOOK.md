# GCP Marketplace Deployment Runbook

**Product**: AP2 Expense Management Agent
**Version**: 1.0.0
**Target**: Google Cloud Marketplace
**Date**: December 6, 2025
**Status**: Production Ready

---

## 📋 Quick Reference

- **Estimated Time**: 4-6 hours (first deployment)
- **Prerequisites**: GCP Project, Billing Account, Domain Name
- **Required Skills**: GCP Console, gcloud CLI, Basic Shell Scripting
- **Support**: See "Emergency Contacts" section at bottom

---

## 🎯 Deployment Overview

This runbook provides step-by-step instructions to deploy AP2 Expense Agent to Google Cloud Marketplace. Follow these steps in order.

### Deployment Phases

1. **Pre-deployment Setup** (2-3 hours)
   - GCP Project & Infrastructure
   - Service Accounts & IAM
   - Secrets & Configuration

2. **Application Deployment** (1-2 hours)
   - Database Setup & Migrations
   - Cloud Run Services
   - Validation & Testing

3. **Marketplace Integration** (1-2 hours)
   - Pub/Sub Configuration
   - Cloud Scheduler Jobs
   - Monitoring & Alerts
   - DLQ monitoring & replay

4. **Marketplace Listing** (4-8 hours, can be done in parallel)
   - Product Listing Creation
   - Assets Upload
   - Pricing Configuration

---

## Phase 1: Pre-Deployment Setup

### 1.1 GCP Project Setup

**Estimated Time**: 15 minutes

```bash
# Set your project ID
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"

# Set as default project
gcloud config set project $GCP_PROJECT_ID

# Enable billing (via Console if not already enabled)
# https://console.cloud.google.com/billing

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  sql-component.googleapis.com \
  sqladmin.googleapis.com \
  storage.googleapis.com \
  secretmanager.googleapis.com \
  cloudkms.googleapis.com \
  cloudbuild.googleapis.com \
  cloudscheduler.googleapis.com \
  pubsub.googleapis.com \
  cloudcommerceprocurement.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com
```

**Validation**:
```bash
gcloud services list --enabled | grep -E "(run|sql|storage|secret|kms|build|scheduler|pubsub|commerce)"
```

### 1.2 Service Accounts & IAM

**Estimated Time**: 20 minutes

Run the automated service account setup script:

```bash
cd /path/to/ap2-expense-agent
chmod +x scripts/setup-service-accounts.sh
./scripts/setup-service-accounts.sh $GCP_PROJECT_ID $GCP_REGION
```

**What this creates**:
- `ap2-expense-sa@PROJECT_ID.iam.gserviceaccount.com` - Application runtime SA
- `ap2-marketplace-api-sa@PROJECT_ID.iam.gserviceaccount.com` - Marketplace API SA
- `cloud-scheduler-sa@PROJECT_ID.iam.gserviceaccount.com` - Scheduler SA

**Important**: The script will create `marketplace-api-key.json`. Store this securely!

```bash
# Upload the service account key to Secret Manager
gcloud secrets create gcp-service-account-key \
  --data-file=marketplace-api-key.json \
  --project=$GCP_PROJECT_ID

# Delete local copy
rm marketplace-api-key.json

# Verify secret was created
gcloud secrets describe gcp-service-account-key
```

**Validation**:
```bash
gcloud iam service-accounts list --project=$GCP_PROJECT_ID
```

### 1.3 Create Required Secrets

**Estimated Time**: 30 minutes

Create all required production secrets in Secret Manager:

```bash
# 1. Database connection string (will be created after Cloud SQL setup)
# Placeholder for now - will update in step 2.1

# 2. JWT Secret Key (generate 64-character random string)
export JWT_SECRET=$(openssl rand -hex 32)
echo -n "$JWT_SECRET" | gcloud secrets create jwt-secret-key \
  --data-file=- \
  --project=$GCP_PROJECT_ID

# 3. JWT Refresh Secret Key
export JWT_REFRESH_SECRET=$(openssl rand -hex 32)
echo -n "$JWT_REFRESH_SECRET" | gcloud secrets create jwt-refresh-secret-key \
  --data-file=- \
  --project=$GCP_PROJECT_ID

# 4. GCP Webhook Secret (generate 32-character random string)
export GCP_WEBHOOK_SECRET=$(openssl rand -hex 16)
echo -n "$GCP_WEBHOOK_SECRET" | gcloud secrets create gcp-webhook-secret \
  --data-file=- \
  --project=$GCP_PROJECT_ID

# 5. Stripe API Keys (get from Stripe Dashboard)
# https://dashboard.stripe.com/apikeys
echo -n "sk_live_YOUR_STRIPE_SECRET_KEY" | gcloud secrets create stripe-secret-key \
  --data-file=- \
  --project=$GCP_PROJECT_ID

# 6. SMTP Password (if using email notifications)
echo -n "YOUR_SMTP_PASSWORD" | gcloud secrets create smtp-password \
  --data-file=- \
  --project=$GCP_PROJECT_ID
```

**Validation**:
```bash
gcloud secrets list --project=$GCP_PROJECT_ID
```

### 1.4 Create Cloud Storage Bucket

**Estimated Time**: 10 minutes

```bash
# Create bucket for receipt uploads
export BUCKET_NAME="${GCP_PROJECT_ID}-receipts"

gsutil mb -p $GCP_PROJECT_ID \
  -c STANDARD \
  -l $GCP_REGION \
  gs://$BUCKET_NAME/

# Set lifecycle policy (delete after 7 years)
cat > lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 2555}
      }
    ]
  }
}
EOF

gsutil lifecycle set lifecycle.json gs://$BUCKET_NAME/
rm lifecycle.json

# Grant service account access
gsutil iam ch \
  serviceAccount:ap2-expense-sa@${GCP_PROJECT_ID}.iam.gserviceaccount.com:roles/storage.objectAdmin \
  gs://$BUCKET_NAME/
```

**Validation**:
```bash
gsutil ls -p $GCP_PROJECT_ID
```

### 1.5 Create Cloud KMS Keyring for AP2 Signing

**Estimated Time**: 10 minutes

```bash
# Create KMS keyring
gcloud kms keyrings create ap2-expense-keyring \
  --location=$GCP_REGION \
  --project=$GCP_PROJECT_ID

# Create asymmetric signing key for AP2 mandates
gcloud kms keys create ap2-mandate-signing-key \
  --location=$GCP_REGION \
  --keyring=ap2-expense-keyring \
  --purpose=asymmetric-signing \
  --default-algorithm=ec-sign-p256-sha256 \
  --project=$GCP_PROJECT_ID

# Grant service account signing permission
gcloud kms keys add-iam-policy-binding ap2-mandate-signing-key \
  --location=$GCP_REGION \
  --keyring=ap2-expense-keyring \
  --member="serviceAccount:ap2-expense-sa@${GCP_PROJECT_ID}.iam.gserviceaccount.com" \
  --role=roles/cloudkms.signerVerifier \
  --project=$GCP_PROJECT_ID
```

**Validation**:
```bash
gcloud kms keys list --location=$GCP_REGION --keyring=ap2-expense-keyring
```

---

## Phase 2: Application Deployment

### 2.1 Cloud SQL Database Setup

**Estimated Time**: 20 minutes

```bash
# Create Cloud SQL PostgreSQL instance
gcloud sql instances create ap2-expense-db \
  --database-version=POSTGRES_14 \
  --tier=db-custom-2-7680 \
  --region=$GCP_REGION \
  --backup-start-time=02:00 \
  --enable-bin-log \
  --retained-backups-count=30 \
  --storage-auto-increase \
  --storage-size=20GB \
  --project=$GCP_PROJECT_ID

# Set root password
gcloud sql users set-password postgres \
  --instance=ap2-expense-db \
  --password="$(openssl rand -base64 32)" \
  --project=$GCP_PROJECT_ID

# Create application database
gcloud sql databases create ap2_production \
  --instance=ap2-expense-db \
  --project=$GCP_PROJECT_ID

# Create application database user
export DB_PASSWORD=$(openssl rand -base64 32)
gcloud sql users create ap2_user \
  --instance=ap2-expense-db \
  --password="$DB_PASSWORD" \
  --project=$GCP_PROJECT_ID

# Create database connection string
export CONNECTION_NAME="${GCP_PROJECT_ID}:${GCP_REGION}:ap2-expense-db"
export DATABASE_URL="postgresql://ap2_user:${DB_PASSWORD}@//cloudsql/${CONNECTION_NAME}/ap2_production"

# Store database connection string in Secret Manager
echo -n "$DATABASE_URL" | gcloud secrets create database-connection-string \
  --data-file=- \
  --project=$GCP_PROJECT_ID
```

**Validation**:
```bash
gcloud sql instances describe ap2-expense-db --project=$GCP_PROJECT_ID
```

### 2.2 Build and Push Docker Images

**Estimated Time**: 15 minutes

```bash
# Build images using the automated script
cd /path/to/ap2-expense-agent
chmod +x scripts/build-and-tag.sh

# Set version
export VERSION="v1.0.0"

# Build and push
./scripts/build-and-tag.sh $VERSION --push --latest
```

**Validation**:
```bash
gcloud container images list --repository=gcr.io/$GCP_PROJECT_ID
gcloud container images list-tags gcr.io/$GCP_PROJECT_ID/ap2-expense-backend
```

### 2.3 Deploy Backend to Cloud Run

**Estimated Time**: 10 minutes

```bash
# Get backend URL placeholder
export BACKEND_URL="https://ap2-expense-backend-${GCP_PROJECT_ID}.a.run.app"

# Deploy backend
gcloud run deploy ap2-expense-backend \
  --image=gcr.io/$GCP_PROJECT_ID/ap2-expense-backend:$VERSION \
  --region=$GCP_REGION \
  --platform=managed \
  --allow-unauthenticated \
  --service-account=ap2-expense-sa@${GCP_PROJECT_ID}.iam.gserviceaccount.com \
  --add-cloudsql-instances=$CONNECTION_NAME \
  --min-instances=1 \
  --max-instances=10 \
  --memory=2Gi \
  --cpu=2 \
  --timeout=300s \
  --concurrency=80 \
  --set-env-vars="ENVIRONMENT=production,\
GCP_PROJECT_ID=$GCP_PROJECT_ID,\
GOOGLE_CLOUD_PROJECT=$GCP_PROJECT_ID,\
GCP_KMS_LOCATION=$GCP_REGION,\
GCP_KMS_KEYRING=ap2-expense-keyring,\
GCP_KMS_SIGNING_KEY=ap2-mandate-signing-key,\
ENABLE_GCP_MARKETPLACE=true,\
GCP_USAGE_REPORTING_ENABLED=true" \
  --set-secrets="DATABASE_URL=database-connection-string:latest,\
JWT_SECRET=jwt-secret-key:latest,\
JWT_REFRESH_SECRET=jwt-refresh-secret-key:latest,\
STRIPE_SECRET_KEY=stripe-secret-key:latest,\
GCP_WEBHOOK_SECRET=gcp-webhook-secret:latest,\
GCP_SERVICE_ACCOUNT_KEY=gcp-service-account-key:latest,\
SMTP_PASSWORD=smtp-password:latest" \
  --project=$GCP_PROJECT_ID

# Get actual backend URL
export BACKEND_URL=$(gcloud run services describe ap2-expense-backend \
  --region=$GCP_REGION \
  --project=$GCP_PROJECT_ID \
  --format="value(status.url)")

echo "Backend deployed at: $BACKEND_URL"

# Update GCP_WEBHOOK_AUDIENCE secret
echo -n "$BACKEND_URL" | gcloud secrets create gcp-webhook-audience \
  --data-file=- \
  --project=$GCP_PROJECT_ID || \
echo -n "$BACKEND_URL" | gcloud secrets versions add gcp-webhook-audience \
  --data-file=-

# Update backend with webhook audience
gcloud run services update ap2-expense-backend \
  --region=$GCP_REGION \
  --update-env-vars="GCP_WEBHOOK_AUDIENCE=$BACKEND_URL" \
  --project=$GCP_PROJECT_ID
```

**Validation**:
```bash
curl $BACKEND_URL/health
# Should return: {"status":"healthy"}
```

### 2.4 Run Database Migrations

**Estimated Time**: 5 minutes

```bash
# Connect to Cloud SQL via proxy (in a separate terminal)
cloud_sql_proxy -instances=$CONNECTION_NAME=tcp:5432 &

# Run migrations
cd backend
source .venv/Scripts/activate  # Windows
# source .venv/bin/activate    # Linux/Mac

# Set database URL for local migration
export DATABASE_URL="postgresql://ap2_user:$DB_PASSWORD@localhost:5432/ap2_production"

# Run Alembic migrations
alembic upgrade head

# Verify migrations
alembic current

# Stop proxy
pkill cloud_sql_proxy
```

**Validation**:
```bash
# Check alembic version table
gcloud sql connect ap2-expense-db --user=ap2_user --database=ap2_production
# Then run: SELECT * FROM alembic_version;
# Should show: 009_usage_metrics
```

### 2.5 Deploy Frontend to Cloud Run

**Estimated Time**: 10 minutes

```bash
# Deploy frontend
gcloud run deploy ap2-expense-frontend \
  --image=gcr.io/$GCP_PROJECT_ID/ap2-expense-frontend:$VERSION \
  --region=$GCP_REGION \
  --platform=managed \
  --allow-unauthenticated \
  --min-instances=1 \
  --max-instances=5 \
  --memory=512Mi \
  --cpu=1 \
  --timeout=60s \
  --set-env-vars="VITE_API_BASE_URL=$BACKEND_URL" \
  --project=$GCP_PROJECT_ID

# Get frontend URL
export FRONTEND_URL=$(gcloud run services describe ap2-expense-frontend \
  --region=$GCP_REGION \
  --project=$GCP_PROJECT_ID \
  --format="value(status.url)")

echo "Frontend deployed at: $FRONTEND_URL"
```

**Validation**:
```bash
curl -I $FRONTEND_URL
# Should return: HTTP/2 200
```

---

## Phase 3: Marketplace Integration

### 3.1 Pub/Sub Configuration

**Estimated Time**: 10 minutes

```bash
# Run automated Pub/Sub setup
chmod +x scripts/setup-pubsub.sh
./scripts/setup-pubsub.sh $GCP_PROJECT_ID $GCP_REGION $BACKEND_URL
```

**Validation**:
```bash
gcloud pubsub topics describe gcp-marketplace-entitlement-events
gcloud pubsub subscriptions describe gcp-marketplace-entitlement-events-sub
```

### 3.2 Cloud Scheduler Jobs

**Estimated Time**: 10 minutes

```bash
# Run automated Cloud Scheduler setup
chmod +x scripts/setup-cloud-scheduler.sh
./scripts/setup-cloud-scheduler.sh $GCP_PROJECT_ID $GCP_REGION $BACKEND_URL
```

**Validation**:
```bash
gcloud scheduler jobs list --location=$GCP_REGION
```

**Test Usage Reporting**:
```bash
# Manually trigger usage reporting job
gcloud scheduler jobs run gcp-marketplace-usage-reporting \
  --location=$GCP_REGION

# Check logs
gcloud logging read 'resource.type=cloud_run_revision
  AND jsonPayload.message=~"usage reporting"' \
  --limit=10 \
  --format=json
```

### 3.3 Monitoring & Alerting

**DLQ Monitoring (Marketplace Webhooks & Usage)**

- Script: `backend/scripts/check_dlq_counts.py`
- Recommended schedule: every 5 minutes via Cloud Scheduler hitting a Cloud Run Job or lightweight VM.
- Example (Cloud Run Job):
  ```bash
  gcloud run jobs create dlq-checker \
    --image=gcr.io/$GCP_PROJECT_ID/ap2-backend:latest \
    --region=$GCP_REGION \
    --command="python" \
    --args="scripts/check_dlq_counts.py","--threshold","0" \
    --service-account=$RUNTIME_SA

  gcloud scheduler jobs create http dlq-check \
    --schedule="*/5 * * * *" \
    --uri=$(gcloud run jobs describe dlq-checker --region=$GCP_REGION --format='value(status.latestCreatedExecution.uri)') \
    --oidc-service-account-email=$SCHEDULER_SA
  ```
- Alerting: job exits non-zero if any DLQ count > threshold; surface failures to Slack/PagerDuty via existing alert policies.

**DLQ Replay (Targeted)**

- Script: `backend/scripts/replay_dlq.py`
- Use after fixing root causes to reprocess failed events.
- Prod auth: mint Google-signed ID token with service account key and audience matching webhook URL.
  ```bash
  python scripts/replay_dlq.py \
    --event-type gcp_webhook_events_dlq \
    --limit 5 \
    --target-url https://your-app.run.app/api/webhooks/gcp/events \
    --service-account-key marketplace-api-key.json \
    --audience https://your-app.run.app/api/webhooks/gcp/events
  ```
- Dev legacy: add `--hmac-secret $GCP_WEBHOOK_SECRET` if testing HMAC endpoints locally.

**Estimated Time**: 15 minutes

```bash
# Set notification email
export NOTIFICATION_EMAIL="ops@yourcompany.com"

# Run automated monitoring setup
chmod +x scripts/setup-monitoring-alerts.sh
./scripts/setup-monitoring-alerts.sh $GCP_PROJECT_ID $NOTIFICATION_EMAIL
```

**Validation**:
```bash
gcloud alpha monitoring policies list --project=$GCP_PROJECT_ID
gcloud logging metrics list --project=$GCP_PROJECT_ID
```

---

## Phase 4: Marketplace Listing

### 4.1 Partner Portal Setup

**Estimated Time**: 30 minutes

1. **Access Partner Portal**:
   - Go to: https://console.cloud.google.com/partner
   - Sign in with your Google account

2. **Company Registration**:
   - Complete company information
   - Upload business verification documents
   - Submit tax forms (W-9 for US entities)
   - Configure bank account for payouts

3. **Create Product Listing**:
   - Click "Create Solution"
   - Select "SaaS" as product type
   - Fill in basic information:
     - Product Name: "AP2 Expense Agent"
     - Short Description: "AI-powered expense management with cryptographic verification"
     - Category: Business Applications > Finance & Accounting

**Required Information**:
- Company Name
- Support Email: support@ap2expense.com
- Product Website: https://ap2expense.com
- Privacy Policy: https://ap2expense.com/privacy
- Terms of Service: https://ap2expense.com/terms

### 4.2 Configure Webhooks in Partner Portal

**Estimated Time**: 15 minutes

In the Partner Portal, navigate to "Technical Configuration":

1. **Procurement Webhook**:
   - URL: `{BACKEND_URL}/api/webhooks/gcp/procurement`
   - Authentication: Google OIDC (automatic)
   - Audience: `{BACKEND_URL}`

2. **Entitlement Events**:
   - Pub/Sub Topic: `projects/{GCP_PROJECT_ID}/topics/gcp-marketplace-entitlement-events`
   - Subscription: Managed by application

3. **Usage Reporting**:
   - Provider ID: `{GCP_PROJECT_ID}`
   - Reporting API: Consumer Procurement API
   - Frequency: Hourly

### 4.3 Configure Pricing

**Estimated Time**: 20 minutes

In Partner Portal > Pricing Configuration:

1. **Pricing Model**: Subscription-based with usage metering

2. **Subscription Tiers**:
   - **Starter**: $29/month
     - Max 3 organizations
     - Max 5 users
     - 50 expenses/month

   - **Professional**: $99/month
     - Max 10 organizations
     - Max 25 users
     - Unlimited expenses

   - **Enterprise**: $399/month
     - Max 25 organizations
     - Max 100 users
     - Unlimited expenses
     - Priority support

3. **Usage Metrics** (for overage billing):
   - AI Categorization: $0.05 per scan
   - AP2 Transaction: $0.10 per transaction

4. **Free Trial**: 14 days (no credit card required)

5. **Billing Frequency**: Monthly (with annual option at 20% discount)

### 4.4 Upload Assets

**Estimated Time**: 2-4 hours

**Required Assets** (see `MARKETPLACE_ASSET_CREATION_GUIDE.md` for details):

1. **Screenshots** (8 required, 1280x800px PNG):
   - Dashboard overview
   - Expense submission
   - Receipt scanning with AI
   - Approval workflow
   - AP2 payment verification
   - Organization management
   - Analytics & reporting
   - Mobile view

2. **Demo Video** (2-5 minutes):
   - Upload to YouTube (unlisted)
   - Add link to Partner Portal
   - Show key features and user flow

3. **Product Icon** (512x512px PNG):
   - Square format
   - Transparent background
   - Clear at small sizes

4. **Logo** (if different from icon, 512x512px)

**Asset Creation Tools**:
- Use `scripts/capture-screenshots.sh` for guided screenshot capture
- Use `backend/seed_screenshot_data.py` to seed demo data

### 4.5 Product Description

**Estimated Time**: 30 minutes

Copy from `marketplace/product-listing.md`:

- Long description (up to 10,000 characters)
- Key features (10-15 bullet points)
- Use cases
- Integration details
- Security & compliance

### 4.6 Submit for Review

**Estimated Time**: 5 minutes (review takes 1-2 weeks)

1. **Review Checklist**:
   - [ ] All required fields completed
   - [ ] 8 screenshots uploaded
   - [ ] Demo video uploaded
   - [ ] Product icon uploaded
   - [ ] Pricing configured
   - [ ] Webhooks configured and tested
   - [ ] Support email verified
   - [ ] Terms of Service and Privacy Policy accessible

2. **Submit for Google Review**:
   - Click "Submit for Review" in Partner Portal
   - Google will review within 1-2 weeks
   - You'll receive email notifications on approval status

---

## Validation & Testing

### Run Comprehensive Validation

**Estimated Time**: 15 minutes

```bash
# Run automated environment validation
chmod +x scripts/validate-environment.sh
./scripts/validate-environment.sh production
```

### Test End-to-End GCP Marketplace Flow

**Estimated Time**: 30 minutes

```bash
# Run E2E integration tests
cd backend
pytest tests/test_gcp_e2e_integration.py -v

# Expected output: All tests passing
```

### Manual Testing Checklist

- [ ] Backend health endpoint responding
- [ ] Frontend loads correctly
- [ ] User registration works
- [ ] Expense submission works
- [ ] Approval workflow works
- [ ] Webhook endpoints accessible
- [ ] Usage reporting cron job running
- [ ] Monitoring alerts configured

---

## Post-Deployment

### Monitor First 24 Hours

```bash
# View backend logs in real-time
gcloud run services logs tail ap2-expense-backend \
  --region=$GCP_REGION \
  --project=$GCP_PROJECT_ID

# View frontend logs
gcloud run services logs tail ap2-expense-frontend \
  --region=$GCP_REGION \
  --project=$GCP_PROJECT_ID

# Monitor error rates
gcloud monitoring time-series list \
  --filter='metric.type="logging.googleapis.com/user/error_rate"' \
  --project=$GCP_PROJECT_ID

# Check usage reporting
gcloud logging read 'jsonPayload.message=~"GCP usage reporting"' \
  --project=$GCP_PROJECT_ID \
  --limit=50
```

### Verify First GCP Marketplace Signup

When first customer signs up via GCP Marketplace:

1. **Check procurement webhook**:
   ```bash
   gcloud logging read 'resource.type=cloud_run_revision
     AND jsonPayload.message=~"procurement"' \
     --limit=10 \
     --project=$GCP_PROJECT_ID
   ```

2. **Verify organization created**:
   - Check database for new organization
   - Verify admin user created
   - Confirm subscription active

3. **Test email delivery**:
   - Welcome email sent to admin
   - Contains temporary password
   - Login link works

---

## Rollback Procedures

### Rollback Cloud Run Deployment

```bash
# List previous revisions
gcloud run revisions list \
  --service=ap2-expense-backend \
  --region=$GCP_REGION \
  --project=$GCP_PROJECT_ID

# Rollback to specific revision
gcloud run services update-traffic ap2-expense-backend \
  --to-revisions=ap2-expense-backend-00042-abc=100 \
  --region=$GCP_REGION \
  --project=$GCP_PROJECT_ID
```

### Rollback Database Migration

```bash
# Connect to database via proxy
cloud_sql_proxy -instances=$CONNECTION_NAME=tcp:5432 &

# Downgrade Alembic migration
cd backend
alembic downgrade -1  # Downgrade by 1 version

# Or downgrade to specific version
alembic downgrade 008_merge_heads
```

---

## Troubleshooting

### Common Issues

**Issue**: Backend health check failing
```bash
# Check logs
gcloud run services logs read ap2-expense-backend --limit=50

# Common causes:
# - Database connection failed
# - Secret not accessible
# - Service account permissions missing
```

**Issue**: Webhook delivery failing (403 Forbidden)
```bash
# Verify OIDC configuration
gcloud pubsub subscriptions describe gcp-marketplace-entitlement-events-sub

# Check backend logs for verification errors
gcloud logging read 'jsonPayload.message=~"OIDC token verification"' --limit=20
```

**Issue**: Usage reporting not working
```bash
# Manually trigger usage reporting
curl -X POST $BACKEND_URL/api/webhooks/gcp/report-usage \
  -H "X-CloudScheduler: true"

# Check response and logs
gcloud logging read 'jsonPayload.message=~"usage"' --limit=30
```

---

## Emergency Contacts

- **On-Call Engineer**: Check PagerDuty or `docs/ON_CALL_SCHEDULE.md`
- **DevOps Lead**: devops@yourcompany.com
- **GCP Support**: https://cloud.google.com/support
- **Google Marketplace Support**: marketplace-support@google.com
- **Stripe Support**: https://support.stripe.com

---

## Appendices

### Useful Commands

```bash
# View all Cloud Run services
gcloud run services list --project=$GCP_PROJECT_ID

# View all secrets
gcloud secrets list --project=$GCP_PROJECT_ID

# View all service accounts
gcloud iam service-accounts list --project=$GCP_PROJECT_ID

# View Cloud Scheduler jobs
gcloud scheduler jobs list --location=$GCP_REGION

# View Pub/Sub topics and subscriptions
gcloud pubsub topics list
gcloud pubsub subscriptions list

# View monitoring dashboards
gcloud monitoring dashboards list
```

### Reference Documentation

- Google Cloud Marketplace: https://cloud.google.com/marketplace/docs
- Cloud Run: https://cloud.google.com/run/docs
- Cloud SQL: https://cloud.google.com/sql/docs
- Pub/Sub: https://cloud.google.com/pubsub/docs
- Secret Manager: https://cloud.google.com/secret-manager/docs

---

**Last Updated**: December 6, 2025
**Version**: 1.0
**Author**: Claude Code (Anthropic)
**Status**: Production Ready
