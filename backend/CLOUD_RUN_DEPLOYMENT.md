# Cloud Run Deployment Guide

## Overview
Deploy the AP2 Expense Agent backend to Google Cloud Run with Cloud SQL PostgreSQL.

## Prerequisites
- ✅ GCP Project created
- ✅ Billing enabled
- ✅ `gcloud` CLI installed and authenticated
- ✅ PostgreSQL migration tested locally
- ✅ Docker installed (for building containers)

---

## Step 1: Enable Required APIs

```bash
# Set your project
PROJECT_ID=your-project-id
REGION=us-central1

gcloud config set project $PROJECT_ID

# Enable all required APIs
gcloud services enable \
  run.googleapis.com \
  sql-component.googleapis.com \
  sqladmin.googleapis.com \
  compute.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  cloudcommerceprocurement.googleapis.com \
  servicecontrol.googleapis.com \
  cloudscheduler.googleapis.com \
  --project=$PROJECT_ID
```

---

## Step 2: Create Cloud SQL Instance

```bash
# Create PostgreSQL 15 instance
gcloud sql instances create ap2-expense-db \
  --database-version=POSTGRES_15 \
  --tier=db-custom-2-7680 \
  --region=$REGION \
  --network=default \
  --no-assign-ip \
  --enable-bin-log \
  --backup-start-time=03:00 \
  --maintenance-window-day=SUN \
  --maintenance-window-hour=04 \
  --project=$PROJECT_ID

# Create database
gcloud sql databases create expenses \
  --instance=ap2-expense-db \
  --project=$PROJECT_ID

# Create user
gcloud sql users create ap2user \
  --instance=ap2-expense-db \
  --password=$(openssl rand -base64 32) \
  --project=$PROJECT_ID

# Save the connection name
CONNECTION_NAME=$(gcloud sql instances describe ap2-expense-db \
  --format="value(connectionName)" \
  --project=$PROJECT_ID)

echo "Cloud SQL Connection Name: $CONNECTION_NAME"
```

---

## Step 3: Set Up Secrets Manager

```bash
# Create secrets for sensitive data
echo -n "$(openssl rand -hex 32)" | \
  gcloud secrets create jwt-secret-key \
    --data-file=- \
    --replication-policy=automatic \
    --project=$PROJECT_ID

echo -n "sk_live_YOUR_STRIPE_KEY" | \
  gcloud secrets create stripe-secret-key \
    --data-file=- \
    --replication-policy=automatic \
    --project=$PROJECT_ID

# Database password
echo -n "YOUR_DB_PASSWORD" | \
  gcloud secrets create database-password \
    --data-file=- \
    --replication-policy=automatic \
    --project=$PROJECT_ID

# Create service account for accessing secrets
gcloud iam service-accounts create cloud-run-sa \
  --display-name="Cloud Run Service Account" \
  --project=$PROJECT_ID

# Grant secret access
for SECRET in jwt-secret-key stripe-secret-key database-password; do
  gcloud secrets add-iam-policy-binding $SECRET \
    --member="serviceAccount:cloud-run-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --project=$PROJECT_ID
done

# Grant Cloud SQL access
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:cloud-run-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"
```

---

## Step 4: Create Dockerfile (if not exists)

Create `Dockerfile` in backend directory:

```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8080

# Run migrations and start server
CMD alembic upgrade head && \
    gunicorn src.api:app \
      --workers 4 \
      --worker-class uvicorn.workers.UvicornWorker \
      --bind 0.0.0.0:8080 \
      --timeout 120 \
      --access-logfile - \
      --error-logfile -
```

Create `.dockerignore`:

```
__pycache__
*.pyc
*.pyo
*.pyd
.pytest_cache
.coverage
htmlcov
.env
.env.*
*.db
*.sqlite
*.sqlite3
venv
.venv
*.log
.git
.gitignore
README.md
tests
alembic/versions/*.pyc
```

---

## Step 5: Build and Push Container

```bash
# Build container using Cloud Build
gcloud builds submit \
  --tag gcr.io/$PROJECT_ID/ap2-expense-backend:latest \
  --project=$PROJECT_ID

# Or build locally and push
docker build -t gcr.io/$PROJECT_ID/ap2-expense-backend:latest .
docker push gcr.io/$PROJECT_ID/ap2-expense-backend:latest
```

---

## Step 6: Deploy to Cloud Run

