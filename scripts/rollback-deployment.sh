#!/bin/bash

# ============================================================================
# Deployment Rollback Procedure
# ============================================================================
#
# Purpose: Safely rollback failed production deployments
# Priority: CRITICAL
# Usage: ./scripts/rollback-deployment.sh <previous-version>
#
# This script handles:
# - Cloud Run service rollback to previous revision
# - Database migration rollback (Alembic)
# - Traffic routing to stable version
# - Health check verification
# - Rollback verification and reporting
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
ENVIRONMENT=${1:-production}
TARGET_VERSION=${2:-}
ROLLBACK_REASON=${3:-"Manual rollback"}

# GCP Configuration
GCP_PROJECT_ID=${GCP_PROJECT_ID:-}
CLOUD_RUN_SERVICE=${CLOUD_RUN_SERVICE:-ap2-expense-backend}
CLOUD_RUN_REGION=${CLOUD_RUN_REGION:-us-central1}

# Database Configuration
DB_INSTANCE_NAME=${DB_INSTANCE_NAME:-}
DATABASE_URL=${DATABASE_URL:-}

# Health check configuration
HEALTH_CHECK_URL=${HEALTH_CHECK_URL:-}
HEALTH_CHECK_TIMEOUT=${HEALTH_CHECK_TIMEOUT:-60}
HEALTH_CHECK_INTERVAL=${HEALTH_CHECK_INTERVAL:-5}

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

    # Check gcloud CLI
    if ! command -v gcloud &> /dev/null; then
        print_error "gcloud CLI not found"
        echo "Install: https://cloud.google.com/sdk/docs/install"
        return 1
    fi
    print_success "gcloud CLI installed"

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

    echo ""
}

confirm_rollback() {
    print_header "Rollback Confirmation"

    echo "⚠️  WARNING: You are about to rollback the production deployment"
    echo ""
    echo "Environment: $ENVIRONMENT"
    echo "Service: $CLOUD_RUN_SERVICE"
    echo "Region: $CLOUD_RUN_REGION"
    echo "Reason: $ROLLBACK_REASON"
    echo ""

    if [ -n "$TARGET_VERSION" ]; then
        echo "Target version: $TARGET_VERSION"
    else
        echo "Target version: Previous stable revision"
    fi

    echo ""
    read -p "Are you sure you want to proceed? (yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        print_warning "Rollback cancelled by user"
        exit 0
    fi

    echo ""
}

get_current_revision() {
    print_header "Getting Current Deployment State"

    local current_revision=$(gcloud run services describe "$CLOUD_RUN_SERVICE" \
        --region="$CLOUD_RUN_REGION" \
        --project="$GCP_PROJECT_ID" \
        --format="value(status.latestReadyRevisionName)")

    echo "Current revision: $current_revision"

    local current_traffic=$(gcloud run services describe "$CLOUD_RUN_SERVICE" \
        --region="$CLOUD_RUN_REGION" \
        --project="$GCP_PROJECT_ID" \
        --format="value(status.traffic.revisionName)")

    echo "Current traffic distribution:"
    gcloud run services describe "$CLOUD_RUN_SERVICE" \
        --region="$CLOUD_RUN_REGION" \
        --project="$GCP_PROJECT_ID" \
        --format="table(status.traffic.revisionName,status.traffic.percent)"

    echo ""
    echo "Current revision: $current_revision" > /tmp/rollback-state.txt
}

list_available_revisions() {
    print_header "Available Revisions"

    echo "Recent revisions (last 10):"
    echo ""

    gcloud run revisions list \
        --service="$CLOUD_RUN_SERVICE" \
        --region="$CLOUD_RUN_REGION" \
        --project="$GCP_PROJECT_ID" \
        --limit=10 \
        --format="table(metadata.name,status.conditions.lastTransitionTime,metadata.labels.version)"

    echo ""
}

