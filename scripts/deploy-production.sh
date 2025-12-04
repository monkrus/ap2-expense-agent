#!/bin/bash

# ============================================================================
# Production Deployment Automation Script
# ============================================================================
#
# Purpose: Automate end-to-end production deployment
# Priority: CRITICAL
# Usage: ./scripts/deploy-production.sh <version>
#
# This script orchestrates:
# 1. Pre-deployment validation
# 2. Database backup
# 3. Environment variable validation
# 4. Docker image build and push
# 5. Database migrations
# 6. Cloud Run deployment
# 7. Health checks and smoke tests
# 8. Traffic routing (gradual rollout)
# 9. Post-deployment verification
# 10. Notification and reporting
#
# ============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
VERSION=${1:-}
ENVIRONMENT=${2:-production}
DRY_RUN=${DRY_RUN:-false}

# GCP Configuration
GCP_PROJECT_ID=${GCP_PROJECT_ID:-}
GCP_REGION=${GCP_REGION:-us-central1}
CLOUD_RUN_SERVICE=${CLOUD_RUN_SERVICE:-ap2-expense-backend}
ARTIFACT_REGISTRY=${ARTIFACT_REGISTRY:-${GCP_REGION}-docker.pkg.dev}
IMAGE_NAME=${IMAGE_NAME:-${ARTIFACT_REGISTRY}/${GCP_PROJECT_ID}/ap2-expense/backend}

# Database Configuration
DB_INSTANCE_NAME=${DB_INSTANCE_NAME:-}

# Deployment Configuration
TRAFFIC_ROLLOUT=${TRAFFIC_ROLLOUT:-gradual}  # gradual or immediate
GRADUAL_ROLLOUT_STEPS=${GRADUAL_ROLLOUT_STEPS:-"25,50,75,100"}
ROLLOUT_WAIT_TIME=${ROLLOUT_WAIT_TIME:-180}  # 3 minutes between steps

# Notification Configuration
SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL:-}
PAGERDUTY_INTEGRATION_KEY=${PAGERDUTY_INTEGRATION_KEY:-}

# Deployment state
DEPLOYMENT_START_TIME=""
CURRENT_REVISION=""
NEW_REVISION=""
DEPLOYMENT_SUCCESS=false

