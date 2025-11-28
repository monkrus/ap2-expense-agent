# Production Deployment Checklist

**Project**: AP2 Expense Management Agent
**Date**: _____________
**Deployed By**: _____________
**Version/Commit**: _____________

---

## Pre-Deployment (Complete Before Starting)

### Code Quality
- [ ] All backend tests passing (`cd backend && pytest`)
- [ ] All frontend tests passing (`cd frontend && npm test`)
- [ ] Frontend builds successfully (`npm run build`)
- [ ] Security audit reviewed (SECURITY_AUDIT_REPORT_FINAL.md)
- [ ] Dependency audit reviewed (DEPENDENCY_AUDIT_REPORT.md)
- [ ] Code review completed by team
- [ ] CHANGELOG updated

### Google Cloud Platform
- [ ] GCP project created: `____________________`
- [ ] Billing enabled and verified
- [ ] Required APIs enabled (Run, SQL, Secret Manager, Container Registry)
- [ ] Service account created: `ap2-expense-backend@PROJECT.iam.gserviceaccount.com`
- [ ] IAM permissions configured

### Database
- [ ] Cloud SQL instance created
- [ ] Database `ap2_expense` created
- [ ] Database user created
- [ ] Database connection tested
- [ ] Alembic migrations run successfully
- [ ] Initial tier data seeded (optional)

### Stripe Configuration
- [ ] Stripe account in production mode (test data toggle OFF)
- [ ] 6 production products created (Starter/Pro/Enterprise × Monthly/Annual)
- [ ] Price IDs documented:
  - Starter Monthly: `____________________`
  - Starter Annual: `____________________`
  - Professional Monthly: `____________________`
  - Professional Annual: `____________________`
  - Enterprise Monthly: `____________________`
  - Enterprise Annual: `____________________`
- [ ] Stripe API keys (production) obtained

### Secrets Management
- [ ] All secrets created in GCP Secret Manager:
  - [ ] `database-url`
  - [ ] `jwt-secret`
  - [ ] `stripe-secret-key`
  - [ ] `stripe-publishable-key`
  - [ ] `stripe-webhook-secret` (placeholder, will update after deployment)
- [ ] Service account granted `secretAccessor` role for all secrets

---

## Deployment

### Backend Deployment
- [ ] Backend Docker image built
- [ ] Backend image pushed to GCR
- [ ] Backend deployed to Cloud Run:
  - Region: `____________________`
  - Min instances: `____`
  - Max instances: `____`
  - Memory: `____`
  - CPU: `____`
- [ ] Environment variables configured (Stripe price IDs)
- [ ] Secrets mounted from Secret Manager
- [ ] Cloud SQL connection configured
- [ ] Service account attached
- [ ] Backend URL obtained: `____________________`
- [ ] Backend health check passed: `curl https://BACKEND_URL/health`

### Frontend Deployment
- [ ] `.env.production` created with backend URL
- [ ] Frontend Docker image built
- [ ] Frontend image pushed to GCR
- [ ] Frontend deployed to Cloud Run:
  - Region: `____________________`
  - Min instances: `____`
  - Max instances: `____`
- [ ] Frontend URL obtained: `____________________`
- [ ] Frontend loads successfully in browser

### Stripe Webhook Configuration
- [ ] Webhook endpoint created in Stripe Dashboard
- [ ] Webhook URL: `https://BACKEND_URL/api/payment/webhooks/stripe`
- [ ] Webhook events selected:
  - [ ] `checkout.session.completed`
  - [ ] `customer.subscription.created`
  - [ ] `customer.subscription.updated`
  - [ ] `customer.subscription.deleted`
  - [ ] `invoice.paid`
  - [ ] `invoice.payment_failed`
- [ ] Webhook signing secret copied: `whsec_____________________`
- [ ] Webhook secret updated in Secret Manager
- [ ] Backend service redeployed with new secret

---

## Post-Deployment Verification

### API Testing
- [ ] Health endpoint responds: `GET /health`
- [ ] User registration works: `POST /api/v1/auth/register`
- [ ] User login works: `POST /api/v1/auth/login`
- [ ] Organization creation works
- [ ] Stripe checkout session creation works
- [ ] API documentation disabled (production security)

### Frontend Testing
- [ ] Homepage loads
- [ ] User can register
- [ ] User can login
- [ ] Dashboard loads after login
- [ ] Organization management works
- [ ] Billing/pricing page loads
- [ ] No console errors

