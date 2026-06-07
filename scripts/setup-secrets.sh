#!/bin/bash
set -e

# AP2 Expense Agent - Secret Manager Setup Script
#
# This script helps you securely store all required secrets in Google Cloud Secret Manager
# and configure Cloud Run services to use them.
#
# Prerequisites:
# - gcloud CLI installed and authenticated
# - Secret Manager API enabled
# - Appropriate IAM permissions
#
# Usage:
#   ./setup-secrets.sh --project PROJECT_ID [OPTIONS]
#
# Options:
#   --project PROJECT_ID    Specify GCP project ID (required)
#   --region REGION         Specify GCP region (default: us-central1)
#   --service SERVICE       Cloud Run service name (default: ap2-expense-backend)
#   --interactive           Prompt for each secret value
#   --help                  Show this help message

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
REGION="us-central1"
SERVICE="ap2-expense-backend"
INTERACTIVE=false
PROJECT_ID=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --project)
            PROJECT_ID="$2"
            shift 2
            ;;
        --region)
            REGION="$2"
            shift 2
            ;;
        --service)
            SERVICE="$2"
            shift 2
            ;;
        --interactive)
            INTERACTIVE=true
            shift
            ;;
        --help)
            echo "Usage: $0 --project PROJECT_ID [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --project PROJECT_ID    Specify GCP project ID (required)"
            echo "  --region REGION         Specify GCP region (default: us-central1)"
            echo "  --service SERVICE       Cloud Run service name (default: ap2-expense-backend)"
            echo "  --interactive           Prompt for each secret value"
            echo "  --help                  Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}ERROR: --project is required${NC}"
    exit 1
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}AP2 Expense Agent - Secret Manager Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}Project: $PROJECT_ID${NC}"
echo -e "${GREEN}Region: $REGION${NC}"
echo -e "${GREEN}Service: $SERVICE${NC}"
echo ""

# Enable Secret Manager API
echo -e "${BLUE}Enabling Secret Manager API...${NC}"
gcloud services enable secretmanager.googleapis.com --project=$PROJECT_ID
echo -e "${GREEN}✓ Secret Manager API enabled${NC}"
echo ""

# Function to create or update a secret
create_secret() {
    local secret_name=$1
    local description=$2
    local example=$3

    echo -e "${BLUE}Setting up: $secret_name${NC}"
    echo "  Description: $description"

    if [ "$INTERACTIVE" = true ]; then
        echo -n "  Enter value (or press Enter to skip): "
        read -s secret_value
        echo ""

        if [ -z "$secret_value" ]; then
            echo -e "${YELLOW}  ⊘ Skipped${NC}"
            return
        fi
    else
        echo -e "${YELLOW}  ℹ Run with --interactive to set value${NC}"
        echo "  Example: $example"

        # Create empty secret if doesn't exist
        if ! gcloud secrets describe $secret_name --project=$PROJECT_ID &>/dev/null; then
            echo "placeholder" | gcloud secrets create $secret_name \
                --data-file=- \
                --replication-policy=automatic \
                --project=$PROJECT_ID \
                --labels=app=ap2-expense-agent 2>/dev/null || true
        fi
        return
    fi

    # Check if secret exists
    if gcloud secrets describe $secret_name --project=$PROJECT_ID &>/dev/null 2>&1; then
        # Update existing secret
        echo "$secret_value" | gcloud secrets versions add $secret_name \
            --data-file=- \
            --project=$PROJECT_ID
        echo -e "${GREEN}  ✓ Secret updated${NC}"
    else
        # Create new secret
        echo "$secret_value" | gcloud secrets create $secret_name \
            --data-file=- \
            --replication-policy=automatic \
            --project=$PROJECT_ID \
            --labels=app=ap2-expense-agent
        echo -e "${GREEN}  ✓ Secret created${NC}"
    fi
    echo ""
}

# Required secrets
echo -e "${BLUE}Creating required secrets...${NC}"
echo ""

create_secret "jwt-secret" \
    "JWT secret key for authentication" \
    "Generate with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""

create_secret "database-url" \
    "PostgreSQL connection string" \
    "postgresql://user:password@/dbname?host=/cloudsql/PROJECT:REGION:INSTANCE"

create_secret "stripe-secret-key" \
    "Stripe secret key (live mode)" \
    "sk_live_..."

create_secret "stripe-publishable-key" \
    "Stripe publishable key (live mode)" \
    "pk_live_..."

create_secret "stripe-webhook-secret" \
    "Stripe webhook signing secret" \
    "whsec_..."

create_secret "quickbooks-client-secret" \
    "QuickBooks OAuth client secret" \
    "From Intuit Developer Portal > Your App > Keys & credentials"

create_secret "smtp-password" \
    "SMTP password for sending emails" \
    "Your SMTP provider password or API key"

