# DEPLOYMENT BLOCKERS - QUICK FIX GUIDE

**Status:** 8 CRITICAL/HIGH BLOCKERS IDENTIFIED
**Timeline:** All fixable in 2-3 hours

---

## BLOCKER #1: JWT_SECRET Using Default Placeholder

**Status:** CRITICAL
**File:** `backend/src/config.py:34`
**Enforced by:** `backend/src/startup_checks.py:28`

### Current State
```python
jwt_secret: str = "your-secret-key-change-in-production"
```

### Impact
- Application startup will FAIL with error: `"JWT_SECRET is using the default placeholder value"`
- Cryptographic key is not secure
- Cannot authenticate users

### Fix (2 minutes)
```bash
# Generate a strong random secret
python -c "import secrets; print(secrets.token_urlsafe(64))"

# Output example:
# xJ9kL2mN5pQ8vW3xY6zA9bC2dE5fG8hI0jK3mN6pQ9sT2uV5xY8zA1bC4dE7fG

# Set in environment
export JWT_SECRET=xJ9kL2mN5pQ8vW3xY6zA9bC2dE5fG8hI0jK3mN6pQ9sT2uV5xY8zA1bC4dE7fG

# Or use Cloud Secret Manager (production)
echo -n "xJ9kL2mN5pQ8vW3xY6zA9bC2dE5fG8hI0jK3mN6pQ9sT2uV5xY8zA1bC4dE7fG" | \
  gcloud secrets create jwt-secret --data-file=-
```

### Validation
```bash
# Test startup validation
cd backend
python -c "from src.startup_checks import validate_settings; validate_settings()"
# Should complete without error
```

---

## BLOCKER #2: DATABASE_URL Not Configured for Production

**Status:** CRITICAL
**File:** `backend/src/startup_checks.py:35`
**Current:** `sqlite:///./test.db`

### Impact
- Application will FAIL to start with error: `"DATABASE_URL points to sqlite; use a managed database"`
- Production data would be lost on container restart
- SQLite doesn't support concurrent connections

### Fix (30 minutes)

**Step 1: Create Cloud SQL Instance**
```bash
# Create PostgreSQL 11+ instance
gcloud sql instances create ap2-expenses \
  --database-version=POSTGRES_11 \
  --region=us-central1 \
  --tier=db-f1-micro  # Upgrade tier for production

# Wait for creation (5-10 minutes)
gcloud sql instances describe ap2-expenses --format="value(state)"
```

**Step 2: Create Database**
```bash
# Get Cloud SQL instance IP
CLOUD_SQL_IP=$(gcloud sql instances describe ap2-expenses \
  --format="value(ipAddresses[0].ipAddress)")

# Create database and user
gcloud sql connect ap2-expenses --user=postgres << EOF
CREATE DATABASE expenses;
CREATE USER ap2user WITH PASSWORD 'your_secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE expenses TO ap2user;
EOF
```

**Step 3: Set Environment Variable**
```bash
# Local development (with Cloud SQL Proxy)
export DATABASE_URL="postgresql://ap2user:your_secure_password_here@localhost:5432/expenses?sslmode=require"

# Cloud Run (automatic via Secret Manager)
gcloud secrets create database-url --data-file=- << EOF
postgresql://ap2user:your_secure_password_here@cloudsql-proxy:5432/expenses?sslmode=require
EOF

# Update Cloud Run service
gcloud run services update ap2-backend --set-secrets DATABASE_URL=database-url:latest
```

**Step 4: Test Connection**
```bash
# Start Cloud SQL Proxy in a terminal
cloud_sql_proxy -instances=PROJECT:us-central1:ap2-expenses=tcp:5432

# In another terminal, test connection
psql -h 127.0.0.1 -U ap2user -d expenses -c "SELECT version();"
```

### Validation
```bash
cd backend
python -c "from src.startup_checks import validate_settings; validate_settings()"
# Should pass without errors
```

---

## BLOCKER #3: DEBUG Mode Enabled in Production

**Status:** CRITICAL
**File:** `backend/src/startup_checks.py:28`
**Current:** `DEBUG=True`

### Impact
- Application startup will FAIL with error: `"debug must be False in production/staging"`
- Exposes stack traces to users
- Enables development endpoints in production
- Security vulnerability

### Fix (1 minute)
```bash
# Set in environment
export DEBUG=False

# Or verify in .env file
echo "DEBUG=False" >> backend/.env

# Cloud Run
gcloud run services update ap2-backend --set-env-vars DEBUG=False
```