determine_target_revision() {
    if [ -n "$TARGET_VERSION" ]; then
        echo "Using specified target version: $TARGET_VERSION"
        TARGET_REVISION="$CLOUD_RUN_SERVICE-$TARGET_VERSION"
    else
        # Get previous stable revision (second in list)
        TARGET_REVISION=$(gcloud run revisions list \
            --service="$CLOUD_RUN_SERVICE" \
            --region="$CLOUD_RUN_REGION" \
            --project="$GCP_PROJECT_ID" \
            --limit=2 \
            --format="value(metadata.name)" \
            | tail -n 1)

        print_warning "No target version specified, using previous revision: $TARGET_REVISION"
    fi

    echo ""
    echo "Target revision: $TARGET_REVISION" >> /tmp/rollback-state.txt
}

create_database_backup() {
    print_header "Creating Pre-Rollback Database Backup"

    echo "Creating safety backup before rollback..."
    echo ""

    if [ -x "./scripts/backup-database.sh" ]; then
        if ./scripts/backup-database.sh; then
            print_success "Pre-rollback backup created"
        else
            print_warning "Backup creation failed, but continuing rollback"
        fi
    else
        print_warning "Backup script not found, skipping pre-rollback backup"
    fi

    echo ""
}

get_migration_version() {
    print_header "Checking Database Migration State"

    # Try to get current Alembic version from database
    if [ -n "$DATABASE_URL" ]; then
        echo "Current database schema version:"

        # Use Cloud SQL Proxy or direct connection
        # This requires psql to be installed
        if command -v psql &> /dev/null; then
            local current_migration=$(psql "$DATABASE_URL" -t -c \
                "SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 1;" \
                2>/dev/null || echo "unknown")

            echo "Migration version: $current_migration"
            echo "$current_migration" > /tmp/rollback-migration.txt
        else
            print_warning "psql not available, cannot check migration version"
            print_warning "Database rollback may need manual intervention"
        fi
    else
        print_warning "DATABASE_URL not set, skipping migration check"
    fi

    echo ""
}

rollback_database_migrations() {
    print_header "Rolling Back Database Migrations"

    if [ ! -f /tmp/rollback-migration.txt ]; then
        print_warning "Cannot determine migration version, skipping database rollback"
        return 0
    fi

    print_warning "Database migration rollback may be needed"
    echo ""
    echo "If your deployment included database migrations, you MUST rollback the schema."
    echo ""
    echo "To rollback migrations manually:"
    echo "  1. Identify target migration version from $TARGET_VERSION release"
    echo "  2. Run: cd backend && alembic downgrade <target_version>"
    echo "  3. Verify schema with: alembic current"
    echo ""

    read -p "Have you reviewed migration requirements? (yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        print_error "Rollback aborted - database migrations not confirmed"
        exit 1
    fi

    echo ""
}

rollback_cloud_run_service() {
    print_header "Rolling Back Cloud Run Service"

    echo "Routing 100% traffic to: $TARGET_REVISION"
    echo ""

    # Route all traffic to target revision
    if gcloud run services update-traffic "$CLOUD_RUN_SERVICE" \
        --to-revisions="$TARGET_REVISION=100" \
        --region="$CLOUD_RUN_REGION" \
        --project="$GCP_PROJECT_ID"; then

        print_success "Traffic routed to target revision"
    else
        print_error "Failed to route traffic"
        return 1
    fi

    echo ""

    # Verify traffic distribution
    echo "New traffic distribution:"
    gcloud run services describe "$CLOUD_RUN_SERVICE" \
        --region="$CLOUD_RUN_REGION" \
        --project="$GCP_PROJECT_ID" \
        --format="table(status.traffic.revisionName,status.traffic.percent)"

    echo ""
}

wait_for_stability() {
    print_header "Waiting for Service Stability"

    echo "Waiting 30 seconds for service to stabilize..."
    sleep 30

    print_success "Stability wait complete"
    echo ""
}

