# Google Cloud Marketplace Billing Integration

Complete guide for implementing usage-based billing with Google Cloud Marketplace.

## Overview

The AP2 Expense Agent implements usage-based billing with the following metrics:
- **API Calls**: Number of API requests per period
- **Storage**: Total storage used (in GB) for receipts
- **Active Users**: Number of active users in the organization
- **Expenses**: Number of expenses processed per month

## Architecture

### Components

1. **Billing Models** (`models_billing.py`)
   - `UsageMetric`: Tracks individual usage metrics
   - `BillingTier`: Defines pricing plans and limits
   - `OrganizationSubscription`: Manages organization subscriptions
   - `BillingEvent`: Audit log for billing events

2. **Billing Service** (`services/billing_service.py`)
   - Usage tracking methods
   - Subscription management
   - GCP reporting integration
   - Limit checking

3. **Billing API** (`routes/billing.py`)
   - REST endpoints for billing operations
   - Subscription management
   - Usage reporting

4. **Usage Reporter** (`scripts/report_usage.py`)
   - Kubernetes CronJob
   - Hourly usage reporting to GCP
   - Automatic metric aggregation

## Billing Tiers

### Free Plan
- **Price**: $0/month
- **Limits**:
  - 1,000 API calls/day
  - 1 GB storage
  - 3 active users
  - 50 expenses/month
- **Features**:
  - Basic expense tracking
  - Email support

### Starter Plan
- **Price**: $29/month
- **Limits**:
  - 10,000 API calls/day
  - 10 GB storage
  - 10 active users
  - 500 expenses/month
- **Overage**:
  - API calls: $0.01 per 100 calls
  - Storage: $0.50/GB
  - Users: $5.00/user
- **Features**:
  - All Free features
  - AP2 protocol compliance
  - Complete audit trails
  - Priority email support

### Professional Plan
- **Price**: $99/month
- **Limits**:
  - 50,000 API calls/day
  - 50 GB storage
  - 50 active users
  - 5,000 expenses/month
- **Overage**:
  - API calls: $0.008 per 100 calls
  - Storage: $0.40/GB
  - Users: $4.00/user
- **Features**:
  - All Starter features
  - Advanced reporting
  - Custom categories
  - API access
  - Phone support
  - SSO integration

### Enterprise Plan
- **Price**: $299/month
- **Limits**:
  - 1,000,000 API calls/month
  - 500 GB storage
  - 1,000 active users
  - Unlimited expenses
- **Features**:
  - All Professional features
  - Dedicated support
  - SLA guarantee
  - Custom integrations
  - White-label option
  - Custom contract

## Setup

### 1. Initialize Billing Tiers

```bash
curl -X POST http://your-api/api/v1/billing/tiers/initialize \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### 2. Create Database Tables

Run Alembic migration:
```bash
cd backend
alembic upgrade head
```

### 3. Deploy Billing CronJob

```bash
kubectl apply -f k8s/billing-cronjob.yaml
```

The CronJob runs every hour to report usage to Google Cloud Marketplace.

## API Endpoints

### Get Billing Tiers

```bash
GET /api/v1/billing/tiers
```

Returns available pricing plans.

### Create Subscription

```bash
POST /api/v1/billing/subscriptions
{
  "organization_id": "org_xxx",
  "tier_name": "starter",
  "gcp_account_id": "account-xxx",
  "is_trial": false
}
```

### Get Subscription

```bash
GET /api/v1/billing/subscriptions/{organization_id}
```

### Get Usage Summary

```bash
GET /api/v1/billing/usage/{organization_id}?days=30
```

### Check Usage Limits

```bash
GET /api/v1/billing/usage/{organization_id}/limits?metric_type=api_calls
```

Returns:
```json
{
  "success": true,
  "allowed": true,
  "details": {
    "allowed": true,
    "current_usage": 5230,
    "limit": 10000,
    "percentage_used": 52.3
  }
}
```

### Report Usage to GCP (Admin)

```bash
POST /api/v1/billing/report-usage
{
  "organization_id": "org_xxx",
  "period_start": "2025-10-10T00:00:00Z",
  "period_end": "2025-10-10T23:59:59Z"
}
```

## Usage Tracking

### Automatic Tracking

Usage is tracked automatically:

1. **API Calls**: Middleware tracks every API request
2. **Storage**: Updated when receipts are uploaded
3. **Active Users**: Counted monthly from organization members
4. **Expenses**: Tracked when expenses are submitted

### Manual Tracking

You can also track usage programmatically:

```python
from src.services.billing_service import BillingService

service = BillingService(db)

# Track API call
service.track_api_call(organization_id, "/api/v1/expenses", "POST")

# Track storage
service.track_storage_usage(organization_id, bytes_used)

# Track active users
service.track_active_users(organization_id)
```

## Google Cloud Marketplace Integration

### 1. Create Service Account

```bash
gcloud iam service-accounts create ap2-expense-billing \
    --display-name="AP2 Expense Billing Reporter"

