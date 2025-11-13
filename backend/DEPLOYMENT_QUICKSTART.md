# Deployment Quick Start Guide

## 🚀 Fast Track to Production

This guide provides the fastest path from development to production deployment on Google Cloud Platform.

---

## Prerequisites

```bash
# Install required tools
- Docker & docker-compose
- gcloud CLI
- PostgreSQL client (optional)
```

---

## Step 1: PostgreSQL Migration (15 minutes)

### Quick Setup

```bash
# Navigate to backend directory
cd /home/user/ap2-expense-agent/backend

# Run automated setup script
./scripts/setup-postgres.sh
```

**What it does:**
- ✅ Starts PostgreSQL in Docker
- ✅ Updates .env configuration
- ✅ Runs all database migrations
- ✅ Verifies setup with tests

**Manual verification:**
```bash
# Check database is running
docker-compose ps

# View tables
docker-compose exec postgres psql -U ap2user -d expenses -c "\dt"

# Run tests
pytest --tb=short
# Expected: 268/278 passing
```

### Troubleshooting

**Port 5432 already in use:**
```bash
# Stop existing PostgreSQL
sudo systemctl stop postgresql
# or
docker stop $(docker ps -q --filter ancestor=postgres)
```

**Migration errors:**
```bash
# Check migration status
alembic current

# Rollback if needed
alembic downgrade -1

# Try again
alembic upgrade head
```

---

## Step 2: GCP Project Setup (10 minutes)

```bash
# Set your project ID
export PROJECT_ID=your-project-id
export REGION=us-central1

# Authenticate
gcloud auth login
gcloud config set project $PROJECT_ID

# Enable ALL required APIs in one command
gcloud services enable \
  run.googleapis.com \
  sql-component.googleapis.com \
  sqladmin.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  cloudcommerceprocurement.googleapis.com \
  servicecontrol.googleapis.com \
  cloudscheduler.googleapis.com
```

---

## Step 3: Cloud SQL Setup (10 minutes)

```bash
# Create PostgreSQL instance
gcloud sql instances create ap2-expense-db \
  --database-version=POSTGRES_15 \
  --tier=db-custom-2-7680 \
  --region=$REGION \
  --no-assign-ip

# Create database and user
gcloud sql databases create expenses --instance=ap2-expense-db
gcloud sql users create ap2user --instance=ap2-expense-db \
  --password=$(openssl rand -base64 32)

# Save connection details
gcloud sql instances describe ap2-expense-db --format="value(connectionName)"
```

---

## Step 4: Secrets Management (5 minutes)

```bash
# Generate and store JWT secret
echo -n "$(openssl rand -hex 32)" | \
  gcloud secrets create jwt-secret-key --data-file=-

# Store Stripe key (use test key initially)
echo -n "sk_test_YOUR_KEY" | \
  gcloud secrets create stripe-secret-key --data-file=-

# Store database password
echo -n "YOUR_DB_PASSWORD" | \
  gcloud secrets create database-password --data-file=-

# Create service account
gcloud iam service-accounts create cloud-run-sa \
  --display-name="Cloud Run Service Account"

# Grant permissions
for SECRET in jwt-secret-key stripe-secret-key database-password; do
  gcloud secrets add-iam-policy-binding $SECRET \
    --member="serviceAccount:cloud-run-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
done
```

---

## Step 5: Deploy to Cloud Run (10 minutes)

```bash
# Get Cloud SQL connection name
CONNECTION_NAME=$(gcloud sql instances describe ap2-expense-db \
  --format="value(connectionName)")

# Build and deploy in one command
gcloud builds submit --tag gcr.io/$PROJECT_ID/ap2-expense-backend && \
gcloud run deploy ap2-expense-backend \
  --image=gcr.io/$PROJECT_ID/ap2-expense-backend:latest \
  --platform=managed \
  --region=$REGION \
  --service-account=cloud-run-sa@${PROJECT_ID}.iam.gserviceaccount.com \
  --add-cloudsql-instances=$CONNECTION_NAME \
  --allow-unauthenticated \
  --memory=2Gi \
  --cpu=2 \
  --min-instances=1 \
  --set-env-vars="ENVIRONMENT=production,GCP_PROJECT_ID=${PROJECT_ID}" \
  --set-secrets="JWT_SECRET_KEY=jwt-secret-key:latest,STRIPE_SECRET_KEY=stripe-secret-key:latest"

# Get service URL
SERVICE_URL=$(gcloud run services describe ap2-expense-backend \
  --region=$REGION --format="value(status.url)")

echo "✅ Deployed to: $SERVICE_URL"
```

---

## Step 6: Verify Deployment (5 minutes)

```bash
# Test health endpoint
curl $SERVICE_URL/health

# Should return:
# {"status":"healthy","database":"connected"}

# Test GCP webhook endpoint
curl $SERVICE_URL/api/webhooks/gcp/health

# View logs
gcloud logging read "resource.type=cloud_run_revision" \
  --limit=20 --format=json
```

---

## Step 7: GCP Marketplace Setup (15 minutes)

### Create Marketplace Service Account

```bash
# Create service account
gcloud iam service-accounts create gcp-marketplace-sa \
  --display-name="GCP Marketplace Service Account"

# Grant permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:gcp-marketplace-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/cloudcommerceprocurement.procurementAdmin"

# Create key
gcloud iam service-accounts keys create gcp-marketplace-key.json \
  --iam-account=gcp-marketplace-sa@${PROJECT_ID}.iam.gserviceaccount.com

# Upload key as secret
gcloud secrets create gcp-marketplace-key \
  --data-file=gcp-marketplace-key.json
```

### Test Procurement Webhook

