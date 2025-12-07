#!/bin/bash
# Setup Cloud Monitoring alerts for GCP Marketplace webhook failures
#
# This script creates:
# 1. Log-based metrics for webhook failures
# 2. Alert policies for critical webhook errors
# 3. Notification channels for alerts
#
# Usage: ./scripts/setup-monitoring-alerts.sh <project-id> <notification-email>
# Example: ./scripts/setup-monitoring-alerts.sh my-project ops@example.com

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Validate arguments
if [ "$#" -ne 2 ]; then
    echo -e "${RED}Error: Invalid arguments${NC}"
    echo "Usage: $0 <project-id> <notification-email>"
    echo "Example: $0 my-project ops@example.com"
    exit 1
fi

PROJECT_ID=$1
NOTIFICATION_EMAIL=$2

echo -e "${GREEN}Setting up Cloud Monitoring for GCP Marketplace webhooks${NC}"
echo "Project: $PROJECT_ID"
echo "Notification Email: $NOTIFICATION_EMAIL"
echo ""

# Set the project
gcloud config set project "$PROJECT_ID"

# Enable required APIs
echo -e "${YELLOW}Enabling required APIs...${NC}"
gcloud services enable monitoring.googleapis.com
gcloud services enable logging.googleapis.com

echo ""
echo -e "${GREEN}Step 1: Creating Log-Based Metrics${NC}"
echo ""

# Metric 1: GCP Webhook Authentication Failures
METRIC_NAME_AUTH="gcp_webhook_auth_failures"
echo -e "${YELLOW}Creating metric: $METRIC_NAME_AUTH${NC}"

gcloud logging metrics delete "$METRIC_NAME_AUTH" --project="$PROJECT_ID" --quiet 2>/dev/null || true

gcloud logging metrics create "$METRIC_NAME_AUTH" \
    --description="Count of GCP Marketplace webhook authentication failures" \
    --log-filter='
        resource.type="cloud_run_revision"
        severity>=ERROR
        (jsonPayload.message=~"webhook signature verification failed" OR
         jsonPayload.message=~"OIDC token verification failed" OR
         jsonPayload.message=~"Unauthorized webhook request" OR
         httpRequest.status=403)
        labels."gcp-webhooks"="true"
    ' \
    --value-extractor="" \
    --metric-kind=DELTA \
    --value-type=INT64 \
    --project="$PROJECT_ID"

echo -e "${GREEN}✓ Created metric: $METRIC_NAME_AUTH${NC}"

# Metric 2: GCP Webhook Processing Failures
METRIC_NAME_PROCESSING="gcp_webhook_processing_failures"
echo -e "${YELLOW}Creating metric: $METRIC_NAME_PROCESSING${NC}"

gcloud logging metrics delete "$METRIC_NAME_PROCESSING" --project="$PROJECT_ID" --quiet 2>/dev/null || true

gcloud logging metrics create "$METRIC_NAME_PROCESSING" \
    --description="Count of GCP Marketplace webhook processing failures" \
    --log-filter='
        resource.type="cloud_run_revision"
        severity>=ERROR
        (jsonPayload.message=~"Failed to process procurement" OR
         jsonPayload.message=~"Failed to process entitlement" OR
         jsonPayload.message=~"Failed to process cancellation" OR
         jsonPayload.message=~"Failed to report usage")
        labels."gcp-webhooks"="true"
    ' \
    --value-extractor="" \
    --metric-kind=DELTA \
    --value-type=INT64 \
    --project="$PROJECT_ID"

echo -e "${GREEN}✓ Created metric: $METRIC_NAME_PROCESSING${NC}"

# Metric 3: Usage Reporting Failures
METRIC_NAME_USAGE="gcp_usage_reporting_failures"
echo -e "${YELLOW}Creating metric: $METRIC_NAME_USAGE${NC}"

gcloud logging metrics delete "$METRIC_NAME_USAGE" --project="$PROJECT_ID" --quiet 2>/dev/null || true

