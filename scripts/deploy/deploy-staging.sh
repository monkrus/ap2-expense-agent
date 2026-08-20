#!/bin/bash
#
# Staging Deployment Script
# Deploys AP2 Expense Management to staging environment
#
# Usage: ./deploy-staging.sh
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
STAGING_PROJECT_ID="${STAGING_GCP_PROJECT_ID:-ap2-expense-staging}"
STAGING_REGION="${STAGING_REGION:-us-central1}"
BACKEND_SERVICE="ap2-expense-backend-staging"
FRONTEND_SERVICE="ap2-expense-frontend-staging"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  AP2 Expense - Staging Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

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

# Step 1: Validate environment
print_step "Step 1: Validating environment"

if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI not found. Please install Google Cloud SDK."
    exit 1
fi

if ! command -v docker &> /dev/null; then
    print_error "Docker not found. Please install Docker."
    exit 1
fi

print_success "gcloud and docker installed"

# Check if logged in to gcloud
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    print_error "Not logged in to gcloud. Run: gcloud auth login"
    exit 1
fi

print_success "Logged in to gcloud"

# Step 2: Set GCP project
print_step "Step 2: Setting GCP project"

gcloud config set project ${STAGING_PROJECT_ID}
print_success "Project set to ${STAGING_PROJECT_ID}"

# Step 3: Run tests
print_step "Step 3: Running tests"

echo "Running backend tests..."
cd backend
if python -m pytest --tb=short -v; then
    print_success "Backend tests passed"
else
    print_error "Backend tests failed. Aborting deployment."
    exit 1
fi
cd ..

echo "Running frontend unit tests..."
cd frontend
if npm run test:unit -- --run; then
    print_success "Frontend unit tests passed"
else
    print_warning "Frontend unit tests failed (non-blocking)"
fi
cd ..

# Step 4: Build frontend
print_step "Step 4: Building frontend"

cd frontend
npm run build

if [ -d "dist" ]; then
    print_success "Frontend build complete"
else
    print_error "Frontend build failed"
    exit 1
fi
cd ..

# Step 5: Build and push Docker images
print_step "Step 5: Building and pushing Docker images"

# Backend
echo "Building backend Docker image..."
docker build -t gcr.io/${STAGING_PROJECT_ID}/${BACKEND_SERVICE}:latest \
    -t gcr.io/${STAGING_PROJECT_ID}/${BACKEND_SERVICE}:$(git rev-parse --short HEAD) \
    ./backend

docker push gcr.io/${STAGING_PROJECT_ID}/${BACKEND_SERVICE}:latest
docker push gcr.io/${STAGING_PROJECT_ID}/${BACKEND_SERVICE}:$(git rev-parse --short HEAD)
print_success "Backend image pushed"

# Frontend
echo "Building frontend Docker image..."
docker build -t gcr.io/${STAGING_PROJECT_ID}/${FRONTEND_SERVICE}:latest \
    -t gcr.io/${STAGING_PROJECT_ID}/${FRONTEND_SERVICE}:$(git rev-parse --short HEAD) \
    ./frontend

docker push gcr.io/${STAGING_PROJECT_ID}/${FRONTEND_SERVICE}:latest
docker push gcr.io/${STAGING_PROJECT_ID}/${FRONTEND_SERVICE}:$(git rev-parse --short HEAD)
print_success "Frontend image pushed"

# Step 6: Deploy to Cloud Run
print_step "Step 6: Deploying to Cloud Run"

# Backend
echo "Deploying backend service..."
gcloud run deploy ${BACKEND_SERVICE} \
    --image gcr.io/${STAGING_PROJECT_ID}/${BACKEND_SERVICE}:latest \
    --platform managed \
    --region ${STAGING_REGION} \
    --allow-unauthenticated \
    --set-env-vars="ENVIRONMENT=staging" \
    --min-instances=0 \
    --max-instances=10 \
    --memory=512Mi \
    --cpu=1 \
    --timeout=300

BACKEND_URL=$(gcloud run services describe ${BACKEND_SERVICE} --region=${STAGING_REGION} --format='value(status.url)')
print_success "Backend deployed to ${BACKEND_URL}"

# Frontend
echo "Deploying frontend service..."
gcloud run deploy ${FRONTEND_SERVICE} \
    --image gcr.io/${STAGING_PROJECT_ID}/${FRONTEND_SERVICE}:latest \
    --platform managed \
    --region ${STAGING_REGION} \
    --allow-unauthenticated \
    --set-env-vars="VITE_API_URL=${BACKEND_URL},VITE_ENVIRONMENT=staging" \
    --min-instances=0 \
    --max-instances=5 \
    --memory=256Mi \
    --cpu=1

FRONTEND_URL=$(gcloud run services describe ${FRONTEND_SERVICE} --region=${STAGING_REGION} --format='value(status.url)')
print_success "Frontend deployed to ${FRONTEND_URL}"

# Step 7: Run smoke tests
print_step "Step 7: Running smoke tests"

echo "Testing backend health endpoint..."
if curl -f "${BACKEND_URL}/api/v1/health" > /dev/null 2>&1; then
    print_success "Backend health check passed"
else
    print_warning "Backend health check failed"
fi

echo "Testing frontend..."
if curl -f "${FRONTEND_URL}" > /dev/null 2>&1; then
    print_success "Frontend health check passed"
else
    print_warning "Frontend health check failed"
fi

# Step 8: Summary
print_step "Deployment Complete!"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Staging Environment URLs${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Frontend: ${BLUE}${FRONTEND_URL}${NC}"
echo -e "Backend:  ${BLUE}${BACKEND_URL}${NC}"
echo -e "API Docs: ${BLUE}${BACKEND_URL}/docs${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Test critical user flows manually"
echo "2. Run E2E tests: cd frontend && npm run test"
echo "3. Monitor logs: gcloud logging tail"
echo "4. If stable, proceed to production deployment"
echo ""
echo -e "${GREEN}Deployment successful! 🚀${NC}"
