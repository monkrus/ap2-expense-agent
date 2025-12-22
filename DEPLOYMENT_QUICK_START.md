# 🚀 Production Deployment Quick Start Guide
**AP2 Expense Management Agent**

---

## ✅ Configuration Fixes Applied

All 8 deployment blockers have been **PRE-CONFIGURED** in `.env.production`:

| Fix | Status | Details |
|-----|--------|---------|
| 1. JWT_SECRET | ✅ DONE | Secure random key generated |
| 2. DEBUG | ✅ DONE | Set to `False` |
| 3. ENVIRONMENT | ✅ DONE | Set to `production` |
| 4. GCP_WEBHOOK_SECRET | ✅ DONE | Secure random key generated |
| 5. CORS_ORIGINS | ⚠️ TODO | Update with your domain |
| 6. DATABASE_URL | ⚠️ TODO | Configure Cloud SQL |
| 7. GCP_PROJECT_ID | ⚠️ TODO | Add your GCP project |
| 8. Stripe Keys | ⚠️ TODO | Add production keys |

**Deployment Readiness**: 50% → 100% (after completing TODOs below)

---

## 📋 Step-by-Step Deployment (4-5 hours)

### **Phase 1: Google Cloud Platform Setup** (1-2 hours)

#### Step 1.1: Create GCP Project (5 min)
```bash
# Set your project name
export PROJECT_ID="ap2-expense-agent-prod"

# Create GCP project
gcloud projects create $PROJECT_ID

# Set as default
gcloud config set project $PROJECT_ID

# Enable billing (required)
# Go to: https://console.cloud.google.com/billing
```

#### Step 1.2: Create Cloud SQL PostgreSQL Instance (30 min)
```bash
# Create PostgreSQL instance
gcloud sql instances create expense-db \
  --database-version=POSTGRES_14 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --root-password=REPLACE_SECURE_PASSWORD

# Create database
gcloud sql databases create expense_db --instance=expense-db

# Create user
gcloud sql users create ap2user \
  --instance=expense-db \
  --password=REPLACE_SECURE_PASSWORD

# Get connection name
gcloud sql instances describe expense-db --format='value(connectionName)'
# Output: your-project:us-central1:expense-db
```

**Update `.env.production`**:
```bash
# For Cloud SQL (Unix socket connection - recommended for Cloud Run):
DATABASE_URL=postgresql://ap2user:YOUR_PASSWORD@/expense_db?host=/cloudsql/YOUR_PROJECT:us-central1:expense-db

# For Cloud SQL (TCP connection):
# DATABASE_URL=postgresql://ap2user:YOUR_PASSWORD@CLOUD_SQL_IP:5432/expense_db
```

#### Step 1.3: Update GCP Configuration in .env.production (5 min)
```bash
# Edit backend/.env.production
GCP_PROJECT_ID=ap2-expense-agent-prod  # Your actual project ID
```

---

### **Phase 2: Frontend Configuration** (15 min)

#### Step 2.1: Update CORS Origins (5 min)
```bash
# In backend/.env.production, update:
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com
```

#### Step 2.2: Update Frontend URL (5 min)
```bash
# In backend/.env.production:
FRONTEND_URL=https://your-domain.com
```

#### Step 2.3: Update Frontend API Base URL (5 min)
Edit `frontend/src/api/config.js`:
```javascript
// BEFORE:
export const API_BASE_URL = 'http://localhost:8000';

// AFTER:
export const API_BASE_URL = 'https://api.your-domain.com';
```

---

### **Phase 3: Marketplace Billing Configuration** (30 min)

#### Step 3.1: Enable Marketplace Billing (10 min)
Update `.env.production`:
```bash
ENABLE_GCP_MARKETPLACE=true
GCP_PROJECT_ID=YOUR_PROJECT_ID
GCP_PROVIDER_ID=YOUR_PROVIDER_ID
GCP_SERVICE_ACCOUNT_PATH=/secrets/gcp-marketplace-sa.json
GCP_WEBHOOK_SECRET=your-webhook-secret
GCP_WEBHOOK_AUDIENCE=your-webhook-audience
GCP_USAGE_REPORTING_ENABLED=true
```