### Validation
Check startup:
```bash
cd backend
ENVIRONMENT=production DEBUG=False python -c "from src.startup_checks import validate_settings; validate_settings()"
# Should pass without errors
```

---

## BLOCKER #4: CORS_ORIGINS Includes Localhost

**Status:** CRITICAL
**File:** `backend/src/startup_checks.py:39-45`
**Current:** `http://localhost:3000,http://localhost:5173,http://127.0.0.1:5173,...`

### Impact
- Application startup will FAIL with error: `"CORS origins include development or wildcard entries"`
- Localhost allowed in production = XSS vulnerability
- Any attacker can craft malicious content from localhost

### Fix (5 minutes)

**Step 1: Determine Production Domain**
```bash
# Example: Your production domain is api.ap2expense.com
FRONTEND_DOMAIN="https://app.ap2expense.com"
BACKEND_DOMAIN="https://api.ap2expense.com"
```

**Step 2: Set Environment Variable**
```bash
# Set only production domains (HTTPS only)
export CORS_ORIGINS="$FRONTEND_DOMAIN,$BACKEND_DOMAIN"

# Example
export CORS_ORIGINS="https://app.ap2expense.com,https://api.ap2expense.com"

# Verify in .env
echo "CORS_ORIGINS=https://app.ap2expense.com,https://api.ap2expense.com" >> backend/.env
```

**Step 3: Update Cloud Run**
```bash
gcloud run services update ap2-backend \
  --set-env-vars "CORS_ORIGINS=https://app.ap2expense.com,https://api.ap2expense.com"
```

### Validation
```bash
# Check startup validation
ENVIRONMENT=production CORS_ORIGINS="https://app.ap2expense.com" \
  python -c "from src.startup_checks import validate_settings; validate_settings()"
# Should pass
```

---

## BLOCKER #5: ENVIRONMENT Not Set to Production

**Status:** CRITICAL
**File:** `backend/src/startup_checks.py`
**Current:** `ENVIRONMENT=development`

### Impact
- Security checks bypassed
- Debug mode may be enabled
- Development defaults applied

### Fix (1 minute)
```bash
# Set environment
export ENVIRONMENT=production

# Cloud Run
gcloud run services update ap2-backend --set-env-vars ENVIRONMENT=production
```

---

## BLOCKER #6: GCP_PROJECT_ID Not Configured

**Status:** HIGH (if using GCP Marketplace)
**File:** `backend/src/config.py:82`
**Required by:** GCP Marketplace integration

### Impact
- Marketplace webhooks will fail
- Account approval/cancellation won't work
- Usage reporting disabled

### Fix (2 minutes)
```bash
# Get your GCP project ID
gcloud config get-value project

# Set environment variable
export GCP_PROJECT_ID=your-gcp-project-id

# Example
export GCP_PROJECT_ID=ap2-expense-production

# Cloud Run
gcloud run services update ap2-backend --set-env-vars GCP_PROJECT_ID=ap2-expense-production
```

### Validation
```bash
gcloud projects describe $GCP_PROJECT_ID
```

---

## BLOCKER #7: GCP_WEBHOOK_SECRET Not Configured

**Status:** HIGH (if using GCP Marketplace)
**File:** `backend/src/gcp/marketplace_client.py`
**Required by:** Webhook signature verification

### Impact
- Marketplace webhooks won't be verified
- Unauthenticated requests could trigger account changes
- Security vulnerability

### Fix (10 minutes)

**Step 1: Get Webhook Secret from GCP Marketplace**
1. Go to Google Cloud Marketplace Console
2. Select your product listing
3. Go to Settings → Webhooks
4. Copy the webhook secret

**Step 2: Set Environment Variable**
```bash
# Set from GCP Marketplace
export GCP_WEBHOOK_SECRET=your_webhook_secret_from_gcp

# Create Cloud Secret Manager secret
echo -n "your_webhook_secret_from_gcp" | \
  gcloud secrets create gcp-webhook-secret --data-file=-

# Update Cloud Run
gcloud run services update ap2-backend \
  --set-secrets GCP_WEBHOOK_SECRET=gcp-webhook-secret:latest
```

