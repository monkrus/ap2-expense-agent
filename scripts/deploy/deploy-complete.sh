#!/bin/bash
set -e

# AP2 Expense Agent - Complete Deployment Orchestrator
#
# This script orchestrates the complete deployment process:
# 1. GCP project setup
# 2. Cloud SQL database creation
# 3. Secret Manager configuration
# 4. Backend deployment to Cloud Run
# 5. Frontend deployment to Cloud Run
# 6. Post-deployment verification
#
# Prerequisites:
# - gcloud CLI installed and authenticated
# - Docker installed
# - GCP project with billing enabled
#
# Usage:
#   ./deploy-complete.sh --project PROJECT_ID [OPTIONS]

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ID=""
REGION="us-central1"
SKIP_DB=false
SKIP_SECRETS=false
DRY_RUN=false

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
        --skip-db)
            SKIP_DB=true
            shift
            ;;
        --skip-secrets)
            SKIP_SECRETS=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help)
            cat << EOF
AP2 Expense Agent - Complete Deployment Orchestrator

Usage: $0 --project PROJECT_ID [OPTIONS]

Options:
  --project PROJECT_ID    GCP project ID (required)
  --region REGION         GCP region (default: us-central1)
  --skip-db               Skip Cloud SQL database setup
  --skip-secrets          Skip Secret Manager setup
  --dry-run               Show what would be done without executing
  --help                  Show this help message

Example:
  $0 --project my-gcp-project --region us-central1

For detailed documentation, see:
  - DEPLOYMENT_QUICKSTART.md (70-minute fast track)
  - CLOUD_RUN_DEPLOYMENT.md (comprehensive guide)
  - DEPLOYMENT_READINESS_REPORT.md (full status)

EOF
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Validate required arguments
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}ERROR: --project is required${NC}"
    echo "Use --help for usage information"
    exit 1
fi

# Banner
echo -e "${CYAN}"
cat << "EOF"
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║      AP2 Expense Agent - Complete Deployment            ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo -e "${GREEN}Configuration:${NC}"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Skip Database: $SKIP_DB"
echo "  Skip Secrets: $SKIP_SECRETS"
echo "  Dry Run: $DRY_RUN"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}DRY RUN MODE - No changes will be made${NC}"
    echo ""
fi

# Confirmation
if [ "$DRY_RUN" = false ]; then
    read -p "Continue with deployment? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled."
        exit 0
    fi
fi

echo ""

# Step 1: Enable APIs
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 1/7: Enabling required GCP APIs${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

APIS=(
    "run.googleapis.com"
    "cloudbuild.googleapis.com"
    "containerregistry.googleapis.com"
    "sqladmin.googleapis.com"
    "secretmanager.googleapis.com"
    "compute.googleapis.com"
    "servicenetworking.googleapis.com"
)

for api in "${APIS[@]}"; do
    echo -n "  Enabling $api... "
    if [ "$DRY_RUN" = false ]; then
        gcloud services enable $api --project=$PROJECT_ID
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${YELLOW}(dry run)${NC}"
    fi
done

echo ""

# Step 2: Cloud SQL Setup
if [ "$SKIP_DB" = false ]; then
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}Step 2/7: Setting up Cloud SQL PostgreSQL${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo ""

    DB_INSTANCE="ap2-expense-db"
    DB_NAME="expenses"
    DB_USER="ap2user"

    echo "Instance: $DB_INSTANCE"
    echo "Database: $DB_NAME"
    echo "Region: $REGION"
    echo ""

    # Check if instance exists
    if gcloud sql instances describe $DB_INSTANCE --project=$PROJECT_ID &>/dev/null 2>&1; then
        echo -e "${YELLOW}✓ Cloud SQL instance already exists${NC}"
    else
        echo "Creating Cloud SQL instance (this may take 10-15 minutes)..."

        if [ "$DRY_RUN" = false ]; then
            gcloud sql instances create $DB_INSTANCE \
                --database-version=POSTGRES_15 \
                --tier=db-f1-micro \
                --region=$REGION \
                --network=default \
                --no-assign-ip \
                --database-flags=max_connections=100 \
                --backup-start-time=03:00 \
                --maintenance-window-day=SUN \
                --maintenance-window-hour=04 \
                --project=$PROJECT_ID

            echo -e "${GREEN}✓ Cloud SQL instance created${NC}"
        else
            echo -e "${YELLOW}(dry run - would create instance)${NC}"
        fi
    fi

    # Generate random password
    DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)

    # Create database
    echo ""
    echo "Creating database and user..."

    if [ "$DRY_RUN" = false ]; then
        # Create user
        gcloud sql users create $DB_USER \
            --instance=$DB_INSTANCE \
            --password=$DB_PASSWORD \
            --project=$PROJECT_ID 2>/dev/null || echo "User may already exist"

        # Create database
        gcloud sql databases create $DB_NAME \
            --instance=$DB_INSTANCE \
            --project=$PROJECT_ID 2>/dev/null || echo "Database may already exist"

        # Store database URL in Secret Manager
        DB_CONNECTION_NAME="${PROJECT_ID}:${REGION}:${DB_INSTANCE}"
        DB_URL="postgresql://${DB_USER}:${DB_PASSWORD}@/${DB_NAME}?host=/cloudsql/${DB_CONNECTION_NAME}"

        echo "$DB_URL" | gcloud secrets create database-url \
            --data-file=- \
            --replication-policy=automatic \
            --project=$PROJECT_ID 2>/dev/null || \
        echo "$DB_URL" | gcloud secrets versions add database-url \
            --data-file=- \
            --project=$PROJECT_ID

        echo -e "${GREEN}✓ Database configured and credentials stored in Secret Manager${NC}"
    else
        echo -e "${YELLOW}(dry run - would create database and store credentials)${NC}"
    fi
