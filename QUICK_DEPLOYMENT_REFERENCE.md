# Quick Deployment Reference

All deployment commands and configurations needed to go live.

## Phase 1: Fix Blockers (1-2 hours)

### 1.1 Generate JWT Secret
```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 1.2 Create Cloud SQL Instance
```bash
gcloud sql instances create ap2-expenses \
  --database-version=POSTGRES_11 \
  --region=us-central1 \
  --tier=db-f1-micro
```

### 1.3 Create Database
```bash
gcloud sql databases create expenses --instance=ap2-expenses
```

### 1.4 Set Environment Variables
```bash
export PROJECT_ID=$(gcloud config get-value project)
export REGION=us-central1
export ENVIRONMENT=production
export DEBUG=False
export JWT_SECRET=<generated>
export DATABASE_URL=postgresql://ap2user:pass@cloudsql-proxy:5432/expenses
export CORS_ORIGINS=https://yourdomain.com
export GCP_PROJECT_ID=$PROJECT_ID
```

### 1.5 Validate Configuration
```bash
cd backend
python -c "from src.startup_checks import validate_settings; validate_settings()"
```

## Phase 2: Create GCP Infrastructure (1 hour)

### 2.1 Create Secrets
```bash
echo -n "postgresql://ap2user:pass@cloudsql-proxy:5432/expenses" | \
  gcloud secrets create database-url --data-file=-

echo -n "jwt-secret-value" | \
  gcloud secrets create jwt-secret --data-file=-
```

### 2.2 Run Database Migrations
```bash
cloud_sql_proxy -instances=$PROJECT_ID:$REGION:ap2-expenses=tcp:5432 &
cd backend
alembic upgrade head
```

## Phase 3: Build & Deploy (45 minutes)

### 3.1 Build Images
```bash
docker build -f backend/Dockerfile -t gcr.io/$PROJECT_ID/ap2-backend:latest .
docker build -f frontend/Dockerfile -t gcr.io/$PROJECT_ID/ap2-frontend:latest .
docker push gcr.io/$PROJECT_ID/ap2-backend:latest
docker push gcr.io/$PROJECT_ID/ap2-frontend:latest
```

### 3.2 Deploy Backend
```bash
gcloud run deploy ap2-backend \
  --image=gcr.io/$PROJECT_ID/ap2-backend:latest \
  --platform=managed \
  --region=$REGION \
  --memory=2Gi \
  --cpu=2 \
  --set-env-vars "ENVIRONMENT=production,DEBUG=False,CORS_ORIGINS=https://yourdomain.com" \
  --set-secrets "DATABASE_URL=database-url:latest,JWT_SECRET=jwt-secret:latest"
```

### 3.3 Deploy Frontend
```bash
gcloud run deploy ap2-frontend \
  --image=gcr.io/$PROJECT_ID/ap2-frontend:latest \
  --platform=managed \
  --region=$REGION \
  --port=80 \
  --memory=512Mi
```

## Phase 4: Test & Verify (1 hour)

### 4.1 Health Checks
```bash
BACKEND_URL=$(gcloud run services describe ap2-backend --platform=managed --region=$REGION --format='value(status.url)')
curl -i $BACKEND_URL/health
```

### 4.2 View Logs
```bash
gcloud logging read "resource.type=cloud_run_revision" --limit=50 --format=json
```

### 4.3 Smoke Tests
```bash
curl -X POST "$BACKEND_URL/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Password123!","full_name":"Test"}'
```

## Rollback (if needed)

```bash
# Get previous revision
gcloud run revisions list --service=ap2-backend --platform=managed --region=$REGION

# Route traffic back
gcloud run services update-traffic ap2-backend \
  --to-revisions=REVISION_ID=100 \
  --platform=managed --region=$REGION
```

## Post-Deployment Checklist

- [ ] Backend health check passing
- [ ] Frontend accessible
- [ ] Database migrations complete
- [ ] Logs in Cloud Logging
- [ ] User registration working
- [ ] Monitoring configured
- [ ] DNS updated (if custom domain)
- [ ] SSL certificate installed

---

**Timeline:** 4-5 hours from start to production
**Status:** READY FOR DEPLOYMENT (once blockers fixed)
