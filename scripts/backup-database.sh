#!/bin/bash

###############################################################################
# Database Backup Script
#
# Creates an on-demand backup of the Cloud SQL database and stores metadata
# in Cloud Storage.
###############################################################################

set -euo pipefail

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check environment variables
check_env_vars() {
    if [ -z "${GCP_PROJECT_ID:-}" ] || [ -z "${DB_INSTANCE_NAME:-}" ]; then
        log_error "Required environment variables not set"
        log_error "Please set: GCP_PROJECT_ID, DB_INSTANCE_NAME"
        exit 1
    fi
}

# Create backup
create_backup() {
    log_info "Creating database backup..."

    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_id="manual-backup-${timestamp}"
    local description="Manual backup created at ${timestamp}"

    if [ "${1:-}" == "automated" ]; then
        backup_id="automated-backup-${timestamp}"
        description="Automated backup created at ${timestamp}"
    fi

    log_info "Backup ID: $backup_id"

    # Create backup
    gcloud sql backups create \
        --instance="$DB_INSTANCE_NAME" \
        --description="$description" \
        --project="$GCP_PROJECT_ID"

    local backup_info=$(gcloud sql backups list \
        --instance="$DB_INSTANCE_NAME" \
        --limit=1 \
        --project="$GCP_PROJECT_ID" \
        --format=json)

    log_success "Backup created successfully"

    # Extract backup details
    local backup_id=$(echo "$backup_info" | jq -r '.[0].id')
    local backup_time=$(echo "$backup_info" | jq -r '.[0].windowStartTime')

    log_info "Backup ID: $backup_id"
    log_info "Backup time: $backup_time"

    # Store backup metadata
    store_backup_metadata "$backup_id" "$backup_time"
}

# Store backup metadata in Cloud Storage
store_backup_metadata() {
    local backup_id=$1
    local backup_time=$2
    local bucket="${GCP_PROJECT_ID}-ap2-expense-backups"

    log_info "Storing backup metadata..."

    # Create metadata file
    cat > /tmp/backup-metadata.json <<EOF
{
  "backup_id": "$backup_id",
  "backup_time": "$backup_time",
  "instance": "$DB_INSTANCE_NAME",
  "project": "$GCP_PROJECT_ID",
  "created_by": "$(whoami)",
  "hostname": "$(hostname)",
  "type": "cloud_sql_backup"
}
EOF

    # Upload to Cloud Storage
    gsutil cp /tmp/backup-metadata.json \
        "gs://${bucket}/metadata/backup-${backup_id}.json"

    rm /tmp/backup-metadata.json

    log_success "Metadata stored in gs://${bucket}/metadata/"
}

# List recent backups
list_backups() {
    log_info "Listing recent backups..."

    gcloud sql backups list \
        --instance="$DB_INSTANCE_NAME" \
        --limit=10 \
        --project="$GCP_PROJECT_ID" \
        --format="table(id, windowStartTime, status)"
}

# Verify backup integrity
verify_backup() {
    local backup_id=$1

    log_info "Verifying backup: $backup_id"

    local backup_status=$(gcloud sql backups describe "$backup_id" \
        --instance="$DB_INSTANCE_NAME" \
        --project="$GCP_PROJECT_ID" \
        --format="value(status)")

    if [ "$backup_status" == "SUCCESSFUL" ]; then
        log_success "Backup verified: $backup_id"
        return 0
    else
        log_error "Backup failed or in progress: $backup_id (status: $backup_status)"
        return 1
    fi
}

# Export database to Cloud Storage (alternative backup method)
export_database() {
    log_info "Exporting database to Cloud Storage..."

    local timestamp=$(date +%Y%m%d-%H%M%S)
    local bucket="${GCP_PROJECT_ID}-ap2-expense-backups"
    local export_file="exports/database-export-${timestamp}.sql.gz"

    log_info "Export location: gs://${bucket}/${export_file}"

    gcloud sql export sql "$DB_INSTANCE_NAME" \
        "gs://${bucket}/${export_file}" \
        --database="${DB_NAME:-ap2_expense}" \
        --project="$GCP_PROJECT_ID"

    log_success "Database exported successfully"
    log_info "Export file: gs://${bucket}/${export_file}"
}

# Print summary
print_summary() {
    echo ""
    log_success "========================================="
    log_success "Backup Complete!"
    log_success "========================================="
    echo ""
    log_info "Backup operations:"
    echo "  1. Cloud SQL automatic backup created"
    echo "  2. Metadata stored in Cloud Storage"
    echo ""
    log_info "To restore from this backup:"
    echo "  gcloud sql backups restore <BACKUP_ID> \\"
    echo "    --backup-instance=$DB_INSTANCE_NAME \\"
    echo "    --backup-instance=$DB_INSTANCE_NAME"
    echo ""
}

# Main execution
main() {
    local command="${1:-create}"

    echo ""
    log_info "========================================="
    log_info "Database Backup Tool"
    log_info "========================================="
    echo ""

    check_env_vars

    case "$command" in
        create)
            create_backup "manual"
            list_backups
            print_summary
            ;;
        automated)
            create_backup "automated"
            ;;
        list)
            list_backups
            ;;
        export)
            export_database
            ;;
        verify)
            if [ -z "${2:-}" ]; then
                log_error "Usage: $0 verify <backup-id>"
                exit 1
            fi
            verify_backup "$2"
            ;;
        *)
            log_error "Unknown command: $command"
            echo "Usage: $0 {create|automated|list|export|verify <backup-id>}"
            exit 1
            ;;
    esac
}

main "$@"
