# Engineering Implementation Tickets
## GCP Marketplace Production Launch

**Sprint**: GCP Marketplace Launch
**Epic**: Production Readiness
**Target**: Q1 2025

---

## 📋 Ticket Template

Each ticket includes:
- **Priority**: P0 (Blocker), P1 (Critical), P2 (Important), P3 (Nice to have)
- **Story Points**: Fibonacci scale (1, 2, 3, 5, 8, 13)
- **Dependencies**: What must be done first
- **Acceptance Criteria**: Definition of done
- **Testing Requirements**: How to verify

---

## 🎯 EPIC 1: GCP Marketplace Integration (40 points)

### Ticket #1: Install Dependencies & Update Configuration
**Priority**: P0
**Story Points**: 2
**Assignee**: Backend Engineer
**Dependencies**: None

**Description**:
Install required Google Cloud libraries and update application configuration for Consumer Procurement API.

**Tasks**:
- [ ] Install `google-cloud-commerce-consumer-procurement==1.1.0`
- [ ] Install `PyJWT[crypto]==2.8.0`
- [ ] Install `tenacity==8.2.3` for retry logic
- [ ] Update `backend/requirements.txt`
- [ ] Add new settings to `backend/src/config.py`
- [ ] Create `.env.production.template` with new vars
- [ ] Update README with new environment variables

**Acceptance Criteria**:
- [ ] All dependencies install without errors
- [ ] Configuration file has all GCP settings
- [ ] Environment template documented
- [ ] README updated with setup instructions

**Testing**:
```bash
pip install -r requirements.txt
python -c "from google.cloud import commerce_consumer_procurement_v1; print('OK')"
```

**Files to Modify**:
- `backend/requirements.txt`
- `backend/src/config.py`
- `backend/.env.production.template`
- `README.md`

**Time Estimate**: 2-3 hours

---

### Ticket #2: Create Consumer Procurement Client
**Priority**: P0
**Story Points**: 5
**Assignee**: Backend Engineer
**Dependencies**: Ticket #1

**Description**:
Create a client wrapper for Google Cloud Consumer Procurement API to handle entitlement operations.

**Tasks**:
- [ ] Create `backend/src/gcp/consumer_procurement_client.py`
- [ ] Implement `get_entitlement()` method with retry logic
- [ ] Implement `list_entitlements()` method
- [ ] Implement `get_entitlement_by_account_id()` helper
- [ ] Add comprehensive error handling
- [ ] Add structured logging
- [ ] Create singleton instance getter
- [ ] Write unit tests (>90% coverage)

**Acceptance Criteria**:
- [ ] All methods implemented with type hints
- [ ] Retry logic with exponential backoff working
- [ ] Comprehensive error handling for GCP exceptions
- [ ] Unit tests pass with mocked GCP client
- [ ] Logging includes all relevant context
- [ ] Docstrings complete with examples

**Testing**:
```python
# Unit test
pytest backend/tests/test_consumer_procurement_client.py -v

# Integration test (requires staging GCP credentials)
python backend/tests/integration/test_gcp_client.py
```

**Files to Create**:
- `backend/src/gcp/consumer_procurement_client.py`
- `backend/tests/test_consumer_procurement_client.py`

**Reference**: See `GCP_API_MIGRATION_GUIDE.md` Phase 2

**Time Estimate**: 4-5 hours

---

### Ticket #3: Implement JWT Verification for Webhooks
**Priority**: P0
**Story Points**: 5
**Assignee**: Backend Engineer
**Dependencies**: Ticket #1

**Description**:
Replace HMAC signature verification with Google-signed JWT token verification for webhook security.

**Tasks**:
- [ ] Create `backend/src/gcp/jwt_verification.py`
- [ ] Implement `GoogleJWTVerifier` class
- [ ] Fetch and cache Google public keys
- [ ] Implement token verification with PyJWT
- [ ] Create FastAPI dependency `verify_gcp_webhook_jwt()`
- [ ] Handle token expiration gracefully
- [ ] Add comprehensive error messages
- [ ] Write unit tests with sample tokens

**Acceptance Criteria**:
- [ ] JWT verification working with RS256 algorithm
- [ ] Public keys cached with 6-hour refresh
- [ ] Expired tokens return 401 with clear message
- [ ] Invalid tokens return 401 with reason
- [ ] FastAPI dependency ready for use
- [ ] Unit tests cover all error cases
- [ ] Integration test with real Google token (staging)

**Testing**:
```python
# Unit test
pytest backend/tests/test_jwt_verification.py -v

# Manual test with sample token
python -c "
from backend.src.gcp.jwt_verification import get_jwt_verifier
verifier = get_jwt_verifier()
claims = verifier.verify_token('SAMPLE_TOKEN_HERE')
print(claims)
"
```

**Files to Create**:
- `backend/src/gcp/jwt_verification.py`
- `backend/tests/test_jwt_verification.py`

**Reference**: See `GCP_API_MIGRATION_GUIDE.md` Phase 3

**Time Estimate**: 4-5 hours

