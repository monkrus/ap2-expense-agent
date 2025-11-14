# AP2 Expense Agent - Quick Reference Guide

**Last Updated:** 2025-11-13
**Version:** 1.0.0

---

## 🚀 Common Commands

### Deployment

```bash
# Complete one-command deployment
./deploy-complete.sh --project my-gcp-project

# Deploy only backend
./deploy-to-cloudrun.sh --project my-gcp-project --skip-frontend

# Deploy only frontend
./deploy-to-cloudrun.sh --project my-gcp-project --skip-backend

# Configure secrets
./scripts/setup-secrets.sh --project my-gcp-project --interactive

# Dry run (test without deploying)
./deploy-complete.sh --project my-gcp-project --dry-run
```

### Local Development

```bash
# Backend
cd backend
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uvicorn src.api:app --reload --port 8000

# Frontend
cd frontend
npm run dev

# Tests
cd backend
pytest -v
pytest --cov=src --cov-report=html

# GCP Integration Tests
cd backend
python test_gcp_integration.py --test all
```

### Database

```bash
# Run migrations
cd backend
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# Rollback last migration
alembic downgrade -1

# Check current version
alembic current

# View migration history
alembic history
```

---

## 🔧 gcloud Commands

### Project Setup

```bash
# Initialize gcloud
gcloud init

# Set project
gcloud config set project PROJECT_ID

# List projects
gcloud projects list

# Enable APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

### Cloud Run

```bash
# List services
gcloud run services list --region us-central1

# Describe service
gcloud run services describe ap2-expense-backend --region us-central1

# Get service URL
gcloud run services describe ap2-expense-backend \
  --region us-central1 \
  --format="value(status.url)"

# View logs
gcloud run services logs read ap2-expense-backend --region us-central1

# Update service
gcloud run services update ap2-expense-backend \
  --region us-central1 \
  --set-env-vars KEY=VALUE

# Delete service
gcloud run services delete ap2-expense-backend --region us-central1
```

### Cloud SQL

```bash
# List instances
gcloud sql instances list

# Describe instance
gcloud sql instances describe ap2-expense-db

# Create instance
gcloud sql instances create ap2-expense-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1

# Connect to instance
gcloud sql connect ap2-expense-db --user=postgres

# Create database
gcloud sql databases create expenses --instance=ap2-expense-db

# Create user
gcloud sql users create ap2user \
  --instance=ap2-expense-db \
  --password=PASSWORD

# Get connection name
gcloud sql instances describe ap2-expense-db \
  --format="value(connectionName)"
```

### Secret Manager

```bash
# Create secret
echo "secret-value" | gcloud secrets create secret-name --data-file=-

# Update secret
echo "new-value" | gcloud secrets versions add secret-name --data-file=-

# List secrets
gcloud secrets list

# Access secret
gcloud secrets versions access latest --secret=secret-name

# Delete secret
gcloud secrets delete secret-name

# Grant access to service account
gcloud secrets add-iam-policy-binding secret-name \
  --member="serviceAccount:SERVICE_ACCOUNT@PROJECT.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Build & Deploy

```bash
# Build Docker image
gcloud builds submit --tag gcr.io/PROJECT_ID/app-name .

# Deploy to Cloud Run
gcloud run deploy app-name \
  --image gcr.io/PROJECT_ID/app-name:latest \
  --region us-central1 \
  --allow-unauthenticated

# View build history
gcloud builds list --limit=10

# Stream build logs
gcloud builds log BUILD_ID --stream
```

---

## 🔐 Secret Management

### Required Secrets

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `jwt-secret` | JWT signing key | Generate with Python |
| `database-url` | PostgreSQL connection | `postgresql://user:pass@/db?host=/cloudsql/...` |
| `stripe-secret-key` | Stripe secret key | `sk_live_...` |
| `stripe-webhook-secret` | Stripe webhook secret | `whsec_...` |
| `gcp-webhook-secret` | GCP webhook secret | Generate with Python |
| `smtp-password` | Email SMTP password | Your SMTP password |

### Generate Secrets

