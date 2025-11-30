#!/bin/bash
set -e

# AP2 Expense Agent - Cloud Run Deployment Script (clean)

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Defaults
REGION="us-central1"
ENVIRONMENT="production"
SKIP_BACKEND=false
SKIP_FRONTEND=false
PROJECT_ID=""

# Args
while [[ $# -gt 0 ]]; do
  case $1 in
    --project) PROJECT_ID="$2"; shift 2;;
    --region) REGION="$2"; shift 2;;
    --env) ENVIRONMENT="$2"; shift 2;;
    --skip-backend) SKIP_BACKEND=true; shift;;
    --skip-frontend) SKIP_FRONTEND=true; shift;;
    --help)
      echo "Usage: $0 [--project PROJECT_ID] [--region REGION] [--env ENV] [--skip-backend] [--skip-frontend]"; exit 0;;
    *) echo -e "${RED}Unknown option: $1${NC}"; exit 1;;
  esac
done

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}AP2 Expense Agent - Cloud Run Deployment${NC}"
echo -e "${BLUE}========================================${NC}"

if ! command -v gcloud >/dev/null 2>&1; then
  echo -e "${RED}ERROR: gcloud CLI is not installed${NC}"; exit 1
fi

if [ -z "$PROJECT_ID" ]; then
  PROJECT_ID=$(gcloud config get-value project 2>/dev/null || true)
  [ -z "$PROJECT_ID" ] && echo -e "${RED}ERROR: No GCP project configured${NC}" && exit 1
fi

echo -e "${GREEN}* GCP Project:${NC} $PROJECT_ID"
echo -e "${GREEN}* Region:${NC} $REGION"
echo -e "${GREEN}* Environment:${NC} $ENVIRONMENT"

read -p "Continue with deployment? (y/N): " -n 1 -r; echo
[[ ! $REPLY =~ ^[Yy]$ ]] && echo "Deployment cancelled." && exit 0

echo -e "${BLUE}Step 1: Enabling required APIs...${NC}"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com containerregistry.googleapis.com sqladmin.googleapis.com secretmanager.googleapis.com --project="$PROJECT_ID"
echo -e "${GREEN}APIs enabled${NC}"

# Backend
if [ "$SKIP_BACKEND" = false ]; then
  echo -e "${BLUE}Step 2: Building and deploying BACKEND...${NC}"
  echo "Building backend Docker image..."
  gcloud builds submit --tag gcr.io/$PROJECT_ID/ap2-expense-backend --timeout=20m backend/
  echo -e "${GREEN}Backend image built${NC}"

  echo "Deploying backend to Cloud Run..."
  gcloud run deploy ap2-expense-backend \
    --image gcr.io/$PROJECT_ID/ap2-expense-backend \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --min-instances 1 \
    --max-instances 10 \
    --memory 2Gi \
    --cpu 2 \
    --port 8080 \
    --timeout 300 \
    --set-env-vars ENVIRONMENT=$ENVIRONMENT \
    --project="$PROJECT_ID"

  BACKEND_URL=$(gcloud run services describe ap2-expense-backend --region "$REGION" --project="$PROJECT_ID" --format="value(status.url)")
  echo -e "${GREEN}Backend deployed successfully!${NC}"
  echo -e "${GREEN}URL:${NC} $BACKEND_URL"
else
  echo -e "${YELLOW}Skipping backend deployment${NC}"
  BACKEND_URL=$(gcloud run services describe ap2-expense-backend --region "$REGION" --project="$PROJECT_ID" --format="value(status.url)" 2>/dev/null || true)
  [ -z "$BACKEND_URL" ] && echo -e "${RED}ERROR: Backend service not found. Cannot deploy frontend without backend.${NC}" && exit 1
  echo -e "${GREEN}Using existing backend:${NC} $BACKEND_URL"
fi

# Frontend
if [ "$SKIP_FRONTEND" = false ]; then
  echo -e "${BLUE}Step 3: Building and deploying FRONTEND...${NC}"
  echo "VITE_API_URL=$BACKEND_URL/api/v1" > frontend/.env.production
  gcloud builds submit --tag gcr.io/$PROJECT_ID/ap2-expense-frontend --timeout=20m frontend/
  echo -e "${GREEN}Frontend image built${NC}"

  gcloud run deploy ap2-expense-frontend \
    --image gcr.io/$PROJECT_ID/ap2-expense-frontend \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --min-instances 1 \
    --max-instances 5 \
    --memory 512Mi \
    --cpu 1 \
    --port 8080 \
    --timeout 60 \
    --project="$PROJECT_ID"

  FRONTEND_URL=$(gcloud run services describe ap2-expense-frontend --region "$REGION" --project="$PROJECT_ID" --format="value(status.url)")
  echo -e "${GREEN}Frontend deployed successfully!${NC}"
  echo -e "${GREEN}URL:${NC} $FRONTEND_URL"
else
  echo -e "${YELLOW}Skipping frontend deployment${NC}"
fi

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Deployment Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo "Your services are now running:"
echo -e "${GREEN}Backend:${NC}  $BACKEND_URL"
if [ "$SKIP_FRONTEND" = false ]; then
  echo -e "${GREEN}Frontend:${NC} $FRONTEND_URL"
fi

echo -e "${BLUE}Testing deployment...${NC}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/health")
if [ "$HTTP_CODE" = "200" ]; then
  echo -e "${GREEN}Backend health check: OK${NC}"
else
  echo -e "${YELLOW}Backend health check returned:${NC} $HTTP_CODE"
fi

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/api/webhooks/gcp/health")
if [ "$HTTP_CODE" = "200" ]; then
  echo -e "${GREEN}GCP webhook health check: OK${NC}"
else
  echo -e "${YELLOW}GCP webhook health check returned:${NC} $HTTP_CODE"
fi

echo -e "${BLUE}Next Steps${NC}"
echo "1. Configure Secret Manager: JWT_SECRET, STRIPE_SECRET_KEY, GCP_WEBHOOK_SECRET, DATABASE_URL"
echo "2. Update Cloud Run services with secrets"
echo "3. Choose Marketplace packaging path and finalize usage/webhook integrations"