---

### Ticket #4: Update Webhook Routes with JWT Verification
**Priority**: P0
**Story Points**: 5
**Assignee**: Backend Engineer
**Dependencies**: Ticket #2, Ticket #3

**Description**:
Update GCP webhook endpoints to use JWT verification and Consumer Procurement API.

**Tasks**:
- [ ] Update `backend/src/routes/gcp_webhooks.py`
- [ ] Replace HMAC verification with JWT dependency
- [ ] Fetch full entitlement details from API
- [ ] Update all event handlers (creation, activation, plan change, cancellation)
- [ ] Add structured logging for all events
- [ ] Implement retry logic for failed webhook processing
- [ ] Add dead letter queue for persistent failures
- [ ] Update API documentation (OpenAPI/Swagger)

**Acceptance Criteria**:
- [ ] All webhook endpoints use JWT verification
- [ ] Entitlement details fetched from Consumer Procurement API
- [ ] Event handlers work for all lifecycle events
- [ ] Failed webhooks retry with exponential backoff
- [ ] Dead letter queue stores failed events after max retries
- [ ] API docs updated with new authentication
- [ ] Integration tests pass

**Testing**:
```bash
# Unit tests
pytest backend/tests/test_gcp_webhooks.py -v

# Integration test with staging
curl -X POST https://staging-api.ap2expense.com/api/webhooks/gcp/procurement \
  -H "Authorization: Bearer VALID_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"eventType": "ENTITLEMENT_CREATION_REQUESTED", ...}'
```

**Files to Modify**:
- `backend/src/routes/gcp_webhooks.py`
- `backend/tests/test_gcp_webhooks.py`

**Reference**: See `GCP_API_MIGRATION_GUIDE.md` Phase 3.2

**Time Estimate**: 5-6 hours

---

### Ticket #5: Implement Usage Tracking Service
**Priority**: P0
**Story Points**: 8
**Assignee**: Backend Engineer
**Dependencies**: Ticket #1

**Description**:
Create a comprehensive usage tracking service to meter AI categorizations, AP2 transactions, and receipt OCR for billing.

**Tasks**:
- [ ] Create `backend/src/services/usage_tracking.py`
- [ ] Define `METERED_RESOURCES` configuration
- [ ] Implement `UsageTracker.track_event()` method
- [ ] Implement `UsageTracker.get_usage_summary()` method
- [ ] Implement `UsageTracker.check_usage_limits()` method
- [ ] Add overage tracking for GCP Marketplace billing
- [ ] Create `UsageEvent` database model (if not exists)
- [ ] Run Alembic migration for new table
- [ ] Write comprehensive unit tests

**Acceptance Criteria**:
- [ ] Usage events tracked in database
- [ ] Monthly usage summaries calculated correctly
- [ ] Tier limits enforced based on subscription
- [ ] Overage billing events created for GCP customers
- [ ] Hard limits enforced for Stripe customers
- [ ] Database migration created and tested
- [ ] Unit tests achieve >90% coverage
- [ ] Performance tested (can handle 1000 events/sec)

**Testing**:
```python
# Unit tests
pytest backend/tests/test_usage_tracking.py -v

# Performance test
python backend/tests/performance/test_usage_tracking_performance.py

# Manual test
python -c "
from backend.src.services.usage_tracking import track_usage
from backend.src.database import SessionLocal
db = SessionLocal()
track_usage(db, 'org-123', 'ai_categorizations', 1)
print('OK')
"
```

**Files to Create**:
- `backend/src/services/usage_tracking.py`
- `backend/tests/test_usage_tracking.py`
- `backend/alembic/versions/XXXXX_add_usage_events.py` (migration)

**Reference**: See `GCP_API_MIGRATION_GUIDE.md` Phase 4.1

**Time Estimate**: 6-8 hours

---

### Ticket #6: Add Usage Tracking to Metered Endpoints
**Priority**: P0
**Story Points**: 5
**Assignee**: Backend Engineer
**Dependencies**: Ticket #5

**Description**:
Integrate usage tracking into all endpoints that consume metered resources.

**Tasks**:
- [ ] Add usage tracking to AI categorization endpoint
- [ ] Add usage tracking to AP2 transaction endpoint
- [ ] Add usage tracking to receipt OCR endpoint
- [ ] Add usage tracking to any other metered features
- [ ] Ensure tracking happens after successful operation
- [ ] Add metadata to track quality/confidence
- [ ] Update API documentation with metered info
- [ ] Add usage dashboard for admins (optional)

**Acceptance Criteria**:
- [ ] All metered endpoints track usage
- [ ] Tracking only happens after success (not on errors)
- [ ] Metadata includes relevant context
- [ ] No performance degradation (<5ms overhead)
- [ ] Integration tests verify tracking works
- [ ] API docs show which endpoints are metered

**Testing**:
```bash
# Integration tests
pytest backend/tests/integration/test_metered_endpoints.py -v

# Manual test
curl -X POST https://staging-api.ap2expense.com/api/v1/expenses/123/categorize \
  -H "Authorization: Bearer $TOKEN" \
  -d '{}'

# Verify usage event created in database
```

