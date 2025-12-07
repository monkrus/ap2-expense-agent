# Quick Start: Deploy to GCP Marketplace (30 Minutes)

This guide gets you from zero to deployed in 30 minutes.

---

## Prerequisites (5 min)

```bash
# 1. Install gcloud CLI (if not installed)
# Windows: Download from https://cloud.google.com/sdk/docs/install
# Mac: brew install google-cloud-sdk
# Linux: curl https://sdk.cloud.google.com | bash

# 2. Login to GCP
gcloud auth login
gcloud auth application-default login

# 3. Set project
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"
gcloud config set project $GCP_PROJECT_ID

# 4. Verify
gcloud config list
```

---

## Step 1: Infrastructure Setup (10 min)

```bash
# Clone repo (if needed)
cd /path/to/ap2-expense-agent

# Run automated setup scripts
chmod +x scripts/*.sh

# 1. Enable APIs and create service accounts (3 min)
./scripts/setup-service-accounts.sh $GCP_PROJECT_ID $GCP_REGION

# 2. Create Cloud SQL database (4 min)
gcloud sql instances create ap2-expense-db \
  --database-version=POSTGRES_14 \
  --tier=db-custom-2-7680 \
  --region=$GCP_REGION \
  --backup-start-time=02:00 \
  --enable-bin-log

# 3. Create database and user (2 min)
gcloud sql databases create ap2_production --instance=ap2-expense-db
export DB_PASSWORD=$(openssl rand -base64 32)
gcloud sql users create ap2_user \
  --instance=ap2-expense-db \
  --password="$DB_PASSWORD"

# 4. Store database connection string
export CONNECTION_NAME="${GCP_PROJECT_ID}:${GCP_REGION}:ap2-expense-db"
export DATABASE_URL="postgresql://ap2_user:${DB_PASSWORD}@//cloudsql/${CONNECTION_NAME}/ap2_production"
echo -n "$DATABASE_URL" | gcloud secrets create database-connection-string --data-file=-

# 5. Create other required secrets (1 min)
echo -n "$(openssl rand -hex 32)" | gcloud secrets create jwt-secret-key --data-file=-
echo -n "$(openssl rand -hex 32)" | gcloud secrets create jwt-refresh-secret-key --data-file=-
echo -n "$(openssl rand -hex 16)" | gcloud secrets create gcp-webhook-secret --data-file=-
```

---

## Step 2: Deploy Application (10 min)

```bash
# 1. Build and push Docker images (5 min)
./scripts/build-and-tag.sh v1.0.0 --push --latest

# 2. Deploy backend to Cloud Run (3 min)
gcloud run deploy ap2-expense-backend \
  --image=gcr.io/$GCP_PROJECT_ID/ap2-expense-backend:v1.0.0 \
  --region=$GCP_REGION \
  --platform=managed \
  --allow-unauthenticated \
  --service-account=ap2-expense-sa@${GCP_PROJECT_ID}.iam.gserviceaccount.com \
  --add-cloudsql-instances=$CONNECTION_NAME \
  --min-instances=1 \
  --max-instances=10 \
  --memory=2Gi \
  --cpu=2 \
  --set-env-vars="ENVIRONMENT=production,\
GCP_PROJECT_ID=$GCP_PROJECT_ID,\
ENABLE_GCP_MARKETPLACE=true" \
  --set-secrets="DATABASE_URL=database-connection-string:latest,\
JWT_SECRET=jwt-secret-key:latest,\
JWT_REFRESH_SECRET=jwt-refresh-secret-key:latest,\
GCP_WEBHOOK_SECRET=gcp-webhook-secret:latest,\
GCP_SERVICE_ACCOUNT_PATH=gcp-service-account-key:latest"

# 3. Get backend URL
export BACKEND_URL=$(gcloud run services describe ap2-expense-backend \
  --region=$GCP_REGION \
  --format="value(status.url)")

# 4. Update webhook audience
gcloud run services update ap2-expense-backend \
  --region=$GCP_REGION \
  --update-env-vars="GCP_WEBHOOK_AUDIENCE=$BACKEND_URL"

# 5. Deploy frontend (2 min)
gcloud run deploy ap2-expense-frontend \
  --image=gcr.io/$GCP_PROJECT_ID/ap2-expense-frontend:v1.0.0 \
  --region=$GCP_REGION \
  --platform=managed \
  --allow-unauthenticated \
  --min-instances=1 \
  --max-instances=5 \
  --memory=512Mi \
  --cpu=1 \
  --set-env-vars="VITE_API_BASE_URL=$BACKEND_URL"

export FRONTEND_URL=$(gcloud run services describe ap2-expense-frontend \
  --region=$GCP_REGION \
  --format="value(status.url)")
```

---

## Step 3: Run Database Migrations (2 min)

```bash
# Start Cloud SQL Proxy in background
cloud_sql_proxy -instances=$CONNECTION_NAME=tcp:5432 &
PROXY_PID=$!

# Run migrations
cd backend
export DATABASE_URL="postgresql://ap2_user:$DB_PASSWORD@localhost:5432/ap2_production"
alembic upgrade head

# Stop proxy
kill $PROXY_PID
cd ..
```

---

## Step 4: Configure GCP Marketplace Integration (5 min)