### End-to-End Checkout Flow
- [ ] Create test user account
- [ ] Create test organization
- [ ] Navigate to pricing/billing page
- [ ] Select a subscription plan
- [ ] Redirected to Stripe Checkout
- [ ] Complete checkout with test card (`4242 4242 4242 4242`)
- [ ] Redirected back to application
- [ ] Subscription activated in application
- [ ] Webhook received in Stripe Dashboard
- [ ] BillingEvent created in database
- [ ] OrganizationSubscription updated in database

### Database Verification
- [ ] Connect to Cloud SQL via proxy
- [ ] Verify all tables exist
- [ ] Check billing_events table has webhook events
- [ ] Check organization_subscriptions table
- [ ] Check users table

### Monitoring & Logs
- [ ] Cloud Run metrics visible in GCP Console
- [ ] Backend logs streaming correctly
- [ ] Frontend logs streaming correctly
- [ ] No critical errors in logs
- [ ] Webhook events visible in Stripe Dashboard
- [ ] Webhook delivery success rate > 95%

---

## Security Verification

### Access Control
- [ ] API requires authentication for protected endpoints
- [ ] CORS configured correctly (only allows production domains)
- [ ] SQL injection tests pass (from security audit)
- [ ] XSS tests pass (from security audit)
- [ ] Rate limiting working on auth endpoints

### Secrets & Credentials
- [ ] No secrets in environment variables (all in Secret Manager)
- [ ] Database password is strong and unique
- [ ] JWT secret is cryptographically random
- [ ] Stripe keys are production keys (not test)
- [ ] Service account has minimum required permissions

### HTTPS & Network
- [ ] All connections use HTTPS
- [ ] Webhook signature verification enabled
- [ ] Database connections encrypted
- [ ] No public database access (Cloud SQL only via private IP/proxy)

---

## Monitoring Setup

### Alerts Configured
- [ ] High error rate alert (> 5%)
- [ ] High latency alert (p95 > 2s)
- [ ] Failed payment alert (`invoice.payment_failed`)
- [ ] Database connection error alert
- [ ] High memory usage alert (> 80%)
- [ ] Uptime check configured

### Dashboards Created
- [ ] Cloud Run metrics dashboard
- [ ] Database performance dashboard
- [ ] Billing events dashboard
- [ ] Stripe webhook delivery dashboard

---

## Documentation

### Updated Documentation
- [ ] Production URLs documented
- [ ] Stripe webhook endpoint documented
- [ ] Runbook updated with production details
- [ ] Team notified of deployment
- [ ] Deployment notes added to CHANGELOG

### Backup & Recovery
- [ ] Database backup strategy documented
- [ ] Rollback procedure tested
- [ ] Disaster recovery plan reviewed
- [ ] Backup restore tested (if applicable)

---

## Final Checks

### Performance
- [ ] Homepage loads in < 2 seconds
- [ ] API response time < 500ms for most endpoints
- [ ] Database queries optimized (checked via logs)
- [ ] No N+1 query issues

### Cost Management
- [ ] Budget alerts configured in GCP
- [ ] Resource limits set (max instances)
- [ ] Cost optimization reviewed
- [ ] Estimated monthly cost: `$____________`

### Team Handoff
- [ ] Production credentials shared securely (via Secret Manager/1Password)
- [ ] Deployment notes shared with team
- [ ] On-call engineer notified
- [ ] Support contacts updated

---

## Sign-Off

**Technical Lead**: ________________________ Date: ________

**DevOps/SRE**: ________________________ Date: ________

**Product Owner**: ________________________ Date: ________

---

## Post-Deployment Tasks (Within 24 Hours)

- [ ] Monitor logs for first 24 hours
- [ ] Check webhook delivery success rate
- [ ] Review any error spikes
- [ ] Verify no failed payments
- [ ] Send test transactions through system
- [ ] Update team documentation
- [ ] Schedule post-deployment review meeting

---

## Known Issues / Risks

Document any known issues or risks identified during deployment:

1. _______________________________________________________________
2. _______________________________________________________________
3. _______________________________________________________________

---

## Rollback Plan (If Needed)

**Trigger Conditions**:
- Critical bugs affecting all users
- Data corruption
- Security vulnerability
- Payment processing failure

**Rollback Steps**:
1. Identify previous working revision
2. Run: `gcloud run services update-traffic SERVICE --to-revisions=REVISION=100`
3. Verify health checks pass
4. Notify team
5. Investigate root cause

**Rollback Tested**: [ ] Yes [ ] No

---

**Deployment Complete**: [ ] Yes [ ] No

**Production URL**: ____________________

**Deployed At**: ____________________