**Files to Modify**:
- `backend/src/routes/expenses.py`
- `backend/src/routes/ap2.py`
- `backend/src/routes/receipts.py`
- `backend/tests/integration/test_metered_endpoints.py`

**Reference**: See `GCP_API_MIGRATION_GUIDE.md` Phase 4.2

**Time Estimate**: 4-5 hours

---

### Ticket #7: Implement GCP Usage Reporter
**Priority**: P0
**Story Points**: 5
**Assignee**: Backend Engineer
**Dependencies**: Ticket #5

**Description**:
Create service to report daily usage to Google Service Control API for billing.

**Tasks**:
- [ ] Create/replace `backend/src/gcp/usage_reporter.py`
- [ ] Implement `GCPUsageReporter` class
- [ ] Implement `report_daily_usage()` method
- [ ] Implement `report_usage()` for single organization
- [ ] Format operations for Service Control API
- [ ] Add comprehensive error handling
- [ ] Create webhook endpoint for Cloud Scheduler
- [ ] Write unit tests with mocked GCP client

**Acceptance Criteria**:
- [ ] Daily usage reported to GCP Service Control API
- [ ] All GCP Marketplace customers included in report
- [ ] Failed reports logged and retried
- [ ] Webhook endpoint secured (Cloud Scheduler only)
- [ ] Unit tests pass with mocked GCP calls
- [ ] Integration test in staging reports successfully
- [ ] Error handling prevents data loss

**Testing**:
```python
# Unit tests
pytest backend/tests/test_usage_reporter.py -v

# Manual test in staging
curl -X POST https://staging-api.ap2expense.com/api/webhooks/gcp/report-usage \
  -H "X-CloudScheduler: true"

# Check logs for successful report
```

**Files to Create/Modify**:
- `backend/src/gcp/usage_reporter.py` (replace existing)
- `backend/src/routes/gcp_webhooks.py` (add endpoint)
- `backend/tests/test_usage_reporter.py`

**Reference**: See `GCP_API_MIGRATION_GUIDE.md` Phase 4.3

**Time Estimate**: 5-6 hours

---

### Ticket #8: Set Up Cloud Scheduler for Usage Reporting
**Priority**: P0
**Story Points**: 2
**Assignee**: DevOps Engineer
**Dependencies**: Ticket #7

**Description**:
Configure Google Cloud Scheduler to trigger daily usage reporting at 1 AM UTC.

**Tasks**:
- [ ] Create Cloud Scheduler job in production project
- [ ] Configure OIDC authentication
- [ ] Set schedule to 1 AM UTC daily
- [ ] Add appropriate headers
- [ ] Test manual run
- [ ] Verify logs show successful execution
- [ ] Set up alerting for failed runs
- [ ] Document in runbook

**Acceptance Criteria**:
- [ ] Cloud Scheduler job created and enabled
- [ ] Runs daily at 1 AM UTC
- [ ] OIDC authentication configured
- [ ] Manual test run succeeds
- [ ] Alerts configured for failures
- [ ] Runbook documentation complete

**Testing**:
```bash
# Create job
gcloud scheduler jobs create http report-gcp-marketplace-usage \
  --location us-central1 \
  --schedule "0 1 * * *" \
  --uri "https://api.ap2expense.com/api/webhooks/gcp/report-usage" \
  ...

# Test run
gcloud scheduler jobs run report-gcp-marketplace-usage --location us-central1

# View logs
gcloud logging read "resource.type=cloud_scheduler_job" --limit 10
```

**Reference**: See `GCP_API_MIGRATION_GUIDE.md` Phase 4.5

**Time Estimate**: 2 hours

---

### Ticket #9: Implement Entitlement Feature Gating
**Priority**: P1
**Story Points**: 5
**Assignee**: Backend Engineer
**Dependencies**: Ticket #2

**Description**:
Create middleware to gate premium features based on customer's GCP Marketplace entitlement and plan.

**Tasks**:
- [ ] Create `backend/src/middleware/entitlement_check.py`
- [ ] Implement `require_entitlement()` middleware
- [ ] Define `PLAN_FEATURES` configuration
- [ ] Apply middleware to protected endpoints
- [ ] Add user-friendly error messages with upgrade prompts
- [ ] Create admin override for demos
- [ ] Write unit and integration tests

**Acceptance Criteria**:
- [ ] Middleware checks entitlement status
- [ ] Plan-based features correctly gated
- [ ] 402 Payment Required returned with upgrade link
- [ ] Admin override works for demos
- [ ] All protected endpoints have middleware applied
- [ ] Tests verify correct enforcement
- [ ] API docs show plan requirements

**Testing**:
```python
# Unit tests
pytest backend/tests/test_entitlement_middleware.py -v

# Integration test
# Try accessing analytics endpoint with STARTER plan
curl -X GET https://staging-api.ap2expense.com/api/v1/analytics \
  -H "Authorization: Bearer $STARTER_PLAN_TOKEN"
# Expected: 402 Payment Required

# Try with PROFESSIONAL plan
curl -X GET https://staging-api.ap2expense.com/api/v1/analytics \
  -H "Authorization: Bearer $PROFESSIONAL_PLAN_TOKEN"
# Expected: 200 OK
```

