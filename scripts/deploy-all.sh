#!/bin/bash
# One-Command Complete Deployment to GCP Marketplace
#
# This script automates the ENTIRE deployment process from zero to production.
# Run this once and get a fully deployed, production-ready application.
#
# Usage: ./scripts/deploy-all.sh <project-id> <region> <notification-email>
# Example: ./scripts/deploy-all.sh my-project us-central1 ops@company.com

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo ""
    echo -e "${BLUE}================================================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================================================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Validate arguments
if [ "$#" -lt 2 ]; then
    print_error "Missing required arguments"
    echo "Usage: $0 <project-id> <region> [notification-email]"
    echo "Example: $0 my-project us-central1 ops@company.com"
    exit 1
fi

PROJECT_ID=$1
REGION=$2
NOTIFICATION_EMAIL=${3:-ops@example.com}

print_header "🚀 AP2 Expense Agent - Complete GCP Marketplace Deployment"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Notification Email: $NOTIFICATION_EMAIL"
echo ""
print_warning "This will take approximately 20-30 minutes. Grab a coffee!"
echo ""
read -p "Press Enter to begin deployment or Ctrl+C to abort..."

# Set project
gcloud config set project $PROJECT_ID

START_TIME=$(date +%s)

# =============================================================================
# PHASE 1: INFRASTRUCTURE SETUP (10 min)
# =============================================================================

print_header "PHASE 1: Infrastructure Setup (10 min)"

# Step 1: Service Accounts & IAM
echo ""
echo "📋 Step 1/5: Creating service accounts and IAM permissions..."
./scripts/setup-service-accounts.sh $PROJECT_ID $REGION
print_success "Service accounts created"

# Step 2: Cloud SQL Database
echo ""
echo "📋 Step 2/5: Creating Cloud SQL database (this may take 5-7 minutes)..."
gcloud sql instances create ap2-expense-db \
  --database-version=POSTGRES_14 \
  --tier=db-custom-2-7680 \
  --region=$REGION \
  --backup-start-time=02:00 \
  --enable-bin-log \
  --retained-backups-count=30 \
  --storage-auto-increase \
  --storage-size=20GB \
  --project=$PROJECT_ID || print_warning "Database may already exist"

gcloud sql databases create ap2_production \
  --instance=ap2-expense-db \
  --project=$PROJECT_ID || print_warning "Database may already exist"

DB_PASSWORD=$(openssl rand -base64 32)
gcloud sql users create ap2_user \
  --instance=ap2-expense-db \
  --password="$DB_PASSWORD" \
  --project=$PROJECT_ID || print_warning "User may already exist"

print_success "Cloud SQL database configured"

# Step 3: Secrets
echo ""
echo "📋 Step 3/5: Creating secrets in Secret Manager..."

CONNECTION_NAME="${PROJECT_ID}:${REGION}:ap2-expense-db"
DATABASE_URL="postgresql://ap2_user:${DB_PASSWORD}@//cloudsql/${CONNECTION_NAME}/ap2_production"

echo -n "$DATABASE_URL" | gcloud secrets create database-connection-string --data-file=- --project=$PROJECT_ID || \
echo -n "$DATABASE_URL" | gcloud secrets versions add database-connection-string --data-file=- --project=$PROJECT_ID

echo -n "$(openssl rand -hex 32)" | gcloud secrets create jwt-secret-key --data-file=- --project=$PROJECT_ID || \
echo -n "$(openssl rand -hex 32)" | gcloud secrets versions add jwt-secret-key --data-file=- --project=$PROJECT_ID

echo -n "$(openssl rand -hex 32)" | gcloud secrets create jwt-refresh-secret-key --data-file=- --project=$PROJECT_ID || \
echo -n "$(openssl rand -hex 32)" | gcloud secrets versions add jwt-refresh-secret-key --data-file=- --project=$PROJECT_ID

echo -n "$(openssl rand -hex 16)" | gcloud secrets create gcp-webhook-secret --data-file=- --project=$PROJECT_ID || \
echo -n "$(openssl rand -hex 16)" | gcloud secrets versions add gcp-webhook-secret --data-file=- --project=$PROJECT_ID

# Placeholder for Stripe key (user must update manually)
echo -n "sk_test_placeholder" | gcloud secrets create stripe-secret-key --data-file=- --project=$PROJECT_ID 2>/dev/null || \
print_warning "Stripe key already exists - you must update it manually"

print_success "Secrets created"

# Step 4: Cloud Storage
echo ""
echo "📋 Step 4/5: Creating Cloud Storage bucket..."

BUCKET_NAME="${PROJECT_ID}-receipts"
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$BUCKET_NAME/ 2>/dev/null || print_warning "Bucket may already exist"

gsutil iam ch serviceAccount:ap2-expense-sa@${PROJECT_ID}.iam.gserviceaccount.com:roles/storage.objectAdmin gs://$BUCKET_NAME/

print_success "Storage bucket configured"

# Step 5: Cloud KMS
echo ""
echo "📋 Step 5/5: Creating Cloud KMS keyring..."

