# Google Cloud Marketplace Integration Testing Guide

## Overview

This document outlines the testing procedures for validating Google Cloud Marketplace integration with the AP2 Expense Agent.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Test Environment Setup](#test-environment-setup)
3. [Entitlement Flow Testing](#entitlement-flow-testing)
4. [Usage Reporting Testing](#usage-reporting-testing)
5. [Billing Integration Testing](#billing-integration-testing)
6. [Test Scenarios](#test-scenarios)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Access

- Google Cloud Marketplace Partner Portal access
- GCP Project with Marketplace API enabled
- Test entitlement accounts
- Admin access to AP2 Expense Agent deployment

### Tools

- `curl` or Postman for API testing
- `gcloud` CLI configured
- Access to Cloud Logging

### Environment Variables

```bash
export GCP_PROJECT_ID="your-project-id"
export API_BASE_URL="https://your-domain.com/api"
export TEST_ENTITLEMENT_ID="test-ent-12345"
export TEST_ACCOUNT_ID="test-acct-67890"
```

---

## Test Environment Setup

### 1. Enable Test Mode

Update backend configuration:

```yaml
# k8s/configmap.yaml
ENABLE_GCP_MARKETPLACE: "true"
GCP_USAGE_REPORTING_ENABLED: "true"
ENVIRONMENT: "staging"  # Use staging for testing
```

Apply changes:

```bash
kubectl apply -f k8s/configmap.yaml
kubectl rollout restart deployment/backend -n ap2-expense
```

### 2. Configure Webhook Endpoint

In Google Cloud Marketplace Partner Portal:

1. Navigate to your product listing
2. Go to "Technical Integration"
3. Set webhook URL: `https://your-domain.com/api/v1/gcp/webhooks`
4. Generate and save webhook secret

Update secret:

```bash
echo -n "your-webhook-secret" | gcloud secrets versions add gcp-webhook-secret --data-file=-
```

### 3. Create Test Organization

```bash
curl -X POST "${API_BASE_URL}/v1/organizations" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -d '{
    "name": "Test Organization",
    "owner_email": "test@example.com",
    "plan": "starter"
  }'
```

---

## Entitlement Flow Testing

### Test 1: New Entitlement Creation

**Objective**: Verify that new entitlements are properly created and linked to organizations.

**Procedure**:

1. Simulate webhook from GCP Marketplace:

```bash
curl -X POST "${API_BASE_URL}/v1/gcp/webhooks/entitlement" \
  -H "Content-Type: application/json" \
  -H "X-GCP-Marketplace-Signature: ${WEBHOOK_SIGNATURE}" \
  -d '{
    "event_type": "ENTITLEMENT_CREATION",
    "entitlement_id": "'"${TEST_ENTITLEMENT_ID}"'",
    "account_id": "'"${TEST_ACCOUNT_ID}"'",
    "plan": "professional",
    "created_at": "2025-11-10T10:00:00Z"
  }'
```

2. Verify in database:

```sql
SELECT * FROM organization_subscriptions
WHERE gcp_entitlement_id = '${TEST_ENTITLEMENT_ID}';
```

3. Check logs:

```bash
kubectl logs -l app.kubernetes.io/component=backend -n ap2-expense --tail=100 | grep entitlement
```

**Expected Result**:
- HTTP 200 response
- New subscription record created
- Organization tier set to "professional"
- Billing event logged

---

### Test 2: Entitlement Update (Tier Change)

**Objective**: Verify tier upgrades/downgrades work correctly.

**Procedure**:

1. Upgrade from Professional to Enterprise:

```bash
curl -X POST "${API_BASE_URL}/v1/gcp/webhooks/entitlement" \
  -H "Content-Type: application/json" \
  -H "X-GCP-Marketplace-Signature: ${WEBHOOK_SIGNATURE}" \
  -d '{
    "event_type": "ENTITLEMENT_PLAN_CHANGE",
    "entitlement_id": "'"${TEST_ENTITLEMENT_ID}"'",
    "old_plan": "professional",
    "new_plan": "enterprise",
    "effective_at": "2025-11-10T11:00:00Z"
  }'
```

2. Verify limits updated:

```bash
curl -X GET "${API_BASE_URL}/v1/organizations/${ORG_ID}" \
  -H "Authorization: Bearer ${USER_TOKEN}"
```

**Expected Result**:
- Tier updated in database
- Usage limits increased (100 → 500 users)
- Email notification sent to org owner
- Billing event created

---

### Test 3: Entitlement Cancellation

**Objective**: Verify graceful handling of subscription cancellations.

**Procedure**:

1. Cancel entitlement:

```bash
curl -X POST "${API_BASE_URL}/v1/gcp/webhooks/entitlement" \
  -H "Content-Type: application/json" \
  -H "X-GCP-Marketplace-Signature: ${WEBHOOK_SIGNATURE}" \
  -d '{
    "event_type": "ENTITLEMENT_CANCELLATION",
    "entitlement_id": "'"${TEST_ENTITLEMENT_ID}"'",
    "effective_at": "2025-11-10T12:00:00Z",
    "reason": "customer_requested"
  }'
```

2. Verify access restrictions:

```bash
curl -X POST "${API_BASE_URL}/v1/expenses" \
  -H "Authorization: Bearer ${USER_TOKEN}" \
  -H "X-Organization-Id: ${ORG_ID}" \
  -d '{
    "amount": 100,
    "category": "travel"
  }'
```

**Expected Result**:
- Subscription status set to "cancelled"
- API requests return 403 Forbidden
- Data retention period starts (30 days grace period)
- Cancellation email sent

---

## Usage Reporting Testing

### Test 4: Hourly Usage Report

**Objective**: Verify usage metrics are correctly aggregated and reported.

**Procedure**:

1. Generate test usage:

```bash
# Create expenses
for i in {1..10}; do
  curl -X POST "${API_BASE_URL}/v1/expenses" \
    -H "Authorization: Bearer ${USER_TOKEN}" \
    -H "X-Organization-Id: ${ORG_ID}" \
    -d "{
      \"amount\": 100,
      \"category\": \"test\",
      \"description\": \"Test expense $i\"
    }"
done

# Trigger AI categorization
curl -X POST "${API_BASE_URL}/v1/expenses/${EXPENSE_ID}/categorize" \
  -H "Authorization: Bearer ${USER_TOKEN}"

# Trigger AP2 transaction
curl -X POST "${API_BASE_URL}/v1/ap2/transactions" \
  -H "Authorization: Bearer ${USER_TOKEN}" \
  -d '{
    "amount": 100,
    "merchant": "Test Merchant"
  }'
```

2. Manually trigger usage reporting:

```bash
kubectl create job --from=cronjob/billing-usage-reporter manual-usage-report -n ap2-expense
```

3. Check job logs:

```bash
kubectl logs job/manual-usage-report -n ap2-expense
```

4. Verify report sent to GCP:

```bash
# Check Cloud Logging
gcloud logging read "resource.type=k8s_pod AND labels.component=billing" \
  --limit 50 \
  --format json
```

**Expected Result**:
- Usage metrics aggregated correctly
- Report sent to GCP Marketplace API
- Metrics include:
  - Active users count
  - Expenses created
  - AI categorizations used
  - AP2 transactions processed
- No errors in logs

---

### Test 5: Usage Limit Enforcement

**Objective**: Verify that tier limits are enforced.

**Procedure**:

1. Set organization to Starter tier (100 expenses/month limit):

```sql
UPDATE organization_subscriptions
SET tier = 'starter',
    current_period_expenses = 95
WHERE organization_id = '${ORG_ID}';
```

2. Create 10 expenses to exceed limit:

```bash
for i in {1..10}; do
  curl -X POST "${API_BASE_URL}/v1/expenses" \
    -H "Authorization: Bearer ${USER_TOKEN}" \
    -H "X-Organization-Id: ${ORG_ID}" \
    -d "{
      \"amount\": 100,
      \"category\": \"test\"
    }"
done
```

**Expected Result**:
- First 5 requests succeed (reaching 100)
- Next 5 requests return 402 Payment Required
- Error message: "Monthly expense limit reached"
- Upgrade prompt included in response

---

## Billing Integration Testing

### Test 6: Overage Charges

**Objective**: Verify overage charges are calculated correctly.

**Procedure**:

1. Exceed AI categorization limit:

```bash
# Professional tier: 5,000 categorizations/month
# Trigger 5,100 categorizations

for i in {1..5100}; do
  curl -X POST "${API_BASE_URL}/v1/expenses/${EXPENSE_ID}/categorize" \
    -H "Authorization: Bearer ${USER_TOKEN}"
done
```

2. Check usage metrics:

```bash
curl -X GET "${API_BASE_URL}/v1/organizations/${ORG_ID}/usage" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}"
```

3. Verify overage calculation:

```sql
SELECT * FROM usage_metrics
WHERE organization_id = '${ORG_ID}'
AND metric_type = 'ai_categorization'
ORDER BY recorded_at DESC
LIMIT 10;
```

**Expected Result**:
- Usage tracked: 5,100 categorizations
- Overage: 100 categorizations
- Overage charge: 100 × $0.05 = $5.00
- Included in next usage report

---

### Test 7: Billing Event Audit Trail

**Objective**: Verify all billing events are properly logged.

**Procedure**:

1. Query billing events:

```sql
SELECT
  event_type,
  tier_from,
  tier_to,
  created_at,
  metadata
FROM billing_events
WHERE organization_id = '${ORG_ID}'
ORDER BY created_at DESC;
```

2. Verify completeness:

```bash
curl -X GET "${API_BASE_URL}/v1/admin/billing-events?organization_id=${ORG_ID}" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}"
```

**Expected Result**:
- All billing events logged:
  - Subscription creation
  - Tier changes
  - Usage reports
  - Overage charges
  - Cancellations
- Timestamps accurate
- Metadata complete

---

## Test Scenarios

### Scenario 1: Complete Customer Journey

**Steps**:

1. Customer purchases from GCP Marketplace
2. Entitlement webhook creates subscription
3. Customer accesses application
4. Customer uses features (create expenses, categorize)
5. Usage reported hourly to GCP
6. Customer upgrades tier
7. New limits applied immediately
8. Customer cancels subscription
9. Grace period begins

**Validation Points**:
- Every step logs properly
- No data loss
- Smooth transitions between tiers
- Email notifications sent

---

### Scenario 2: Webhook Failure Recovery

**Steps**:

1. Disable backend pods:

```bash
kubectl scale deployment/backend --replicas=0 -n ap2-expense
```

2. Send webhook (should fail)
3. Re-enable backend:

```bash
kubectl scale deployment/backend --replicas=3 -n ap2-expense
```

4. Check if webhook is retried by GCP

**Expected Result**:
- GCP Marketplace retries webhook
- Entitlement processed after recovery
- No duplicate records created

---

### Scenario 3: Split Organization (Edge Case)

**Objective**: Test what happens when users from same organization are in different tiers.

**Steps**:

1. Create organization with Professional tier
2. Add 10 users
3. Manually create second subscription (should not happen in production)
4. Observe behavior

**Expected Result**:
- System detects duplicate subscription
- Warning logged
- Support notified

---

## Automated Test Suite

Create automated tests using pytest:

```python
# backend/tests/test_marketplace_integration.py

import pytest
from src.gcp.entitlement_handler import handle_entitlement_creation
from src.gcp.usage_reporter import GCPUsageReporter

class TestMarketplaceIntegration:

    def test_entitlement_creation(self, db_session, mock_org):
        """Test new entitlement creates subscription"""
        webhook_data = {
            "entitlement_id": "test-ent-123",
            "account_id": "test-acct-456",
            "plan": "professional"
        }

        result = await handle_entitlement_creation(webhook_data, db_session)

        assert result["status"] == "success"
        assert result["tier"] == "professional"

    def test_usage_reporting(self, db_session, test_subscription):
        """Test usage metrics are reported correctly"""
        reporter = GCPUsageReporter(db_session)

        result = await reporter.report_organization_usage(test_subscription)

        assert result["status"] == "success"
        assert "metrics_reported" in result
        assert result["metrics_reported"] > 0

    def test_tier_upgrade(self, db_session, test_subscription):
        """Test tier upgrade updates limits"""
        webhook_data = {
            "entitlement_id": test_subscription.gcp_entitlement_id,
            "old_plan": "starter",
            "new_plan": "professional"
        }

        result = await handle_entitlement_update(webhook_data, db_session)

        # Refresh subscription
        db_session.refresh(test_subscription)

        assert test_subscription.tier == "professional"
        assert test_subscription.limits["users"] == 100
```

Run tests:

```bash
cd backend
pytest tests/test_marketplace_integration.py -v
```

---

## Troubleshooting

### Issue: Webhook Not Received

**Symptoms**:
- Entitlement created in GCP but not in app
- No logs showing webhook receipt

**Investigation**:

1. Check ingress configuration:

```bash
kubectl describe ingress ap2-expense-ingress -n ap2-expense
```

2. Check backend logs:

```bash
kubectl logs -l app.kubernetes.io/component=backend -n ap2-expense | grep webhook
```

3. Test endpoint manually:

```bash
curl -X POST "${API_BASE_URL}/v1/gcp/webhooks/health"
```

**Resolution**:
- Verify webhook URL is accessible from GCP
- Check firewall rules
- Verify webhook secret is correct

---

### Issue: Usage Not Reported

**Symptoms**:
- CronJob runs but no usage in GCP console

**Investigation**:

1. Check CronJob status:

```bash
kubectl get cronjob billing-usage-reporter -n ap2-expense
kubectl get jobs -n ap2-expense
```

2. Check latest job logs:

```bash
LATEST_JOB=$(kubectl get jobs -n ap2-expense -l app.kubernetes.io/component=billing --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}')
kubectl logs job/${LATEST_JOB} -n ap2-expense
```

**Resolution**:
- Verify service account has correct IAM permissions
- Check GCP_PROJECT_ID is set correctly
- Verify entitlement_id is valid

---

### Issue: Tier Limits Not Enforced

**Symptoms**:
- Users can exceed limits without error

**Investigation**:

1. Check middleware is loaded:

```bash
# Check backend logs for middleware initialization
kubectl logs -l app.kubernetes.io/component=backend -n ap2-expense | grep middleware
```

2. Verify tier limits in database:

```sql
SELECT
  tier,
  limits,
  current_period_expenses,
  current_period_ai_categorizations
FROM organization_subscriptions
WHERE organization_id = '${ORG_ID}';
```

**Resolution**:
- Ensure tier limits middleware is active
- Check that current_period_* counters are updating
- Verify period reset logic runs monthly

---

## Performance Testing

### Load Test Usage Reporting

Use locust to simulate high load:

```python
# load-test-marketplace.py

from locust import HttpUser, task, between

class MarketplaceLoadTest(HttpUser):
    wait_time = between(1, 3)

    @task
    def create_expense(self):
        self.client.post("/v1/expenses", json={
            "amount": 100,
            "category": "test"
        })

    @task(2)
    def trigger_categorization(self):
        self.client.post(f"/v1/expenses/{self.expense_id}/categorize")
```

Run:

```bash
locust -f load-test-marketplace.py --host=${API_BASE_URL} --users=100 --spawn-rate=10
```

---

## Compliance Checklist

Before going live:

- [ ] All webhook endpoints tested
- [ ] Usage reporting verified accurate
- [ ] Tier limits enforced correctly
- [ ] Email notifications working
- [ ] Billing events auditable
- [ ] Error handling tested
- [ ] Webhook signature validation enabled
- [ ] Rate limiting configured
- [ ] Monitoring alerts set up
- [ ] Documentation complete
- [ ] Support team trained

---

## Support Contacts

- Marketplace API Issues: marketplace-support@google.com
- Partner Portal Access: partner-portal-support@google.com
- Technical Integration: Your partner manager

---

## References

- [Google Cloud Marketplace Integration Guide](https://cloud.google.com/marketplace/docs/partners)
- [Marketplace API Reference](https://cloud.google.com/marketplace/docs/partners/integrated-saas/backend-integration)
- [Procurement API](https://cloud.google.com/marketplace/docs/partners/integrated-saas/procurement-api)
