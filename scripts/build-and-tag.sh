#!/bin/bash
# Build and tag Docker images with semantic versioning
#
# This script builds Docker images and tags them with:
# 1. Semantic version (e.g., v1.0.0, v1.2.3)
# 2. Commit SHA (for traceability)
# 3. Latest tag (optional, for current stable release)
#
# Usage: ./scripts/build-and-tag.sh <version> [--push] [--latest]
# Example: ./scripts/build-and-tag.sh v1.0.0 --push --latest

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
VERSION=$1
PUSH=false
TAG_LATEST=false

if [ -z "$VERSION" ]; then
    echo -e "${RED}Error: Version argument required${NC}"
    echo "Usage: $0 <version> [--push] [--latest]"
    echo "Example: $0 v1.0.0 --push --latest"
    exit 1
fi

# Validate version format (vX.Y.Z)
if ! [[ "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo -e "${RED}Error: Invalid version format. Use semantic versioning: vX.Y.Z${NC}"
    echo "Example: v1.0.0, v2.1.3"
    exit 1
fi

shift
while [ "$#" -gt 0 ]; do
    case "$1" in
        --push)
            PUSH=true
            shift
            ;;
        --latest)
            TAG_LATEST=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Get current commit SHA (short version)
COMMIT_SHA=$(git rev-parse --short HEAD)

# Get GCP project ID from gcloud config or environment
if [ -z "$GCP_PROJECT_ID" ]; then
    GCP_PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
fi

if [ -z "$GCP_PROJECT_ID" ]; then
    echo -e "${RED}Error: GCP_PROJECT_ID not set${NC}"
    echo "Set it via: export GCP_PROJECT_ID=your-project-id"
    echo "Or configure: gcloud config set project your-project-id"
    exit 1
fi

# Container registry
REGISTRY="gcr.io/$GCP_PROJECT_ID"

# Image names
BACKEND_IMAGE="ap2-expense-backend"
FRONTEND_IMAGE="ap2-expense-frontend"

echo -e "${GREEN}Building and tagging Docker images${NC}"
echo "Version: $VERSION"
echo "Commit SHA: $COMMIT_SHA"
echo "Registry: $REGISTRY"
echo "Push to registry: $PUSH"
echo "Tag as latest: $TAG_LATEST"
echo ""

# Build backend image
echo -e "${YELLOW}Building backend image...${NC}"
docker build \
    -f Dockerfile.backend \
    -t "$REGISTRY/$BACKEND_IMAGE:$VERSION" \
    -t "$REGISTRY/$BACKEND_IMAGE:$COMMIT_SHA" \
    --build-arg VERSION="$VERSION" \
    --build-arg COMMIT_SHA="$COMMIT_SHA" \
    --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
    .

if [ "$TAG_LATEST" = true ]; then
    docker tag "$REGISTRY/$BACKEND_IMAGE:$VERSION" "$REGISTRY/$BACKEND_IMAGE:latest"
fi

echo -e "${GREEN}✓ Backend image built${NC}"

# Build frontend image
echo -e "${YELLOW}Building frontend image...${NC}"
docker build \
    -f Dockerfile.frontend \
    -t "$REGISTRY/$FRONTEND_IMAGE:$VERSION" \
    -t "$REGISTRY/$FRONTEND_IMAGE:$COMMIT_SHA" \
    --build-arg VERSION="$VERSION" \
    --build-arg COMMIT_SHA="$COMMIT_SHA" \
    --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
    .

if [ "$TAG_LATEST" = true ]; then
    docker tag "$REGISTRY/$FRONTEND_IMAGE:$VERSION" "$REGISTRY/$FRONTEND_IMAGE:latest"
fi

echo -e "${GREEN}✓ Frontend image built${NC}"
echo ""

# List created images
echo -e "${GREEN}Created images:${NC}"
docker images "$REGISTRY/$BACKEND_IMAGE" --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" | head -5
docker images "$REGISTRY/$FRONTEND_IMAGE" --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}" | head -5

# Push to registry if requested
if [ "$PUSH" = true ]; then
    echo ""
    echo -e "${YELLOW}Pushing images to registry...${NC}"

    # Backend
    docker push "$REGISTRY/$BACKEND_IMAGE:$VERSION"
    docker push "$REGISTRY/$BACKEND_IMAGE:$COMMIT_SHA"

    if [ "$TAG_LATEST" = true ]; then
        docker push "$REGISTRY/$BACKEND_IMAGE:latest"
    fi

    # Frontend
    docker push "$REGISTRY/$FRONTEND_IMAGE:$VERSION"
    docker push "$REGISTRY/$FRONTEND_IMAGE:$COMMIT_SHA"

    if [ "$TAG_LATEST" = true ]; then
        docker push "$REGISTRY/$FRONTEND_IMAGE:latest"
    fi

    echo -e "${GREEN}✓ Images pushed to registry${NC}"
fi

echo ""
echo -e "${GREEN}Build complete!${NC}"
echo ""
echo "Image tags created:"
echo "  Backend:"
echo "    - $REGISTRY/$BACKEND_IMAGE:$VERSION"
echo "    - $REGISTRY/$BACKEND_IMAGE:$COMMIT_SHA"
if [ "$TAG_LATEST" = true ]; then
    echo "    - $REGISTRY/$BACKEND_IMAGE:latest"
fi
echo "  Frontend:"
echo "    - $REGISTRY/$FRONTEND_IMAGE:$VERSION"
echo "    - $REGISTRY/$FRONTEND_IMAGE:$COMMIT_SHA"
if [ "$TAG_LATEST" = true ]; then
    echo "    - $REGISTRY/$FRONTEND_IMAGE:latest"
fi
echo ""

if [ "$PUSH" = false ]; then
    echo -e "${YELLOW}Images not pushed to registry. Run with --push to push.${NC}"
fi

echo ""
echo "Next steps:"
echo "1. Test images locally: docker run -p 8000:8000 $REGISTRY/$BACKEND_IMAGE:$VERSION"
echo "2. Deploy to Cloud Run: ./scripts/deploy-version.sh $VERSION"
echo "3. Create git tag: git tag $VERSION && git push origin $VERSION"
echo "4. Update CHANGELOG.md with release notes"