else
    echo -e "${YELLOW}⊘ Skipping Cloud SQL setup${NC}"
fi

echo ""

# Step 3: Secret Manager Setup
if [ "$SKIP_SECRETS" = false ]; then
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}Step 3/7: Configuring Secret Manager${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo ""

    echo "Setting up required secrets..."
    echo ""
    echo "NOTE: You'll need to update these secrets with actual values:"
    echo "  - jwt-secret"
    echo "  - stripe-secret-key"
    echo "  - stripe-webhook-secret"
    echo "  - gcp-webhook-secret"
    echo "  - smtp-password"
    echo ""

    if [ "$DRY_RUN" = false ]; then
        if [ -f "$SCRIPT_DIR/scripts/setup-secrets.sh" ]; then
            bash "$SCRIPT_DIR/scripts/setup-secrets.sh" --project $PROJECT_ID --region $REGION
        else
            echo -e "${YELLOW}⚠ setup-secrets.sh not found, skipping${NC}"
        fi
    else
        echo -e "${YELLOW}(dry run - would run setup-secrets.sh)${NC}"
    fi
else
    echo -e "${YELLOW}⊘ Skipping Secret Manager setup${NC}"
fi

echo ""

# Step 4: Deploy Backend
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 4/7: Deploying Backend to Cloud Run${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

if [ "$DRY_RUN" = false ]; then
    bash "$SCRIPT_DIR/deploy-to-cloudrun.sh" \
        --project $PROJECT_ID \
        --region $REGION \
        --skip-frontend
    BACKEND_URL=$(gcloud run services describe ap2-expense-backend \
        --region $REGION \
        --project=$PROJECT_ID \
        --format="value(status.url)")
else
    echo -e "${YELLOW}(dry run - would deploy backend)${NC}"
    BACKEND_URL="https://placeholder-backend-url.run.app"
fi

echo ""

# Step 5: Deploy Frontend
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 5/7: Deploying Frontend to Cloud Run${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

if [ "$DRY_RUN" = false ]; then
    bash "$SCRIPT_DIR/deploy-to-cloudrun.sh" \
        --project $PROJECT_ID \
        --region $REGION \
        --skip-backend
    FRONTEND_URL=$(gcloud run services describe ap2-expense-frontend \
        --region $REGION \
        --project=$PROJECT_ID \
        --format="value(status.url)")
else
    echo -e "${YELLOW}(dry run - would deploy frontend)${NC}"
    FRONTEND_URL="https://placeholder-frontend-url.run.app"
fi

echo ""

# Step 6: Post-Deployment Verification
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 6/7: Post-Deployment Verification${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

if [ "$DRY_RUN" = false ]; then
    echo "Testing backend health..."
    sleep 5

    if curl -f -s "$BACKEND_URL/health" > /dev/null; then
        echo -e "${GREEN}✓ Backend health check passed${NC}"
    else
        echo -e "${RED}✗ Backend health check failed${NC}"
    fi

    if curl -f -s "$BACKEND_URL/api/webhooks/gcp/health" > /dev/null; then
        echo -e "${GREEN}✓ GCP webhook health check passed${NC}"
    else
        echo -e "${RED}✗ GCP webhook health check failed${NC}"
    fi

    echo ""
    echo "Testing frontend..."
    if curl -f -s "$FRONTEND_URL" > /dev/null; then
        echo -e "${GREEN}✓ Frontend accessible${NC}"
    else
        echo -e "${RED}✗ Frontend not accessible${NC}"
    fi
else
    echo -e "${YELLOW}(dry run - would verify deployment)${NC}"
fi

echo ""

# Step 7: Summary and Next Steps
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 7/7: Deployment Summary${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${GREEN}✓ Deployment Complete!${NC}"
echo ""
echo "Your services are running at:"
echo -e "  Backend:  ${CYAN}$BACKEND_URL${NC}"
echo -e "  Frontend: ${CYAN}$FRONTEND_URL${NC}"
echo ""

if [ "$DRY_RUN" = false ]; then
    echo "Important next steps:"
    echo ""
    echo "1. Update secrets with production values:"
    echo "   gcloud secrets versions add jwt-secret --data-file=- --project=$PROJECT_ID"
    echo ""
    echo "2. Run database migrations:"
    echo "   gcloud run jobs execute migration-job --region $REGION"
    echo ""
    echo "3. Configure Stripe webhooks:"
    echo "   Webhook URL: $BACKEND_URL/webhooks/stripe"
    echo ""
    echo "4. Configure QuickBooks integration (see INTUIT_APP_STORE.md)"
    echo ""
    echo "5. Set up custom domain (optional):"
    echo "   gcloud run domain-mappings create --service ap2-expense-backend --domain api.yourdomain.com"
    echo ""
    echo "6. Set up monitoring and alerting"
    echo ""
    echo "Documentation:"
    echo "  - Complete guide: CLOUD_RUN_DEPLOYMENT.md"
    echo "  - Intuit App Store: INTUIT_APP_STORE.md"
    echo ""
fi

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║           Deployment orchestration complete!              ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"