```bash
# 1. Setup Pub/Sub (2 min)
./scripts/setup-pubsub.sh $GCP_PROJECT_ID $GCP_REGION $BACKEND_URL

# 2. Setup Cloud Scheduler (2 min)
./scripts/setup-cloud-scheduler.sh $GCP_PROJECT_ID $GCP_REGION $BACKEND_URL

# 3. Setup Monitoring (1 min - optional but recommended)
./scripts/setup-monitoring-alerts.sh $GCP_PROJECT_ID "ops@yourcompany.com"
```

---

## Step 5: Validate Deployment (3 min)

```bash
# Run validation script
./scripts/validate-environment.sh production

# Test endpoints manually
curl $BACKEND_URL/health
# Should return: {"status":"healthy"}

curl $BACKEND_URL/api/webhooks/gcp/health
# Should return: {"status":"ok"}

curl -I $FRONTEND_URL
# Should return: HTTP/2 200

# View in browser
echo "Backend: $BACKEND_URL"
echo "Frontend: $FRONTEND_URL"
```

---

## What You've Deployed

✅ **Infrastructure**:
- Cloud SQL PostgreSQL database with backups
- Cloud Run backend (2 GB RAM, 2 CPUs, auto-scaling 1-10)
- Cloud Run frontend (512 MB RAM, 1 CPU, auto-scaling 1-5)
- 4 service accounts with proper IAM permissions
- Pub/Sub topic and subscription for marketplace events
- Cloud Scheduler jobs (hourly usage reporting)
- Secret Manager for all sensitive configuration
- Cloud Storage bucket for receipts (optional, add if needed)
- Cloud KMS keyring for AP2 signing (optional, add if needed)

✅ **GCP Marketplace Integration**:
- Procurement webhook: `$BACKEND_URL/api/webhooks/gcp/procurement`
- Entitlement events: `$BACKEND_URL/api/webhooks/gcp/events`
- Usage reporting: Automated hourly via Cloud Scheduler
- JWT/OIDC verification: Enabled for production security

---

## Next Steps

### 1. Create Marketplace Assets (4-8 hours)

```bash
# Seed demo data
cd backend
python seed_screenshot_data.py

# Capture screenshots
cd ..
./scripts/capture-screenshots.sh

# Record demo video (follow script)
# See: marketplace/DEMO_VIDEO_SCRIPT.md

# Export product icon
# See: marketplace/ICON_DESIGN_GUIDE.md
```

### 2. Register Domain (1 hour)

- Register: `ap2expense.com`
- Configure DNS
- Set up: `support@ap2expense.com`
- Map custom domains to Cloud Run (optional)

### 3. Submit to GCP Marketplace (1 hour)

1. Go to: https://console.cloud.google.com/partner
2. Create product listing
3. Upload assets (8 screenshots, video, icon)
4. Configure pricing tiers
5. Add webhook URLs:
   - Procurement: `$BACKEND_URL/api/webhooks/gcp/procurement`
   - Events: `projects/$GCP_PROJECT_ID/topics/gcp-marketplace-entitlement-events`
6. Submit for Google review (1-2 weeks)

---

## Troubleshooting

### Backend not starting
```bash
# Check logs
gcloud run services logs read ap2-expense-backend --limit=50

# Common issues:
# - Database connection failed: Check DATABASE_URL secret
# - Permission denied: Verify service account has Cloud SQL Client role
# - Secret not found: Ensure all secrets are created
```

### Frontend 502 errors
```bash
# Check if backend is accessible
curl $BACKEND_URL/health

# Update frontend with correct backend URL
gcloud run services update ap2-expense-frontend \
  --update-env-vars="VITE_API_BASE_URL=$BACKEND_URL"
```

### Webhook delivery failing
```bash
# Check OIDC configuration
gcloud pubsub subscriptions describe gcp-marketplace-entitlement-events-sub

# Verify audience matches
echo "Expected: $BACKEND_URL"
echo "Configured:"
gcloud run services describe ap2-expense-backend \
  --format="value(spec.template.spec.containers[0].env[?(@.name=='GCP_WEBHOOK_AUDIENCE')].value)"
```

---

## Cost Estimate (Monthly)

| Resource | Configuration | Cost |
|----------|--------------|------|
| Cloud Run Backend | 1-10 instances, 2GB RAM | $20-100 |
| Cloud Run Frontend | 1-5 instances, 512MB RAM | $10-30 |
| Cloud SQL | db-custom-2-7680 + 20GB storage | $120 |
| Cloud Storage | 100GB receipts | $2 |
| Cloud Scheduler | 2 jobs x 720 runs | $0.30 |
| Pub/Sub | 10K messages | $0.40 |
| Secret Manager | 10 secrets x 6 versions | $0.30 |
| **Total** | | **~$155/month** |

Note: Costs scale with usage. Add autoscaling limits to control costs.

---

## Production Checklist

Before launching to customers:

- [ ] Domain registered and configured
- [ ] Support email set up
- [ ] SSL certificates verified
- [ ] Backups tested and automated
- [ ] Monitoring and alerting configured
- [ ] Secrets rotated from defaults
- [ ] Rate limiting enabled
- [ ] CORS origins restricted to production domains
- [ ] Environment variables verified
- [ ] Smoke tests passing
- [ ] E2E tests passing
- [ ] Security audit clean
- [ ] Documentation published

---

## Support

- **Deployment Issues**: See `GCP_MARKETPLACE_DEPLOYMENT_RUNBOOK.md`
- **GCP Issues**: https://cloud.google.com/support
- **Application Issues**: Check logs with `gcloud run services logs read`

---

**Total Time**: ~30 minutes (excluding asset creation)

**Next Action**: Create marketplace assets or test the deployed application at $FRONTEND_URL
