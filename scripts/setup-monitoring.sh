#!/bin/bash
#
# Monitoring & Alerts Setup Script
# Sets up Cloud Monitoring, Uptime Checks, Log Metrics, and Alerting Policies
#
# Usage: ./scripts/setup-monitoring.sh [environment]
#   environment: staging | production (default: staging)
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-staging}
PROJECT_ID=${GCP_PROJECT_ID}
REGION=${GCP_REGION:-us-central1}

# URLs based on environment
if [ "$ENVIRONMENT" = "production" ]; then
    BACKEND_URL=${PRODUCTION_BACKEND_URL}
    FRONTEND_URL=${PRODUCTION_FRONTEND_URL}
else
    BACKEND_URL=${STAGING_BACKEND_URL:-"https://staging-backend.example.com"}
    FRONTEND_URL=${STAGING_FRONTEND_URL:-"https://staging-frontend.example.com"}
fi

# Function to print step headers
print_step() {
    echo -e "\n${BLUE}>>> $1${NC}\n"
}

# Function to print success messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print warnings
print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Function to print errors
print_error() {
    echo -e "${RED}✗ $1${NC}"
}

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  AP2 Expense - Monitoring Setup${NC}"
echo -e "${BLUE}  Environment: ${ENVIRONMENT}${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Validate required environment variables
print_step "Step 1: Validating environment variables"

if [ -z "$PROJECT_ID" ]; then
    print_error "GCP_PROJECT_ID is not set"
    echo "Export GCP_PROJECT_ID before running this script"
    exit 1
fi

if [ -z "$BACKEND_URL" ]; then
    print_warning "Backend URL not set, using example URL"
fi

if [ -z "$FRONTEND_URL" ]; then
    print_warning "Frontend URL not set, using example URL"
fi

print_success "Environment variables validated"

# Set GCP project
print_step "Step 2: Setting GCP project"
gcloud config set project ${PROJECT_ID}
print_success "Project set to ${PROJECT_ID}"

# Create notification channels
print_step "Step 3: Creating notification channels"

# Check if SLACK_WEBHOOK_URL is set
if [ -n "$SLACK_WEBHOOK_URL" ]; then
    echo "Creating Slack notification channel..."
    SLACK_CHANNEL=$(gcloud alpha monitoring channels create \
        --display-name="Slack - AP2 Engineering (${ENVIRONMENT})" \
        --type=slack \
        --channel-labels=url="${SLACK_WEBHOOK_URL}" \
        --format='value(name)' 2>/dev/null || echo "")

    if [ -n "$SLACK_CHANNEL" ]; then
        print_success "Slack channel created: ${SLACK_CHANNEL}"
    else
        print_warning "Slack channel already exists or failed to create"
        # Get existing channel
        SLACK_CHANNEL=$(gcloud alpha monitoring channels list \
            --filter="displayName:'Slack - AP2 Engineering (${ENVIRONMENT})'" \
            --format='value(name)' | head -n 1)
    fi
else
    print_warning "SLACK_WEBHOOK_URL not set, skipping Slack channel creation"
    SLACK_CHANNEL=""
fi

# Check if PAGERDUTY_SERVICE_KEY is set
if [ -n "$PAGERDUTY_SERVICE_KEY" ]; then
    echo "Creating PagerDuty notification channel..."
    PAGERDUTY_CHANNEL=$(gcloud alpha monitoring channels create \
        --display-name="PagerDuty - On-Call (${ENVIRONMENT})" \
        --type=pagerduty \
        --channel-labels=service_key="${PAGERDUTY_SERVICE_KEY}" \
        --format='value(name)' 2>/dev/null || echo "")

    if [ -n "$PAGERDUTY_CHANNEL" ]; then
        print_success "PagerDuty channel created: ${PAGERDUTY_CHANNEL}"
    else
        print_warning "PagerDuty channel already exists or failed to create"
        PAGERDUTY_CHANNEL=$(gcloud alpha monitoring channels list \
            --filter="displayName:'PagerDuty - On-Call (${ENVIRONMENT})'" \
            --format='value(name)' | head -n 1)
    fi
else
    print_warning "PAGERDUTY_SERVICE_KEY not set, skipping PagerDuty channel creation"
    PAGERDUTY_CHANNEL=""
