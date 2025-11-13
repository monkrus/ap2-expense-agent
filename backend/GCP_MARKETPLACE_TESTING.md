# GCP Marketplace Integration Testing Guide

## Overview
This guide covers testing Google Cloud Marketplace integration for the AP2 Expense Agent, including entitlement approval, usage reporting, and procurement webhooks.

## Prerequisites
- ✅ PostgreSQL migration complete
- ✅ Application deployed to Cloud Run
- ✅ GCP Service Account with required permissions
- ✅ Partner Portal access for GCP Marketplace

---

## Architecture Overview

```
GCP Marketplace
    ↓ (Entitlement Created)
Procurement API Webhook
    ↓ (Approval Request)
Your Backend (/api/webhooks/gcp/procurement)
    ↓ (Approve)
GCP Procurement API
    ↓ (Entitlement Approved)
User Gets Access
    ↓ (Usage Events)
Usage Reporting Cron
    ↓ (Report Usage)
GCP Service Control API
    ↓ (Billing)
Google Cloud Billing
```

---

## Step 1: Enable Required APIs

```bash
# Set your project ID
PROJECT_ID=your-project-id

# Enable required APIs
gcloud services enable cloudcommerceprocurement.googleapis.com \
  --project=$PROJECT_ID

gcloud services enable servicecontrol.googleapis.com \
  --project=$PROJECT_ID

gcloud services enable servicemanagement.googleapis.com \
  --project=$PROJECT_ID
```

---

## Step 2: Create Service Account

```bash
# Create service account for marketplace integration
gcloud iam service-accounts create gcp-marketplace-sa \
  --display-name="GCP Marketplace Service Account" \
  --project=$PROJECT_ID

# Grant required roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:gcp-marketplace-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/cloudcommerceprocurement.procurementAdmin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:gcp-marketplace-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/servicecontrol.serviceController"

# Create key
gcloud iam service-accounts keys create gcp-marketplace-key.json \
  --iam-account=gcp-marketplace-sa@${PROJECT_ID}.iam.gserviceaccount.com \
  --project=$PROJECT_ID
```

---

## Step 3: Configure Application

Update `.env` with GCP credentials:

```bash
# GCP Configuration
GCP_PROJECT_ID=your-project-id
GCP_SERVICE_ACCOUNT_KEY=/path/to/gcp-marketplace-key.json

# Marketplace Product ID (get from Partner Portal)
GCP_MARKETPLACE_PRODUCT_ID=your-product-id

# Service name for usage reporting
GCP_SERVICE_NAME=ap2-expense-agent.endpoints.${GCP_PROJECT_ID}.cloud.goog
```

---

## Step 4: Test Procurement Webhook

### Check Webhook Endpoint

```bash
# Verify webhook is accessible
curl https://your-app-url.run.app/api/webhooks/gcp/health

# Expected response:
# {"status": "healthy", "service": "gcp-webhooks"}
```

### Review Webhook Implementation

Check `src/routes/gcp_procurement.py`:

```python
@router.post("/procurement")
async def handle_procurement_event(
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle GCP procurement events (account creation, entitlement)"""
    # This webhook receives:
    # 1. Account Creation events
    # 2. Entitlement Approved events
    # 3. Entitlement Cancelled events
```

### Simulate Procurement Event

Create test payload:

```json
{
  "eventId": "test-event-123",
  "eventType": "ENTITLEMENT_PENDING_PLAN_CHANGE_APPROVED",
  "eventTimestamp": "2025-11-13T19:00:00Z",
  "entitlement": {
    "id": "ent-test-123",
    "name": "providers/test-provider/entitlements/test-ent",
    "account": "providers/test-provider/accounts/acc-123",
    "product": "products/ap2-expense-agent",
    "plan": "PROFESSIONAL",
    "state": "ENTITLEMENT_ACTIVATION_REQUESTED",
    "createTime": "2025-11-13T19:00:00Z",
    "updateTime": "2025-11-13T19:00:00Z"
  }
}
```

Test webhook:

```bash
curl -X POST https://your-app-url.run.app/api/webhooks/gcp/procurement \
  -H "Content-Type: application/json" \
  -d @procurement-test-event.json
```

---

## Step 5: Implement Entitlement Approval

Update `src/gcp_marketplace_client.py` with approval logic:

```python
from google.cloud import commerceprocurement_v1
from google.oauth2 import service_account

class GCPMarketplaceClient:
    def __init__(self):
        credentials = service_account.Credentials.from_service_account_file(
            settings.gcp_service_account_key
        )
        self.client = commerceprocurement_v1.CloudCommercePartnerProcurementServiceClient(
            credentials=credentials
        )

    def approve_entitlement(self, entitlement_name: str):
        """Approve a pending entitlement"""
        request = commerceprocurement_v1.ApproveEntitlementRequest(
            name=entitlement_name
        )

        try:
            response = self.client.approve_entitlement(request=request)
            return response
        except Exception as e:
            logger.error(f"Failed to approve entitlement: {e}")
            raise

    def get_entitlement(self, entitlement_name: str):
        """Get entitlement details"""
        request = commerceprocurement_v1.GetEntitlementRequest(
            name=entitlement_name
        )
        return self.client.get_entitlement(request=request)
```