gcloud logging metrics create "$METRIC_NAME_USAGE" \
    --description="Count of GCP Marketplace usage reporting failures" \
    --log-filter='
        resource.type="cloud_run_revision"
        severity>=ERROR
        (jsonPayload.message=~"Failed to report usage" OR
         jsonPayload.message=~"Usage reporting error")
        resource.labels.service_name="ap2-expense-backend"
    ' \
    --value-extractor="" \
    --metric-kind=DELTA \
    --value-type=INT64 \
    --project="$PROJECT_ID"

echo -e "${GREEN}✓ Created metric: $METRIC_NAME_USAGE${NC}"

echo ""
echo -e "${GREEN}Step 2: Creating Notification Channel${NC}"
echo ""

# Create email notification channel
CHANNEL_NAME="gcp-marketplace-alerts"
echo -e "${YELLOW}Creating notification channel: $CHANNEL_NAME${NC}"

# Create notification channel using gcloud (v2 API)
CHANNEL_ID=$(gcloud alpha monitoring channels create \
    --display-name="$CHANNEL_NAME" \
    --type=email \
    --channel-labels=email_address="$NOTIFICATION_EMAIL" \
    --project="$PROJECT_ID" \
    --format="value(name)")

echo -e "${GREEN}✓ Created notification channel: $CHANNEL_ID${NC}"

echo ""
echo -e "${GREEN}Step 3: Creating Alert Policies${NC}"
echo ""

# Alert 1: Webhook Authentication Failures
ALERT_NAME_AUTH="GCP Marketplace Webhook Authentication Failures"
echo -e "${YELLOW}Creating alert: $ALERT_NAME_AUTH${NC}"

cat > /tmp/alert-webhook-auth.json <<EOF
{
  "displayName": "$ALERT_NAME_AUTH",
  "documentation": {
    "content": "Multiple GCP Marketplace webhook authentication failures detected. This indicates:\n- Invalid OIDC tokens from Google\n- Signature verification failures\n- Potential security issue or misconfiguration\n\nAction: Check Cloud Run logs for details and verify GCP_WEBHOOK_AUDIENCE configuration.",
    "mimeType": "text/markdown"
  },
  "conditions": [
    {
      "displayName": "Webhook auth failures > 5 in 5 minutes",
      "conditionThreshold": {
        "filter": "resource.type=\"cloud_run_revision\" AND metric.type=\"logging.googleapis.com/user/$METRIC_NAME_AUTH\"",
        "comparison": "COMPARISON_GT",
        "thresholdValue": 5,
        "duration": "300s",
        "aggregations": [
          {
            "alignmentPeriod": "300s",
            "perSeriesAligner": "ALIGN_SUM"
          }
        ]
      }
    }
  ],
  "combiner": "OR",
  "enabled": true,
  "notificationChannels": ["$CHANNEL_ID"],
  "alertStrategy": {
    "autoClose": "1800s"
  },
  "severity": "CRITICAL"
}
EOF

gcloud alpha monitoring policies create --policy-from-file=/tmp/alert-webhook-auth.json --project="$PROJECT_ID"
echo -e "${GREEN}✓ Created alert: $ALERT_NAME_AUTH${NC}"

# Alert 2: Webhook Processing Failures
ALERT_NAME_PROCESSING="GCP Marketplace Webhook Processing Failures"
echo -e "${YELLOW}Creating alert: $ALERT_NAME_PROCESSING${NC}"