fi

# Create email notification channel
if [ -n "$ALERT_EMAIL" ]; then
    echo "Creating email notification channel..."
    EMAIL_CHANNEL=$(gcloud alpha monitoring channels create \
        --display-name="Email - Engineering Lead (${ENVIRONMENT})" \
        --type=email \
        --channel-labels=email_address="${ALERT_EMAIL}" \
        --format='value(name)' 2>/dev/null || echo "")

    if [ -n "$EMAIL_CHANNEL" ]; then
        print_success "Email channel created: ${EMAIL_CHANNEL}"
    else
        print_warning "Email channel already exists or failed to create"
        EMAIL_CHANNEL=$(gcloud alpha monitoring channels list \
            --filter="displayName:'Email - Engineering Lead (${ENVIRONMENT})'" \
            --format='value(name)' | head -n 1)
    fi
else
    print_warning "ALERT_EMAIL not set, skipping email channel creation"
    EMAIL_CHANNEL=""
fi

# Create uptime checks
print_step "Step 4: Creating uptime checks"

if [ "$BACKEND_URL" != "https://staging-backend.example.com" ]; then
    echo "Creating backend health check..."
    gcloud monitoring uptime-configs create "ap2-backend-health-${ENVIRONMENT}" \
        --display-name="AP2 Backend Health (${ENVIRONMENT})" \
        --resource-type=uptime-url \
        --monitored-resource="${BACKEND_URL}/api/v1/health" \
        --check-interval=60s \
        --timeout=10s \
        --selected-regions=usa,europe,asia 2>/dev/null || \
        print_warning "Backend uptime check already exists"

    print_success "Backend uptime check configured"
else
    print_warning "Skipping backend uptime check (URL not configured)"
fi

if [ "$FRONTEND_URL" != "https://staging-frontend.example.com" ]; then
    echo "Creating frontend uptime check..."
    gcloud monitoring uptime-configs create "ap2-frontend-uptime-${ENVIRONMENT}" \
        --display-name="AP2 Frontend Uptime (${ENVIRONMENT})" \
        --resource-type=uptime-url \
        --monitored-resource="${FRONTEND_URL}" \
        --check-interval=60s \
        --timeout=10s \
        --selected-regions=usa,europe,asia 2>/dev/null || \
        print_warning "Frontend uptime check already exists"

    print_success "Frontend uptime check configured"
else
    print_warning "Skipping frontend uptime check (URL not configured)"
fi

# Create log-based metrics
print_step "Step 5: Creating log-based metrics"

echo "Creating authentication failures metric..."
gcloud logging metrics create "auth_failures_${ENVIRONMENT}" \
    --description="Count of authentication failures (401 errors) in ${ENVIRONMENT}" \
    --log-filter="resource.type=\"cloud_run_revision\"
        AND resource.labels.service_name=\"ap2-expense-backend-${ENVIRONMENT}\"
        AND httpRequest.status=401
        AND jsonPayload.endpoint=~\"/auth/.*\"" 2>/dev/null || \
    print_warning "auth_failures metric already exists"

echo "Creating API errors metric..."
gcloud logging metrics create "api_errors_${ENVIRONMENT}" \
    --description="5xx errors in ${ENVIRONMENT}" \
    --log-filter="resource.type=\"cloud_run_revision\"
        AND resource.labels.service_name=\"ap2-expense-backend-${ENVIRONMENT}\"
        AND httpRequest.status>=500
        AND httpRequest.status<600" 2>/dev/null || \
    print_warning "api_errors metric already exists"

echo "Creating slow queries metric..."
gcloud logging metrics create "slow_queries_${ENVIRONMENT}" \
    --description="Database queries taking > 1 second in ${ENVIRONMENT}" \
    --log-filter="resource.type=\"cloud_run_revision\"
        AND resource.labels.service_name=\"ap2-expense-backend-${ENVIRONMENT}\"
        AND jsonPayload.query_duration_ms>1000" 2>/dev/null || \
    print_warning "slow_queries metric already exists"

print_success "Log-based metrics created"

# Create alerting policies
print_step "Step 6: Creating alerting policies"

# Prepare notification channels list
NOTIFICATION_CHANNELS=""
if [ -n "$PAGERDUTY_CHANNEL" ]; then
    NOTIFICATION_CHANNELS="${PAGERDUTY_CHANNEL}"
