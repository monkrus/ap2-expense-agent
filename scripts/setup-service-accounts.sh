#!/bin/bash
# Setup GCP Service Accounts and IAM Permissions
#
# This script creates all service accounts needed for:
# 1. Application runtime (Cloud Run/GKE)
# 2. GCP Marketplace API access
# 3. Cloud Build CI/CD
# 4. Cloud Scheduler cron jobs
#
# Usage: ./scripts/setup-service-accounts.sh <project-id> <region>
# Example: ./scripts/setup-service-accounts.sh my-project us-central1

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Validate arguments
if [ "$#" -ne 2 ]; then
    echo -e "${RED}Error: Invalid arguments${NC}"
    echo "Usage: $0 <project-id> <region>"
    echo "Example: $0 my-project us-central1"
    exit 1
fi

PROJECT_ID=$1
REGION=$2

echo -e "${GREEN}Setting up GCP Service Accounts${NC}"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Set the project
gcloud config set project "$PROJECT_ID"

# Enable required APIs
echo -e "${YELLOW}Enabling required APIs...${NC}"
gcloud services enable iam.googleapis.com
gcloud services enable cloudresourcemanager.googleapis.com
gcloud services enable cloudcommerceprocurement.googleapis.com

echo ""
echo -e "${GREEN}Step 1: Application Runtime Service Account${NC}"
echo ""

# Service account for Cloud Run/GKE application
APP_SA_NAME="ap2-expense-sa"
APP_SA_EMAIL="${APP_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

if gcloud iam service-accounts describe "$APP_SA_EMAIL" --project="$PROJECT_ID" &>/dev/null; then
    echo -e "${GREEN}Service account $APP_SA_EMAIL already exists${NC}"
else
    echo -e "${YELLOW}Creating application service account...${NC}"
    gcloud iam service-accounts create "$APP_SA_NAME" \
        --display-name="AP2 Expense Application Service Account" \
        --description="Service account for AP2 Expense Agent runtime (Cloud Run/GKE)" \
        --project="$PROJECT_ID"
    echo -e "${GREEN}✓ Created: $APP_SA_EMAIL${NC}"
fi

# Grant necessary roles to application service account
echo -e "${YELLOW}Granting roles to application service account...${NC}"

# Cloud SQL Client (for database access)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${APP_SA_EMAIL}" \
    --role="roles/cloudsql.client" \
    --condition=None || true

# Secret Manager Secret Accessor (for accessing secrets)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${APP_SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor" \
    --condition=None || true

# Cloud Storage Object Admin (for receipt uploads)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${APP_SA_EMAIL}" \
    --role="roles/storage.objectAdmin" \
    --condition=None || true

# Cloud KMS Crypto Key Signer/Verifier (for AP2 mandate signing)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${APP_SA_EMAIL}" \
    --role="roles/cloudkms.signerVerifier" \
    --condition=None || true

# Monitoring Metric Writer (for custom metrics)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${APP_SA_EMAIL}" \
    --role="roles/monitoring.metricWriter" \
    --condition=None || true

# Cloud Trace Agent (for distributed tracing)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${APP_SA_EMAIL}" \
    --role="roles/cloudtrace.agent" \
    --condition=None || true

# Logging Log Writer
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${APP_SA_EMAIL}" \
    --role="roles/logging.logWriter" \
    --condition=None || true

echo -e "${GREEN}✓ Granted roles to application service account${NC}"

echo ""
echo -e "${GREEN}Step 2: GCP Marketplace API Service Account${NC}"
echo ""

# Service account for GCP Marketplace API access
MARKETPLACE_SA_NAME="ap2-marketplace-api-sa"
MARKETPLACE_SA_EMAIL="${MARKETPLACE_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

if gcloud iam service-accounts describe "$MARKETPLACE_SA_EMAIL" --project="$PROJECT_ID" &>/dev/null; then
    echo -e "${GREEN}Service account $MARKETPLACE_SA_EMAIL already exists${NC}"
else
    echo -e "${YELLOW}Creating marketplace API service account...${NC}"
    gcloud iam service-accounts create "$MARKETPLACE_SA_NAME" \
        --display-name="GCP Marketplace API Service Account" \
        --description="Service account for accessing GCP Marketplace Consumer Procurement API" \
        --project="$PROJECT_ID"
    echo -e "${GREEN}✓ Created: $MARKETPLACE_SA_EMAIL${NC}"
fi

# Grant marketplace API permissions
echo -e "${YELLOW}Granting Marketplace API permissions...${NC}"

# Commerce Producer Admin (for reporting usage and managing entitlements)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${MARKETPLACE_SA_EMAIL}" \
    --role="roles/commerceproducer.admin" \
    --condition=None || true

echo -e "${GREEN}✓ Granted Marketplace API permissions${NC}"

