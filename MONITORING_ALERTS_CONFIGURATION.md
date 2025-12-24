# Monitoring & Alerts Configuration

**AP2 Expense Management - Google Cloud Platform**

Last Updated: December 23, 2025

---

## Table of Contents

1. [Overview](#overview)
2. [Cloud Monitoring Dashboards](#cloud-monitoring-dashboards)
3. [Alerting Policies](#alerting-policies)
4. [Uptime Checks](#uptime-checks)
5. [Log-Based Metrics](#log-based-metrics)
6. [Custom Metrics](#custom-metrics)
7. [Notification Channels](#notification-channels)
8. [Incident Response](#incident-response)

---

## Overview

### Monitoring Strategy

**Objectives**:
- **Availability**: 99.9% uptime SLA
- **Performance**: p95 latency < 500ms
- **Reliability**: Error rate < 1%
- **Security**: Detect suspicious activity within 5 minutes

**Key Metrics**:
- Request rate (requests/second)
- Latency (p50, p95, p99)
- Error rate (4xx, 5xx)
- CPU & memory utilization
- Database connections & query performance
- User authentication failures
- API rate limit violations

---

## Cloud Monitoring Dashboards

### 1. Application Overview Dashboard

**Name**: `AP2 Expense - Application Overview`

**Metrics**:

#### Cloud Run - Backend
```yaml
- Request Count (requests/minute)
  - Metric: run.googleapis.com/request_count
  - Filter: resource.service_name="ap2-expense-backend"
  - Aggregation: Sum, 1-minute intervals

- Request Latency (ms)
  - Metric: run.googleapis.com/request_latencies
  - Filter: resource.service_name="ap2-expense-backend"
  - Percentiles: p50, p95, p99

- Error Rate (%)
  - Metric: run.googleapis.com/request_count
  - Filter: metric.response_code_class="5xx"
  - Calculation: (5xx / total) * 100

- Container Instance Count
  - Metric: run.googleapis.com/container/instance_count
  - Shows: active instances, max configured

- CPU Utilization (%)
  - Metric: run.googleapis.com/container/cpu/utilization_time
  - Filter: resource.service_name="ap2-expense-backend"

- Memory Utilization (MB)
  - Metric: run.googleapis.com/container/memory/utilizations
  - Filter: resource.service_name="ap2-expense-backend"
```

#### Cloud Run - Frontend
```yaml
- Request Count (requests/minute)
  - Same as backend, filter: service_name="ap2-expense-frontend"

- Request Latency (ms)
  - Same as backend, filter: service_name="ap2-expense-frontend"

- Static Asset Cache Hit Rate (%)
  - Track CDN cache effectiveness
```

### 2. Database Performance Dashboard

**Name**: `AP2 Expense - Database`

**Metrics**:

#### Cloud SQL
```yaml
- Active Connections
  - Metric: cloudsql.googleapis.com/database/postgresql/num_backends
  - Warning threshold: > 50 (out of 60 max)

- CPU Utilization (%)
  - Metric: cloudsql.googleapis.com/database/cpu/utilization
  - Critical threshold: > 80%

- Memory Utilization (%)
  - Metric: cloudsql.googleapis.com/database/memory/utilization
  - Critical threshold: > 85%

- Disk Read/Write IOPS
  - Metric: cloudsql.googleapis.com/database/disk/read_ops_count
  - Metric: cloudsql.googleapis.com/database/disk/write_ops_count

- Disk Utilization (%)
  - Metric: cloudsql.googleapis.com/database/disk/utilization
  - Warning threshold: > 70%

- Replication Lag (seconds)
  - Metric: cloudsql.googleapis.com/database/replication/replica_lag
  - Critical if > 10 seconds

- Query Performance
  - Slowest queries (from pg_stat_statements)
  - Query counts per minute
  - Lock contention metrics
```

### 3. Security & Authentication Dashboard

**Name**: `AP2 Expense - Security`

**Metrics**:

```yaml
- Failed Login Attempts (count/minute)
  - Log-based metric
  - Filter: "401" AND "login"
  - Alert threshold: > 10/minute

- Rate Limit Violations (count/minute)
  - Log-based metric
  - Filter: "429 Too Many Requests"

- JWT Token Failures
  - Log-based metric
  - Filter: "Invalid token" OR "Expired token"

- Suspicious Activity Patterns
  - Multiple failed logins from same IP
  - Unusual API access patterns
  - Large data exports

- CORS Violations
  - Log-based metric
  - Filter: "CORS" AND "blocked"
```

### 4. Business Metrics Dashboard

**Name**: `AP2 Expense - Business Metrics`

**Metrics**:

```yaml
- Active Users (count)
  - Unique users logged in per hour
  - Daily active users (DAU)
  - Monthly active users (MAU)

- Expenses Created (count/hour)
  - Total expenses submitted
  - By category breakdown
  - By organization

- Receipts Uploaded (count/hour)
  - Successful uploads
  - Failed uploads (with reasons)

- PDF Exports (count/hour)
  - Export requests
  - Export failures

- Excel Exports (count/hour)
  - Export requests
  - Export failures

- Approval Workflow Metrics
  - Time to approval (median, p95)
  - Auto-approval rate
  - Rejection rate

- Google Cloud Marketplace
  - New subscriptions (count/day)
  - Tier distribution
  - Entitlement updates
  - Webhook failures
```

### Setup Commands

#### Create Application Dashboard
```bash
gcloud monitoring dashboards create \
  --config-from-file=monitoring/dashboards/application-overview.yaml
```

#### Dashboard Configuration (YAML)
Save as `monitoring/dashboards/application-overview.yaml`:

```yaml
displayName: "AP2 Expense - Application Overview"
mosaicLayout:
  columns: 12
  tiles:
    - width: 6
      height: 4
      widget:
        title: "Backend Request Rate"
        xyChart:
          dataSets:
            - timeSeriesQuery:
                timeSeriesFilter:
                  filter: 'resource.type="cloud_run_revision" resource.service_name="ap2-expense-backend" metric.type="run.googleapis.com/request_count"'
                  aggregation:
                    alignmentPeriod: 60s
                    perSeriesAligner: ALIGN_RATE
          yAxis:
            label: "Requests/second"

    - width: 6
      height: 4
      widget:
        title: "Backend Latency (p95)"
        xyChart:
          dataSets:
            - timeSeriesQuery:
                timeSeriesFilter:
                  filter: 'resource.type="cloud_run_revision" resource.service_name="ap2-expense-backend" metric.type="run.googleapis.com/request_latencies"'
                  aggregation:
                    alignmentPeriod: 60s
                    perSeriesAligner: ALIGN_DELTA
                    crossSeriesReducer: REDUCE_PERCENTILE_95
          yAxis:
            label: "Milliseconds"

    - width: 6
      height: 4
      widget:
        title: "Error Rate"
        xyChart:
          dataSets:
            - timeSeriesQuery:
                timeSeriesFilter:
                  filter: 'resource.type="cloud_run_revision" metric.type="run.googleapis.com/request_count" metric.response_code_class="5xx"'
                  aggregation:
                    alignmentPeriod: 60s
                    perSeriesAligner: ALIGN_RATE
          yAxis:
            label: "Errors/second"

    - width: 6
      height: 4
      widget:
        title: "Database Connections"
        xyChart:
          dataSets:
            - timeSeriesQuery:
                timeSeriesFilter:
                  filter: 'resource.type="cloudsql_database" metric.type="cloudsql.googleapis.com/database/postgresql/num_backends"'
                  aggregation:
                    alignmentPeriod: 60s
                    perSeriesAligner: ALIGN_MEAN
          yAxis:
            label: "Active connections"
          thresholds:
            - value: 50
              color: YELLOW
            - value: 55
              color: RED
```

---

## Alerting Policies

### Critical Alerts (Page On-Call)

#### 1. Service Down
```bash
gcloud alpha monitoring policies create \
  --notification-channels=PAGERDUTY_CHANNEL_ID \
  --display-name="[P1] Service Down" \
  --condition-display-name="Health check failing" \
  --condition-threshold-value=0 \
  --condition-threshold-duration=180s \
  --condition-threshold-filter='resource.type="uptime_url" metric.type="monitoring.googleapis.com/uptime_check/check_passed"' \
  --condition-threshold-comparison=COMPARISON_LT \
  --alert-strategy-auto-close=1800s
```

**When**: Health check fails for 3 consecutive minutes
**Action**: Page on-call engineer immediately
**Severity**: P1 - Critical

#### 2. High Error Rate
```bash
gcloud alpha monitoring policies create \
  --notification-channels=PAGERDUTY_CHANNEL_ID,SLACK_CHANNEL_ID \
  --display-name="[P1] High Error Rate" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=0.05 \
  --condition-threshold-duration=300s \
  --condition-threshold-filter='resource.type="cloud_run_revision" metric.type="run.googleapis.com/request_count" metric.response_code_class="5xx"' \
  --condition-threshold-comparison=COMPARISON_GT
```

**When**: Error rate > 5% for 5 minutes
**Action**: Page on-call + post to Slack
**Severity**: P1 - Critical

#### 3. Database Connection Exhaustion
```bash
gcloud alpha monitoring policies create \
  --notification-channels=PAGERDUTY_CHANNEL_ID \
  --display-name="[P1] Database Connections Exhausted" \
  --condition-display-name="Active connections > 55" \
  --condition-threshold-value=55 \
  --condition-threshold-duration=120s \
  --condition-threshold-filter='resource.type="cloudsql_database" metric.type="cloudsql.googleapis.com/database/postgresql/num_backends"' \
  --condition-threshold-comparison=COMPARISON_GT
```

**When**: Active connections > 55 (out of 60 max) for 2 minutes
**Action**: Page on-call immediately
**Severity**: P1 - Critical
**Runbook**: Scale database or investigate connection leaks

### High Priority Alerts (Slack Notification)

#### 4. High Latency
```bash
gcloud alpha monitoring policies create \
  --notification-channels=SLACK_CHANNEL_ID \
  --display-name="[P2] High Latency" \
  --condition-display-name="p95 latency > 1000ms" \
  --condition-threshold-value=1000 \
  --condition-threshold-duration=600s \
  --condition-threshold-filter='resource.type="cloud_run_revision" metric.type="run.googleapis.com/request_latencies"' \
  --condition-threshold-comparison=COMPARISON_GT \
  --condition-threshold-aggregations='alignment_period=60s,per_series_aligner=ALIGN_DELTA,cross_series_reducer=REDUCE_PERCENTILE_95'
```

**When**: p95 latency > 1 second for 10 minutes
**Action**: Notify team via Slack
**Severity**: P2 - High

#### 5. Database CPU High
```bash
gcloud alpha monitoring policies create \
  --notification-channels=SLACK_CHANNEL_ID \
  --display-name="[P2] Database CPU High" \
  --condition-display-name="CPU > 80%" \
  --condition-threshold-value=0.80 \
  --condition-threshold-duration=600s \
  --condition-threshold-filter='resource.type="cloudsql_database" metric.type="cloudsql.googleapis.com/database/cpu/utilization"' \
  --condition-threshold-comparison=COMPARISON_GT
```

**When**: Database CPU > 80% for 10 minutes
**Action**: Notify team via Slack
**Severity**: P2 - High
**Runbook**: Investigate slow queries, consider scaling

#### 6. Memory Usage High
```bash
gcloud alpha monitoring policies create \
  --notification-channels=SLACK_CHANNEL_ID \
  --display-name="[P2] Memory Usage High" \
  --condition-display-name="Memory > 85%" \
  --condition-threshold-value=0.85 \
  --condition-threshold-duration=600s \
  --condition-threshold-filter='resource.type="cloud_run_revision" metric.type="run.googleapis.com/container/memory/utilizations"' \
  --condition-threshold-comparison=COMPARISON_GT
```

**When**: Container memory > 85% for 10 minutes
**Action**: Notify team via Slack
**Severity**: P2 - High
**Runbook**: Check for memory leaks, consider scaling

### Security Alerts

#### 7. Suspicious Authentication Activity
```yaml
# Log-based alert for failed login attempts
displayName: "[P2] High Failed Login Rate"
conditions:
  - displayName: "Failed logins > 20/minute"
    conditionThreshold:
      filter: 'resource.type="cloud_run_revision" AND "401 Unauthorized" AND "/auth/login"'
      aggregations:
        - alignmentPeriod: 60s
          perSeriesAligner: ALIGN_RATE
      comparison: COMPARISON_GT
      thresholdValue: 20
      duration: 300s
notificationChannels:
  - SECURITY_SLACK_CHANNEL_ID
```

**When**: > 20 failed logins per minute for 5 minutes
**Action**: Notify security team
**Severity**: P2 - Security

#### 8. Rate Limit Violations
```yaml
displayName: "[P3] Rate Limit Violations"
conditions:
  - displayName: "429 errors > 10/minute"
    conditionThreshold:
      filter: 'resource.type="cloud_run_revision" AND "429 Too Many Requests"'
      aggregations:
        - alignmentPeriod: 60s
          perSeriesAligner: ALIGN_RATE
      comparison: COMPARISON_GT
      thresholdValue: 10
      duration: 300s
notificationChannels:
  - SLACK_CHANNEL_ID
```

**When**: > 10 rate limit violations per minute
**Action**: Log for investigation
**Severity**: P3 - Monitoring

### Business Metrics Alerts

#### 9. GCP Marketplace Webhook Failures
```yaml
displayName: "[P2] Marketplace Webhook Failures"
conditions:
  - displayName: "Webhook processing failed"
    conditionThreshold:
      filter: 'resource.type="cloud_run_revision" AND "Marketplace webhook failed"'
      aggregations:
        - alignmentPeriod: 60s
          perSeriesAligner: ALIGN_RATE
      comparison: COMPARISON_GT
      thresholdValue: 1
      duration: 60s
notificationChannels:
  - MARKETPLACE_TEAM_CHANNEL_ID
```

**When**: Any webhook failure
**Action**: Immediate investigation
**Severity**: P2 - Revenue impacting

#### 10. Low Usage (Business Warning)
```yaml
displayName: "[P4] Unusually Low Traffic"
conditions:
  - displayName: "Request rate < 10/minute"
    conditionThreshold:
      filter: 'resource.type="cloud_run_revision" metric.type="run.googleapis.com/request_count"'
      aggregations:
        - alignmentPeriod: 60s
          perSeriesAligner: ALIGN_RATE
      comparison: COMPARISON_LT
      thresholdValue: 10
      duration: 1800s
notificationChannels:
  - SLACK_CHANNEL_ID
```

**When**: Request rate drops below 10/min for 30 minutes
**Action**: Check if service is unreachable
**Severity**: P4 - Low (could indicate outage)

---

## Uptime Checks

### Backend Health Check

```bash
gcloud monitoring uptime-configs create backend-health \
  --display-name="AP2 Backend Health Check" \
  --resource-type=uptime-url \
  --monitored-resource=https://api.your-domain.com/api/v1/health \
  --check-interval=60s \
  --timeout=10s \
  --selected-regions=usa,europe,asia
```

**Configuration**:
- **Interval**: 60 seconds
- **Timeout**: 10 seconds
- **Regions**: USA, Europe, Asia (global monitoring)
- **Expected**: 200 OK with JSON body `{"status": "healthy"}`

### Frontend Uptime Check

```bash
gcloud monitoring uptime-configs create frontend-uptime \
  --display-name="AP2 Frontend Uptime Check" \
  --resource-type=uptime-url \
  --monitored-resource=https://app.your-domain.com \
  --check-interval=60s \
  --timeout=10s \
  --selected-regions=usa,europe,asia
```

**Configuration**:
- **Interval**: 60 seconds
- **Timeout**: 10 seconds
- **Regions**: USA, Europe, Asia
- **Expected**: 200 OK with HTML content

### Database Connectivity Check

```bash
# Internal check via backend endpoint
gcloud monitoring uptime-configs create database-connectivity \
  --display-name="Database Connectivity Check" \
  --resource-type=uptime-url \
  --monitored-resource=https://api.your-domain.com/api/v1/health/database \
  --check-interval=300s \
  --timeout=15s \
  --selected-regions=usa
```

**Configuration**:
- **Interval**: 5 minutes
- **Timeout**: 15 seconds
- **Expected**: 200 OK indicating successful DB connection

---

## Log-Based Metrics

### 1. Authentication Failures

```bash
gcloud logging metrics create auth_failures \
  --description="Count of authentication failures (401 errors)" \
  --log-filter='resource.type="cloud_run_revision"
    AND resource.labels.service_name="ap2-expense-backend"
    AND httpRequest.status=401
    AND jsonPayload.endpoint=~"/auth/.*"' \
  --value-extractor='EXTRACT(httpRequest.status)'
```

### 2. API Errors by Endpoint

```bash
gcloud logging metrics create api_errors_by_endpoint \
  --description="5xx errors grouped by endpoint" \
  --log-filter='resource.type="cloud_run_revision"
    AND resource.labels.service_name="ap2-expense-backend"
    AND httpRequest.status>=500
    AND httpRequest.status<600' \
  --value-extractor='EXTRACT(httpRequest.requestUrl)'
```

### 3. Slow Queries (> 1 second)

```bash
gcloud logging metrics create slow_database_queries \
  --description="Database queries taking > 1 second" \
  --log-filter='resource.type="cloud_run_revision"
    AND jsonPayload.query_duration_ms>1000' \
  --value-extractor='EXTRACT(jsonPayload.query_duration_ms)'
```

### 4. Expense Operations

```bash
gcloud logging metrics create expense_operations \
  --description="Expense CRUD operations count" \
  --log-filter='resource.type="cloud_run_revision"
    AND (jsonPayload.operation="create_expense"
      OR jsonPayload.operation="update_expense"
      OR jsonPayload.operation="delete_expense")' \
  --value-extractor='EXTRACT(jsonPayload.operation)'
```

### 5. Receipt Upload Failures

```bash
gcloud logging metrics create receipt_upload_failures \
  --description="Failed receipt uploads" \
  --log-filter='resource.type="cloud_run_revision"
    AND jsonPayload.operation="upload_receipt"
    AND jsonPayload.status="failed"' \
  --value-extractor='EXTRACT(jsonPayload.error_reason)'
```

---

## Custom Metrics

### Backend Application Metrics

Add to `backend/src/monitoring.py`:

```python
from google.cloud import monitoring_v3
from google.api_core import retry
import time

class MetricsClient:
    def __init__(self, project_id: str):
        self.client = monitoring_v3.MetricServiceClient()
        self.project_name = f"projects/{project_id}"

    def write_time_series(self, metric_type: str, value: float, labels: dict = None):
        """Write a single metric value"""
        series = monitoring_v3.TimeSeries()
        series.metric.type = f"custom.googleapis.com/{metric_type}"

        if labels:
            series.metric.labels.update(labels)

        series.resource.type = "cloud_run_revision"
        series.resource.labels["service_name"] = "ap2-expense-backend"
        series.resource.labels["location"] = "us-central1"

        point = monitoring_v3.Point()
        point.value.double_value = value
        point.interval.end_time.FromDatetime(datetime.utcnow())

        series.points = [point]

        self.client.create_time_series(
            name=self.project_name,
            time_series=[series]
        )

# Usage
metrics = MetricsClient(project_id="your-project")

# Track expense submissions
metrics.write_time_series(
    "expense/submissions",
    value=1,
    labels={"category": "meals", "organization_id": org_id}
)

# Track approval time
metrics.write_time_series(
    "expense/approval_time_seconds",
    value=approval_duration,
    labels={"organization_id": org_id}
)

# Track receipt processing time
metrics.write_time_series(
    "receipt/processing_time_ms",
    value=processing_time,
    labels={"file_type": "pdf", "file_size_kb": file_size}
)

# Track PDF export generation
metrics.write_time_series(
    "export/pdf_generation_time_ms",
    value=generation_time,
    labels={"expense_count": count}
)
```

### Custom Metric Definitions

```bash
# 1. Expense submissions per organization
gcloud logging metrics create expense_submissions_by_org \
  --description="Expense submissions grouped by organization" \
  --log-filter='resource.type="cloud_run_revision"
    AND jsonPayload.operation="create_expense"' \
  --value-extractor='EXTRACT(jsonPayload.organization_id)'

# 2. Average approval time
gcloud logging metrics create expense_approval_time \
  --description="Time from submission to approval (seconds)" \
  --log-filter='resource.type="cloud_run_revision"
    AND jsonPayload.operation="approve_expense"' \
  --value-extractor='EXTRACT(jsonPayload.approval_duration_seconds)'

# 3. Receipt OCR accuracy (if using AI)
gcloud logging metrics create receipt_ocr_accuracy \
  --description="Receipt OCR confidence scores" \
  --log-filter='resource.type="cloud_run_revision"
    AND jsonPayload.operation="process_receipt"' \
  --value-extractor='EXTRACT(jsonPayload.confidence_score)'

# 4. GCP Marketplace entitlement updates
gcloud logging metrics create marketplace_entitlement_updates \
  --description="Marketplace entitlement update events" \
  --log-filter='resource.type="cloud_run_revision"
    AND jsonPayload.event_type="ENTITLEMENT_UPDATED"' \
  --value-extractor='EXTRACT(jsonPayload.event_type)'
```

---

## Notification Channels

### Setup Notification Channels

#### 1. PagerDuty (Critical Alerts)

```bash
gcloud alpha monitoring channels create \
  --display-name="PagerDuty - On-Call" \
  --type=pagerduty \
  --channel-labels=service_key=YOUR_PAGERDUTY_SERVICE_KEY
```

**Use for**: P1 alerts that require immediate response

#### 2. Slack (Team Notifications)

```bash
gcloud alpha monitoring channels create \
  --display-name="Slack - Engineering Team" \
  --type=slack \
  --channel-labels=url=YOUR_SLACK_WEBHOOK_URL
```

**Use for**: P2-P3 alerts, general monitoring

#### 3. Email (Backup)

```bash
gcloud alpha monitoring channels create \
  --display-name="Email - Engineering Lead" \
  --type=email \
  --channel-labels=email_address=eng-lead@company.com
```

**Use for**: Backup notification channel

#### 4. SMS (Urgent Only)

```bash
gcloud alpha monitoring channels create \
  --display-name="SMS - On-Call" \
  --type=sms \
  --channel-labels=number=+15555555555
```

**Use for**: Critical failures when PagerDuty is down

### List All Channels

```bash
gcloud alpha monitoring channels list --format="table(name,type,displayName,labels)"
```

---

## Incident Response

### Alert Severity Levels

| Priority | Response Time | Notification           | Examples                              |
|----------|--------------|------------------------|---------------------------------------|
| **P1**   | 15 minutes   | PagerDuty + SMS        | Service down, data loss, security breach |
| **P2**   | 1 hour       | Slack + Email          | High latency, DB CPU high, webhook failures |
| **P3**   | 4 hours      | Slack                  | Elevated errors, slow queries        |
| **P4**   | Next business day | Email              | Low traffic, minor warnings          |

### On-Call Rotation

```bash
# Configure on-call rotation (example structure)
Week 1: Engineer A
Week 2: Engineer B
Week 3: Engineer C
Backup: Engineering Lead
```

### Incident Response Runbooks

#### P1: Service Down

1. **Acknowledge**: Acknowledge PagerDuty alert immediately
2. **Assess**: Check Cloud Monitoring dashboard
3. **Communicate**: Post incident in #incidents Slack channel
4. **Investigate**:
   - Check Cloud Run logs: `gcloud logging read --limit=50 --format=json`
   - Check recent deployments: `gcloud run revisions list`
   - Check database health: Cloud SQL dashboard
5. **Mitigate**:
   - If recent deployment: Rollback (`./scripts/rollback-deployment.sh`)
   - If database issue: Scale up or check connections
   - If Cloud Run issue: Restart service or scale up
6. **Resolve**: Verify health checks pass
7. **Post-Mortem**: Document incident within 24 hours

#### P2: High Latency

1. **Investigate**:
   - Check Cloud Trace for slow requests
   - Check database query performance
   - Check Cloud Run instance count
2. **Mitigate**:
   - Scale Cloud Run instances if needed
   - Optimize slow queries
   - Enable caching if applicable
3. **Monitor**: Watch for improvement over next hour

#### P2: Database CPU High

1. **Investigate**:
   - Check `pg_stat_statements` for slow queries
   - Check connection count
   - Check for long-running transactions
2. **Mitigate**:
   - Kill long-running queries if safe
   - Optimize slow queries
   - Scale database if needed
3. **Long-term**: Add indexes, optimize queries, consider read replicas

---

## Setup Script

Save as `scripts/setup-monitoring.sh`:

```bash
#!/bin/bash
set -e

echo "Setting up monitoring & alerts for AP2 Expense Management..."

PROJECT_ID=${GCP_PROJECT_ID}
REGION="us-central1"

# Create notification channels
echo "Creating notification channels..."

PAGERDUTY_CHANNEL=$(gcloud alpha monitoring channels create \
  --display-name="PagerDuty - On-Call" \
  --type=pagerduty \
  --channel-labels=service_key=${PAGERDUTY_SERVICE_KEY} \
  --format='value(name)')

SLACK_CHANNEL=$(gcloud alpha monitoring channels create \
  --display-name="Slack - Engineering" \
  --type=slack \
  --channel-labels=url=${SLACK_WEBHOOK_URL} \
  --format='value(name)')

echo "✅ Notification channels created"

# Create uptime checks
echo "Creating uptime checks..."

gcloud monitoring uptime-configs create backend-health \
  --display-name="Backend Health Check" \
  --resource-type=uptime-url \
  --monitored-resource=${BACKEND_URL}/api/v1/health \
  --check-interval=60s \
  --timeout=10s

gcloud monitoring uptime-configs create frontend-uptime \
  --display-name="Frontend Uptime Check" \
  --resource-type=uptime-url \
  --monitored-resource=${FRONTEND_URL} \
  --check-interval=60s \
  --timeout=10s

echo "✅ Uptime checks created"

# Create log-based metrics
echo "Creating log-based metrics..."

gcloud logging metrics create auth_failures \
  --description="Authentication failures" \
  --log-filter='resource.type="cloud_run_revision" AND httpRequest.status=401'

gcloud logging metrics create slow_queries \
  --description="Slow database queries" \
  --log-filter='resource.type="cloud_run_revision" AND jsonPayload.query_duration_ms>1000'

echo "✅ Log-based metrics created"

# Create alerting policies
echo "Creating alerting policies..."

# Service down alert
gcloud alpha monitoring policies create \
  --notification-channels=${PAGERDUTY_CHANNEL} \
  --display-name="[P1] Service Down" \
  --condition-display-name="Health check failing" \
  --condition-threshold-value=0 \
  --condition-threshold-duration=180s \
  --condition-threshold-filter='resource.type="uptime_url"' \
  --condition-threshold-comparison=COMPARISON_LT

# High error rate alert
gcloud alpha monitoring policies create \
  --notification-channels=${PAGERDUTY_CHANNEL},${SLACK_CHANNEL} \
  --display-name="[P1] High Error Rate" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=0.05 \
  --condition-threshold-duration=300s

echo "✅ Alerting policies created"

echo ""
echo "====================================="
echo "Monitoring & Alerts Setup Complete!"
echo "====================================="
echo ""
echo "PagerDuty Channel: ${PAGERDUTY_CHANNEL}"
echo "Slack Channel: ${SLACK_CHANNEL}"
echo ""
echo "Next steps:"
echo "1. Test uptime checks: gcloud monitoring uptime-configs list"
echo "2. View dashboards: https://console.cloud.google.com/monitoring/dashboards"
echo "3. Test alerts: Trigger a test failure"
echo ""
```

Run with:
```bash
export PAGERDUTY_SERVICE_KEY="your-key"
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
export BACKEND_URL="https://api.your-domain.com"
export FRONTEND_URL="https://app.your-domain.com"

chmod +x scripts/setup-monitoring.sh
./scripts/setup-monitoring.sh
```

---

## Monitoring Cost Optimization

### Best Practices

1. **Use sampling for high-volume metrics**
   - Sample 10% of requests for detailed tracing
   - Aggregate metrics at 1-minute intervals instead of real-time

2. **Set log retention appropriately**
   - Keep 30 days in Cloud Logging
   - Archive to Cloud Storage for long-term retention

3. **Use log exclusions**
   - Exclude health check logs from storage
   - Exclude DEBUG logs in production

4. **Optimize uptime checks**
   - Don't check every endpoint - use key endpoints only
   - Use longer intervals for non-critical checks (5 min vs 1 min)

### Example Log Exclusion (Health Checks)

```bash
gcloud logging exclusions create health-check-exclusion \
  --log-filter='resource.type="cloud_run_revision" AND httpRequest.requestUrl=~"/health"' \
  --description="Exclude health check logs to reduce costs"
```

---

**Last Updated**: December 23, 2025
**Owner**: DevOps Team
**Review Frequency**: Quarterly