#### Step 3.2: Configure SKU Map (10 min)
```bash
GCP_MARKETPLACE_SKU_MAP={"expenses":{"unit":"expense","sku":"SKU_EXP"},"ai_categorizations":{"unit":"ai_categorization","sku":"SKU_AI"},"ap2_transactions":{"unit":"ap2_transaction","sku":"SKU_AP2"}}
```

#### Step 3.3: Verify Marketplace Webhook (10 min - AFTER DEPLOYMENT)
```bash
# Ensure the Marketplace webhook endpoint is reachable
# Endpoint: https://api.your-domain.com/api/v1/webhooks/gcp
```

---

### **Phase 4: Email Configuration** (10 min)

#### Option A: Gmail (Quick Setup)
```bash
# 1. Enable 2FA on your Google account
# 2. Generate App Password: https://myaccount.google.com/apppasswords
# 3. Update .env.production:

SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password-here
SMTP_FROM_EMAIL=noreply@your-domain.com
```

#### Option B: SendGrid (Recommended for Production)
```bash
# 1. Sign up at https://sendgrid.com
# 2. Create API key
# 3. Update .env.production:

SMTP_SERVER=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=your-sendgrid-api-key
SMTP_FROM_EMAIL=noreply@your-domain.com
```

---

### **Phase 5: Build & Deploy** (1-2 hours)

#### Step 5.1: Build Docker Images (10 min)
```bash
# Backend
cd backend
docker build -t gcr.io/$PROJECT_ID/ap2-backend:latest .

# Frontend
cd ../frontend
docker build -t gcr.io/$PROJECT_ID/ap2-frontend:latest .
```

#### Step 5.2: Push to Google Container Registry (5 min)
```bash
# Configure Docker for GCR
gcloud auth configure-docker

# Push images
docker push gcr.io/$PROJECT_ID/ap2-backend:latest
docker push gcr.io/$PROJECT_ID/ap2-frontend:latest
```

#### Step 5.3: Run Database Migrations (5 min)
```bash
# From backend directory
python -m alembic upgrade head
```

#### Step 5.4: Deploy Backend to Cloud Run (15 min)
```bash
gcloud run deploy ap2-backend \
  --image gcr.io/$PROJECT_ID/ap2-backend:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --add-cloudsql-instances $PROJECT_ID:us-central1:expense-db \
  --set-env-vars "$(cat backend/.env.production | grep -v '^#' | xargs | sed 's/ /,/g')" \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10

# Get backend URL
gcloud run services describe ap2-backend --region us-central1 --format='value(status.url)'
```

#### Step 5.5: Deploy Frontend to Cloud Run (15 min)
```bash
# Update frontend/.env.production with backend URL
echo "VITE_API_URL=https://ap2-backend-xxx-uc.a.run.app" > frontend/.env.production

# Rebuild frontend with production API URL
cd frontend
npm run build

# Deploy
gcloud run deploy ap2-frontend \
  --image gcr.io/$PROJECT_ID/ap2-frontend:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 256Mi \
  --cpu 1

# Get frontend URL
gcloud run services describe ap2-frontend --region us-central1 --format='value(status.url)'
```

#### Step 5.6: Configure Custom Domain (30 min - Optional)
```bash
# Map custom domain to Cloud Run services
gcloud beta run domain-mappings create \
  --service ap2-frontend \
  --domain your-domain.com \
  --region us-central1

gcloud beta run domain-mappings create \
  --service ap2-backend \
  --domain api.your-domain.com \
  --region us-central1

# Update DNS records as instructed by gcloud output
```

---

### **Phase 6: Post-Deployment Verification** (30 min)

#### Step 6.1: Smoke Tests (15 min)
```bash
# Test backend health
curl https://api.your-domain.com/health

# Test user registration
curl -X POST https://api.your-domain.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "SecurePass123!",
    "full_name": "Test User",
    "role": "employee"
  }'

# Test login
curl -X POST https://api.your-domain.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "SecurePass123!"
  }'
```

#### Step 6.2: Frontend Tests (10 min)
1. Visit https://your-domain.com
2. Test user registration
3. Test login
4. Create organization
5. Submit expense
6. Test tier limits (try creating 2nd org on Free tier)

#### Step 6.3: Security Verification (5 min)
```bash
# Check security headers
curl -I https://api.your-domain.com

# Verify:
# - X-Frame-Options: DENY
# - X-Content-Type-Options: nosniff
# - Strict-Transport-Security present
# - Content-Security-Policy present
```