---

## Step 6: Test Entitlement Flow End-to-End

### Manual Test Process

1. **Create Test Entitlement** (via GCP Partner Portal):
   - Go to Partner Portal
   - Create test customer
   - Subscribe to PROFESSIONAL plan
   - Note the entitlement ID

2. **Verify Webhook Received**:
```bash
# Check application logs
gcloud logging read "resource.type=cloud_run_revision \
  AND jsonPayload.message=~'Received procurement event'" \
  --limit=10 \
  --format=json \
  --project=$PROJECT_ID
```

3. **Check Database**:
```sql
-- Verify organization_subscription created
SELECT * FROM organization_subscriptions
WHERE gcp_account_id IS NOT NULL
ORDER BY created_at DESC LIMIT 5;

-- Check entitlement stored
SELECT * FROM organization_subscriptions
WHERE entitlement_id LIKE 'ent-%';
```

4. **Verify Approval Sent**:
```bash
# Check logs for approval confirmation
gcloud logging read "resource.type=cloud_run_revision \
  AND jsonPayload.message=~'Entitlement approved'" \
  --limit=10 \
  --format=json \
  --project=$PROJECT_ID
```

---

## Step 7: Implement Usage Reporting

### Create Usage Reporting Service

Create `src/services/gcp_usage_reporter.py`:

```python
from google.cloud import servicecontrol_v1
from google.api import metric_pb2
from datetime import datetime, timezone
from decimal import Decimal

class GCPUsageReporter:
    """Report usage to GCP Service Control API for marketplace billing"""

    def __init__(self):
        self.client = servicecontrol_v1.ServiceControllerClient()
        self.service_name = settings.gcp_service_name

    def report_usage(
        self,
        organization_id: str,
        metric_type: str,
        metric_value: float,
        start_time: datetime,
        end_time: datetime
    ):
        """Report usage metrics to GCP"""

        operation = servicecontrol_v1.Operation(
            operation_id=f"{organization_id}-{int(start_time.timestamp())}",
            operation_name=f"{self.service_name}/operations/{organization_id}",
            consumer_id=f"project:{settings.gcp_project_id}",
            start_time=start_time,
            end_time=end_time,
            metric_value_sets=[
                servicecontrol_v1.MetricValueSet(
                    metric_name=f"{self.service_name}/{metric_type}",
                    metric_values=[
                        metric_pb2.MetricValue(
                            double_value=metric_value
                        )
                    ]
                )
            ]
        )

        request = servicecontrol_v1.ReportRequest(
            service_name=self.service_name,
            operations=[operation]
        )

        response = self.client.report(request=request)
        return response
```

### Create Cron Job for Usage Reporting

Create `src/tasks/report_usage.py`:

```python
#!/usr/bin/env python
"""
Cron job to report usage metrics to GCP
Run this hourly or daily via Cloud Scheduler
"""

from datetime import datetime, timedelta
from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session

from src.config import settings
from src.models_billing import OrganizationSubscription, UsageMetric
from src.services.gcp_usage_reporter import GCPUsageReporter

def report_usage_to_gcp():
    """Report unreported usage metrics to GCP"""

    engine = create_engine(settings.database_url)
    db = Session(engine)
    reporter = GCPUsageReporter()

    try:
        # Get all unreported usage metrics
        unreported = db.query(UsageMetric).filter(
            UsageMetric.reported_to_gcp == False
        ).all()

        print(f"Found {len(unreported)} unreported usage metrics")

        for metric in unreported:
            # Get organization subscription
            org_sub = db.query(OrganizationSubscription).filter(
                OrganizationSubscription.organization_id == metric.organization_id
            ).first()

            if not org_sub or not org_sub.gcp_account_id:
                print(f"Skipping metric {metric.id} - no GCP account")
                continue

            # Report to GCP
            try:
                reporter.report_usage(
                    organization_id=metric.organization_id,
                    metric_type=metric.metric_type,
                    metric_value=float(metric.metric_value),
                    start_time=metric.period_start,
                    end_time=metric.period_end
                )

                # Mark as reported
                metric.reported_to_gcp = True
                metric.gcp_reported_at = datetime.utcnow()
                db.commit()

                print(f"Reported metric {metric.id} to GCP")

            except Exception as e:
                print(f"Failed to report metric {metric.id}: {e}")
                db.rollback()

    finally:
        db.close()

if __name__ == "__main__":
    report_usage_to_gcp()
```

---

## Step 8: Set Up Cloud Scheduler

```bash
# Create Cloud Scheduler job to run usage reporting hourly
gcloud scheduler jobs create http report-gcp-usage \
  --schedule="0 * * * *" \
  --uri="https://your-app-url.run.app/api/webhooks/gcp/report-usage" \
  --http-method=POST \
  --oidc-service-account-email=gcp-marketplace-sa@${PROJECT_ID}.iam.gserviceaccount.com \
  --oidc-token-audience="https://your-app-url.run.app" \
  --project=$PROJECT_ID

# Or create app engine cron job
# Create cron.yaml:
# cron:
# - description: "Report usage to GCP"
#   url: /api/webhooks/gcp/report-usage
#   schedule: every 1 hours
```