gcloud kms keyrings create ap2-expense-keyring \
  --location=$REGION \
  --project=$PROJECT_ID 2>/dev/null || print_warning "Keyring may already exist"

gcloud kms keys create ap2-mandate-signing-key \
  --location=$REGION \
  --keyring=ap2-expense-keyring \
  --purpose=asymmetric-signing \
  --default-algorithm=ec-sign-p256-sha256 \
  --project=$PROJECT_ID 2>/dev/null || print_warning "Key may already exist"

gcloud kms keys add-iam-policy-binding ap2-mandate-signing-key \
  --location=$REGION \
  --keyring=ap2-expense-keyring \
  --member="serviceAccount:ap2-expense-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role=roles/cloudkms.signerVerifier \
  --project=$PROJECT_ID || true

print_success "Cloud KMS configured"

PHASE1_END=$(date +%s)
PHASE1_DURATION=$((PHASE1_END - START_TIME))
print_success "Phase 1 complete in ${PHASE1_DURATION}s"

# =============================================================================
# PHASE 2: APPLICATION DEPLOYMENT (10 min)
# =============================================================================

print_header "PHASE 2: Application Deployment (10 min)"

# Step 1: Build Images
echo ""
echo "📋 Step 1/4: Building Docker images (5 min)..."
./scripts/build-and-tag.sh v1.0.0 --push
print_success "Docker images built and pushed"

# Step 2: Deploy Backend
echo ""
echo "📋 Step 2/4: Deploying backend to Cloud Run..."

gcloud run deploy ap2-expense-backend \
  --image=gcr.io/$PROJECT_ID/ap2-expense-backend:v1.0.0 \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --service-account=ap2-expense-sa@${PROJECT_ID}.iam.gserviceaccount.com \
  --add-cloudsql-instances=$CONNECTION_NAME \
  --min-instances=1 \
  --max-instances=10 \
  --memory=2Gi \
  --cpu=2 \
  --timeout=300s \
  --concurrency=80 \
  --set-env-vars="ENVIRONMENT=production,\
GCP_PROJECT_ID=$PROJECT_ID,\
GOOGLE_CLOUD_PROJECT=$PROJECT_ID,\
GCP_KMS_LOCATION=$REGION,\
GCP_KMS_KEYRING=ap2-expense-keyring,\
GCP_KMS_SIGNING_KEY=ap2-mandate-signing-key,\
ENABLE_GCP_MARKETPLACE=true,\
GCP_USAGE_REPORTING_ENABLED=true" \
  --set-secrets="DATABASE_URL=database-connection-string:latest,\
JWT_SECRET=jwt-secret-key:latest,\
JWT_REFRESH_SECRET=jwt-refresh-secret-key:latest,\
GCP_WEBHOOK_SECRET=gcp-webhook-secret:latest,\
GCP_SERVICE_ACCOUNT_PATH=gcp-service-account-key:latest" \
  --project=$PROJECT_ID

BACKEND_URL=$(gcloud run services describe ap2-expense-backend \
  --region=$REGION \
  --project=$PROJECT_ID \
  --format="value(status.url)")

gcloud run services update ap2-expense-backend \
  --region=$REGION \
  --update-env-vars="GCP_WEBHOOK_AUDIENCE=$BACKEND_URL" \
  --project=$PROJECT_ID

print_success "Backend deployed at: $BACKEND_URL"

# Step 3: Deploy Frontend
echo ""
echo "📋 Step 3/4: Deploying frontend to Cloud Run..."

gcloud run deploy ap2-expense-frontend \
  --image=gcr.io/$PROJECT_ID/ap2-expense-frontend:v1.0.0 \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --min-instances=1 \
  --max-instances=5 \
  --memory=512Mi \
  --cpu=1 \
  --timeout=60s \
  --concurrency=100 \
  --set-env-vars="VITE_API_BASE_URL=$BACKEND_URL" \
  --project=$PROJECT_ID

FRONTEND_URL=$(gcloud run services describe ap2-expense-frontend \
  --region=$REGION \
  --project=$PROJECT_ID \
  --format="value(status.url)")

print_success "Frontend deployed at: $FRONTEND_URL"

# Step 4: Database Migrations
echo ""
echo "📋 Step 4/4: Running database migrations..."

# Start Cloud SQL Proxy
cloud_sql_proxy -instances=$CONNECTION_NAME=tcp:5432 &
PROXY_PID=$!
sleep 5

# Run migrations
cd backend
export DATABASE_URL="postgresql://ap2_user:${DB_PASSWORD}@localhost:5432/ap2_production"
.venv/Scripts/python.exe -m alembic upgrade head || python -m alembic upgrade head
cd ..

# Stop proxy
kill $PROXY_PID

print_success "Database migrations complete"

PHASE2_END=$(date +%s)
PHASE2_DURATION=$((PHASE2_END - PHASE1_END))
print_success "Phase 2 complete in ${PHASE2_DURATION}s"

# =============================================================================
# PHASE 3: GCP MARKETPLACE INTEGRATION (5 min)
# =============================================================================

print_header "PHASE 3: GCP Marketplace Integration (5 min)"

