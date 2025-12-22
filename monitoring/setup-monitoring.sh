#!/bin/bash
# Setup Google Cloud Monitoring for AP2 Expense Agent
# Usage: ./setup-monitoring.sh PROJECT_ID

set -e

PROJECT_ID="${1:-YOUR_PROJECT_ID}"
NOTIFICATION_EMAIL="${2:-your-email@example.com}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up monitoring for AP2 Expense Agent${NC}"
echo -e "Project ID: ${YELLOW}${PROJECT_ID}${NC}"
echo -e "Notification Email: ${YELLOW}${NOTIFICATION_EMAIL}${NC}"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${YELLOW}Error: gcloud CLI not found. Please install it first.${NC}"
    exit 1
fi

# Set project
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo -e "${GREEN}[1/5] Enabling required APIs...${NC}"
gcloud services enable \
    monitoring.googleapis.com \
    logging.googleapis.com \
    cloudtrace.googleapis.com \
    cloudprofiler.googleapis.com

# Create notification channel
echo -e "${GREEN}[2/5] Creating notification channel...${NC}"
CHANNEL_ID=$(gcloud alpha monitoring channels create \
    --display-name="AP2 Expense Alerts" \
    --type=email \
    --channel-labels=email_address=${NOTIFICATION_EMAIL} \
    --format="value(name)" | sed 's/.*\///')

echo -e "Notification channel created: ${YELLOW}${CHANNEL_ID}${NC}"

# Upload dashboards
echo -e "${GREEN}[3/5] Creating monitoring dashboards...${NC}"

# Main dashboard
gcloud monitoring dashboards create --config-from-file=dashboards/main-dashboard.json || \
    echo "Main dashboard might already exist, skipping..."

# Billing dashboard
gcloud monitoring dashboards create --config-from-file=dashboards/billing-dashboard.json || \
    echo "Billing dashboard might already exist, skipping..."

echo -e "${GREEN}Dashboards created successfully${NC}"

# Create alert policies
echo -e "${GREEN}[4/5] Creating alert policies...${NC}"

# Replace placeholders in alert policies
sed -i.bak "s/YOUR_PROJECT_ID/${PROJECT_ID}/g" alerts/alert-policies.yaml
sed -i.bak "s/YOUR_CHANNEL_ID/${CHANNEL_ID}/g" alerts/alert-policies.yaml

# Note: gcloud alpha monitoring policies create doesn't support YAML directly
# We'll need to create them via API or manually
echo -e "${YELLOW}Note: Alert policies need to be created manually or via API${NC}"
echo -e "Template file ready at: alerts/alert-policies.yaml"
echo -e "Replace YOUR_CHANNEL_ID with: ${CHANNEL_ID}"

# Create uptime checks
echo -e "${GREEN}[5/5] Creating uptime checks...${NC}"

gcloud monitoring uptime create \
    --display-name="AP2 Expense - Backend Health" \
    --resource-type=uptime-url \
    --host=your-domain.com \
    --path=/health \
    --timeout=10s \
    --period=5m \
    --selected-regions=ASIA_PACIFIC,EUROPE,USA || \
    echo "Uptime check might already exist, skipping..."

gcloud monitoring uptime create \
    --display-name="AP2 Expense - Frontend Health" \
    --resource-type=uptime-url \
    --host=your-domain.com \
    --path=/ \
    --timeout=10s \
    --period=5m \
    --selected-regions=ASIA_PACIFIC,EUROPE,USA || \
    echo "Frontend uptime check might already exist, skipping..."

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Monitoring setup completed!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Next steps:"
echo -e "1. View dashboards: ${YELLOW}https://console.cloud.google.com/monitoring/dashboards${NC}"
echo -e "2. Configure alert policies: ${YELLOW}https://console.cloud.google.com/monitoring/alerting${NC}"
echo -e "3. Test notifications: ${YELLOW}gcloud alpha monitoring channels test ${CHANNEL_ID}${NC}"
echo -e "4. Update domain in uptime checks"
echo ""
echo -e "Notification channel ID: ${YELLOW}${CHANNEL_ID}${NC}"
echo -e "Save this ID for reference!"