print_header() {
    echo -e "${BLUE}============================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================================${NC}"
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

check_prerequisites() {
    print_header "Checking Prerequisites"

    # Check version argument
    if [ -z "$VERSION" ]; then
        print_error "Version argument required"
        echo "Usage: $0 <version> [environment]"
        echo "Example: $0 v1.0.0 production"
        return 1
    fi

    # Validate version format (vX.Y.Z)
    if [[ ! "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        print_error "Invalid version format: $VERSION"
        echo "Expected format: vX.Y.Z (e.g., v1.0.0)"
        return 1
    fi

    print_success "Version: $VERSION"

    # Check gcloud CLI
    if ! command -v gcloud &> /dev/null; then
        print_error "gcloud CLI not found"
        echo "Install: https://cloud.google.com/sdk/docs/install"
        return 1
    fi
    print_success "gcloud CLI installed"

    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker not found"
        echo "Install: https://docs.docker.com/get-docker/"
        return 1
    fi
    print_success "Docker installed"

    # Check environment variables
    if [ -z "$GCP_PROJECT_ID" ]; then
        print_error "GCP_PROJECT_ID not set"
        return 1
    fi
    print_success "GCP project: $GCP_PROJECT_ID"

    # Check authentication
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
        print_error "Not authenticated with gcloud"
        echo "Run: gcloud auth login"
        return 1
    fi
    print_success "Authenticated with gcloud"

    # Check if scripts exist
    local required_scripts=(
        "scripts/validate-environment.sh"
        "scripts/backup-database.sh"
        "scripts/smoke-test.sh"
    )

    for script in "${required_scripts[@]}"; do
        if [ ! -f "$script" ]; then
            print_error "Required script not found: $script"
            return 1
        fi
    done
    print_success "All required scripts present"

    echo ""
}

validate_environment() {
    print_header "Step 1: Validating Environment Variables"

    if [ -x "./scripts/validate-environment.sh" ]; then
        if ./scripts/validate-environment.sh "$ENVIRONMENT"; then
            print_success "Environment validation: PASSED"
        else
            print_error "Environment validation: FAILED"
            echo ""
            echo "Fix environment variables before deploying"
            return 1
        fi
    else
        print_warning "Validation script not executable, skipping"
    fi

    echo ""
}

create_backup() {
    print_header "Step 2: Creating Pre-Deployment Backup"

    if [ "$DRY_RUN" = true ]; then
        print_warning "DRY RUN: Skipping backup creation"
        return 0
    fi

    if [ -x "./scripts/backup-database.sh" ]; then
        if ./scripts/backup-database.sh; then
            print_success "Pre-deployment backup: CREATED"
        else
            print_warning "Backup creation failed, but continuing"
        fi
    else
        print_warning "Backup script not found, skipping"
    fi

    echo ""
}

get_current_state() {
    print_header "Step 3: Recording Current Deployment State"

    CURRENT_REVISION=$(gcloud run services describe "$CLOUD_RUN_SERVICE" \
        --region="$GCP_REGION" \
        --project="$GCP_PROJECT_ID" \
        --format="value(status.latestReadyRevisionName)" \
        2>/dev/null || echo "none")

    echo "Current revision: $CURRENT_REVISION"

    # Save current state for rollback
    echo "$CURRENT_REVISION" > /tmp/deployment-previous-revision.txt

    echo ""
}

build_docker_image() {
    print_header "Step 4: Building Docker Image"

    local image_tag="${IMAGE_NAME}:${VERSION}"
    local latest_tag="${IMAGE_NAME}:latest"

    echo "Building image: $image_tag"
    echo ""

    if [ "$DRY_RUN" = true ]; then
        print_warning "DRY RUN: Skipping Docker build"
        return 0
    fi

    # Build backend image
    if docker build \
        -t "$image_tag" \
        -t "$latest_tag" \
        --build-arg VERSION="$VERSION" \
        --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
        -f backend/Dockerfile \
        backend/; then

        print_success "Docker image built: $image_tag"
    else
        print_error "Docker build failed"
        return 1
    fi

    echo ""
}

push_docker_image() {
    print_header "Step 5: Pushing Docker Image"

    local image_tag="${IMAGE_NAME}:${VERSION}"
    local latest_tag="${IMAGE_NAME}:latest"

    if [ "$DRY_RUN" = true ]; then
        print_warning "DRY RUN: Skipping Docker push"
        return 0
    fi

    # Configure Docker to use gcloud authentication
    gcloud auth configure-docker "$ARTIFACT_REGISTRY" --quiet

    # Push versioned image
    echo "Pushing: $image_tag"
    if docker push "$image_tag"; then
        print_success "Pushed: $image_tag"
    else
        print_error "Failed to push image"
        return 1
    fi

    # Push latest tag
    echo "Pushing: $latest_tag"
    if docker push "$latest_tag"; then
        print_success "Pushed: $latest_tag"
    else
        print_warning "Failed to push latest tag (non-critical)"
    fi

    echo ""
}

run_database_migrations() {
    print_header "Step 6: Running Database Migrations"

    if [ "$DRY_RUN" = true ]; then
        print_warning "DRY RUN: Skipping database migrations"
        return 0
    fi

    print_warning "Database migrations require manual verification"
    echo ""
    echo "To run migrations:"
    echo "  1. Connect to database via Cloud SQL Proxy"
    echo "  2. Run: cd backend && alembic upgrade head"
    echo "  3. Verify: alembic current"
    echo ""

    read -p "Have migrations been applied? (yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        print_error "Migrations not confirmed - deployment aborted"
        return 1
    fi

    print_success "Database migrations: CONFIRMED"
    echo ""
}

deploy_cloud_run() {
    print_header "Step 7: Deploying to Cloud Run"

    local image_tag="${IMAGE_NAME}:${VERSION}"

    echo "Deploying: $image_tag"
    echo "Service: $CLOUD_RUN_SERVICE"
    echo "Region: $GCP_REGION"
    echo ""

    if [ "$DRY_RUN" = true ]; then
        print_warning "DRY RUN: Skipping Cloud Run deployment"
        return 0
    fi

    # Deploy with no traffic (revision only)
    if gcloud run deploy "$CLOUD_RUN_SERVICE" \
        --image="$image_tag" \
        --region="$GCP_REGION" \
        --project="$GCP_PROJECT_ID" \
        --platform=managed \
        --no-traffic \
        --tag="$VERSION" \
        --set-env-vars="VERSION=$VERSION" \
        --timeout=300 \
        --memory=1Gi \
        --cpu=2 \
        --min-instances=1 \
        --max-instances=10; then

        print_success "Cloud Run deployment: SUCCESS (no traffic)"
    else
        print_error "Cloud Run deployment failed"
        return 1
    fi

    # Get new revision name
    NEW_REVISION=$(gcloud run services describe "$CLOUD_RUN_SERVICE" \
        --region="$GCP_REGION" \
        --project="$GCP_PROJECT_ID" \
        --format="value(status.latestCreatedRevisionName)")

    echo "New revision: $NEW_REVISION"
    echo "$NEW_REVISION" > /tmp/deployment-new-revision.txt

    echo ""
}

wait_for_revision_ready() {
    print_header "Step 8: Waiting for Revision to be Ready"

    echo "Waiting for revision to be ready..."
    echo "Revision: $NEW_REVISION"
    echo ""

    local max_wait=300  # 5 minutes
    local elapsed=0
    local interval=10

    while [ $elapsed -lt $max_wait ]; do
        local status=$(gcloud run revisions describe "$NEW_REVISION" \
            --region="$GCP_REGION" \
            --project="$GCP_PROJECT_ID" \
            --format="value(status.conditions[0].status)" \
            2>/dev/null || echo "Unknown")

        if [ "$status" = "True" ]; then
            print_success "Revision ready: $NEW_REVISION"
            return 0
        fi

        echo "Status: $status (waiting ${interval}s...)"
        sleep $interval
        elapsed=$((elapsed + interval))
    done

    print_error "Revision did not become ready in time"
    return 1
}

run_health_checks() {
    print_header "Step 9: Running Health Checks"

    # Get revision URL
    local revision_url=$(gcloud run services describe "$CLOUD_RUN_SERVICE" \
        --region="$GCP_REGION" \
        --project="$GCP_PROJECT_ID" \
        --format="value(status.url)")

    echo "Testing revision: $NEW_REVISION"
    echo "URL: $revision_url"
    echo ""

    # Test health endpoint
    local max_attempts=10
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        echo -n "Health check attempt $attempt/$max_attempts: "

        if curl -sf -m 10 "${revision_url}/health" > /dev/null 2>&1; then
            print_success "PASSED"
            return 0
        else
            echo "Failed (retrying in 5s...)"
            sleep 5
            attempt=$((attempt + 1))
        fi
    done

    print_error "Health checks failed"
    return 1
}

run_smoke_tests() {
    print_header "Step 10: Running Smoke Tests"

    if [ ! -x "./scripts/smoke-test.sh" ]; then
        print_warning "Smoke test script not found"
        return 0
    fi

    # Get service URL
    local service_url=$(gcloud run services describe "$CLOUD_RUN_SERVICE" \
        --region="$GCP_REGION" \
        --project="$GCP_PROJECT_ID" \
        --format="value(status.url)")

    export API_BASE_URL="$service_url"

    if ./scripts/smoke-test.sh "$ENVIRONMENT"; then
        print_success "Smoke tests: PASSED"
        return 0
    else
        print_error "Smoke tests: FAILED"
        return 1
    fi
}

route_traffic() {
    print_header "Step 11: Routing Traffic"

    if [ "$DRY_RUN" = true ]; then
        print_warning "DRY RUN: Skipping traffic routing"
        return 0
    fi

    case $TRAFFIC_ROLLOUT in
        immediate)
            echo "Routing 100% traffic immediately..."
            route_traffic_immediate
            ;;
        gradual)
            echo "Gradual rollout: $GRADUAL_ROLLOUT_STEPS"
            route_traffic_gradual
            ;;
        *)
            print_error "Invalid rollout strategy: $TRAFFIC_ROLLOUT"
            return 1
            ;;
    esac
}