**Files to Create**:
- `backend/src/middleware/entitlement_check.py`
- `backend/src/billing/feature_flags.py`
- `backend/tests/test_entitlement_middleware.py`

**Time Estimate**: 5-6 hours

---

## 🎯 EPIC 2: Production Infrastructure (25 points)

### Ticket #10: Create Production GCP Project
**Priority**: P0
**Story Points**: 3
**Assignee**: DevOps Engineer
**Dependencies**: None

**Description**:
Set up production Google Cloud Platform project with all required APIs and IAM configuration.

**Tasks**:
- [ ] Create GCP project `ap2-expense-prod`
- [ ] Link billing account
- [ ] Enable required APIs (Cloud Run, SQL, Secret Manager, etc.)
- [ ] Create service accounts with least-privilege IAM
- [ ] Set up VPC network
- [ ] Configure Cloud NAT
- [ ] Set budget alerts ($500 warning, $1000 alert)
- [ ] Document project structure

**Acceptance Criteria**:
- [ ] Project created with correct billing
- [ ] All required APIs enabled
- [ ] Service accounts created with appropriate roles
- [ ] VPC networking configured
- [ ] Budget alerts active
- [ ] Documentation updated

**Testing**:
```bash
# Verify APIs enabled
gcloud services list --enabled --project=ap2-expense-prod

# Verify service accounts
gcloud iam service-accounts list --project=ap2-expense-prod

# Test Cloud Run deployment
gcloud run services list --project=ap2-expense-prod
```

**Reference**: See `GCP_MARKETPLACE_PRODUCTION_PLAN.md` Phase 1.1

**Time Estimate**: 3-4 hours

---

### Ticket #11: Set Up Production Database (Cloud SQL)
**Priority**: P0
**Story Points**: 5
**Assignee**: DevOps Engineer
**Dependencies**: Ticket #10

**Description**:
Create and configure Cloud SQL PostgreSQL instance for production with high availability and automated backups.

**Tasks**:
- [ ] Create Cloud SQL instance (db-n1-standard-2)
- [ ] Enable automated daily backups (retained 30 days)
- [ ] Enable point-in-time recovery
- [ ] Configure high availability (regional)
- [ ] Create database `ap2_expense_prod`
- [ ] Create application user with appropriate permissions
- [ ] Create read-only user for analytics
- [ ] Configure connection pooling
- [ ] Set up database monitoring alerts

**Acceptance Criteria**:
- [ ] Cloud SQL instance running
- [ ] Automated backups configured and verified
- [ ] High availability enabled
- [ ] Database users created with correct permissions
- [ ] Connection pooling configured
- [ ] Monitoring alerts active
- [ ] Test connection from Cloud Run

**Testing**:
```bash
# Verify instance
gcloud sql instances describe ap2-expense-db-prod

# Test connection via Cloud SQL Proxy
cloud_sql_proxy -instances=PROJECT:REGION:INSTANCE=tcp:5432 &
psql "host=localhost port=5432 user=ap2_app_user dbname=ap2_expense_prod"

# Verify backups
gcloud sql backups list --instance=ap2-expense-db-prod
```

**Reference**: See `GCP_MARKETPLACE_PRODUCTION_PLAN.md` Phase 1.2

**Time Estimate**: 4-5 hours

---

### Ticket #12: Configure Production Secrets (Secret Manager)
**Priority**: P0
**Story Points**: 3
**Assignee**: DevOps Engineer
**Dependencies**: Ticket #10, Ticket #11

**Description**:
Create all production secrets in Google Secret Manager and configure IAM permissions.

**Tasks**:
- [ ] Generate JWT secrets (64-byte hex)
- [ ] Create database connection string secret
- [ ] Add Stripe production keys
- [ ] Add GCP webhook secret
- [ ] Add monitoring webhook URLs (Slack, PagerDuty)
- [ ] Add email service credentials
- [ ] Grant service account access to secrets
- [ ] Document secret rotation schedule
- [ ] Create secret rotation runbook

**Acceptance Criteria**:
- [ ] All secrets created in Secret Manager
- [ ] IAM permissions configured correctly
- [ ] Service account can access secrets
- [ ] Secret rotation schedule documented
- [ ] Runbook created for rotation procedures
- [ ] Test secret retrieval from Cloud Run

**Testing**:
```bash
# Verify secrets exist
gcloud secrets list --project=ap2-expense-prod

# Test access from service account
gcloud secrets versions access latest --secret=jwt-secret-key \
  --impersonate-service-account=ap2-expense-backend@PROJECT.iam.gserviceaccount.com

# Test from Cloud Run container
curl http://localhost:8080/health  # Should have access to DB secret
```

**Reference**: See `GCP_MARKETPLACE_PRODUCTION_PLAN.md` Phase 1.3

