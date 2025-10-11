#!/bin/bash
# Build and push Docker images to Google Artifact Registry
# Usage: ./build-and-push.sh [PROJECT_ID] [VERSION]

set -e

# Configuration
PROJECT_ID="${1:-YOUR_PROJECT_ID}"
VERSION="${2:-latest}"
REGION="us-central1"
REPOSITORY="ap2-expense"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Building and pushing AP2 Expense Agent images${NC}"
echo -e "Project ID: ${YELLOW}${PROJECT_ID}${NC}"
echo -e "Version: ${YELLOW}${VERSION}${NC}"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI not found. Please install it first.${NC}"
    exit 1
fi

# Configure Docker for Artifact Registry
echo -e "${GREEN}[1/5] Configuring Docker authentication...${NC}"
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Create Artifact Registry repository if it doesn't exist
echo -e "${GREEN}[2/5] Ensuring Artifact Registry repository exists...${NC}"
gcloud artifacts repositories describe ${REPOSITORY} \
    --location=${REGION} \
    --project=${PROJECT_ID} &> /dev/null || \
gcloud artifacts repositories create ${REPOSITORY} \
    --repository-format=docker \
    --location=${REGION} \
    --description="AP2 Expense Management Agent" \
    --project=${PROJECT_ID}

# Build backend image
echo -e "${GREEN}[3/5] Building backend image...${NC}"
cd backend
BACKEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/backend:${VERSION}"
docker build -t ${BACKEND_IMAGE} .
echo -e "${GREEN}Backend image built: ${BACKEND_IMAGE}${NC}"

# Build frontend image
echo -e "${GREEN}[4/5] Building frontend image...${NC}"
cd ../frontend
FRONTEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/frontend:${VERSION}"
docker build -t ${FRONTEND_IMAGE} .
echo -e "${GREEN}Frontend image built: ${FRONTEND_IMAGE}${NC}"

# Push images
echo -e "${GREEN}[5/5] Pushing images to Artifact Registry...${NC}"
docker push ${BACKEND_IMAGE}
echo -e "${GREEN}✓ Backend image pushed${NC}"

docker push ${FRONTEND_IMAGE}
echo -e "${GREEN}✓ Frontend image pushed${NC}"

# Tag as latest if version is not "latest"
if [ "$VERSION" != "latest" ]; then
    echo -e "${YELLOW}Tagging images as 'latest'...${NC}"

    BACKEND_LATEST="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/backend:latest"
    FRONTEND_LATEST="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/frontend:latest"

    docker tag ${BACKEND_IMAGE} ${BACKEND_LATEST}
    docker tag ${FRONTEND_IMAGE} ${FRONTEND_LATEST}

    docker push ${BACKEND_LATEST}
    docker push ${FRONTEND_LATEST}

    echo -e "${GREEN}✓ Latest tags pushed${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Build and push completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Backend image:  ${YELLOW}${BACKEND_IMAGE}${NC}"
echo -e "Frontend image: ${YELLOW}${FRONTEND_IMAGE}${NC}"
echo ""
echo -e "Next steps:"
echo -e "1. Update k8s/*.yaml files with PROJECT_ID: ${YELLOW}${PROJECT_ID}${NC}"
echo -e "2. Deploy to Kubernetes: ${YELLOW}kubectl apply -f k8s/${NC}"
echo -e "3. Check deployment status: ${YELLOW}kubectl get pods -n ap2-expense${NC}"