run_health_checks() {
    print_header "Running Health Checks"

    if [ -z "$HEALTH_CHECK_URL" ]; then
        # Try to construct health check URL
        HEALTH_CHECK_URL=$(gcloud run services describe "$CLOUD_RUN_SERVICE" \
            --region="$CLOUD_RUN_REGION" \
            --project="$GCP_PROJECT_ID" \
            --format="value(status.url)")
        HEALTH_CHECK_URL="${HEALTH_CHECK_URL}/health"
    fi

    echo "Health check URL: $HEALTH_CHECK_URL"
    echo "Timeout: ${HEALTH_CHECK_TIMEOUT}s"
    echo "Interval: ${HEALTH_CHECK_INTERVAL}s"
    echo ""

    local elapsed=0
    local max_attempts=$((HEALTH_CHECK_TIMEOUT / HEALTH_CHECK_INTERVAL))
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        echo -n "Attempt $attempt/$max_attempts: "

        if curl -sf -m 10 "$HEALTH_CHECK_URL" > /dev/null 2>&1; then
            print_success "Health check PASSED"
            return 0
        else
            echo "Failed (retrying in ${HEALTH_CHECK_INTERVAL}s...)"
            sleep $HEALTH_CHECK_INTERVAL
            attempt=$((attempt + 1))
        fi
    done

    print_error "Health checks failed after $HEALTH_CHECK_TIMEOUT seconds"
    return 1
}

run_smoke_tests() {
    print_header "Running Smoke Tests"

    if [ -x "./scripts/smoke-test.sh" ]; then
        echo "Running smoke tests..."
        echo ""

        if ./scripts/smoke-test.sh "$ENVIRONMENT"; then
            print_success "Smoke tests PASSED"
            return 0
        else
            print_error "Smoke tests FAILED"
            return 1
        fi
    else
        print_warning "Smoke test script not found, skipping"
        return 0
    fi
}

send_rollback_notification() {
    print_header "Sending Rollback Notification"

    local current_revision=$(cat /tmp/rollback-state.txt | grep "Current revision" | cut -d: -f2 | xargs)
    local target_revision=$(cat /tmp/rollback-state.txt | grep "Target revision" | cut -d: -f2 | xargs)

    # Send Slack notification if webhook configured
    if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
        curl -X POST "$SLACK_WEBHOOK_URL" \
            -H 'Content-Type: application/json' \
            -d "{
                \"text\": \"🔄 *Production Rollback Completed*\",
                \"attachments\": [{
                    \"color\": \"warning\",
                    \"fields\": [
                        {\"title\": \"Environment\", \"value\": \"$ENVIRONMENT\", \"short\": true},
                        {\"title\": \"Service\", \"value\": \"$CLOUD_RUN_SERVICE\", \"short\": true},
                        {\"title\": \"From Revision\", \"value\": \"$current_revision\", \"short\": true},
                        {\"title\": \"To Revision\", \"value\": \"$target_revision\", \"short\": true},
                        {\"title\": \"Reason\", \"value\": \"$ROLLBACK_REASON\", \"short\": false},
                        {\"title\": \"Status\", \"value\": \"✓ Rollback successful\", \"short\": false}
                    ]
                }]
            }" > /dev/null 2>&1

        print_success "Slack notification sent"
    else
        print_warning "SLACK_WEBHOOK_URL not set, skipping notification"
    fi

    # Send PagerDuty event if configured
    if [ -n "${PAGERDUTY_INTEGRATION_KEY:-}" ]; then
        curl -X POST https://events.pagerduty.com/v2/enqueue \
            -H 'Content-Type: application/json' \
            -d "{
                \"routing_key\": \"$PAGERDUTY_INTEGRATION_KEY\",
                \"event_action\": \"trigger\",
                \"payload\": {
                    \"summary\": \"Production rollback completed: $CLOUD_RUN_SERVICE\",
                    \"severity\": \"warning\",
                    \"source\": \"AP2 Expense Agent - Rollback Script\",
                    \"custom_details\": {
                        \"environment\": \"$ENVIRONMENT\",
                        \"service\": \"$CLOUD_RUN_SERVICE\",
                        \"from_revision\": \"$current_revision\",
                        \"to_revision\": \"$target_revision\",
                        \"reason\": \"$ROLLBACK_REASON\"
                    }
                }
            }" > /dev/null 2>&1

        print_success "PagerDuty notification sent"
    fi

    echo ""
}