**Time Estimate**: 3-4 hours

---

### Ticket #13: Deploy Backend to Cloud Run
**Priority**: P0
**Story Points**: 5
**Assignee**: DevOps Engineer
**Dependencies**: Ticket #10, Ticket #11, Ticket #12

**Description**:
Build and deploy production backend to Google Cloud Run with proper configuration.

**Tasks**:
- [ ] Build Docker image with v1.0.0 tag
- [ ] Push to Artifact Registry
- [ ] Deploy to Cloud Run with production settings
- [ ] Configure min/max instances (1-100)
- [ ] Set memory (2Gi) and CPU (2)
- [ ] Map secrets to environment variables
- [ ] Configure Cloud SQL connection
- [ ] Map custom domain `api.ap2expense.com`
- [ ] Verify health checks pass
- [ ] Run smoke tests

**Acceptance Criteria**:
- [ ] Backend deployed and healthy
- [ ] Health check endpoint returns 200
- [ ] API docs accessible at /docs
- [ ] Custom domain working with SSL
- [ ] Secrets loaded correctly
- [ ] Database connection working
- [ ] Auto-scaling functional
- [ ] Smoke tests pass

**Testing**:
```bash
# Deploy
./scripts/deploy-production.sh v1.0.0 production

# Smoke tests
./scripts/smoke-test.sh production

# Manual tests
curl https://api.ap2expense.com/health
curl https://api.ap2expense.com/docs
```

**Reference**: See `GCP_MARKETPLACE_PRODUCTION_PLAN.md` Phase 2.1

**Time Estimate**: 5-6 hours

---

### Ticket #14: Deploy Frontend to Cloud Run
**Priority**: P0
**Story Points**: 3
**Assignee**: DevOps Engineer
**Dependencies**: Ticket #13

**Description**:
Build and deploy production frontend to Google Cloud Run.

**Tasks**:
- [ ] Build frontend with production environment variables
- [ ] Build Docker image
- [ ] Push to Artifact Registry
- [ ] Deploy to Cloud Run
- [ ] Configure min/max instances (1-50)
- [ ] Map custom domain `app.ap2expense.com`
- [ ] Verify frontend loads
- [ ] Test authentication flow
- [ ] Check for console errors

**Acceptance Criteria**:
- [ ] Frontend deployed and accessible
- [ ] Custom domain working with SSL
- [ ] Frontend can communicate with backend
- [ ] Authentication flow works end-to-end
- [ ] No console errors in browser
- [ ] Assets load quickly (<2s)

**Testing**:
```bash
# Build and deploy
cd frontend
npm run build
docker build -t REGION-docker.pkg.dev/PROJECT/frontend:v1.0.0 .
gcloud run deploy frontend ...

# Manual test
open https://app.ap2expense.com
# Test: Register → Login → Create expense
```

**Reference**: See `GCP_MARKETPLACE_PRODUCTION_PLAN.md` Phase 2.2

**Time Estimate**: 3-4 hours

---

### Ticket #15: Set Up Production Monitoring & Alerting
**Priority**: P0
**Story Points**: 8
**Assignee**: DevOps Engineer
**Dependencies**: Ticket #13

**Description**:
Configure comprehensive monitoring dashboards and alerting for production.

**Tasks**:
- [ ] Deploy Cloud Monitoring dashboards
- [ ] Create alert policies (error rate, latency, availability)
- [ ] Configure Slack webhook integration
- [ ] Configure PagerDuty integration
- [ ] Set up on-call rotation
- [ ] Test all alert notifications
- [ ] Create runbook for common incidents
- [ ] Document escalation procedures

**Acceptance Criteria**:
- [ ] 5 dashboards deployed and accessible
- [ ] 7+ alert policies active
- [ ] Slack notifications working
- [ ] PagerDuty incidents creating correctly
- [ ] On-call rotation configured
- [ ] Test alerts sent successfully
- [ ] Runbook documentation complete
- [ ] Team trained on incident response

**Testing**:
```bash
# Deploy monitoring
./monitoring/setup-monitoring.sh production

# Test alerts
./scripts/test-alerts.sh

# Trigger test incident
curl -X POST $PAGERDUTY_WEBHOOK_URL -d '{"event_type": "trigger", ...}'
```

**Reference**: See `PRODUCTION_ALERTING_SETUP.md` and Phase 5.1

**Time Estimate**: 8-10 hours

---

## 🎯 EPIC 3: Marketplace Assets (15 points)

### Ticket #16: Create Product Icon & Logo
**Priority**: P0
**Story Points**: 3
**Assignee**: Designer
**Dependencies**: None

**Description**:
Design professional product icon and logo for GCP Marketplace listing.

**Tasks**:
- [ ] Create 3 design concepts
- [ ] Get stakeholder approval on concept
- [ ] Finalize icon design
- [ ] Export at multiple sizes (128px, 256px, 512px)
- [ ] Create logo variants (light/dark backgrounds)
- [ ] Upload to Cloud Storage
- [ ] Update favicon on website