```python
# JWT Secret
python -c "import secrets; print(secrets.token_urlsafe(64))"

# GCP Webhook Secret
python -c "import secrets; print(secrets.token_hex(32))"

# Random Password
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Bind Secrets to Cloud Run

```bash
gcloud run services update ap2-expense-backend \
  --update-secrets=JWT_SECRET=jwt-secret:latest \
  --update-secrets=DATABASE_URL=database-url:latest \
  --update-secrets=STRIPE_SECRET_KEY=stripe-secret-key:latest \
  --update-secrets=STRIPE_WEBHOOK_SECRET=stripe-webhook-secret:latest \
  --update-secrets=GCP_WEBHOOK_SECRET=gcp-webhook-secret:latest \
  --update-secrets=SMTP_PASSWORD=smtp-password:latest \
  --region us-central1
```

---

## 🧪 Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_auth.py

# Run specific test
pytest tests/test_auth.py::TestAuth::test_login

# Run with verbose output
pytest -v -s

# Run and stop on first failure
pytest -x

# Run only failed tests
pytest --lf
```

### Frontend Tests

```bash
cd frontend

# Build for production
npm run build

# Run linter
npm run lint

# Type checking (if TypeScript)
npm run type-check

# Run Playwright tests
npm test

# Run tests in UI mode
npm run test:ui
```

### Integration Tests

```bash
cd backend

# Run GCP integration tests
python test_gcp_integration.py --test all

# Test only procurement
python test_gcp_integration.py --test procurement

# Test only usage reporting
python test_gcp_integration.py --test usage

# Custom backend URL
python test_gcp_integration.py --url http://localhost:8000 --test all
```

---

## 🔍 Monitoring & Debugging

### View Logs

```bash
# Cloud Run logs
gcloud run services logs read ap2-expense-backend --region us-central1

# Stream logs in real-time
gcloud run services logs tail ap2-expense-backend --region us-central1

# Filter logs
gcloud run services logs read ap2-expense-backend \
  --region us-central1 \
  --filter="severity>=ERROR"

# Last 100 lines
gcloud run services logs read ap2-expense-backend \
  --region us-central1 \
  --limit=100
```

### Health Checks

```bash
# Backend health
curl https://your-backend-url/health

# GCP webhook health
curl https://your-backend-url/api/webhooks/gcp/health

# Stripe webhook health
curl https://your-backend-url/webhooks/health

# Full health check with jq
curl -s https://your-backend-url/health | jq
```

### Database Queries

```bash
# Connect to Cloud SQL
gcloud sql connect ap2-expense-db --user=ap2user --database=expenses

# Common SQL queries
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM expenses;
SELECT COUNT(*) FROM organizations;
SELECT tier, COUNT(*) FROM subscriptions GROUP BY tier;
```

---

## 📊 Useful Queries

### Backend API

```bash
# Get API version
curl https://your-backend-url/health

# Test authentication
curl -X POST https://your-backend-url/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test"}'

# Get expenses (with auth token)
curl https://your-backend-url/api/v1/expenses \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Create expense
curl -X POST https://your-backend-url/api/v1/expenses \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount":50.00,"description":"Test expense","category":"Office"}'
```

### Database Metrics

```sql
-- User statistics
SELECT
  COUNT(*) as total_users,
  COUNT(CASE WHEN is_active = true THEN 1 END) as active_users,
  COUNT(CASE WHEN totp_enabled = true THEN 1 END) as users_with_2fa
FROM users;

-- Expense statistics
SELECT
  status,
  COUNT(*) as count,
  SUM(amount) as total_amount,
  AVG(amount) as avg_amount
FROM expenses
GROUP BY status;

-- Organization statistics
SELECT
  COUNT(*) as total_organizations,
  COUNT(DISTINCT om.user_id) as total_members
FROM organizations o
LEFT JOIN organization_members om ON o.id = om.organization_id;

-- Subscription breakdown
SELECT
  tier,
  status,
  COUNT(*) as count
FROM subscriptions
GROUP BY tier, status;
```

---

## 🔄 Common Operations

### Update Backend

```bash
# Make code changes
git add .
git commit -m "Update backend"
git push

# Rebuild and redeploy
cd backend
gcloud builds submit --tag gcr.io/PROJECT_ID/ap2-expense-backend .
gcloud run deploy ap2-expense-backend \
  --image gcr.io/PROJECT_ID/ap2-expense-backend:latest \
  --region us-central1
```

### Update Frontend