---

### **Phase 7: Monitoring & Alerting** (30 min)

#### Step 7.1: Enable Cloud Logging (10 min)
```bash
# Logs are automatically sent to Cloud Logging for Cloud Run
# View logs:
gcloud logging read "resource.type=cloud_run_revision"
```

#### Step 7.2: Set Up Error Tracking (15 min - Optional)
```bash
# Sign up for Sentry: https://sentry.io
# Create project
# Copy DSN

# Update .env.production:
SENTRY_DSN=https://xxx@o0.ingest.sentry.io/123456

# Redeploy backend
```

#### Step 7.3: Configure Alerts (5 min)
```bash
# In GCP Console, set up alerts for:
# - Error rate > 5%
# - Response time > 2s (p95)
# - CPU utilization > 80%
# - Memory utilization > 90%
```

---

## 🎯 Deployment Checklist

### Pre-Deployment ✅
- [x] JWT_SECRET generated (✅ DONE)
- [x] DEBUG=False (✅ DONE)
- [x] ENVIRONMENT=production (✅ DONE)
- [x] GCP_WEBHOOK_SECRET generated (✅ DONE)
- [ ] GCP project created
- [ ] Cloud SQL PostgreSQL instance created
- [ ] DATABASE_URL configured
- [ ] CORS_ORIGINS updated
- [ ] GCP_PROJECT_ID set
- [ ] Stripe production keys added
- [ ] Stripe products/prices created
- [ ] SMTP/email configured

### Deployment ✅
- [ ] Docker images built
- [ ] Images pushed to GCR
- [ ] Database migrations run
- [ ] Backend deployed to Cloud Run
- [ ] Frontend deployed to Cloud Run
- [ ] Custom domain configured (optional)

### Post-Deployment ✅
- [ ] Smoke tests passed
- [ ] User registration working
- [ ] Login working
- [ ] Organization creation working
- [ ] Expense submission working
- [ ] Tier limits enforced
- [ ] Stripe webhook configured
- [ ] Email sending working
- [ ] Error tracking configured (optional)
- [ ] Alerts configured

---

## 📊 Expected Timeline

| Phase | Time | Cumulative |
|-------|------|------------|
| 1. GCP Setup | 1-2h | 1-2h |
| 2. Frontend Config | 15m | 1.25-2.25h |
| 3. Stripe Config | 30m | 1.75-2.75h |
| 4. Email Config | 10m | 1.83-2.83h |
| 5. Build & Deploy | 1-2h | 2.83-4.83h |
| 6. Verification | 30m | 3.33-5.33h |
| 7. Monitoring | 30m | 3.83-5.83h |
| **TOTAL** | **4-6 hours** | - |

---

## 🆘 Troubleshooting

### Database Connection Fails
```bash
# Verify Cloud SQL instance is running
gcloud sql instances list

# Test connection
gcloud sql connect expense-db --user=ap2user

# Check Cloud Run has Cloud SQL connection
gcloud run services describe ap2-backend --format='value(spec.template.spec.containers[0].env)'
```

### CORS Errors
```bash
# Verify CORS_ORIGINS in .env.production matches your frontend domain
# Redeploy backend after updating
```

### Email Not Sending
```bash
# Test SMTP connection
python -c "
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('your-email@gmail.com', 'your-app-password')
print('SMTP connection successful!')
server.quit()
"
```

---

## 📞 Next Steps

After deployment:
1. Monitor logs for first 24 hours
2. Test all critical workflows
3. Set up automated backups (Cloud SQL)
4. Configure CDN for static assets (optional)
5. Set up staging environment
6. Implement CI/CD pipeline

---

## 🔗 Useful Links

- [GCP Console](https://console.cloud.google.com)
- [Stripe Dashboard](https://dashboard.stripe.com)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud SQL Documentation](https://cloud.google.com/sql/docs)
- [Deployment Validation Report](./DEPLOYMENT_VALIDATION_REPORT.md)

---

**Questions?** Review the comprehensive reports:
- `DEPLOYMENT_VALIDATION_REPORT.md`
- `DEPLOYMENT_BLOCKERS.md`
- `FINAL_COMPREHENSIVE_TEST_SUMMARY.md`