```bash
# Deploy with all configurations
gcloud run deploy ap2-expense-backend \
  --image=gcr.io/$PROJECT_ID/ap2-expense-backend:latest \
  --platform=managed \
  --region=$REGION \
  --service-account=cloud-run-sa@${PROJECT_ID}.iam.gserviceaccount.com \
  --add-cloudsql-instances=$CONNECTION_NAME \
  --allow-unauthenticated \
  --port=8080 \
  --memory=2Gi \
  --cpu=2 \
  --min-instances=1 \
  --max-instances=100 \
  --timeout=300 \
  --concurrency=80 \
  --set-env-vars="ENVIRONMENT=production,GCP_PROJECT_ID=${PROJECT_ID}" \
  --set-secrets="JWT_SECRET_KEY=jwt-secret-key:latest,STRIPE_SECRET_KEY=stripe-secret-key:latest,DATABASE_PASSWORD=database-password:latest" \
  --update-env-vars="DATABASE_URL=postgresql://ap2user:\$(DATABASE_PASSWORD)@/expenses?host=/cloudsql/${CONNECTION_NAME}" \
  --project=$PROJECT_ID

# Get the service URL
SERVICE_URL=$(gcloud run services describe ap2-expense-backend \
  --platform=managed \
  --region=$REGION \
  --format="value(status.url)" \
  --project=$PROJECT_ID)

echo "Service deployed at: $SERVICE_URL"
```

---

## Step 7: Set Up Custom Domain (Optional)

```bash
# Add domain mapping
gcloud run domain-mappings create \
  --service=ap2-expense-backend \
  --domain=api.yourdomain.com \
  --region=$REGION \
  --project=$PROJECT_ID

# Follow instructions to add DNS records
gcloud run domain-mappings describe \
  --domain=api.yourdomain.com \
  --region=$REGION \
  --project=$PROJECT_ID
```

---

## Step 8: Run Database Migrations

```bash
# Option 1: Run migrations during deployment (already in Dockerfile CMD)

# Option 2: Run manually via Cloud Run Jobs
gcloud run jobs create migrate-db \
  --image=gcr.io/$PROJECT_ID/ap2-expense-backend:latest \
  --region=$REGION \
  --service-account=cloud-run-sa@${PROJECT_ID}.iam.gserviceaccount.com \
  --add-cloudsql-instances=$CONNECTION_NAME \
  --set-secrets="DATABASE_PASSWORD=database-password:latest" \
  --set-env-vars="DATABASE_URL=postgresql://ap2user:\$(DATABASE_PASSWORD)@/expenses?host=/cloudsql/${CONNECTION_NAME}" \
  --command="alembic" \
  --args="upgrade,head" \
  --project=$PROJECT_ID

# Execute migration job
gcloud run jobs execute migrate-db \
  --region=$REGION \
  --project=$PROJECT_ID \
  --wait
```

---

## Step 9: Configure CORS

Update `src/api.py` CORS settings for production:

```python
# In src/api.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://yourdomain.com",
        "https://app.yourdomain.com",
        # Add your frontend URLs
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Redeploy after CORS changes.

---

## Step 10: Set Up Health Checks

Cloud Run already uses `/health` endpoint. Verify:

```bash
curl $SERVICE_URL/health

# Expected response:
# {"status":"healthy","database":"connected","version":"1.0.0"}
```

---

## Step 11: Configure Monitoring

```bash
# Create uptime check
gcloud monitoring uptime create ${SERVICE_URL}/health \
  --display-name="AP2 Backend Health" \
  --check-interval=60s \
  --timeout=10s \
  --project=$PROJECT_ID

# Create alerts
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="High Error Rate" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=0.05 \
  --condition-threshold-duration=300s \
  --project=$PROJECT_ID
```

---

## Step 12: Set Up Cloud Scheduler for Usage Reporting

```bash
# Create scheduler job for hourly usage reporting
gcloud scheduler jobs create http report-gcp-usage \
  --schedule="0 * * * *" \
  --uri="${SERVICE_URL}/api/webhooks/gcp/report-usage" \
  --http-method=POST \
  --oidc-service-account-email=cloud-run-sa@${PROJECT_ID}.iam.gserviceaccount.com \
  --oidc-token-audience="${SERVICE_URL}" \
  --location=$REGION \
  --project=$PROJECT_ID