**Acceptance Criteria**:
- [ ] Icon looks professional at all sizes
- [ ] Meets GCP Marketplace guidelines
- [ ] Exported in PNG with transparency
- [ ] Uploaded to gs://ap2-expense-agent-assets/
- [ ] Favicon updated on app.ap2expense.com

**Deliverables**:
- `icon-128.png`
- `icon-256.png`
- `icon-512.png`
- `logo-light.svg`
- `logo-dark.svg`
- `favicon.ico`

**Time Estimate**: 4-6 hours

---

### Ticket #17: Capture Product Screenshots
**Priority**: P0
**Story Points**: 5
**Assignee**: Product Manager + Designer
**Dependencies**: Ticket #13, Ticket #14

**Description**:
Create 8 high-quality screenshots for GCP Marketplace listing following the comprehensive guide.

**Tasks**:
- [ ] Run `python backend/seed_screenshot_data.py` to create demo data
- [ ] Use `./scripts/capture-screenshots.sh` interactive guide
- [ ] Capture 8 screenshots at 1280x800px:
  1. Dashboard overview
  2. Submit expense form
  3. Expense list & filtering
  4. Approval workflow
  5. AP2 payment protocol
  6. Budget tracking
  7. Analytics & reporting
  8. Admin panel
- [ ] Edit screenshots (add annotations if needed)
- [ ] Optimize file sizes (<5MB each)
- [ ] Upload to Cloud Storage

**Acceptance Criteria**:
- [ ] 8 screenshots captured
- [ ] All exactly 1280x800px
- [ ] No PII visible
- [ ] Clean, professional UI
- [ ] Realistic demo data
- [ ] Uploaded to gs://ap2-expense-agent-assets/
- [ ] Captioned with feature descriptions

**Reference**: See `MARKETPLACE_ASSET_CREATION_GUIDE.md` (9,000+ lines)

**Time Estimate**: 6-8 hours

---

### Ticket #18: Produce Demo Video
**Priority**: P0
**Story Points**: 8
**Assignee**: Product Manager + Video Producer (Contract)
**Dependencies**: Ticket #13, Ticket #14

**Description**:
Create professional 2-3 minute demo video showcasing key product features.

**Tasks**:
- [ ] Write detailed video script
- [ ] Record screen walkthrough (OBS Studio)
- [ ] Record professional voiceover
- [ ] Edit video (add transitions, annotations)
- [ ] Add background music (royalty-free)
- [ ] Add captions (English)
- [ ] Export at 1920x1080 MP4
- [ ] Upload to YouTube (unlisted)
- [ ] Add YouTube link to Partner Portal

**Acceptance Criteria**:
- [ ] Video is 2-3 minutes long
- [ ] Covers all key features
- [ ] Professional voiceover
- [ ] Good audio quality
- [ ] Captions included
- [ ] Uploaded to YouTube
- [ ] Link ready for Partner Portal

**Script Outline**:
- 0:00-0:15: Hook & problem statement
- 0:15-0:45: Solution overview
- 0:45-1:30: Feature walkthrough
- 1:30-2:15: Key differentiators
- 2:15-2:45: Call to action

**Time Estimate**: 10-12 hours (including editing)

---

## 🎯 EPIC 4: Legal & Compliance (12 points)

### Ticket #19: Draft Terms of Service
**Priority**: P0
**Story Points**: 5
**Assignee**: Legal (Contract Attorney)
**Dependencies**: None

**Description**:
Create comprehensive Terms of Service document covering all legal requirements.

**Tasks**:
- [ ] Draft Terms of Service (GDPR/CCPA compliant)
- [ ] Include acceptable use policy
- [ ] Define payment terms
- [ ] Clarify data ownership
- [ ] Add liability limitations
- [ ] Define termination clauses
- [ ] Legal review by attorney
- [ ] Publish on website at /terms
- [ ] Add link to Partner Portal

**Acceptance Criteria**:
- [ ] Document covers all required sections
- [ ] GDPR compliant
- [ ] CCPA compliant
- [ ] Attorney reviewed and approved
- [ ] Published on ap2expense.com/terms
- [ ] Accessible from signup flow

**Time Estimate**: 6-8 hours (attorney time)

---

### Ticket #20: Draft Privacy Policy
**Priority**: P0
**Story Points**: 5
**Assignee**: Legal (Contract Attorney)
**Dependencies**: None

**Description**:
Create comprehensive Privacy Policy document with GDPR/CCPA compliance.

**Tasks**:
- [ ] Draft Privacy Policy
- [ ] Detail data collection practices
- [ ] Explain data usage
- [ ] List third-party sharing (Stripe, GCP, etc.)
- [ ] Define data retention periods
- [ ] Include user rights (access, deletion, portability)
- [ ] Add cookie policy
- [ ] Legal review
- [ ] Publish on website at /privacy

**Acceptance Criteria**:
- [ ] Document covers all data practices
- [ ] GDPR compliant (EU users)
- [ ] CCPA compliant (California users)
- [ ] Attorney reviewed
- [ ] Published on ap2expense.com/privacy
- [ ] Accessible from signup flow