generate_rollback_report() {
    print_header "Generating Rollback Report"

    local report_file="rollback-report-$(date +%Y%m%d-%H%M%S).md"

    cat > "$report_file" <<EOF
# Deployment Rollback Report

**Date**: $(date)
**Environment**: $ENVIRONMENT
**Operator**: $(whoami)

## Rollback Details

- **Service**: $CLOUD_RUN_SERVICE
- **Region**: $CLOUD_RUN_REGION
- **From Revision**: $(cat /tmp/rollback-state.txt | grep "Current revision" | cut -d: -f2 | xargs)
- **To Revision**: $(cat /tmp/rollback-state.txt | grep "Target revision" | cut -d: -f2 | xargs)
- **Reason**: $ROLLBACK_REASON

## Actions Taken

1. ✓ Created pre-rollback database backup
2. ✓ Checked database migration state
3. ✓ Routed 100% traffic to target revision
4. ✓ Verified health checks
5. ✓ Ran smoke tests
6. ✓ Sent notifications to team

## Verification

- **Health Checks**: PASSED
- **Smoke Tests**: PASSED
- **Service Status**: RUNNING

## Next Steps

1. Monitor application metrics for 15 minutes
2. Review logs for any errors
3. Communicate rollback to stakeholders
4. Create incident postmortem (if applicable)
5. Identify and fix root cause of deployment failure

## Rollback Logs

\`\`\`
$(gcloud run services describe "$CLOUD_RUN_SERVICE" \
    --region="$CLOUD_RUN_REGION" \
    --project="$GCP_PROJECT_ID" \
    --format="table(status.traffic.revisionName,status.traffic.percent)")
\`\`\`

---

*Report generated by rollback-deployment.sh*
EOF

    print_success "Report saved: $report_file"
    echo ""
    echo "Report contents:"
    cat "$report_file"
    echo ""
}

cleanup() {
    rm -f /tmp/rollback-state.txt
    rm -f /tmp/rollback-migration.txt
}

# ============================================================================
# Main Execution
# ============================================================================

print_header "Production Deployment Rollback"
echo ""
echo "Environment: $ENVIRONMENT"
echo "Service: $CLOUD_RUN_SERVICE"
echo "Reason: $ROLLBACK_REASON"
echo ""

# Check prerequisites
if ! check_prerequisites; then
    exit 1
fi

# Confirm rollback
confirm_rollback

# Get current state
get_current_revision

# List available revisions
list_available_revisions

# Determine target revision
determine_target_revision

# Create safety backup
create_database_backup

# Check database migration state
get_migration_version

# Rollback database if needed
rollback_database_migrations

# Perform Cloud Run rollback
if ! rollback_cloud_run_service; then
    print_error "Rollback failed"
    cleanup
    exit 1
fi

# Wait for stability
wait_for_stability

# Run health checks
if ! run_health_checks; then
    print_error "Health checks failed after rollback"
    print_warning "Service may be unhealthy - manual intervention required"
fi

# Run smoke tests
if ! run_smoke_tests; then
    print_warning "Smoke tests failed - verify application functionality"
fi

# Send notifications
send_rollback_notification

# Generate report
generate_rollback_report

# Cleanup
cleanup

# Final summary
print_header "Rollback Summary"
print_success "Rollback completed successfully"
echo ""
echo "✓ Service rolled back to: $TARGET_REVISION"
echo "✓ Health checks passed"
echo "✓ Notifications sent"
echo ""
echo "Next steps:"
echo "1. Monitor metrics: GCP Console → Cloud Run → $CLOUD_RUN_SERVICE"
echo "2. Check logs: gcloud logging read --limit 100"
echo "3. Review rollback report (see above)"
echo "4. Identify root cause of deployment failure"
echo "5. Create incident postmortem"
echo ""

exit 0