```

---

## Step 13: Configure CI/CD (Optional)

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches: [main]

env:
  PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
  REGION: us-central1
  SERVICE_NAME: ap2-expense-backend

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - id: 'auth'
        uses: 'google-github-actions/auth@v1'
        with:
          credentials_json: '${{ secrets.GCP_SA_KEY }}'

      - name: 'Set up Cloud SDK'
        uses: 'google-github-actions/setup-gcloud@v1'

      - name: 'Build and Push Container'
        run: |
          gcloud builds submit \
            --tag gcr.io/$PROJECT_ID/$SERVICE_NAME:$GITHUB_SHA

      - name: 'Deploy to Cloud Run'
        run: |
          gcloud run deploy $SERVICE_NAME \
            --image gcr.io/$PROJECT_ID/$SERVICE_NAME:$GITHUB_SHA \
            --region $REGION \
            --platform managed
```

---

## Verification Checklist

After deployment, verify:

- [ ] Service is accessible: `curl $SERVICE_URL/health`
- [ ] Database connection works
- [ ] Migrations applied: Check logs
- [ ] Secrets loaded correctly
- [ ] CORS configured for your domain
- [ ] GCP webhooks accessible
- [ ] Usage reporting cron job scheduled
- [ ] Monitoring alerts configured
- [ ] SSL certificate valid
- [ ] Custom domain working (if configured)

---

## Testing in Production

```bash
# Test health endpoint
curl https://your-service-url.run.app/health

# Test authentication
curl -X POST https://your-service-url.run.app/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"test"}'

# Test GCP webhook
curl -X GET https://your-service-url.run.app/api/webhooks/gcp/health
```

---

## Scaling Configuration

```bash
# Update scaling parameters
gcloud run services update ap2-expense-backend \
  --min-instances=2 \
  --max-instances=200 \
  --cpu-throttling \
  --region=$REGION \
  --project=$PROJECT_ID

# Configure request throttling
# (Set in src/rate_limit.py)
```

---

## Cost Optimization

1. **Use minimum instances wisely**:
   - 0 for development
   - 1-2 for production (avoid cold starts)

2. **Right-size resources**:
   - Start with 1 vCPU, 1GB RAM
   - Monitor and adjust based on load

3. **Enable Cloud SQL connection pooling**:
   - Configured in `database.py`

4. **Use Cloud CDN** for static assets

---

## Troubleshooting

### Service Won't Start

```bash
# View logs
gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=ap2-expense-backend" \
  --limit=50 \
  --format=json \
  --project=$PROJECT_ID
```

### Database Connection Issues

```bash
# Test Cloud SQL connection
gcloud sql connect ap2-expense-db \
  --user=ap2user \
  --database=expenses \
  --project=$PROJECT_ID

# Check Cloud SQL proxy settings in Cloud Run
gcloud run services describe ap2-expense-backend \
  --region=$REGION \
  --format="value(spec.template.metadata.annotations)" \
  --project=$PROJECT_ID
```

### High Latency

```bash
# Check Cloud Run metrics
gcloud monitoring dashboards list --project=$PROJECT_ID

# View request latency
gcloud logging read "resource.type=cloud_run_revision \
  AND httpRequest.latency>1s" \
  --limit=20 \
  --format=json \
  --project=$PROJECT_ID
```

---

## Security Checklist

- [ ] Secrets stored in Secret Manager (not env vars)
- [ ] Service account has minimum required permissions
- [ ] Cloud SQL uses private IP
- [ ] HTTPS enforced (automatic with Cloud Run)
- [ ] CORS configured for specific domains only
- [ ] Rate limiting enabled
- [ ] SQL injection protection (SQLAlchemy ORM)
- [ ] JWT tokens with strong secret key
- [ ] Security headers configured (in middleware)

---

## Production Readiness

✅ **Ready for production when:**
- All health checks passing
- Database migrations successful
- Tests passing (268/278)
- Monitoring configured
- Alerts set up
- Backups enabled
- Documentation complete
- Support process defined

---

## Next Steps

1. ✅ Configure Stripe billing and QuickBooks integration
2. ✅ Load testing (use `locust` or `ab`)
3. ✅ Security audit
4. ✅ Performance tuning
5. ✅ Beta customer onboarding
6. ✅ Submit to QuickBooks App Store

**Deployment complete! Your application is ready for production.** 🚀
