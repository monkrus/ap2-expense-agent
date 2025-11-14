#!/bin/bash
set -e

# AP2 Expense Agent - Cloud Run Deployment Script
# This script deploys both backend and frontend to Google Cloud Run
#
# Prerequisites:
# - gcloud CLI installed and authenticated
# - Docker installed (for local builds)
# - GCP project with billing enabled
#
# Usage:
#   ./deploy-to-cloudrun.sh [OPTIONS]
#
# Options:
#   --project PROJECT_ID    Specify GCP project ID
#   --region REGION         Specify GCP region (default: us-central1)
#   --env ENV               Specify environment (dev|staging|production)
#   --skip-backend          Skip backend deployment
#   --skip-frontend         Skip frontend deployment
#   --help                  Show this help message

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
REGION="us-central1"
ENVIRONMENT="production"
SKIP_BACKEND=false
SKIP_FRONTEND=false
PROJECT_ID=""

# Parse command line arguments
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
        --env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --skip-backend)
            SKIP_BACKEND=true
            shift
            ;;
        --skip-frontend)
            SKIP_FRONTEND=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --project PROJECT_ID    Specify GCP project ID"
            echo "  --region REGION         Specify GCP region (default: us-central1)"
            echo "  --env ENV               Specify environment (dev|staging|production)"
            echo "  --skip-backend          Skip backend deployment"
            echo "  --skip-frontend         Skip frontend deployment"
            echo "  --help                  Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}AP2 Expense Agent - Cloud Run Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}ERROR: gcloud CLI is not installed${NC}"
    echo "Please install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get current project if not specified
if [ -z "$PROJECT_ID" ]; then
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
    if [ -z "$PROJECT_ID" ]; then
        echo -e "${RED}ERROR: No GCP project configured${NC}"
        echo "Please run: gcloud init"
        echo "Or specify project with: --project PROJECT_ID"
        exit 1
    fi
fi

echo -e "${GREEN}✓ GCP Project: $PROJECT_ID${NC}"
echo -e "${GREEN}✓ Region: $REGION${NC}"
echo -e "${GREEN}✓ Environment: $ENVIRONMENT${NC}"
echo ""

# Confirm deployment
read -p "Continue with deployment? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

echo ""
echo -e "${BLUE}Step 1: Enabling required APIs...${NC}"
echo ""

gcloud services enable run.googleapis.com --project=$PROJECT_ID
gcloud services enable cloudbuild.googleapis.com --project=$PROJECT_ID
gcloud services enable containerregistry.googleapis.com --project=$PROJECT_ID
gcloud services enable sqladmin.googleapis.com --project=$PROJECT_ID
gcloud services enable secretmanager.googleapis.com --project=$PROJECT_ID

echo -e "${GREEN}✓ APIs enabled${NC}"

# Deploy Backend
if [ "$SKIP_BACKEND" = false ]; then
    echo ""
    echo -e "${BLUE}Step 2: Building and deploying BACKEND...${NC}"
    echo ""

    # Build backend image
    echo "Building backend Docker image..."
    gcloud builds submit --tag gcr.io/$PROJECT_ID/ap2-expense-backend \
        --timeout=20m \
        backend/

    if [ $? -ne 0 ]; then
        echo -e "${RED}ERROR: Backend build failed${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ Backend image built${NC}"

    # Deploy backend to Cloud Run
    echo ""
    echo "Deploying backend to Cloud Run..."
    gcloud run deploy ap2-expense-backend \
        --image gcr.io/$PROJECT_ID/ap2-expense-backend \
        --region $REGION \
        --platform managed \
        --allow-unauthenticated \
        --min-instances 1 \
        --max-instances 10 \
        --memory 2Gi \
        --cpu 2 \
        --port 8000 \
        --timeout 300 \
        --set-env-vars ENVIRONMENT=$ENVIRONMENT \
        --project=$PROJECT_ID

    if [ $? -ne 0 ]; then
        echo -e "${RED}ERROR: Backend deployment failed${NC}"
        exit 1
    fi

    # Get backend URL
    BACKEND_URL=$(gcloud run services describe ap2-expense-backend \
        --region $REGION \
        --project=$PROJECT_ID \
        --format="value(status.url)")

    echo ""
    echo -e "${GREEN}✓ Backend deployed successfully!${NC}"
    echo -e "${GREEN}  URL: $BACKEND_URL${NC}"
