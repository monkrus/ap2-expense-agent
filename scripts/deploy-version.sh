#!/bin/bash
# Deploy a specific version to Cloud Run
#
# This script deploys a tagged version of the application to Cloud Run.
# It ensures the version exists in GCR before deploying.
#
# Usage: ./scripts/deploy-version.sh <version> <environment> [--traffic-percent]
# Example: ./scripts/deploy-version.sh v1.0.0 production
# Example: ./scripts/deploy-version.sh v1.1.0 staging --traffic-percent=20

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
VERSION=$1
ENVIRONMENT=${2:-production}
TRAFFIC_PERCENT=100

if [ -z "$VERSION" ]; then
    echo -e "${RED}Error: Version argument required${NC}"
    echo "Usage: $0 <version> <environment> [--traffic-percent=N]"
    echo "Example: $0 v1.0.0 production"
    echo "Example: $0 v1.1.0 staging --traffic-percent=20"
    exit 1
fi

# Validate version format
if ! [[ "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo -e "${RED}Error: Invalid version format. Use: vX.Y.Z${NC}"
    exit 1
fi

shift 2
while [ "$#" -gt 0 ]; do
    case "$1" in
        --traffic-percent=*)
            TRAFFIC_PERCENT="${1#*=}"
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Get GCP project ID
if [ -z "$GCP_PROJECT_ID" ]; then
    GCP_PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
fi

if [ -z "$GCP_PROJECT_ID" ]; then
    echo -e "${RED}Error: GCP_PROJECT_ID not set${NC}"
    exit 1
fi

# Configuration based on environment
case "$ENVIRONMENT" in
    production)
        REGION="us-central1"
        MIN_INSTANCES=2
        MAX_INSTANCES=10
        ;;
    staging)
        REGION="us-central1"
        MIN_INSTANCES=1
        MAX_INSTANCES=5
        ;;
    development)
        REGION="us-central1"
        MIN_INSTANCES=0
        MAX_INSTANCES=3
        ;;
    *)
        echo -e "${RED}Error: Invalid environment. Use: production, staging, or development${NC}"
        exit 1
        ;;
esac

REGISTRY="gcr.io/$GCP_PROJECT_ID"
BACKEND_IMAGE="$REGISTRY/ap2-expense-backend:$VERSION"
FRONTEND_IMAGE="$REGISTRY/ap2-expense-frontend:$VERSION"

echo -e "${GREEN}Deploying version $VERSION to $ENVIRONMENT${NC}"
echo "Project: $GCP_PROJECT_ID"
echo "Region: $REGION"
echo "Traffic: $TRAFFIC_PERCENT%"
echo ""

# Verify images exist in registry
echo -e "${YELLOW}Verifying images exist in registry...${NC}"

if ! gcloud container images describe "$BACKEND_IMAGE" --project="$GCP_PROJECT_ID" &>/dev/null; then
    echo -e "${RED}Error: Backend image not found: $BACKEND_IMAGE${NC}"
    echo "Build and push first: ./scripts/build-and-tag.sh $VERSION --push"
    exit 1
fi

if ! gcloud container images describe "$FRONTEND_IMAGE" --project="$GCP_PROJECT_ID" &>/dev/null; then
    echo -e "${RED}Error: Frontend image not found: $FRONTEND_IMAGE${NC}"
    echo "Build and push first: ./scripts/build-and-tag.sh $VERSION --push"
    exit 1
fi

echo -e "${GREEN}✓ Images verified in registry${NC}"
echo ""

# Deploy backend
echo -e "${YELLOW}Deploying backend...${NC}"

# Get current revision before deployment
CURRENT_BACKEND_REVISION=$(gcloud run services describe ap2-expense-backend \
    --region="$REGION" \
    --project="$GCP_PROJECT_ID" \
    --format="value(status.latestReadyRevisionName)" 2>/dev/null || echo "none")

gcloud run deploy ap2-expense-backend \
    --image="$BACKEND_IMAGE" \
    --region="$REGION" \
    --platform=managed \
    --project="$GCP_PROJECT_ID" \
    --min-instances="$MIN_INSTANCES" \
    --max-instances="$MAX_INSTANCES" \
    --memory=2Gi \
    --cpu=2 \
    --timeout=300s \
    --concurrency=80 \
    --service-account="ap2-expense-sa@$GCP_PROJECT_ID.iam.gserviceaccount.com" \
    --add-cloudsql-instances="$GCP_PROJECT_ID:$REGION:ap2-expense-db" \
    --allow-unauthenticated \
    --tag="$VERSION" \
    --no-traffic

echo -e "${GREEN}✓ Backend deployed (revision tagged: $VERSION)${NC}"

# Deploy frontend
echo -e "${YELLOW}Deploying frontend...${NC}"