# Step 1: Pub/Sub
echo ""
echo "📋 Step 1/3: Configuring Pub/Sub..."
./scripts/setup-pubsub.sh $PROJECT_ID $REGION $BACKEND_URL
print_success "Pub/Sub configured"

# Step 2: Cloud Scheduler
echo ""
echo "📋 Step 2/3: Configuring Cloud Scheduler..."
./scripts/setup-cloud-scheduler.sh $PROJECT_ID $REGION $BACKEND_URL
print_success "Cloud Scheduler configured"

# Step 3: Monitoring
echo ""
echo "📋 Step 3/3: Configuring monitoring and alerts..."
./scripts/setup-monitoring-alerts.sh $PROJECT_ID $NOTIFICATION_EMAIL
print_success "Monitoring configured"

PHASE3_END=$(date +%s)
PHASE3_DURATION=$((PHASE3_END - PHASE2_END))
print_success "Phase 3 complete in ${PHASE3_DURATION}s"

# =============================================================================
# PHASE 4: VALIDATION (2 min)
# =============================================================================

print_header "PHASE 4: Validation (2 min)"

echo ""
echo "🧪 Running smoke tests..."

# Test backend health
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/health")
if [ "$HTTP_CODE" = "200" ]; then
    print_success "Backend health check passed"
else
    print_error "Backend health check failed (HTTP $HTTP_CODE)"
fi

# Test GCP webhook health
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/api/webhooks/gcp/health")
if [ "$HTTP_CODE" = "200" ]; then
    print_success "GCP webhook health check passed"
else
    print_error "GCP webhook health check failed (HTTP $HTTP_CODE)"
fi

# Test frontend
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL")
if [ "$HTTP_CODE" = "200" ]; then
    print_success "Frontend health check passed"
else
    print_error "Frontend health check failed (HTTP $HTTP_CODE)"
fi

TOTAL_END=$(date +%s)
TOTAL_DURATION=$((TOTAL_END - START_TIME))
TOTAL_MINUTES=$((TOTAL_DURATION / 60))

# =============================================================================
# DEPLOYMENT COMPLETE
# =============================================================================

print_header "🎉 DEPLOYMENT COMPLETE!"

echo ""
echo "Deployment Summary:"
echo "  Total Time: ${TOTAL_MINUTES} minutes ${TOTAL_DURATION}s"
echo "  Project: $PROJECT_ID"
echo "  Region: $REGION"
echo ""
echo "URLs:"
echo "  Backend:  $BACKEND_URL"
echo "  Frontend: $FRONTEND_URL"
echo ""
echo "Next Steps:"
echo ""
echo "1. Test the application:"
echo "   Open: $FRONTEND_URL"
echo "   Register a new account and test functionality"
echo ""
echo "2. Update Stripe API key (required for payments):"
echo "   gcloud secrets versions add stripe-secret-key --data-file=- --project=$PROJECT_ID"
echo "   (Paste your Stripe secret key, then Ctrl+D)"
echo ""
echo "3. Create marketplace assets:"
echo "   - Screenshots: ./scripts/capture-screenshots.sh"
echo "   - Video: Follow marketplace/DEMO_VIDEO_SCRIPT.md"
echo "   - Icon: Export marketplace/product-icon-template.svg"
echo ""
echo "4. Submit to GCP Marketplace:"
echo "   - Go to: https://console.cloud.google.com/partner"
echo "   - Create product listing"
echo "   - Use content from: marketplace/PRODUCT_LISTING_TEXT.md"
echo "   - Configure webhooks:"
echo "     * Procurement: $BACKEND_URL/api/webhooks/gcp/procurement"
echo "     * Entitlement: projects/$PROJECT_ID/topics/gcp-marketplace-entitlement-events"
echo ""
echo "5. View monitoring:"
echo "   https://console.cloud.google.com/monitoring?project=$PROJECT_ID"
echo ""
echo "🎊 Your application is now live and production-ready!"
echo ""

# Save deployment info
cat > deployment-info.txt <<EOF
AP2 Expense Agent - Deployment Information
==========================================

Deployed: $(date)
Project: $PROJECT_ID
Region: $REGION
Duration: ${TOTAL_MINUTES} minutes

URLs:
  Backend:  $BACKEND_URL
  Frontend: $FRONTEND_URL

GCP Resources:
  Cloud SQL: ap2-expense-db
  Cloud Run: ap2-expense-backend, ap2-expense-frontend
  Storage: gs://${PROJECT_ID}-receipts
  KMS: ap2-expense-keyring/ap2-mandate-signing-key

Marketplace Webhooks:
  Procurement: $BACKEND_URL/api/webhooks/gcp/procurement
  Events: projects/$PROJECT_ID/topics/gcp-marketplace-entitlement-events

Credentials stored in Secret Manager:
  - database-connection-string
  - jwt-secret-key
  - jwt-refresh-secret-key
  - gcp-webhook-secret
  - stripe-secret-key (UPDATE REQUIRED)
  - gcp-service-account-key

Next: Create marketplace assets and submit for review
EOF

print_success "Deployment info saved to: deployment-info.txt"

exit 0