else
    echo ""
    echo -e "${YELLOW}⊘ Skipping backend deployment${NC}"

    # Get existing backend URL
    BACKEND_URL=$(gcloud run services describe ap2-expense-backend \
        --region $REGION \
        --project=$PROJECT_ID \
        --format="value(status.url)" 2>/dev/null || echo "")

    if [ -z "$BACKEND_URL" ]; then
        echo -e "${RED}ERROR: Backend service not found. Cannot deploy frontend without backend.${NC}"
        exit 1
    fi

    echo -e "${GREEN}  Using existing backend: $BACKEND_URL${NC}"
fi

# Deploy Frontend
if [ "$SKIP_FRONTEND" = false ]; then
    echo ""
    echo -e "${BLUE}Step 3: Building and deploying FRONTEND...${NC}"
    echo ""

    # Create production environment file for frontend
    echo "VITE_API_URL=$BACKEND_URL/api/v1" > frontend/.env.production

    # Build frontend image
    echo "Building frontend Docker image..."
    gcloud builds submit --tag gcr.io/$PROJECT_ID/ap2-expense-frontend \
        --timeout=20m \
        frontend/

    if [ $? -ne 0 ]; then
        echo -e "${RED}ERROR: Frontend build failed${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ Frontend image built${NC}"

    # Deploy frontend to Cloud Run
    echo ""
    echo "Deploying frontend to Cloud Run..."
    gcloud run deploy ap2-expense-frontend \
        --image gcr.io/$PROJECT_ID/ap2-expense-frontend \
        --region $REGION \
        --platform managed \
        --allow-unauthenticated \
        --min-instances 1 \
        --max-instances 5 \
        --memory 512Mi \
        --cpu 1 \
        --port 80 \
        --timeout 60 \
        --project=$PROJECT_ID

    if [ $? -ne 0 ]; then
        echo -e "${RED}ERROR: Frontend deployment failed${NC}"
        exit 1
    fi

    # Get frontend URL
    FRONTEND_URL=$(gcloud run services describe ap2-expense-frontend \
        --region $REGION \
        --project=$PROJECT_ID \
        --format="value(status.url)")

    echo ""
    echo -e "${GREEN}✓ Frontend deployed successfully!${NC}"
    echo -e "${GREEN}  URL: $FRONTEND_URL${NC}"
else
    echo ""
    echo -e "${YELLOW}⊘ Skipping frontend deployment${NC}"
fi

# Summary
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Deployment Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Your services are now running:"
echo -e "${GREEN}Backend:  $BACKEND_URL${NC}"
if [ "$SKIP_FRONTEND" = false ]; then
    echo -e "${GREEN}Frontend: $FRONTEND_URL${NC}"
fi
echo ""

# Test endpoints
echo -e "${BLUE}Testing deployment...${NC}"
echo ""

# Test backend health
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $BACKEND_URL/health)
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Backend health check: OK${NC}"
else
    echo -e "${YELLOW}⚠ Backend health check returned: $HTTP_CODE${NC}"
fi

# Test GCP webhook health
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $BACKEND_URL/api/webhooks/gcp/health)
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ GCP webhook health check: OK${NC}"
else
    echo -e "${YELLOW}⚠ GCP webhook health check returned: $HTTP_CODE${NC}"
fi

# Next steps
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Next Steps${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "1. Set up Cloud SQL PostgreSQL database"
echo "   See: backend/POSTGRESQL_MIGRATION.md"
echo ""
echo "2. Configure Secret Manager secrets"
echo "   - JWT_SECRET"
echo "   - STRIPE_SECRET_KEY"
echo "   - GCP_WEBHOOK_SECRET"
echo "   - DATABASE_URL"
echo ""
echo "3. Update Cloud Run services with secrets:"
echo "   gcloud run services update ap2-expense-backend \\"
echo "     --update-secrets=JWT_SECRET=jwt-secret:latest \\"
echo "     --region $REGION"
echo ""
echo "4. Set up custom domain (optional)"
echo "   gcloud run domain-mappings create \\"
echo "     --service ap2-expense-backend \\"
echo "     --domain api.yourdomain.com \\"
echo "     --region $REGION"
echo ""
echo "5. Configure GCP Marketplace integration"
echo "   See: backend/GCP_MARKETPLACE_TESTING.md"
echo ""
echo -e "${GREEN}Deployment script completed successfully!${NC}"
echo ""
