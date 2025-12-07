#!/bin/bash
# Setup Google Cloud Scheduler jobs for GCP Marketplace integration
#
# This script creates the necessary Cloud Scheduler jobs for:
# 1. Hourly usage reporting to GCP Marketplace
# 2. Daily trial expiration processing
#
# Usage: ./scripts/setup-cloud-scheduler.sh <project-id> <region> <backend-url>
# Example: ./scripts/setup-cloud-scheduler.sh my-project us-central1 https://ap2-expense-backend-xyz-uc.a.run.app

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Validate arguments
if [ "$#" -ne 3 ]; then
    echo -e "${RED}Error: Invalid arguments${NC}"
    echo "Usage: $0 <project-id> <region> <backend-url>"
    echo "Example: $0 my-project us-central1 https://ap2-expense-backend-xyz-uc.a.run.app"
    exit 1
fi

PROJECT_ID=$1
REGION=$2
BACKEND_URL=$3

# Remove trailing slash from URL if present
BACKEND_URL=${BACKEND_URL%/}

echo -e "${GREEN}Setting up Cloud Scheduler jobs for GCP Marketplace${NC}"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Backend URL: $BACKEND_URL"
echo ""

# Set the project
gcloud config set project "$PROJECT_ID"

# Enable Cloud Scheduler API if not already enabled
echo -e "${YELLOW}Enabling Cloud Scheduler API...${NC}"
gcloud services enable cloudscheduler.googleapis.com

# Create service account for Cloud Scheduler if it doesn't exist
SA_NAME="cloud-scheduler-sa"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

if gcloud iam service-accounts describe "$SA_EMAIL" --project="$PROJECT_ID" &>/dev/null; then
    echo -e "${GREEN}Service account $SA_EMAIL already exists${NC}"
else
    echo -e "${YELLOW}Creating service account for Cloud Scheduler...${NC}"
    gcloud iam service-accounts create "$SA_NAME" \
        --display-name="Cloud Scheduler Service Account" \
        --project="$PROJECT_ID"
fi

# Grant Cloud Run Invoker role to the service account
echo -e "${YELLOW}Granting Cloud Run Invoker role...${NC}"
gcloud run services add-iam-policy-binding ap2-expense-backend \
    --region="$REGION" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/run.invoker" \
    --platform=managed \
    --project="$PROJECT_ID" || true

echo ""
echo -e "${GREEN}Creating Cloud Scheduler Jobs${NC}"
echo ""

# Job 1: Hourly Usage Reporting to GCP Marketplace
JOB_NAME_USAGE="gcp-marketplace-usage-reporting"
echo -e "${YELLOW}Creating job: $JOB_NAME_USAGE${NC}"

# Delete existing job if it exists
gcloud scheduler jobs delete "$JOB_NAME_USAGE" \
    --location="$REGION" \
    --project="$PROJECT_ID" \
    --quiet 2>/dev/null || true

# Create the hourly usage reporting job
gcloud scheduler jobs create http "$JOB_NAME_USAGE" \
    --location="$REGION" \
    --schedule="0 * * * *" \
    --time-zone="UTC" \
    --uri="${BACKEND_URL}/api/webhooks/gcp/report-usage" \
    --http-method=POST \
    --oidc-service-account-email="$SA_EMAIL" \
    --oidc-token-audience="${BACKEND_URL}" \
    --headers="Content-Type=application/json,X-CloudScheduler=true" \
    --max-retry-attempts=3 \
    --min-backoff=5s \
    --max-backoff=3600s \
    --max-doublings=5 \
    --attempt-deadline=300s \
    --description="Hourly usage reporting to GCP Marketplace for billing" \
    --project="$PROJECT_ID"

echo -e "${GREEN}✓ Created: $JOB_NAME_USAGE (runs every hour at :00)${NC}"
echo ""

# Job 2: Daily Trial Processing
JOB_NAME_TRIALS="gcp-marketplace-trial-processing"
echo -e "${YELLOW}Creating job: $JOB_NAME_TRIALS${NC}"

# Delete existing job if it exists
gcloud scheduler jobs delete "$JOB_NAME_TRIALS" \
    --location="$REGION" \
    --project="$PROJECT_ID" \
    --quiet 2>/dev/null || true

# Create the daily trial processing job (runs at 2 AM UTC)
gcloud scheduler jobs create http "$JOB_NAME_TRIALS" \
    --location="$REGION" \
    --schedule="0 2 * * *" \
    --time-zone="UTC" \
    --uri="${BACKEND_URL}/api/webhooks/gcp/process-trials" \
    --http-method=POST \
    --oidc-service-account-email="$SA_EMAIL" \
    --oidc-token-audience="${BACKEND_URL}" \
    --headers="Content-Type=application/json,X-CloudScheduler=true" \
    --max-retry-attempts=3 \
    --min-backoff=5s \
    --max-backoff=1800s \
    --max-doublings=4 \
    --attempt-deadline=600s \
    --description="Daily processing of expiring and expired trials" \
    --project="$PROJECT_ID"

echo -e "${GREEN}✓ Created: $JOB_NAME_TRIALS (runs daily at 2:00 AM UTC)${NC}"
echo ""

# List all jobs to verify
echo -e "${GREEN}Cloud Scheduler Jobs Summary:${NC}"
gcloud scheduler jobs list --location="$REGION" --project="$PROJECT_ID" --filter="name:gcp-marketplace"

echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Verify jobs are created: gcloud scheduler jobs list --location=$REGION"
echo "2. Test manually: gcloud scheduler jobs run $JOB_NAME_USAGE --location=$REGION"
echo "3. Monitor execution: gcloud scheduler jobs describe $JOB_NAME_USAGE --location=$REGION"
echo "4. View logs: gcloud logging read 'resource.type=cloud_scheduler_job' --limit=50 --format=json"
echo ""
echo -e "${YELLOW}Important:${NC}"
echo "- Usage reporting will run every hour on the hour (e.g., 1:00, 2:00, 3:00)"
echo "- Trial processing will run daily at 2:00 AM UTC"
echo "- Both jobs use OIDC authentication with service account: $SA_EMAIL"
echo "- Logs are available in Cloud Logging under 'Cloud Scheduler Job' resource"