CURRENT_FRONTEND_REVISION=$(gcloud run services describe ap2-expense-frontend \
    --region="$REGION" \
    --project="$GCP_PROJECT_ID" \
    --format="value(status.latestReadyRevisionName)" 2>/dev/null || echo "none")

gcloud run deploy ap2-expense-frontend \
    --image="$FRONTEND_IMAGE" \
    --region="$REGION" \
    --platform=managed \
    --project="$GCP_PROJECT_ID" \
    --min-instances="$MIN_INSTANCES" \
    --max-instances="$MAX_INSTANCES" \
    --memory=512Mi \
    --cpu=1 \
    --timeout=60s \
    --concurrency=100 \
    --allow-unauthenticated \
    --tag="$VERSION" \
    --no-traffic

echo -e "${GREEN}✓ Frontend deployed (revision tagged: $VERSION)${NC}"
echo ""

# Gradually route traffic to new version
echo -e "${YELLOW}Routing $TRAFFIC_PERCENT% traffic to new version...${NC}"

# Get new revision names
NEW_BACKEND_REVISION=$(gcloud run services describe ap2-expense-backend \
    --region="$REGION" \
    --project="$GCP_PROJECT_ID" \
    --format="value(status.latestReadyRevisionName)")

NEW_FRONTEND_REVISION=$(gcloud run services describe ap2-expense-frontend \
    --region="$REGION" \
    --project="$GCP_PROJECT_ID" \
    --format="value(status.latestReadyRevisionName)")

# Route traffic
if [ "$TRAFFIC_PERCENT" -eq 100 ]; then
    # Route 100% traffic to new version
    gcloud run services update-traffic ap2-expense-backend \
        --to-latest \
        --region="$REGION" \
        --project="$GCP_PROJECT_ID"

    gcloud run services update-traffic ap2-expense-frontend \
        --to-latest \
        --region="$REGION" \
        --project="$GCP_PROJECT_ID"

    echo -e "${GREEN}✓ Routed 100% traffic to new version${NC}"
else
    # Split traffic (canary deployment)
    REMAINING_PERCENT=$((100 - TRAFFIC_PERCENT))

    gcloud run services update-traffic ap2-expense-backend \
        --to-revisions="$NEW_BACKEND_REVISION=$TRAFFIC_PERCENT,$CURRENT_BACKEND_REVISION=$REMAINING_PERCENT" \
        --region="$REGION" \
        --project="$GCP_PROJECT_ID"

    gcloud run services update-traffic ap2-expense-frontend \
        --to-revisions="$NEW_FRONTEND_REVISION=$TRAFFIC_PERCENT,$CURRENT_FRONTEND_REVISION=$REMAINING_PERCENT" \
        --region="$REGION" \
        --project="$GCP_PROJECT_ID"

    echo -e "${GREEN}✓ Split traffic: $TRAFFIC_PERCENT% to $VERSION, $REMAINING_PERCENT% to previous${NC}"
fi

echo ""
echo -e "${GREEN}Deployment complete!${NC}"
echo ""
echo "Version: $VERSION"
echo "Environment: $ENVIRONMENT"
echo "Traffic: $TRAFFIC_PERCENT%"
echo ""
echo "Service URLs:"
BACKEND_URL=$(gcloud run services describe ap2-expense-backend --region="$REGION" --project="$GCP_PROJECT_ID" --format="value(status.url)")
FRONTEND_URL=$(gcloud run services describe ap2-expense-frontend --region="$REGION" --project="$GCP_PROJECT_ID" --format="value(status.url)")
echo "  Backend: $BACKEND_URL"
echo "  Frontend: $FRONTEND_URL"
echo ""
echo "Revision-specific URLs (for testing):"
echo "  Backend ($VERSION): https://$VERSION---ap2-expense-backend-<hash>-uc.a.run.app"
echo "  Frontend ($VERSION): https://$VERSION---ap2-expense-frontend-<hash>-uc.a.run.app"
echo ""

if [ "$TRAFFIC_PERCENT" -ne 100 ]; then
    echo -e "${YELLOW}Canary deployment active${NC}"
    echo "Monitor metrics, then:"
    echo "  - Increase traffic: ./scripts/deploy-version.sh $VERSION $ENVIRONMENT --traffic-percent=50"
    echo "  - Full rollout: ./scripts/deploy-version.sh $VERSION $ENVIRONMENT --traffic-percent=100"
    echo "  - Rollback: ./scripts/rollback-deployment.sh <previous-version>"
fi

echo ""
echo "Next steps:"
echo "1. Run smoke tests: ./scripts/smoke-test.sh $ENVIRONMENT"
echo "2. Monitor logs: gcloud run services logs read ap2-expense-backend --region=$REGION"
echo "3. Check metrics: https://console.cloud.google.com/run?project=$GCP_PROJECT_ID"