fi
if [ -n "$SLACK_CHANNEL" ]; then
    if [ -n "$NOTIFICATION_CHANNELS" ]; then
        NOTIFICATION_CHANNELS="${NOTIFICATION_CHANNELS},${SLACK_CHANNEL}"
    else
        NOTIFICATION_CHANNELS="${SLACK_CHANNEL}"
    fi
fi
if [ -n "$EMAIL_CHANNEL" ]; then
    if [ -n "$NOTIFICATION_CHANNELS" ]; then
        NOTIFICATION_CHANNELS="${NOTIFICATION_CHANNELS},${EMAIL_CHANNEL}"
    else
        NOTIFICATION_CHANNELS="${EMAIL_CHANNEL}"
    fi
fi

if [ -z "$NOTIFICATION_CHANNELS" ]; then
    print_warning "No notification channels configured, skipping alert creation"
    print_warning "Set SLACK_WEBHOOK_URL, PAGERDUTY_SERVICE_KEY, or ALERT_EMAIL to enable alerts"
else
    echo "Creating high error rate alert..."
    gcloud alpha monitoring policies create \
        --notification-channels="${NOTIFICATION_CHANNELS}" \
        --display-name="[P1] High Error Rate - ${ENVIRONMENT}" \
        --condition-display-name="Error rate > 5%" \
        --condition-threshold-value=0.05 \
        --condition-threshold-duration=300s \
        --condition-threshold-filter="resource.type=\"cloud_run_revision\"
            resource.labels.service_name=\"ap2-expense-backend-${ENVIRONMENT}\"
            metric.type=\"run.googleapis.com/request_count\"
            metric.response_code_class=\"5xx\"" \
        --condition-threshold-comparison=COMPARISON_GT 2>/dev/null || \
        print_warning "High error rate alert already exists"

    echo "Creating high latency alert..."
    gcloud alpha monitoring policies create \
        --notification-channels="${SLACK_CHANNEL}" \
        --display-name="[P2] High Latency - ${ENVIRONMENT}" \
        --condition-display-name="p95 latency > 1000ms" \
        --condition-threshold-value=1000 \
        --condition-threshold-duration=600s \
        --condition-threshold-filter="resource.type=\"cloud_run_revision\"
            resource.labels.service_name=\"ap2-expense-backend-${ENVIRONMENT}\"
            metric.type=\"run.googleapis.com/request_latencies\"" \
        --condition-threshold-comparison=COMPARISON_GT 2>/dev/null || \
        print_warning "High latency alert already exists"

    print_success "Alerting policies created"
fi

# Summary
print_step "Setup Complete!"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Monitoring Setup Summary${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Environment: ${BLUE}${ENVIRONMENT}${NC}"
echo -e "Project: ${BLUE}${PROJECT_ID}${NC}"
echo ""
echo -e "Notification Channels:"
if [ -n "$SLACK_CHANNEL" ]; then
    echo -e "  ✓ Slack: ${SLACK_CHANNEL}"
fi
if [ -n "$PAGERDUTY_CHANNEL" ]; then
    echo -e "  ✓ PagerDuty: ${PAGERDUTY_CHANNEL}"
fi
if [ -n "$EMAIL_CHANNEL" ]; then
    echo -e "  ✓ Email: ${EMAIL_CHANNEL}"
fi
echo ""
echo -e "Uptime Checks:"
echo -e "  ✓ Backend: ${BACKEND_URL}/api/v1/health"
echo -e "  ✓ Frontend: ${FRONTEND_URL}"
echo ""
echo -e "Log-Based Metrics:"
echo -e "  ✓ auth_failures_${ENVIRONMENT}"
echo -e "  ✓ api_errors_${ENVIRONMENT}"
echo -e "  ✓ slow_queries_${ENVIRONMENT}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. View uptime checks: gcloud monitoring uptime-configs list"
echo "2. View dashboards: https://console.cloud.google.com/monitoring/dashboards"
echo "3. View alerts: https://console.cloud.google.com/monitoring/alerting/policies"
echo "4. Test alerts by triggering a failure"
echo ""
echo -e "${GREEN}Monitoring setup successful! 🎉${NC}"