create_secret "sentry-dsn" \
    "Sentry DSN for error tracking (optional)" \
    "https://...@sentry.io/..."

# Service account for Cloud Run
echo -e "${BLUE}Service Account Setup${NC}"
echo ""
echo "For Cloud Run deployment, you need a service account JSON key."
echo "Follow these steps:"
echo ""
echo "1. Create service account:"
echo "   gcloud iam service-accounts create ap2-expense-sa \\"
echo "     --display-name='AP2 Expense Service Account' \\"
echo "     --project=$PROJECT_ID"
echo ""
echo "2. Grant required permissions:"
echo "   gcloud projects add-iam-policy-binding $PROJECT_ID \\"
echo "     --member='serviceAccount:gcp-marketplace-sa@${PROJECT_ID}.iam.gserviceaccount.com' \\"
echo "     --role='roles/cloudcommerceprocurement.procurementAdmin'"
echo ""
echo "3. Create and download key:"
echo "   gcloud iam service-accounts keys create gcp-marketplace-sa-key.json \\"
echo "     --iam-account=gcp-marketplace-sa@${PROJECT_ID}.iam.gserviceaccount.com"
echo ""
echo "4. Store key in Secret Manager:"
echo "   gcloud secrets create gcp-marketplace-sa-key \\"
echo "     --data-file=gcp-marketplace-sa-key.json \\"
echo "     --project=$PROJECT_ID"
echo ""
echo "5. Delete local key file (security):"
echo "   rm gcp-marketplace-sa-key.json"
echo ""

# Grant Cloud Run access to secrets
echo -e "${BLUE}Granting Cloud Run access to secrets...${NC}"
echo ""

# Get Cloud Run service account
SERVICE_ACCOUNT=$(gcloud run services describe $SERVICE \
    --region=$REGION \
    --project=$PROJECT_ID \
    --format="value(spec.template.spec.serviceAccountName)" 2>/dev/null || echo "")

if [ -z "$SERVICE_ACCOUNT" ]; then
    # Use default compute service account
    PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
    SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
    echo "Using default compute service account: $SERVICE_ACCOUNT"
fi

# Grant Secret Manager access
SECRETS=(
    "jwt-secret"
    "database-url"
    "stripe-secret-key"
    "stripe-webhook-secret"
    "gcp-webhook-secret"
    "smtp-password"
)

for secret in "${SECRETS[@]}"; do
    if gcloud secrets describe $secret --project=$PROJECT_ID &>/dev/null 2>&1; then
        gcloud secrets add-iam-policy-binding $secret \
            --member="serviceAccount:$SERVICE_ACCOUNT" \
            --role="roles/secretmanager.secretAccessor" \
            --project=$PROJECT_ID &>/dev/null || true
        echo -e "${GREEN}✓ Granted access to $secret${NC}"
    fi
done

echo ""
echo -e "${BLUE}Configuring Cloud Run service...${NC}"
echo ""

# Check if service exists
if gcloud run services describe $SERVICE --region=$REGION --project=$PROJECT_ID &>/dev/null 2>&1; then
    echo "Updating $SERVICE with secret environment variables..."

    gcloud run services update $SERVICE \
        --update-secrets=JWT_SECRET=jwt-secret:latest \
        --update-secrets=DATABASE_URL=database-url:latest \
        --update-secrets=STRIPE_SECRET_KEY=stripe-secret-key:latest \
        --update-secrets=STRIPE_WEBHOOK_SECRET=stripe-webhook-secret:latest \
        --update-secrets=GCP_WEBHOOK_SECRET=gcp-webhook-secret:latest \
        --update-secrets=SMTP_PASSWORD=smtp-password:latest \
        --region=$REGION \
        --project=$PROJECT_ID

    echo -e "${GREEN}✓ Cloud Run service updated${NC}"
else
    echo -e "${YELLOW}⚠ Service $SERVICE not found. Deploy the service first, then run this script again.${NC}"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Setup Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Next steps:"
echo ""
echo "1. Review secrets in Cloud Console:"
echo "   https://console.cloud.google.com/security/secret-manager?project=$PROJECT_ID"
echo ""
echo "2. Set secret values if not done interactively:"
echo "   echo 'YOUR_SECRET_VALUE' | gcloud secrets versions add SECRET_NAME --data-file=- --project=$PROJECT_ID"
echo ""
echo "3. Verify Cloud Run service configuration:"
echo "   gcloud run services describe $SERVICE --region=$REGION --project=$PROJECT_ID"
echo ""
echo "4. Test your deployment:"
echo "   SERVICE_URL=\$(gcloud run services describe $SERVICE --region=$REGION --project=$PROJECT_ID --format='value(status.url)')"
echo "   curl \$SERVICE_URL/health"
echo ""
echo -e "${GREEN}All secrets configured!${NC}"
echo ""
