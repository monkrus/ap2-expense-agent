# Troubleshooting Guide

Common issues and solutions for AP2 Expense Agent.

---

## Table of Contents

1. [Login & Authentication Issues](#login--authentication-issues)
2. [Expense Submission Problems](#expense-submission-problems)
3. [Receipt Upload Failures](#receipt-upload-failures)
4. [API Integration Issues](#api-integration-issues)
5. [Deployment Problems](#deployment-problems)
6. [Database Connection Errors](#database-connection-errors)
7. [Performance Issues](#performance-issues)
8. [Payment & AP2 Errors](#payment--ap2-errors)

---

## Login & Authentication Issues

### Issue: "Invalid credentials" error

**Symptoms:**
- Cannot login with username/password
- Error message: "Invalid username or password"

**Solutions:**

1. **Verify username**
   - Check for typos
   - Ensure username is registered
   - Try "Forgot Password" link

2. **Check password**
   - Passwords are case-sensitive
   - No extra spaces
   - If using password manager, try typing manually

3. **Account may be locked**
   - After 5 failed attempts, accounts lock for 15 minutes
   - Wait 15 minutes and try again
   - Contact admin to unlock

4. **Check account status**
   ```bash
   # Admin can check via API
   curl -X GET https://your-backend-url/api/v1/admin/users/{user_id} \
     -H "Authorization: Bearer <TOKEN>"

   # Look for: "is_active": true
   ```

### Issue: JWT Token Expired

**Symptoms:**
- Error: "Token has expired"
- HTTP 401 Unauthorized after working earlier

**Solutions:**

1. **Refresh the token**
   ```bash
   curl -X POST https://your-backend-url/api/v1/auth/refresh \
     -H "Content-Type: application/json" \
     -d '{"refresh_token": "<REFRESH_TOKEN>"}'
   ```

2. **Login again**
   - Access tokens expire after 1 hour
   - Refresh tokens expire after 7 days
   - If both expired, re-authenticate

3. **Implement auto-refresh in your client**
   ```python
   import requests
   from datetime import datetime, timedelta

   class TokenManager:
       def __init__(self):
           self.access_token = None
           self.refresh_token = None
           self.expires_at = None

       def is_expired(self):
           return datetime.now() >= self.expires_at

       def refresh_if_needed(self):
           if self.is_expired():
               response = requests.post(
                   f"{API_BASE}/auth/refresh",
                   json={"refresh_token": self.refresh_token}
               )
               data = response.json()
               self.access_token = data['access_token']
               self.expires_at = datetime.now() + timedelta(seconds=data['expires_in'])
   ```

### Issue: 2FA Code Not Working

**Symptoms:**
- "Invalid verification code" error
- 2FA code rejected

**Solutions:**

1. **Check time sync**
   - TOTP codes depend on accurate time
   - Sync device clock with internet time
   - On Windows: Settings → Time & Language → Set time automatically
   - On Mac: System Preferences → Date & Time → Set date and time automatically

2. **Use backup codes**
   - If time sync fails, use backup codes from setup
   - Each backup code works only once
   - Generate new codes after using

3. **Disable and re-enable 2FA**
   - Contact admin to temporarily disable 2FA
   - Re-setup with authenticator app
   - Save new backup codes

---

## Expense Submission Problems

### Issue: "Amount must be positive" error

**Symptoms:**
- Cannot submit expense
- Validation error on amount field

**Solutions:**

1. **Check amount format**
   - Must be positive number: `45.99` ✅
   - No currency symbols: `$45.99` ❌
   - No commas: `1,234.56` ❌ (use `1234.56` ✅)
   - No negative: `-45.99` ❌

2. **API format**
   ```python
   # Correct
   {"amount": 45.99}

   # Incorrect
   {"amount": "$45.99"}  # No $ symbol
   {"amount": "45.99"}   # Should be number, not string
   ```

### Issue: "Invalid category" error

**Symptoms:**
- Expense rejected with category validation error

**Solutions:**

1. **Use valid categories only**

   Valid categories:
   - `office_supplies`
   - `travel`
   - `meals`
   - `software`
   - `equipment`
   - `professional_services`
   - `marketing`
   - `training`
   - `other`

2. **Check case sensitivity**
   ```python
   # Correct
   {"category": "office_supplies"}

   # Incorrect
   {"category": "Office Supplies"}  # Wrong case
   {"category": "office-supplies"}  # Wrong separator
   ```

3. **Get valid categories from API**
   ```bash
   curl https://your-backend-url/api/v1/expenses/categories
   ```

### Issue: Cannot Edit Approved Expense

**Symptoms:**
- Edit button disabled
- Error: "Cannot edit expense with status: approved"

**Solution:**
- ✅ **Expected behavior** - approved expenses are locked
- Ask manager to reject the expense
- Resubmit with corrections
- Only pending expenses can be edited

---

## Receipt Upload Failures

### Issue: "File type not supported"

**Symptoms:**
- Upload fails immediately
- Error about file type

**Solutions:**

1. **Use supported formats only**
   - ✅ PDF (`.pdf`)
   - ✅ JPEG (`.jpg`, `.jpeg`)
   - ✅ PNG (`.png`)
   - ❌ Word docs (`.doc`, `.docx`)
   - ❌ Excel (`.xls`, `.xlsx`)
   - ❌ Text files (`.txt`)

2. **Convert unsupported files**
   - Use online converter to PDF
   - Screenshot Word doc and save as PNG
   - Take photo of printed document

### Issue: "File too large" error

**Symptoms:**
- Upload fails on large files
- Error: "File exceeds maximum size"

**Solutions:**

1. **Check file size limit: 10MB**
   ```bash
   # Check file size on Linux/Mac
   ls -lh receipt.pdf

   # On Windows
   dir receipt.pdf
   ```

2. **Compress PDF**
   - Use online tools: SmallPDF, ILovePDF
   - Or command line:
   ```bash
   # Using Ghostscript
   gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/ebook \
      -dNOPAUSE -dQUIET -dBATCH -sOutputFile=compressed.pdf input.pdf
   ```

3. **Reduce image resolution**
   - Export image at lower DPI (150-200 DPI is sufficient)
   - Resize large images before upload

### Issue: Receipt Upload Freezes

**Symptoms:**
- Upload progress bar stuck
- No error, just hangs

**Solutions:**

1. **Check network connection**
   - Test internet speed
   - Try on different network
   - Disable VPN temporarily

2. **Clear browser cache**
   - Chrome: Ctrl+Shift+Delete → Clear cached images and files
   - Firefox: Ctrl+Shift+Delete → Cached Web Content

3. **Try different browser**
   - Test in Chrome, Firefox, Safari, Edge
   - Some browsers handle large uploads better

4. **Use API instead**
   ```python
   import requests

   with open('receipt.pdf', 'rb') as f:
       files = {'file': f}
       response = requests.post(
           f"{API_BASE}/expenses/{expense_id}/receipts",
           headers={"Authorization": f"Bearer {token}"},
           files=files,
           timeout=120  # 2 minute timeout
       )
   ```

---

## API Integration Issues

### Issue: CORS Error in Browser

**Symptoms:**
- Error: "Access to fetch has been blocked by CORS policy"
- API works in Postman but not browser

**Solutions:**

1. **Check CORS configuration**
   - API must allow your frontend domain
   - Contact admin to add domain to CORS whitelist

2. **Verify request headers**
   ```javascript
   // Include credentials
   fetch(url, {
     method: 'GET',
     headers: {
       'Authorization': `Bearer ${token}`,
       'Content-Type': 'application/json'
     },
     credentials: 'include'  // Important for CORS
   })
   ```

3. **Backend CORS setup** (for admins)
   ```python
   # In backend/src/config.py
   CORS_ORIGINS = "https://your-frontend.com,https://localhost:5173"
   ```

### Issue: Rate Limit Exceeded

**Symptoms:**
- HTTP 429 error
- Header: "X-RateLimit-Remaining: 0"

**Solutions:**

1. **Implement rate limit handling**
   ```python
   import time

   response = requests.get(url, headers=headers)

   if response.status_code == 429:
       retry_after = int(response.headers.get('Retry-After', 60))
       print(f"Rate limited. Waiting {retry_after}s...")
       time.sleep(retry_after)
       response = requests.get(url, headers=headers)  # Retry
   ```

2. **Check rate limits**
   - Default: 100 requests/minute for read operations
   - 20 requests/minute for write operations
   - Monitor `X-RateLimit-*` headers

3. **Optimize API calls**
   - Batch operations when possible
   - Cache responses
   - Use pagination instead of fetching all data

### Issue: "Organization not found" error

**Symptoms:**
- API returns 404 for organization operations
- Error: "No organization context available"

**Solutions:**

1. **Set X-Organization-Id header**
   ```bash
   curl -X GET https://your-backend-url/api/v1/expenses \
     -H "Authorization: Bearer <TOKEN>" \
     -H "X-Organization-Id: org_abc123"
   ```

2. **Get your organization ID**
   ```bash
   curl -X GET https://your-backend-url/api/v1/organizations \
     -H "Authorization: Bearer <TOKEN>"
   ```

3. **Join an organization**
   - If you're a new user, accept organization invitation
   - Or create a new organization

---

## Deployment Problems

### Issue: Cloud Run Deployment Fails

**Symptoms:**
- Deployment times out
- Health checks failing
- Error: "The request failed one or more health checks"

**Solutions:**

1. **Check health endpoint**
   ```bash
   # Test locally first
   curl http://localhost:8000/health

   # Should return:
   # {"status": "healthy", "service": "AP2 Expense Management Agent"}
   ```

2. **Increase timeout**
   ```bash
   gcloud run deploy backend \
     --timeout 300 \  # 5 minutes
     --max-instances 10
   ```

3. **Check logs**
   ```bash
   gcloud logging read "resource.type=cloud_run_revision" \
     --limit 50 \
     --format json
   ```

4. **Verify environment variables**
   ```bash
   gcloud run services describe backend \
     --region us-central1 \
     --format "value(spec.template.spec.containers[0].env)"
   ```

### Issue: Database Connection Failed

**Symptoms:**
- Error: "Connection to database failed"
- Error: "FATAL: password authentication failed"

**Solutions:**

1. **Verify DATABASE_URL format**
   ```bash
   # Correct format
   postgresql://user:password@host:5432/database

   # With Cloud SQL
   postgresql://user:password@/database?host=/cloudsql/project:region:instance
   ```

2. **Test database connection**
   ```bash
   # From Cloud Shell
   gcloud sql connect INSTANCE_NAME --user=postgres
   ```

3. **Check Cloud SQL settings**
   - Ensure Cloud SQL instance is running
   - Verify database name exists
   - Check user permissions
   - Enable Cloud SQL Admin API

4. **Check service account permissions**
   ```bash
   gcloud projects add-iam-policy-binding PROJECT_ID \
     --member="serviceAccount:SERVICE_ACCOUNT@PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/cloudsql.client"
   ```

### Issue: Secrets Not Loading

**Symptoms:**
- Error: "SECRET_NAME not found in Secret Manager"
- Missing environment variables

**Solutions:**

1. **Verify secrets exist**
   ```bash
   gcloud secrets list --project PROJECT_ID
   ```

2. **Create missing secrets**
   ```bash
   echo -n "your-secret-value" | gcloud secrets create SECRET_NAME \
     --data-file=- \
     --project PROJECT_ID
   ```

3. **Grant access to service account**
   ```bash
   gcloud secrets add-iam-policy-binding SECRET_NAME \
     --member="serviceAccount:SERVICE_ACCOUNT@PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/secretmanager.secretAccessor"
   ```

---

## Database Connection Errors

### Issue: "Too many connections"

**Symptoms:**
- Error: "FATAL: too many connections"
- Intermittent connection failures

**Solutions:**

1. **Check max connections**
   ```sql
   -- Connect to database
   SHOW max_connections;
   ```

2. **Use connection pooling**
   ```python
   # backend/src/database.py
   engine = create_engine(
       DATABASE_URL,
       pool_size=10,           # Max persistent connections
       max_overflow=20,        # Additional overflow connections
       pool_pre_ping=True,     # Verify connections before use
       pool_recycle=3600       # Recycle connections after 1 hour
   )
   ```

3. **Close idle connections**
   ```sql
   -- Find idle connections
   SELECT * FROM pg_stat_activity WHERE state = 'idle';

   -- Terminate idle connections
   SELECT pg_terminate_backend(pid) FROM pg_stat_activity
   WHERE state = 'idle' AND state_change < NOW() - INTERVAL '5 minutes';
   ```

### Issue: Migration Failures

**Symptoms:**
- Error: "Target database is not up to date"
- Alembic migration errors

**Solutions:**

1. **Check migration status**
   ```bash
   cd backend
   alembic current
   alembic history
   ```

2. **Run migrations manually**
   ```bash
   alembic upgrade head
   ```

3. **Resolve migration conflicts**
   ```bash
   # If migrations are out of sync
   alembic stamp head  # Mark as current (use carefully!)

   # Or downgrade and re-upgrade
   alembic downgrade -1
   alembic upgrade head
   ```

4. **Reset database (DANGER - loses data)**
   ```bash
   # Only for development!
   alembic downgrade base
   alembic upgrade head
   ```

---

## Performance Issues

### Issue: Slow API Response Times

**Symptoms:**
- API calls take > 2 seconds
- Timeouts on large queries

**Solutions:**

1. **Add database indexes**
   ```sql
   -- Check slow queries
   SELECT query, calls, total_time, mean_time
   FROM pg_stat_statements
   ORDER BY mean_time DESC
   LIMIT 10;

   -- Add indexes
   CREATE INDEX idx_expenses_org_id ON expenses(organization_id);
   CREATE INDEX idx_expenses_status ON expenses(status);
   ```

2. **Use pagination**
   ```python
   # Instead of fetching all
   expenses = db.query(Expense).all()  # Slow!

   # Use pagination
   expenses = db.query(Expense).limit(50).offset(0).all()
   ```

3. **Enable query caching**
   ```python
   # Use Redis for caching
   from redis import Redis
   import json

   redis_client = Redis(host='localhost', port=6379, decode_responses=True)

   def get_expenses_cached(org_id):
       cache_key = f"expenses:{org_id}"
       cached = redis_client.get(cache_key)

       if cached:
           return json.loads(cached)

       expenses = db.query(Expense).filter_by(organization_id=org_id).all()
       redis_client.setex(cache_key, 300, json.dumps(expenses))  # 5 min cache
       return expenses
   ```

### Issue: High Memory Usage

**Symptoms:**
- Cloud Run instance crashes with OOM (Out of Memory)
- Error: "Exceeded memory limit"

**Solutions:**

1. **Increase memory allocation**
   ```bash
   gcloud run deploy backend \
     --memory 2Gi \  # Increase from 512Mi
     --cpu 2
   ```

2. **Optimize database queries**
   ```python
   # Don't load everything into memory
   for expense in db.query(Expense).yield_per(100):  # Process in batches
       process_expense(expense)
   ```

3. **Monitor memory usage**
   ```bash
   # View Cloud Run metrics
   gcloud monitoring time-series list \
     --filter='metric.type="run.googleapis.com/container/memory/utilizations"'
   ```

---

## Payment & AP2 Errors

### Issue: "Stripe not configured" error

**Symptoms:**
- Payment fails with configuration error
- Error: "STRIPE_SECRET_KEY not set"

**Solutions:**

1. **Set Stripe secret key**
   ```bash
   # Create secret
   echo -n "sk_live_YOUR_KEY" | gcloud secrets create stripe-secret-key \
     --data-file=- \
     --project PROJECT_ID

   # Update Cloud Run
   gcloud run services update backend \
     --update-secrets=STRIPE_SECRET_KEY=stripe-secret-key:latest
   ```

2. **Verify key is correct**
   ```bash
   # Test Stripe key
   curl https://api.stripe.com/v1/customers \
     -u sk_test_YOUR_KEY:
   ```

### Issue: AP2 Mandate Signature Verification Failed

**Symptoms:**
- Error: "Invalid mandate signature"
- AP2 flow fails at verification

**Solutions:**

1. **Check KMS configuration**
   ```bash
   # Verify KMS key exists
   gcloud kms keys list \
     --location=global \
     --keyring=ap2-keyring
   ```

2. **Verify service account has KMS permissions**
   ```bash
   gcloud kms keys add-iam-policy-binding ap2-signing-key \
     --location=global \
     --keyring=ap2-keyring \
     --member="serviceAccount:YOUR_SA@PROJECT.iam.gserviceaccount.com" \
     --role="roles/cloudkms.signerVerifier"
   ```

3. **Check timestamp issues**
   - KMS signatures include timestamp
   - Ensure server time is synced
   ```bash
   # Check server time
   date

   # Sync if needed (Linux)
   sudo ntpdate -s time.nist.gov
   ```

---

## Getting More Help

### Check System Status
- **Status Page**: https://status.ap2expense.com
- **GCP Status**: https://status.cloud.google.com

### Enable Debug Logging

**Backend:**
```python
# backend/src/config.py
LOG_LEVEL = "DEBUG"  # Change from INFO
```

**View Logs:**
```bash
# Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision" \
  --limit 100 \
  --format json

# Filter by severity
gcloud logging read "severity>=ERROR" --limit 50
```

### Contact Support

- **Email**: support@ap2expense.com
- **Response Times**:
  - Starter: 48 hours
  - Professional: 24 hours
  - Enterprise: 4 hours
- **Include in support request**:
  - Error message (full text)
  - Request ID (from headers)
  - Timestamp when error occurred
  - Steps to reproduce
  - Screenshots/logs

### Additional Resources
- [User Getting Started Guide](USER_GETTING_STARTED.md)
- [API Integration Guide](API_INTEGRATION_GUIDE.md)
- [Deployment Documentation](../backend/CLOUD_RUN_DEPLOYMENT.md)
- [Security Guide](../SECURITY.md)

---

*Last Updated: November 2025*
*Version: 1.0*