```bash
# Create test payload
cat > test-procurement.json <<EOF
{
  "eventType": "ENTITLEMENT_PENDING_PLAN_CHANGE_APPROVED",
  "entitlement": {
    "id": "test-ent-123",
    "name": "providers/test/entitlements/test-ent-123",
    "account": "providers/test/accounts/acc-123",
    "product": "products/ap2-expense-agent",
    "plan": "PROFESSIONAL"
  }
}
EOF

# Test webhook
curl -X POST $SERVICE_URL/api/webhooks/gcp/procurement \
  -H "Content-Type: application/json" \
  -d @test-procurement.json

# Check logs for processing
gcloud logging read "resource.type=cloud_run_revision \
  AND jsonPayload.message=~'procurement'" --limit=5
```

### Set Up Usage Reporting Cron

```bash
# Create hourly cron job
gcloud scheduler jobs create http report-gcp-usage \
  --schedule="0 * * * *" \
  --uri="${SERVICE_URL}/api/webhooks/gcp/report-usage" \
  --http-method=POST \
  --oidc-service-account-email=cloud-run-sa@${PROJECT_ID}.iam.gserviceaccount.com \
  --location=$REGION
```

---

## Total Time: ~70 minutes

- PostgreSQL: 15 min
- GCP Setup: 10 min
- Cloud SQL: 10 min
- Secrets: 5 min
- Deploy: 10 min
- Verify: 5 min
- Marketplace: 15 min

---

## Post-Deployment Checklist

### Immediate (Day 1)
- [ ] Health checks passing
- [ ] Database migrations successful
- [ ] GCP webhooks receiving events
- [ ] Usage reporting cron scheduled
- [ ] Monitoring configured

### Week 1
- [ ] Custom domain configured
- [ ] SSL certificates verified
- [ ] CORS configured for frontend
- [ ] Load testing completed (target: 1000 RPS)
- [ ] Error alerting configured

### Week 2
- [ ] Beta customers onboarded
- [ ] Support email configured
- [ ] Documentation updated
- [ ] Performance tuned
- [ ] Security audit completed

### Before Public Launch
- [ ] Stripe production keys configured
- [ ] Terms of Service finalized
- [ ] Privacy Policy reviewed
- [ ] Compliance audit (SOX/GDPR)
- [ ] Disaster recovery tested
- [ ] Submit to GCP Marketplace

---

## Common Commands

```bash
# View logs
gcloud logging read "resource.type=cloud_run_revision" --limit=50

# Update service
gcloud run services update ap2-expense-backend \
  --region=$REGION \
  --set-env-vars="NEW_VAR=value"

# Rollback deployment
gcloud run services update-traffic ap2-expense-backend \
  --to-revisions=PREVIOUS_REVISION=100 \
  --region=$REGION

# Scale up
gcloud run services update ap2-expense-backend \
  --max-instances=200 \
  --region=$REGION

# Database access
gcloud sql connect ap2-expense-db --user=ap2user

# View service details
gcloud run services describe ap2-expense-backend \
  --region=$REGION
```

---

## Troubleshooting Quick Reference

| Issue | Solution |
|-------|----------|
| Build fails | Check Dockerfile, verify all files present |
| Migration error | `alembic downgrade -1 && alembic upgrade head` |
| DB connection fails | Verify Cloud SQL instance running, check connection name |
| Secrets not loading | Check service account has secretmanager.secretAccessor role |
| 502 errors | Check logs: `gcloud logging read` |
| Cold starts slow | Increase min-instances to 1-2 |
| High costs | Reduce min-instances, right-size memory/CPU |

---

## Environment Variables Reference

**Required:**
- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET_KEY` - From Secret Manager
- `STRIPE_SECRET_KEY` - From Secret Manager
- `GCP_PROJECT_ID` - Your GCP project

**Optional but Recommended:**
- `ENVIRONMENT=production`
- `DEBUG=false`
- `ALLOWED_ORIGINS` - CORS domains
- `GCP_MARKETPLACE_PRODUCT_ID`
- `REDIS_URL` - For caching

---

## Success Metrics

After deployment, monitor:

1. **Uptime**: > 99.9%
2. **Response Time**: < 200ms (p95)
3. **Error Rate**: < 0.1%
4. **Test Pass Rate**: 268/278 (96.4%)
5. **Database Queries**: < 100ms average

---

## Next Steps

1. **Performance Testing**
   ```bash
   # Install locust
   pip install locust

   # Run load test
   locust -f tests/load_test.py --host=$SERVICE_URL
   ```

2. **Security Scan**
   ```bash
   # Run security scan
   gcloud container images scan gcr.io/$PROJECT_ID/ap2-expense-backend:latest
   ```

3. **Submit to Marketplace**
   - Complete Partner Portal listing
   - Add pricing tiers
   - Submit for review
   - Wait for approval (~2 weeks)

---

## Support & Resources

- **Detailed Guides**:
  - `POSTGRESQL_MIGRATION.md` - Full PostgreSQL setup
  - `GCP_MARKETPLACE_TESTING.md` - Marketplace integration
  - `CLOUD_RUN_DEPLOYMENT.md` - Complete deployment guide

- **Documentation**:
  - Cloud Run: https://cloud.google.com/run/docs
  - Cloud SQL: https://cloud.google.com/sql/docs
  - Marketplace: https://cloud.google.com/marketplace/docs/partners

- **Getting Help**:
  - GitHub Issues: Report bugs
  - GCP Support: For platform issues
  - Partner Portal: For marketplace questions

---

**You're now ready for production deployment!** 🎉

Start with the PostgreSQL setup script and work through each step. The entire process takes about 70 minutes from start to finish.