# Grant Commerce Producer role
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:ap2-expense-billing@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/cloudcommerceprocurement.producer"
```

### 2. Configure Metering

In Google Cloud Console:
1. Go to Cloud Marketplace > Products
2. Select your product
3. Configure pricing:
   - Add usage metrics (api_calls, storage_gb, active_users)
   - Set pricing per unit
   - Configure billing period (monthly)

### 3. Usage Reporting Format

The system reports usage in Google's required format:

```json
{
  "name": "operations/report-xxx",
  "operationId": "report-org_xxx-20251010120000",
  "consumerId": "gcp-account-id",
  "usageReportingId": "org_xxx",
  "startTime": "2025-10-10T00:00:00Z",
  "endTime": "2025-10-10T01:00:00Z",
  "metricValueSets": [
    {
      "metricName": "compute.googleapis.com/api_calls",
      "metricValues": [{"int64Value": "1234"}]
    },
    {
      "metricName": "compute.googleapis.com/storage_gb",
      "metricValues": [{"int64Value": "5"}]
    },
    {
      "metricName": "compute.googleapis.com/active_users",
      "metricValues": [{"int64Value": "10"}]
    }
  ]
}
```

### 4. Entitlement Webhook

Handle marketplace entitlements (purchases):

```bash
POST /api/v1/billing/marketplace/entitlement
{
  "account_id": "gcp-account-xxx",
  "entitlement_id": "entitlement-xxx",
  "organization_id": "org_xxx",
  "plan": "starter"
}
```

This creates a subscription linked to the GCP account.

## Testing

### 1. Test Usage Tracking

```bash
# Create subscription
curl -X POST http://localhost:8000/api/v1/billing/subscriptions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "organization_id": "test_org",
    "tier_name": "starter",
    "is_trial": true
  }'

# Make some API calls (these will be tracked)
curl -X GET http://localhost:8000/api/v1/expenses/report \
  -H "Authorization: Bearer $TOKEN"

# Check usage
curl http://localhost:8000/api/v1/billing/usage/test_org?days=1 \
  -H "Authorization: Bearer $TOKEN"
```

### 2. Test Usage Limits

```bash
# Check if within limits
curl "http://localhost:8000/api/v1/billing/usage/test_org/limits?metric_type=api_calls" \
  -H "Authorization: Bearer $TOKEN"
```

### 3. Test Usage Reporting

```bash
# Manual report (admin only)
curl -X POST http://localhost:8000/api/v1/billing/report-usage \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "organization_id": "test_org",
    "period_start": "2025-10-10T00:00:00Z",
    "period_end": "2025-10-10T23:59:59Z"
  }'
```

### 4. Test CronJob Locally

```bash
cd backend
python -m scripts.report_usage
```

## Monitoring

### Check CronJob Status

```bash
# List CronJobs
kubectl get cronjobs -n ap2-expense

# Check recent jobs
kubectl get jobs -n ap2-expense

# View logs
kubectl logs -n ap2-expense job/billing-usage-reporter-xxx
```

### Monitor Usage Metrics

```bash
# Get usage overview (admin)
curl http://localhost:8000/api/v1/billing/admin/usage-overview?days=30 \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Database Queries

```sql
-- Check usage metrics
SELECT
  organization_id,
  metric_type,
  SUM(metric_value) as total_usage,
  COUNT(*) as metric_count
FROM usage_metrics
WHERE period_start >= NOW() - INTERVAL '30 days'
GROUP BY organization_id, metric_type;

-- Check unreported metrics
SELECT COUNT(*)
FROM usage_metrics
WHERE reported_to_gcp = false;

-- Check subscriptions
SELECT
  organization_id,
  tier_name,
  status,
  is_trial,
  billing_period_end
FROM organization_subscriptions
WHERE status = 'active';
```

## Troubleshooting

### Usage Not Being Tracked

1. Check middleware is registered:
```python
# In api.py, add billing middleware
@app.middleware("http")
async def track_api_usage(request: Request, call_next):
    # Track usage here
    pass
```

2. Verify database tables exist:
```bash
psql $DATABASE_URL -c "\dt usage_metrics"
```

### CronJob Not Running

1. Check CronJob schedule:
```bash
kubectl describe cronjob billing-usage-reporter -n ap2-expense
```

2. Check service account permissions:
```bash
kubectl get serviceaccount ap2-expense-sa -n ap2-expense -o yaml
```

3. View recent job logs:
```bash
kubectl logs -n ap2-expense \
  $(kubectl get pods -n ap2-expense -l app.kubernetes.io/component=billing --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}')
```

### Reports Failing

1. Check GCP credentials:
```bash
gcloud auth application-default print-access-token
```

2. Verify Commerce API is enabled:
```bash
gcloud services list | grep commerce
```

3. Check billing event logs:
```sql
SELECT * FROM billing_events
WHERE status = 'failed'
ORDER BY occurred_at DESC
LIMIT 10;
```

## Production Checklist

- [ ] Billing tiers initialized
- [ ] Database tables created
- [ ] CronJob deployed and running
- [ ] GCP service account created
- [ ] Commerce Producer role granted
- [ ] Metering configured in Marketplace
- [ ] Usage tracking tested
- [ ] Limit enforcement tested
- [ ] Usage reporting tested
- [ ] Monitoring dashboards setup
- [ ] Alert rules configured
- [ ] Documentation reviewed

## Next Steps

1. **Week 2**: Configure monitoring dashboards
2. **Week 2**: Add usage alerts for approaching limits
3. **Week 3**: Create marketplace listing
4. **Week 3**: Add billing portal UI for customers

## Resources

- [Google Cloud Commerce API](https://cloud.google.com/marketplace/docs/partners/commerce-procurement-api)
- [Usage-Based Pricing](https://cloud.google.com/marketplace/docs/partners/create-usage-based-saas)
- [Entitlement Management](https://cloud.google.com/marketplace/docs/partners/entitlement-management)
