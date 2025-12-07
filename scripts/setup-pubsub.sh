#!/bin/bash
# Setup Google Cloud Pub/Sub for GCP Marketplace integration
#
# This script creates:
# 1. Pub/Sub topics for entitlement events
# 2. Pub/Sub subscriptions with push endpoints
# 3. Service account for Pub/Sub push authentication
#
# Usage: ./scripts/setup-pubsub.sh <project-id> <region> <backend-url>
# Example: ./scripts/setup-pubsub.sh my-project us-central1 https://ap2-expense-backend-xyz-uc.a.run.app

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Validate arguments
if [ "$#" -ne 3 ]; then
    echo -e "${RED}Error: Invalid arguments${NC}"
    echo "Usage: $0 <project-id> <region> <backend-url>"
    echo "Example: $0 my-project us-central1 https://ap2-expense-backend-xyz-uc.a.run.app"
    exit 1
fi

PROJECT_ID=$1
REGION=$2
BACKEND_URL=$3

# Remove trailing slash from URL if present
BACKEND_URL=${BACKEND_URL%/}

echo -e "${GREEN}Setting up Pub/Sub for GCP Marketplace${NC}"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Backend URL: $BACKEND_URL"
echo ""

# Set the project
gcloud config set project "$PROJECT_ID"

# Enable Pub/Sub API
echo -e "${YELLOW}Enabling Pub/Sub API...${NC}"
gcloud services enable pubsub.googleapis.com

echo ""
echo -e "${GREEN}Step 1: Creating Pub/Sub Topics${NC}"
echo ""

# Topic for entitlement events (created by GCP Marketplace)
# Note: The actual topic is created by Google when you register your product
# We're creating a topic for testing purposes
TOPIC_NAME="gcp-marketplace-entitlement-events"

echo -e "${YELLOW}Creating topic: $TOPIC_NAME${NC}"

# Check if topic exists
if gcloud pubsub topics describe "$TOPIC_NAME" --project="$PROJECT_ID" &>/dev/null; then
    echo -e "${GREEN}Topic $TOPIC_NAME already exists${NC}"
else
    gcloud pubsub topics create "$TOPIC_NAME" \
        --project="$PROJECT_ID"
    echo -e "${GREEN}✓ Created topic: $TOPIC_NAME${NC}"
fi

echo ""
echo -e "${GREEN}Step 2: Creating Service Account for Pub/Sub Push${NC}"
echo ""

# Create service account for Pub/Sub push (if it doesn't exist)
SA_NAME="pubsub-push-sa"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

if gcloud iam service-accounts describe "$SA_EMAIL" --project="$PROJECT_ID" &>/dev/null; then
    echo -e "${GREEN}Service account $SA_EMAIL already exists${NC}"
else
    echo -e "${YELLOW}Creating service account for Pub/Sub push...${NC}"
    gcloud iam service-accounts create "$SA_NAME" \
        --display-name="Pub/Sub Push Service Account" \
        --project="$PROJECT_ID"
    echo -e "${GREEN}✓ Created service account: $SA_EMAIL${NC}"
fi

# Grant Cloud Run Invoker role to the service account
echo -e "${YELLOW}Granting Cloud Run Invoker role...${NC}"
gcloud run services add-iam-policy-binding ap2-expense-backend \
    --region="$REGION" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/run.invoker" \
    --platform=managed \
    --project="$PROJECT_ID" || true

echo -e "${GREEN}✓ Granted roles/run.invoker to $SA_EMAIL${NC}"

echo ""
echo -e "${GREEN}Step 3: Creating Pub/Sub Subscriptions${NC}"
echo ""

# Subscription for entitlement events
SUBSCRIPTION_NAME="gcp-marketplace-entitlement-events-sub"
PUSH_ENDPOINT="${BACKEND_URL}/api/webhooks/gcp/events"

echo -e "${YELLOW}Creating subscription: $SUBSCRIPTION_NAME${NC}"
echo "Push endpoint: $PUSH_ENDPOINT"

# Delete existing subscription if it exists
gcloud pubsub subscriptions delete "$SUBSCRIPTION_NAME" \
    --project="$PROJECT_ID" \
    --quiet 2>/dev/null || true

# Create push subscription with OIDC authentication
gcloud pubsub subscriptions create "$SUBSCRIPTION_NAME" \
    --topic="$TOPIC_NAME" \
    --push-endpoint="$PUSH_ENDPOINT" \
    --push-auth-service-account="$SA_EMAIL" \
    --push-auth-token-audience="$BACKEND_URL" \
    --ack-deadline=60 \
    --message-retention-duration=7d \
    --expiration-period=never \
    --project="$PROJECT_ID"

echo -e "${GREEN}✓ Created subscription: $SUBSCRIPTION_NAME${NC}"

echo ""
echo -e "${GREEN}Step 4: Setting up IAM Permissions${NC}"
echo ""

# Grant Pub/Sub Publisher role to Google Marketplace
# Note: This is done automatically by Google when you register your product
# But we can grant it to a test service account for local testing

echo -e "${YELLOW}Granting Pub/Sub Publisher role to service account...${NC}"

gcloud pubsub topics add-iam-policy-binding "$TOPIC_NAME" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/pubsub.publisher" \
    --project="$PROJECT_ID" || true

echo -e "${GREEN}✓ Granted roles/pubsub.publisher${NC}"

echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "Created Resources:"
echo "- Pub/Sub topic: $TOPIC_NAME"
echo "- Pub/Sub subscription: $SUBSCRIPTION_NAME (push to $PUSH_ENDPOINT)"
echo "- Service account: $SA_EMAIL"
echo ""
echo "Next steps:"
echo "1. Verify subscription: gcloud pubsub subscriptions describe $SUBSCRIPTION_NAME"
echo "2. Test message publishing:"
echo "   gcloud pubsub topics publish $TOPIC_NAME --message='{\"test\":\"data\"}'"
echo "3. Monitor subscription: gcloud pubsub subscriptions pull $SUBSCRIPTION_NAME --auto-ack --limit=10"
echo "4. View logs: gcloud logging read 'resource.type=cloud_run_revision' --limit=50 --format=json"
echo ""
echo -e "${YELLOW}Important:${NC}"
echo "- When registering with GCP Marketplace, provide topic: projects/$PROJECT_ID/topics/$TOPIC_NAME"
echo "- Google will automatically publish entitlement events to this topic"
echo "- Your backend will receive events at: $PUSH_ENDPOINT"
echo "- OIDC tokens will be verified using audience: $BACKEND_URL"
echo "- Service account: $SA_EMAIL will authenticate push requests"
echo ""
echo -e "${GREEN}Configuration for GCP Marketplace Partner Portal:${NC}"
echo "Topic: projects/$PROJECT_ID/topics/$TOPIC_NAME"
echo "Webhook URL: $PUSH_ENDPOINT"
echo "Authentication: Google OIDC (automatic via push subscription)"