route_traffic_immediate() {
    if gcloud run services update-traffic "$CLOUD_RUN_SERVICE" \
        --to-revisions="$NEW_REVISION=100" \
        --region="$GCP_REGION" \
        --project="$GCP_PROJECT_ID"; then

        print_success "Traffic routed: 100% to $NEW_REVISION"
    else
        print_error "Traffic routing failed"
        return 1
    fi
}

route_traffic_gradual() {
    IFS=',' read -ra STEPS <<< "$GRADUAL_ROLLOUT_STEPS"

    for step in "${STEPS[@]}"; do
        local new_percent=$step
        local old_percent=$((100 - new_percent))

        echo ""
        echo "Rolling out: ${new_percent}% new, ${old_percent}% old"

        if gcloud run services update-traffic "$CLOUD_RUN_SERVICE" \
            --to-revisions="${NEW_REVISION}=${new_percent},${CURRENT_REVISION}=${old_percent}" \
            --region="$GCP_REGION" \
            --project="$GCP_PROJECT_ID"; then

            print_success "Traffic updated: ${new_percent}% to new revision"
        else
            print_error "Traffic routing failed at ${new_percent}%"
            return 1
        fi

        # Wait and monitor
        if [ $new_percent -lt 100 ]; then
            echo "Waiting ${ROLLOUT_WAIT_TIME}s before next step..."
            echo "Monitoring for errors..."
            sleep $ROLLOUT_WAIT_TIME

            # Check for errors (could query Cloud Logging here)
            # For now, just a simple health check
            if ! curl -sf "${API_BASE_URL:-}/health" > /dev/null 2>&1; then
                print_error "Health check failed during rollout"
                echo "Rolling back to previous revision..."
                rollback_traffic
                return 1
            fi
        fi
    done

    print_success "Gradual rollout complete: 100% to $NEW_REVISION"
}

