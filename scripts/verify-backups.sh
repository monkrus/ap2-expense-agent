#!/bin/bash

# ============================================================================
# Database Backup Verification Script
# ============================================================================
#
# Purpose: Verify that Cloud SQL automated backups are configured and working
# Priority: CRITICAL
# Run: ./scripts/verify-backups.sh
#
# ============================================================================

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-""}
INSTANCE_NAME="ap2-expense-db"  # Change this to your Cloud SQL instance name
REGION="us-central1"            # Change this to your region

# ============================================================================
# Helper Functions
# ============================================================================

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

print_info() {
    echo -e "ℹ $1"
}

# ============================================================================
# Pre-flight Checks
# ============================================================================

print_header "Database Backup Verification"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI not found. Please install Google Cloud SDK."
    exit 1
fi
print_success "gcloud CLI found"

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    print_error "Not authenticated with gcloud. Run: gcloud auth login"
    exit 1
fi
print_success "gcloud authenticated"

# Get project ID if not set
if [ -z "$PROJECT_ID" ]; then
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
    if [ -z "$PROJECT_ID" ]; then
        print_error "GCP_PROJECT_ID not set. Run: gcloud config set project YOUR_PROJECT_ID"
        exit 1
    fi
fi
print_success "Using project: $PROJECT_ID"

# ============================================================================
# Check Cloud SQL Instance
# ============================================================================

print_header "Checking Cloud SQL Instance"

# Check if instance exists
if ! gcloud sql instances describe $INSTANCE_NAME --project=$PROJECT_ID &> /dev/null; then
    print_error "Cloud SQL instance '$INSTANCE_NAME' not found in project '$PROJECT_ID'"
    print_info "Available instances:"
    gcloud sql instances list --project=$PROJECT_ID
    exit 1
fi
print_success "Cloud SQL instance found: $INSTANCE_NAME"

# Get instance details
INSTANCE_STATE=$(gcloud sql instances describe $INSTANCE_NAME \
    --project=$PROJECT_ID \
    --format="value(state)")

if [ "$INSTANCE_STATE" != "RUNNABLE" ]; then
    print_warning "Instance state: $INSTANCE_STATE (expected: RUNNABLE)"
else
    print_success "Instance state: RUNNABLE"
fi

# ============================================================================
# Check Automated Backup Configuration
# ============================================================================

print_header "Checking Automated Backup Configuration"

# Get backup configuration
BACKUP_ENABLED=$(gcloud sql instances describe $INSTANCE_NAME \
    --project=$PROJECT_ID \
    --format="value(settings.backupConfiguration.enabled)")

BACKUP_START_TIME=$(gcloud sql instances describe $INSTANCE_NAME \
    --project=$PROJECT_ID \
    --format="value(settings.backupConfiguration.startTime)")

BACKUP_LOCATION=$(gcloud sql instances describe $INSTANCE_NAME \
    --project=$PROJECT_ID \
    --format="value(settings.backupConfiguration.location)")

BINARY_LOG_ENABLED=$(gcloud sql instances describe $INSTANCE_NAME \
    --project=$PROJECT_ID \
    --format="value(settings.backupConfiguration.binaryLogEnabled)")

POINT_IN_TIME_ENABLED=$(gcloud sql instances describe $INSTANCE_NAME \
    --project=$PROJECT_ID \
    --format="value(settings.backupConfiguration.pointInTimeRecoveryEnabled)")

# Verify backup is enabled
if [ "$BACKUP_ENABLED" = "True" ]; then
    print_success "Automated backups: ENABLED"
else
    print_error "Automated backups: DISABLED"
    print_info "Enable with: gcloud sql instances patch $INSTANCE_NAME --backup-start-time=02:00"
    exit 1
fi

# Check backup start time
if [ -n "$BACKUP_START_TIME" ]; then
    print_success "Backup start time: $BACKUP_START_TIME UTC"
else
    print_warning "Backup start time not configured"
fi

# Check backup location
if [ -n "$BACKUP_LOCATION" ]; then
    print_success "Backup location: $BACKUP_LOCATION"
else
    print_info "Backup location: Default (same region as instance)"
fi

# Check binary log (required for point-in-time recovery)
if [ "$BINARY_LOG_ENABLED" = "True" ]; then
    print_success "Binary logging: ENABLED"
else
    print_warning "Binary logging: DISABLED (point-in-time recovery not available)"
    print_info "Enable with: gcloud sql instances patch $INSTANCE_NAME --enable-bin-log"
fi

# Check point-in-time recovery
if [ "$POINT_IN_TIME_ENABLED" = "True" ]; then
    print_success "Point-in-time recovery: ENABLED"
else
    print_warning "Point-in-time recovery: DISABLED"
fi

# ============================================================================
# List Recent Backups
# ============================================================================

print_header "Recent Backups"

# Get list of backups
BACKUPS=$(gcloud sql backups list \
    --instance=$INSTANCE_NAME \
    --project=$PROJECT_ID \
    --limit=10 \
    --format="table(id,type,windowStartTime,status)" 2>&1)

if [ $? -eq 0 ]; then
    echo "$BACKUPS"

    # Count successful backups
    SUCCESSFUL_BACKUPS=$(gcloud sql backups list \
        --instance=$INSTANCE_NAME \
        --project=$PROJECT_ID \
        --filter="status=SUCCESSFUL" \
        --limit=10 \
        --format="value(id)" | wc -l)

    if [ "$SUCCESSFUL_BACKUPS" -gt 0 ]; then
        print_success "Found $SUCCESSFUL_BACKUPS successful backup(s)"
    else
        print_error "No successful backups found!"
        print_info "Wait for next scheduled backup or create manual backup:"
        print_info "  gcloud sql backups create --instance=$INSTANCE_NAME"
    fi