**Time Estimate**: 6-8 hours (attorney time)

---

### Ticket #21: Create SLA & DPA Documents
**Priority**: P1
**Story Points**: 3
**Assignee**: Legal (Contract Attorney) + Product Manager
**Dependencies**: None

**Description**:
Create Service Level Agreement and Data Processing Agreement for enterprise customers.

**Tasks**:
- [ ] Draft SLA (99.9% uptime guarantee)
- [ ] Define service credits for downtime
- [ ] Specify support response times
- [ ] Create DPA for GDPR compliance
- [ ] List sub-processors
- [ ] Define data breach notification process
- [ ] Legal review
- [ ] Publish on website

**Acceptance Criteria**:
- [ ] SLA defines clear uptime targets
- [ ] Service credits properly structured
- [ ] DPA is GDPR compliant
- [ ] Sub-processors listed
- [ ] Documents published
- [ ] Available for enterprise customers

**Time Estimate**: 4-6 hours

---

## 🎯 EPIC 5: Testing & Quality (20 points)

### Ticket #22: Write Unit Tests for New Components
**Priority**: P1
**Story Points**: 8
**Assignee**: Backend Engineer
**Dependencies**: Tickets #2-9

**Description**:
Write comprehensive unit tests for all new GCP Marketplace components.

**Tasks**:
- [ ] Unit tests for Consumer Procurement client
- [ ] Unit tests for JWT verification
- [ ] Unit tests for usage tracking service
- [ ] Unit tests for usage reporter
- [ ] Unit tests for entitlement middleware
- [ ] Mock all external GCP API calls
- [ ] Achieve >90% code coverage
- [ ] Add to CI/CD pipeline

**Acceptance Criteria**:
- [ ] All new modules have unit tests
- [ ] Test coverage >90%
- [ ] All tests pass locally
- [ ] All tests pass in CI/CD
- [ ] Mocks work correctly
- [ ] No flaky tests

**Testing**:
```bash
# Run all unit tests
cd backend
pytest tests/ -v --cov=src --cov-report=html

# Check coverage
open htmlcov/index.html

# Should show >90% coverage
```

**Time Estimate**: 8-10 hours

---

### Ticket #23: End-to-End GCP Marketplace Testing
**Priority**: P0
**Story Points**: 8
**Assignee**: Backend Engineer + QA
**Dependencies**: All implementation tickets

**Description**:
Test complete GCP Marketplace integration end-to-end in staging environment.

**Tasks**:
- [ ] Create test entitlement in GCP Partner Portal
- [ ] Test new customer signup flow
- [ ] Test entitlement activation
- [ ] Test plan upgrade flow
- [ ] Test plan downgrade flow
- [ ] Test usage metering and reporting
- [ ] Test cancellation flow
- [ ] Document test results

**Test Scenarios**:
1. New customer subscribes via GCP Marketplace
2. Organization automatically created
3. User completes signup
4. User submits expenses (track usage)
5. User hits tier limit (upgrade prompt shown)
6. User upgrades plan via GCP
7. New limits take effect immediately
8. Daily usage reported to GCP
9. User cancels subscription
10. Grace period and data retention work

**Acceptance Criteria**:
- [ ] All test scenarios pass
- [ ] Webhooks received and processed correctly
- [ ] Usage reporting works
- [ ] No errors in logs
- [ ] Test results documented
- [ ] Any bugs filed and fixed

**Time Estimate**: 8-10 hours

---

### Ticket #24: Load Testing
**Priority**: P2
**Story Points**: 5
**Assignee**: Backend Engineer
**Dependencies**: Ticket #13

**Description**:
Perform load testing to ensure production infrastructure can handle expected traffic.

**Tasks**:
- [ ] Set up k6 or Apache Bench
- [ ] Create load test scenarios
- [ ] Test with 100 concurrent users
- [ ] Test with 1000 requests/sec
- [ ] Measure P50, P95, P99 latency
- [ ] Identify bottlenecks
- [ ] Optimize as needed
- [ ] Document results

**Acceptance Criteria**:
- [ ] System handles 1000 RPS
- [ ] P95 latency < 500ms
- [ ] P99 latency < 1000ms
- [ ] Error rate < 0.1%
- [ ] No memory leaks
- [ ] Auto-scaling works correctly
- [ ] Results documented

**Testing**:
```bash
# Install k6
brew install k6  # or apt-get install k6

# Run load test
k6 run --vus 100 --duration 5m backend/tests/load/api_test.js

# Analyze results
k6 run --out json=results.json backend/tests/load/api_test.js
```

**Time Estimate**: 5-6 hours

---

## 🎯 EPIC 6: Launch Preparation (10 points)

### Ticket #25: Register Domain & Set Up DNS
**Priority**: P0
**Story Points**: 2
**Assignee**: DevOps Engineer
**Dependencies**: None

**Description**:
Register production domain and configure DNS records.