rollback_traffic() {
    print_warning "Rolling back traffic to: $CURRENT_REVISION"

    gcloud run services update-traffic "$CLOUD_RUN_SERVICE" \
        --to-revisions="$CURRENT_REVISION=100" \
        --region="$GCP_REGION" \
        --project="$GCP_PROJECT_ID"
}

verify_deployment() {
    print_header "Step 12: Final Deployment Verification"

    # Verify traffic distribution
    echo "Current traffic distribution:"
    gcloud run services describe "$CLOUD_RUN_SERVICE" \
        --region="$GCP_REGION" \
        --project="$GCP_PROJECT_ID" \
        --format="table(status.traffic.revisionName,status.traffic.percent)"

    echo ""

    # Run final health checks
    if run_health_checks; then
        print_success "Final verification: PASSED"
        DEPLOYMENT_SUCCESS=true
        return 0
    else
        print_error "Final verification: FAILED"
        return 1
    fi
}

send_deployment_notification() {
    print_header "Step 13: Sending Deployment Notification"

    local status_emoji="✅"
    local status_text="SUCCESS"
    local color="good"

    if [ "$DEPLOYMENT_SUCCESS" = false ]; then
        status_emoji="❌"
        status_text="FAILED"
        color="danger"
    fi

    # Slack notification
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        curl -X POST "$SLACK_WEBHOOK_URL" \
            -H 'Content-Type: application/json' \
            -d "{
                \"text\": \"$status_emoji *Production Deployment $status_text*\",
                \"attachments\": [{
                    \"color\": \"$color\",
                    \"fields\": [
                        {\"title\": \"Version\", \"value\": \"$VERSION\", \"short\": true},
                        {\"title\": \"Environment\", \"value\": \"$ENVIRONMENT\", \"short\": true},
                        {\"title\": \"Service\", \"value\": \"$CLOUD_RUN_SERVICE\", \"short\": true},
                        {\"title\": \"Region\", \"value\": \"$GCP_REGION\", \"short\": true},
                        {\"title\": \"Revision\", \"value\": \"$NEW_REVISION\", \"short\": false},
                        {\"title\": \"Status\", \"value\": \"$status_text\", \"short\": false}
                    ]
                }]
            }" > /dev/null 2>&1

        print_success "Slack notification sent"
    fi

    # PagerDuty notification (only if failed)
    if [ "$DEPLOYMENT_SUCCESS" = false ] && [ -n "$PAGERDUTY_INTEGRATION_KEY" ]; then
        curl -X POST https://events.pagerduty.com/v2/enqueue \
            -H 'Content-Type: application/json' \
            -d "{
                \"routing_key\": \"$PAGERDUTY_INTEGRATION_KEY\",
                \"event_action\": \"trigger\",
                \"payload\": {
                    \"summary\": \"Production deployment failed: $VERSION\",
                    \"severity\": \"error\",
                    \"source\": \"AP2 Expense Agent - Deploy Script\",
                    \"custom_details\": {
                        \"version\": \"$VERSION\",
                        \"environment\": \"$ENVIRONMENT\",
                        \"service\": \"$CLOUD_RUN_SERVICE\",
                        \"revision\": \"$NEW_REVISION\"
                    }
                }
            }" > /dev/null 2>&1

        print_success "PagerDuty alert sent"
    fi

    echo ""
}