else
    print_error "Failed to list backups: $BACKUPS"
fi

# ============================================================================
# Check Backup Retention
# ============================================================================

print_header "Backup Retention Settings"

RETAINED_BACKUPS=$(gcloud sql instances describe $INSTANCE_NAME \
    --project=$PROJECT_ID \
    --format="value(settings.backupConfiguration.backupRetentionSettings.retainedBackups)")

RETENTION_UNIT=$(gcloud sql instances describe $INSTANCE_NAME \
    --project=$PROJECT_ID \
    --format="value(settings.backupConfiguration.backupRetentionSettings.retentionUnit)")

if [ -n "$RETAINED_BACKUPS" ]; then
    print_success "Retained backups: $RETAINED_BACKUPS $RETENTION_UNIT"

    if [ "$RETAINED_BACKUPS" -lt 7 ]; then
        print_warning "Retention is less than 7 backups. Recommended: 30 days"
        print_info "Update with: gcloud sql instances patch $INSTANCE_NAME --retained-backups-count=30"
    fi
else
    print_info "Retention: Default (7 automated backups)"
fi

# ============================================================================
# Backup Size Estimation
# ============================================================================

print_header "Backup Storage"

DATABASE_SIZE=$(gcloud sql instances describe $INSTANCE_NAME \
    --project=$PROJECT_ID \
    --format="value(settings.dataDiskSizeGb)")

if [ -n "$DATABASE_SIZE" ]; then
    print_info "Database disk size: ${DATABASE_SIZE}GB"

    # Estimate backup storage (assuming 10 backups * disk size)
    ESTIMATED_BACKUP_STORAGE=$((DATABASE_SIZE * 10))
    print_info "Estimated backup storage (10 backups): ~${ESTIMATED_BACKUP_STORAGE}GB"

    # Calculate monthly cost (Cloud SQL backup pricing: $0.08/GB/month)
    ESTIMATED_COST=$(echo "scale=2; $ESTIMATED_BACKUP_STORAGE * 0.08" | bc)
    print_info "Estimated monthly backup cost: ~\$${ESTIMATED_COST}"
fi

# ============================================================================
# Test Backup Restoration (DRY RUN)
# ============================================================================

print_header "Backup Restoration Test (Dry Run)"

print_info "To test backup restoration, run:"
echo ""
echo "# 1. Get latest backup ID"
echo "BACKUP_ID=\$(gcloud sql backups list --instance=$INSTANCE_NAME --limit=1 --format='value(id)')"
echo ""
echo "# 2. Create test instance from backup (WARNING: Creates billable resource)"
echo "gcloud sql instances clone $INSTANCE_NAME ${INSTANCE_NAME}-test-restore --backup-run=\$BACKUP_ID"
echo ""
echo "# 3. Verify data integrity on test instance"
echo ""
echo "# 4. Delete test instance when done"
echo "gcloud sql instances delete ${INSTANCE_NAME}-test-restore"
echo ""

print_warning "Restoration test creates a temporary instance. Remember to delete it!"

# ============================================================================
# Recommendations
# ============================================================================

print_header "Recommendations"

RECOMMENDATIONS=()

if [ "$BACKUP_ENABLED" != "True" ]; then
    RECOMMENDATIONS+=("🔴 CRITICAL: Enable automated backups immediately")
fi

if [ "$BINARY_LOG_ENABLED" != "True" ]; then
    RECOMMENDATIONS+=("🟡 Enable binary logging for point-in-time recovery")
fi

if [ -n "$RETAINED_BACKUPS" ] && [ "$RETAINED_BACKUPS" -lt 30 ]; then
    RECOMMENDATIONS+=("🟡 Increase backup retention to 30 days minimum")
fi

if [ "$SUCCESSFUL_BACKUPS" -eq 0 ]; then
    RECOMMENDATIONS+=("🔴 CRITICAL: No successful backups found - create manual backup now")
fi

if [ ${#RECOMMENDATIONS[@]} -eq 0 ]; then
    print_success "All backup configurations look good! ✨"
else
    echo "Action items:"
    for rec in "${RECOMMENDATIONS[@]}"; do
        echo "  $rec"
    done
fi

# ============================================================================
# Summary
# ============================================================================

print_header "Summary"

echo "Instance: $INSTANCE_NAME"
echo "Project: $PROJECT_ID"
echo "Automated Backups: $([ "$BACKUP_ENABLED" = "True" ] && echo "✓ Enabled" || echo "✗ Disabled")"
echo "Successful Backups: $SUCCESSFUL_BACKUPS"
echo "Retention: ${RETAINED_BACKUPS:-7} ${RETENTION_UNIT:-backups}"
echo "Point-in-Time Recovery: $([ "$POINT_IN_TIME_ENABLED" = "True" ] && echo "✓ Enabled" || echo "✗ Disabled")"
echo ""

if [ "$BACKUP_ENABLED" = "True" ] && [ "$SUCCESSFUL_BACKUPS" -gt 0 ]; then
    print_success "Backup verification PASSED ✓"
    exit 0
else
    print_error "Backup verification FAILED ✗"
    exit 1
fi