# Create and download service account key
KEY_FILE="marketplace-api-key.json"
if [ -f "$KEY_FILE" ]; then
    echo -e "${YELLOW}Key file $KEY_FILE already exists. Skipping key creation.${NC}"
    echo -e "${YELLOW}Delete the file if you want to generate a new key.${NC}"
else
    echo -e "${YELLOW}Creating service account key...${NC}"
    gcloud iam service-accounts keys create "$KEY_FILE" \
        --iam-account="$MARKETPLACE_SA_EMAIL" \
        --project="$PROJECT_ID"
    echo -e "${GREEN}✓ Created service account key: $KEY_FILE${NC}"
    echo -e "${YELLOW}⚠️  IMPORTANT: Store this key securely and add to Secret Manager!${NC}"
fi

echo ""
echo -e "${GREEN}Step 3: Cloud Build Service Account${NC}"
echo ""

# Cloud Build uses a default service account: PROJECT_NUMBER@cloudbuild.gserviceaccount.com
# We'll grant it additional permissions it needs

PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
CLOUDBUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

echo -e "${YELLOW}Granting permissions to Cloud Build service account: $CLOUDBUILD_SA${NC}"

# Cloud Run Admin (for deploying to Cloud Run)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${CLOUDBUILD_SA}" \
    --role="roles/run.admin" \
    --condition=None || true

# Service Account User (to deploy as application service account)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${CLOUDBUILD_SA}" \
    --role="roles/iam.serviceAccountUser" \
    --condition=None || true

# Secret Manager Secret Accessor (for build-time secrets)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${CLOUDBUILD_SA}" \
    --role="roles/secretmanager.secretAccessor" \
    --condition=None || true

echo -e "${GREEN}✓ Granted permissions to Cloud Build service account${NC}"

echo ""
echo -e "${GREEN}Step 4: Cloud Scheduler Service Account${NC}"
echo ""

# Service account for Cloud Scheduler (already created by setup-cloud-scheduler.sh)
SCHEDULER_SA_NAME="cloud-scheduler-sa"
SCHEDULER_SA_EMAIL="${SCHEDULER_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

if gcloud iam service-accounts describe "$SCHEDULER_SA_EMAIL" --project="$PROJECT_ID" &>/dev/null; then
    echo -e "${GREEN}Service account $SCHEDULER_SA_EMAIL already exists${NC}"
else
    echo -e "${YELLOW}Creating Cloud Scheduler service account...${NC}"
    gcloud iam service-accounts create "$SCHEDULER_SA_NAME" \
        --display-name="Cloud Scheduler Service Account" \
        --description="Service account for Cloud Scheduler to invoke Cloud Run" \
        --project="$PROJECT_ID"
    echo -e "${GREEN}✓ Created: $SCHEDULER_SA_EMAIL${NC}"
fi

# Cloud Run Invoker role granted by setup-cloud-scheduler.sh

echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "Created Service Accounts:"
echo "1. Application Runtime: $APP_SA_EMAIL"
echo "   - Cloud SQL Client"
echo "   - Secret Manager Accessor"
echo "   - Storage Object Admin"
echo "   - Cloud KMS Signer/Verifier"
echo "   - Monitoring Metric Writer"
echo "   - Cloud Trace Agent"
echo "   - Logging Log Writer"
echo ""
echo "2. Marketplace API: $MARKETPLACE_SA_EMAIL"
echo "   - Commerce Producer Admin"
echo "   - Key file: $KEY_FILE (store in Secret Manager!)"
echo ""
echo "3. Cloud Build: $CLOUDBUILD_SA"
echo "   - Cloud Run Admin"
echo "   - Service Account User"
echo "   - Secret Manager Accessor"
echo ""
echo "4. Cloud Scheduler: $SCHEDULER_SA_EMAIL"
echo "   - Cloud Run Invoker"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Store marketplace API key in Secret Manager:"
echo "   gcloud secrets create gcp-service-account-key --data-file=$KEY_FILE"
echo "   rm $KEY_FILE  # Delete local copy after upload"
echo ""
echo "2. Update Cloud Run deployment to use service account:"
echo "   gcloud run services update ap2-expense-backend \\"
echo "     --service-account=$APP_SA_EMAIL \\"
echo "     --region=$REGION"
echo ""
echo "3. Configure environment variables:"
echo "   GCP_SERVICE_ACCOUNT_PATH=/secrets/gcp-service-account-key"
echo "   GCP_PROJECT_ID=$PROJECT_ID"
echo ""
echo "4. Verify permissions:"
echo "   gcloud projects get-iam-policy $PROJECT_ID \\"
echo "     --flatten='bindings[].members' \\"
echo "     --filter='bindings.members:$APP_SA_EMAIL'"