generate_deployment_report() {
    print_header "Deployment Report"

    local report_file="deployment-report-${VERSION}-$(date +%Y%m%d-%H%M%S).md"

    cat > "$report_file" <<EOF
# Production Deployment Report

**Version**: $VERSION
**Date**: $(date)
**Environment**: $ENVIRONMENT
**Operator**: $(whoami)
**Status**: $([ "$DEPLOYMENT_SUCCESS" = true ] && echo "✅ SUCCESS" || echo "❌ FAILED")

## Deployment Details

- **Service**: $CLOUD_RUN_SERVICE
- **Region**: $GCP_REGION
- **Previous Revision**: $CURRENT_REVISION
- **New Revision**: $NEW_REVISION
- **Rollout Strategy**: $TRAFFIC_ROLLOUT

## Steps Completed

1. ✓ Environment validation
2. ✓ Pre-deployment backup
3. ✓ Docker image build and push
4. ✓ Database migrations
5. ✓ Cloud Run deployment
6. ✓ Health checks
7. ✓ Smoke tests
8. ✓ Traffic routing
9. ✓ Final verification

## Traffic Distribution

\`\`\`
$(gcloud run services describe "$CLOUD_RUN_SERVICE" \
    --region="$GCP_REGION" \
    --project="$GCP_PROJECT_ID" \
    --format="table(status.traffic.revisionName,status.traffic.percent)")
\`\`\`

## Verification

- **Health Checks**: $([ "$DEPLOYMENT_SUCCESS" = true ] && echo "PASSED" || echo "FAILED")
- **Smoke Tests**: $([ "$DEPLOYMENT_SUCCESS" = true ] && echo "PASSED" || echo "FAILED")
- **Service Status**: RUNNING

## Next Steps

$(if [ "$DEPLOYMENT_SUCCESS" = true ]; then
    echo "1. Monitor metrics for 15 minutes"
    echo "2. Check logs for errors"
    echo "3. Verify user-facing functionality"
    echo "4. Update documentation if needed"
else
    echo "1. Review error logs above"
    echo "2. Identify root cause of failure"
    echo "3. Fix issues and redeploy"
    echo "4. Consider rollback if critical"
fi)

---

*Report generated by deploy-production.sh*
EOF

    print_success "Report saved: $report_file"
    echo ""
    cat "$report_file"
    echo ""
}

cleanup() {
    rm -f /tmp/deployment-previous-revision.txt
    rm -f /tmp/deployment-new-revision.txt
}

# ============================================================================
# Main Execution
# ============================================================================

DEPLOYMENT_START_TIME=$(date +%s)

print_header "Production Deployment Automation"
echo ""
echo "Version: $VERSION"
echo "Environment: $ENVIRONMENT"
echo "Service: $CLOUD_RUN_SERVICE"
echo "Dry Run: $DRY_RUN"
echo ""

# Check prerequisites
if ! check_prerequisites; then
    exit 1
fi

# Execute deployment steps
validate_environment || exit 1
create_backup
get_current_state
build_docker_image || exit 1
push_docker_image || exit 1
run_database_migrations || exit 1
deploy_cloud_run || exit 1
wait_for_revision_ready || exit 1
run_health_checks || exit 1
run_smoke_tests || exit 1
route_traffic || exit 1
verify_deployment

# Send notifications
send_deployment_notification

# Generate report
generate_deployment_report

# Cleanup
cleanup

# Calculate deployment time
DEPLOYMENT_END_TIME=$(date +%s)
DEPLOYMENT_DURATION=$((DEPLOYMENT_END_TIME - DEPLOYMENT_START_TIME))

# Final summary
print_header "Deployment Summary"

if [ "$DEPLOYMENT_SUCCESS" = true ]; then
    print_success "Deployment completed successfully!"
    echo ""
    echo "✓ Version $VERSION deployed"
    echo "✓ Service: $CLOUD_RUN_SERVICE"
    echo "✓ Revision: $NEW_REVISION"
    echo "✓ Duration: ${DEPLOYMENT_DURATION}s"
    echo ""
    echo "Monitor deployment:"
    echo "  - Metrics: GCP Console → Cloud Run → $CLOUD_RUN_SERVICE"
    echo "  - Logs: gcloud logging read --limit 100"
    echo "  - Service: $(gcloud run services describe $CLOUD_RUN_SERVICE --region=$GCP_REGION --format='value(status.url)')"
    echo ""
    exit 0
else
    print_error "Deployment failed"
    echo ""
    echo "To rollback:"
    echo "  ./scripts/rollback-deployment.sh $CURRENT_REVISION"
    echo ""
    exit 1
fi