```bash
# Make code changes
git add .
git commit -m "Update frontend"
git push

# Rebuild with new backend URL
cd frontend
echo "VITE_API_URL=https://your-backend-url/api/v1" > .env.production
npm run build

# Deploy
gcloud builds submit --tag gcr.io/PROJECT_ID/ap2-expense-frontend .
gcloud run deploy ap2-expense-frontend \
  --image gcr.io/PROJECT_ID/ap2-expense-frontend:latest \
  --region us-central1
```

### Rollback Deployment

```bash
# List revisions
gcloud run revisions list --service ap2-expense-backend --region us-central1

# Update to specific revision
gcloud run services update-traffic ap2-expense-backend \
  --to-revisions REVISION_NAME=100 \
  --region us-central1
```

### Scale Service

```bash
# Update instance limits
gcloud run services update ap2-expense-backend \
  --min-instances=2 \
  --max-instances=20 \
  --region us-central1

# Update resources
gcloud run services update ap2-expense-backend \
  --memory=4Gi \
  --cpu=4 \
  --region us-central1
```

---

## 🛠️ Troubleshooting

### Common Issues

#### "No module named 'src'"
```bash
# Ensure you're in the backend directory
cd backend
export PYTHONPATH="${PYTHONPATH}:${PWD}"
```

#### "Database connection failed"
```bash
# Check DATABASE_URL
echo $DATABASE_URL

# Test connection
python -c "from sqlalchemy import create_engine; engine = create_engine('$DATABASE_URL'); engine.connect()"
```

#### "Port already in use"
```bash
# Find process using port
lsof -i :8000  # Mac/Linux
netstat -ano | findstr :8000  # Windows

# Kill process
kill -9 PID  # Mac/Linux
taskkill /F /PID PID  # Windows
```

#### "Cloud Run deployment failed"
```bash
# Check build logs
gcloud builds log BUILD_ID

# Check service logs
gcloud run services logs read SERVICE_NAME --region REGION

# Verify image exists
gcloud container images list --repository=gcr.io/PROJECT_ID
```

---

## 📋 Checklists

### Pre-Deployment Checklist

- [ ] Tests passing (backend: 268/278)
- [ ] Frontend builds successfully
- [ ] Environment variables configured
- [ ] Secrets created in Secret Manager
- [ ] Cloud SQL instance created
- [ ] Database migrations ready
- [ ] Stripe keys (test mode for staging)
- [ ] GCP project configured
- [ ] APIs enabled
- [ ] Service accounts created

### Post-Deployment Checklist

- [ ] Health endpoints responding
- [ ] Frontend loads successfully
- [ ] Backend API accessible
- [ ] Database connection working
- [ ] Secrets mounted correctly
- [ ] Logs streaming to Cloud Logging
- [ ] Monitoring dashboard configured
- [ ] Alerts configured
- [ ] Custom domain mapped (if applicable)
- [ ] SSL certificate provisioned

### Go-Live Checklist

- [ ] All tests passing
- [ ] Security audit completed
- [ ] Performance testing completed
- [ ] Load testing completed
- [ ] Backup strategy in place
- [ ] Disaster recovery plan documented
- [ ] Monitoring and alerting active
- [ ] On-call rotation established
- [ ] Documentation updated
- [ ] Customer support ready
- [ ] Stripe production keys configured
- [ ] GCP Marketplace listing live

---

## 📞 Support Resources

### Documentation
- [Main README](README.md)
- [Deployment Quickstart](DEPLOYMENT_QUICKSTART.md)
- [Cloud Run Deployment](backend/CLOUD_RUN_DEPLOYMENT.md)
- [GCP Marketplace Testing](backend/GCP_MARKETPLACE_TESTING.md)
- [Security Report](backend/SECURITY_REMEDIATION_REPORT.md)

### External Resources
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Cloud Run Docs](https://cloud.google.com/run/docs)
- [Stripe API Docs](https://stripe.com/docs/api)
- [React Docs](https://react.dev/)

### Getting Help
- GitHub Issues: https://github.com/monkrus/ap2-expense-agent/issues
- Email: support@yourdomain.com
- Slack: [Join community](#)

---

**Quick Reference Version:** 1.0.0
**Last Updated:** 2025-11-13
**Maintained by:** AP2 Expense Agent Team