**Tasks**:
- [ ] Register `ap2expense.com` domain
- [ ] Set up DNS in Google Cloud DNS or registrar
- [ ] Create A records for app and api subdomains
- [ ] Create MX records for email
- [ ] Verify domain ownership for GCP
- [ ] Configure SSL certificates
- [ ] Test all domains resolve correctly

**Acceptance Criteria**:
- [ ] Domain registered
- [ ] DNS records configured
- [ ] SSL certificates active
- [ ] All domains resolve correctly
- [ ] Email delivery works

**Time Estimate**: 2-3 hours

---

### Ticket #26: GCP Marketplace Partner Portal Setup
**Priority**: P0
**Story Points**: 5
**Assignee**: Product Manager
**Dependencies**: Tickets #16-18, #19-20

**Description**:
Complete GCP Marketplace Partner Portal listing with all assets and configuration.

**Tasks**:
- [ ] Access Partner Portal (console.cloud.google.com/partner)
- [ ] Create product listing
- [ ] Upload icon and screenshots
- [ ] Add demo video link
- [ ] Configure pricing tiers
- [ ] Set up webhook endpoints
- [ ] Add legal document links
- [ ] Submit for Google review

**Acceptance Criteria**:
- [ ] Listing complete with all required fields
- [ ] All assets uploaded
- [ ] Pricing configured correctly
- [ ] Webhooks configured
- [ ] Legal docs linked
- [ ] Submitted for review

**Time Estimate**: 4-6 hours

---

### Ticket #27: Create Deployment Runbook
**Priority**: P1
**Story Points**: 3
**Assignee**: DevOps Engineer
**Dependencies**: All infrastructure tickets

**Description**:
Document comprehensive runbook for production operations.

**Tasks**:
- [ ] Document deployment procedures
- [ ] Document rollback procedures
- [ ] Document common incident responses
- [ ] Document secret rotation procedures
- [ ] Document database maintenance
- [ ] Document monitoring & alerting
- [ ] Create troubleshooting guide
- [ ] Train team on runbook

**Acceptance Criteria**:
- [ ] Runbook covers all operations
- [ ] Step-by-step procedures documented
- [ ] Screenshots/examples included
- [ ] Team trained
- [ ] Runbook tested

**Time Estimate**: 3-4 hours

---

## 📊 Summary Statistics

**Total Story Points**: 122 points
**Estimated Team Capacity**: 30 points/week (2.5 engineers)
**Timeline**: 4-5 sprints (8-10 weeks)

**Breakdown by Epic**:
- EPIC 1: GCP Marketplace Integration - 40 points (33%)
- EPIC 2: Production Infrastructure - 25 points (20%)
- EPIC 3: Marketplace Assets - 15 points (12%)
- EPIC 4: Legal & Compliance - 12 points (10%)
- EPIC 5: Testing & Quality - 20 points (16%)
- EPIC 6: Launch Preparation - 10 points (8%)

**Critical Path** (P0 tickets): 70 points (~3 weeks with 3 engineers)

---

## 📅 Recommended Sprint Plan

### Sprint 1 (Week 1-2): Foundation
- Ticket #1: Dependencies
- Ticket #2: Consumer Procurement Client
- Ticket #3: JWT Verification
- Ticket #10: GCP Project Setup
- Ticket #11: Production Database
- Ticket #16: Product Icon

**Total**: 23 points

### Sprint 2 (Week 3-4): Core Integration
- Ticket #4: Update Webhook Routes
- Ticket #5: Usage Tracking Service
- Ticket #6: Add Tracking to Endpoints
- Ticket #12: Production Secrets
- Ticket #25: Domain Registration

**Total**: 18 points

### Sprint 3 (Week 5-6): Usage Reporting & Assets
- Ticket #7: Usage Reporter
- Ticket #8: Cloud Scheduler
- Ticket #9: Feature Gating
- Ticket #13: Deploy Backend
- Ticket #17: Screenshots
- Ticket #19: Terms of Service

**Total**: 25 points

### Sprint 4 (Week 7-8): Deployment & Testing
- Ticket #14: Deploy Frontend
- Ticket #15: Monitoring & Alerting
- Ticket #20: Privacy Policy
- Ticket #22: Unit Tests
- Ticket #23: E2E Testing

**Total**: 29 points

### Sprint 5 (Week 9-10): Launch
- Ticket #18: Demo Video
- Ticket #21: SLA & DPA
- Ticket #24: Load Testing (optional)
- Ticket #26: Partner Portal
- Ticket #27: Runbook
- Final testing and launch

**Total**: 21 points

---

## 🎯 Definition of Done

For each ticket to be considered "done":
- [ ] Code implemented and peer-reviewed
- [ ] Unit tests written and passing
- [ ] Integration tests passing (if applicable)
- [ ] Code merged to main branch
- [ ] Documentation updated
- [ ] Deployed to staging and tested
- [ ] Product owner accepts

---

**Document Version**: 1.0
**Last Updated**: 2025-12-05
**Next Steps**: Import tickets into Jira/Linear and assign to sprint