Add webhook endpoint:

```python
# In src/routes/gcp_webhooks.py
@router.post("/report-usage")
async def trigger_usage_reporting(
    request: Request,
    db: Session = Depends(get_db)
):
    """Trigger usage reporting to GCP (called by Cloud Scheduler)"""
    from src.tasks.report_usage import report_usage_to_gcp

    try:
        report_usage_to_gcp()
        return {"status": "success", "message": "Usage reported to GCP"}
    except Exception as e:
        logger.error(f"Usage reporting failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Step 9: Testing Usage Reporting

### Create Test Usage Data

```python
# test_usage_creation.py
from datetime import datetime, timedelta
from src.billing.usage_tracker import UsageTracker
from src.database import SessionLocal

db = SessionLocal()
tracker = UsageTracker(db)

# Create test usage for an organization with GCP account
tracker.track_usage(
    user_id="test-user-id",
    usage_type="expense",
    quantity=10,
    organization_id="org-with-gcp-account"
)

tracker.track_usage(
    user_id="test-user-id",
    usage_type="ai_categorization",
    quantity=50,
    organization_id="org-with-gcp-account"
)

db.close()
```

### Verify Usage Metrics

```sql
-- Check usage_metrics table
SELECT
    id,
    organization_id,
    metric_type,
    metric_value,
    reported_to_gcp,
    created_at
FROM usage_metrics
WHERE organization_id = 'org-with-gcp-account'
ORDER BY created_at DESC;
```

### Trigger Manual Report

```bash
# Run usage reporting manually
python src/tasks/report_usage.py

# Or trigger via webhook
curl -X POST https://your-app-url.run.app/api/webhooks/gcp/report-usage \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)"
```

### Verify in GCP

```bash
# Check Service Control API logs
gcloud logging read "resource.type=servicecontrol.googleapis.com/Control \
  AND protoPayload.serviceName=ap2-expense-agent.endpoints.${PROJECT_ID}.cloud.goog" \
  --limit=20 \
  --format=json \
  --project=$PROJECT_ID
```

---

## Step 10: Integration Testing Checklist

### Account Creation Flow
- [ ] Webhook receives account creation event
- [ ] Organization created in database
- [ ] GCP account ID stored correctly
- [ ] Success logged

### Entitlement Approval Flow
- [ ] Webhook receives entitlement request
- [ ] Subscription tier mapped correctly (STARTER/PROFESSIONAL/etc.)
- [ ] Approval sent to GCP Procurement API
- [ ] Entitlement ID stored in database
- [ ] Organization granted access

### Usage Reporting Flow
- [ ] Usage events create UsageMetric records
- [ ] Usage metrics flagged as unreported
- [ ] Cron job picks up unreported metrics
- [ ] Metrics sent to Service Control API
- [ ] Metrics marked as reported
- [ ] GCP billing reflects usage

### Cancellation Flow
- [ ] Webhook receives cancellation event
- [ ] Subscription marked as cancelled
- [ ] Access revoked appropriately
- [ ] Data retention handled per policy

---

## Troubleshooting

### Webhook Not Receiving Events

1. Check webhook URL is publicly accessible
2. Verify SSL certificate is valid
3. Check firewall rules allow GCP IPs
4. Review application logs for errors

### Entitlement Approval Fails

```bash
# Check service account permissions
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:gcp-marketplace-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# Verify Procurement API is enabled
gcloud services list --enabled --project=$PROJECT_ID | grep procurement
```

### Usage Not Reported

```sql
-- Check for stuck metrics
SELECT * FROM usage_metrics
WHERE reported_to_gcp = FALSE
  AND created_at < NOW() - INTERVAL '24 hours';

-- Force mark as reported (emergency only)
UPDATE usage_metrics
SET reported_to_gcp = TRUE,
    gcp_reported_at = NOW()
WHERE id = 'stuck-metric-id';
```

---

## Success Criteria

✅ Procurement webhook receiving events
✅ Entitlements automatically approved
✅ Organizations linked to GCP accounts
✅ Usage metrics tracked in database
✅ Usage reported to GCP hourly
✅ Test customer can subscribe successfully
✅ Billing reflects actual usage

---

## Next Steps

After GCP testing:
1. ✅ Submit to GCP Marketplace for review
2. ✅ Complete Partner Portal documentation
3. ✅ Set up support channels
4. ✅ Launch beta program
5. ✅ Monitor for issues

---

## Production Checklist

Before going live:
- [ ] Service account permissions verified
- [ ] Webhook endpoint secured (authentication)
- [ ] Usage reporting cron job scheduled
- [ ] Error alerting configured
- [ ] Database backups enabled
- [ ] Monitoring dashboards created
- [ ] Support email configured
- [ ] Terms of Service updated
- [ ] Privacy Policy reviewed
- [ ] Compliance audit completed