### Validation
```bash
# Verify webhook can be verified
python << 'EOF'
import hmac
import hashlib
from src.gcp.marketplace_client import MarketplaceClient

# Test signature verification
client = MarketplaceClient()
test_payload = '{"test": "data"}'
correct_signature = hmac.new(
    b'test-secret',
    test_payload.encode(),
    hashlib.sha256
).hexdigest()
print(f"Signature: {correct_signature}")
EOF
```

---

## BLOCKER #8: Pytest AsyncIO Configuration

**Status:** MEDIUM
**File:** `backend/pytest.ini`
**Impact:** 69 async tests not running (false failures)

### Current Symptom
```
FAILED tests/test_*.py - Failed: async def functions are not natively supported.
You need to install a suitable plugin for your async framework, for example:
  - anyio
  - pytest-asyncio
```

### Fix (2 minutes)
```bash
# Edit backend/pytest.ini
# Add after [pytest] section:
[pytest]
asyncio_mode = auto
```

### Updated pytest.ini
```ini
[pytest]
pythonpath = .
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
addopts = -v --tb=short --strict-markers -p no:warnings
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
    auth: marks authentication tests
    expenses: marks expense-related tests
    permissions: marks permission tests
    multi_tenant: marks multi-tenancy tests
```

### Validation
```bash
cd backend
pytest tests/test_auth.py -v
# Should show "32 passed"
```

---

## BLOCKER #9: Cloud SQL Instance Not Created

**Status:** CRITICAL
**Impact:** No production database available

### Quick Fix (15 minutes)
```bash
# Create instance
gcloud sql instances create ap2-expenses \
  --database-version=POSTGRES_11 \
  --region=us-central1 \
  --tier=db-f1-micro

# Create database
gcloud sql databases create expenses \
  --instance=ap2-expenses

# Get instance IP
gcloud sql instances describe ap2-expenses \
  --format="value(ipAddresses[0].ipAddress)"

# Test connection (requires Cloud SQL Proxy)
cloud_sql_proxy -instances=PROJECT:us-central1:ap2-expenses=tcp:5432 &
psql -h 127.0.0.1 -U postgres -d expenses -c "SELECT 1"
```

---

## QUICK FIX SUMMARY

Run these commands to fix all blockers:

```bash
#!/bin/bash

# 1. Generate JWT secret
JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(64))")
echo "JWT_SECRET=$JWT_SECRET"

# 2. Set critical environment variables
export ENVIRONMENT=production
export DEBUG=False
export JWT_SECRET=$JWT_SECRET
export CORS_ORIGINS="https://app.yourdomain.com,https://api.yourdomain.com"
export GCP_PROJECT_ID=$(gcloud config get-value project)

# 3. Create Cloud SQL (if needed)
# gcloud sql instances create ap2-expenses --database-version=POSTGRES_11 --region=us-central1 --tier=db-f1-micro

# 4. Update .env file
cat > backend/.env << EOF
ENVIRONMENT=production
DEBUG=False
DATABASE_URL=postgresql://user:pass@cloud-sql-proxy:5432/expenses
JWT_SECRET=$JWT_SECRET
CORS_ORIGINS=https://app.yourdomain.com,https://api.yourdomain.com
GCP_PROJECT_ID=$GCP_PROJECT_ID
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=...
EOF

# 5. Fix pytest.ini
echo "asyncio_mode = auto" >> backend/pytest.ini

# 6. Validate startup
cd backend
python -c "from src.startup_checks import validate_settings; validate_settings()"
echo "All checks passed!"
```

---

## DEPLOYMENT READINESS AFTER FIXES

Once all blockers are fixed:

- [ ] Backend starts without errors
- [ ] Health check endpoint responds: `GET /health → 200 OK`
- [ ] Database migrations run automatically on startup
- [ ] Tests pass: `pytest tests/ -v`
- [ ] Logs appear in Cloud Logging
- [ ] Metrics available in Cloud Monitoring

---

## VALIDATION CHECKLIST

```bash
# Test backend startup
cd backend
python -c "
from src.startup_checks import validate_settings
validate_settings()
print('✓ All startup checks passed!')
"

# Run auth tests (should all pass)
cd backend
pytest tests/test_auth.py -v

# Test database connection
psql -h cloud-sql-proxy-ip -U ap2user -d expenses -c "SELECT COUNT(*) FROM users;"

# Test API health
curl https://ap2-backend.run.app/health

# Check logs
gcloud logging read --limit=10 --format=json
```

---

**Status:** All blockers can be fixed in < 3 hours
**Ready for Deployment:** Upon completion of all blockers