cat > /tmp/alert-webhook-processing.json <<EOF
{
  "displayName": "$ALERT_NAME_PROCESSING",
  "documentation": {
    "content": "Multiple GCP Marketplace webhook processing failures detected. This may indicate:\n- Database connection issues\n- Invalid payload format\n- Application logic errors\n- Billing integration problems\n\nAction: Check Cloud Run logs and database connectivity. Review recent webhook payloads.",
    "mimeType": "text/markdown"
  },
  "conditions": [
    {
      "displayName": "Webhook processing failures > 3 in 10 minutes",
      "conditionThreshold": {
        "filter": "resource.type=\"cloud_run_revision\" AND metric.type=\"logging.googleapis.com/user/$METRIC_NAME_PROCESSING\"",
        "comparison": "COMPARISON_GT",
        "thresholdValue": 3,
        "duration": "600s",
        "aggregations": [
          {
            "alignmentPeriod": "600s",
            "perSeriesAligner": "ALIGN_SUM"
          }
        ]
      }
    }
  ],
  "combiner": "OR",
  "enabled": true,
  "notificationChannels": ["$CHANNEL_ID"],
  "alertStrategy": {
    "autoClose": "3600s"
  },
  "severity": "ERROR"
}
EOF

gcloud alpha monitoring policies create --policy-from-file=/tmp/alert-webhook-processing.json --project="$PROJECT_ID"
echo -e "${GREEN}✓ Created alert: $ALERT_NAME_PROCESSING${NC}"

# Alert 3: Usage Reporting Failures
ALERT_NAME_USAGE="GCP Marketplace Usage Reporting Failures"
echo -e "${YELLOW}Creating alert: $ALERT_NAME_USAGE${NC}"

cat > /tmp/alert-usage-reporting.json <<EOF
{
  "displayName": "$ALERT_NAME_USAGE",
  "documentation": {
    "content": "Usage reporting to GCP Marketplace is failing. This will affect customer billing!\n\nThis indicates:\n- GCP API connectivity issues\n- Invalid service account credentials\n- Incorrect entitlement IDs\n- Rate limiting from GCP\n\nAction: URGENT - Check service account permissions and GCP API status. Verify usage reporting endpoint logs.",
    "mimeType": "text/markdown"
  },
  "conditions": [
    {
      "displayName": "Usage reporting failures > 2 consecutive hours",
      "conditionThreshold": {
        "filter": "resource.type=\"cloud_run_revision\" AND metric.type=\"logging.googleapis.com/user/$METRIC_NAME_USAGE\"",
        "comparison": "COMPARISON_GT",
        "thresholdValue": 2,
        "duration": "7200s",
        "aggregations": [
          {
            "alignmentPeriod": "3600s",
            "perSeriesAligner": "ALIGN_SUM"
          }
        ]
      }
    }
  ],
  "combiner": "OR",
  "enabled": true,
  "notificationChannels": ["$CHANNEL_ID"],
  "alertStrategy": {
    "autoClose": "7200s"
  },
  "severity": "CRITICAL"
}
EOF

gcloud alpha monitoring policies create --policy-from-file=/tmp/alert-usage-reporting.json --project="$PROJECT_ID"
echo -e "${GREEN}✓ Created alert: $ALERT_NAME_USAGE${NC}"

# Cleanup temp files
rm -f /tmp/alert-*.json

echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "Created Resources:"
echo "- 3 log-based metrics for webhook monitoring"
echo "- 1 email notification channel ($NOTIFICATION_EMAIL)"
echo "- 3 alert policies for critical failures"
echo ""
echo "Alert Policies:"
echo "1. $ALERT_NAME_AUTH (> 5 failures in 5 min)"
echo "2. $ALERT_NAME_PROCESSING (> 3 failures in 10 min)"
echo "3. $ALERT_NAME_USAGE (> 2 failures in 2 hours)"
echo ""
echo "Next steps:"
echo "1. View metrics: https://console.cloud.google.com/logs/metrics?project=$PROJECT_ID"
echo "2. View alerts: https://console.cloud.google.com/monitoring/alerting?project=$PROJECT_ID"
echo "3. Test alert: Trigger a webhook failure and verify email notification"
echo "4. Add additional notification channels (PagerDuty, Slack, etc.) via Console"
echo ""
echo -e "${YELLOW}Important:${NC}"
echo "- Alerts will trigger email notifications to: $NOTIFICATION_EMAIL"
echo "- Usage reporting failures are CRITICAL and affect billing"
echo "- Alert policies have auto-close windows to prevent alert fatigue"
echo "- Review and adjust thresholds based on production traffic patterns"
