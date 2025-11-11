#!/bin/bash

###############################################################################
# Setup Cloud Storage for AP2 Expense Agent
#
# This script creates and configures Cloud Storage buckets for:
# - Receipt uploads
# - Database backups
# - Application assets
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
    if [ -z "${GCP_PROJECT_ID:-}" ] || [ -z "${GCP_REGION:-}" ]; then
        log_error "Required environment variables not set"
        log_error "Please set: GCP_PROJECT_ID, GCP_REGION"
        exit 1
    fi
}

# Create receipts bucket
create_receipts_bucket() {
    local bucket_name="${GCP_PROJECT_ID}-ap2-expense-receipts"

    log_info "Creating receipts bucket: $bucket_name"

    if gsutil ls -b "gs://$bucket_name" &>/dev/null; then
        log_warning "Bucket already exists"
        return 0
    fi

    # Create bucket with uniform bucket-level access
    gsutil mb \
        -p "$GCP_PROJECT_ID" \
        -l "$GCP_REGION" \
        -b on \
        "gs://$bucket_name"

    # Set lifecycle policy: delete after 7 years (2555 days) for compliance
    cat > /tmp/receipts-lifecycle.json <<'EOF'
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
        "condition": {"age": 90}
      },
      {
        "action": {"type": "SetStorageClass", "storageClass": "COLDLINE"},
        "condition": {"age": 365}
      },
      {
        "action": {"type": "Delete"},
        "condition": {"age": 2555}
      }
    ]
  }
}
EOF

    gsutil lifecycle set /tmp/receipts-lifecycle.json "gs://$bucket_name"
    rm /tmp/receipts-lifecycle.json

    # Enable versioning for accidental deletion protection
    gsutil versioning set on "gs://$bucket_name"

    # Set CORS for frontend uploads
    cat > /tmp/cors.json <<'EOF'
[
  {
    "origin": ["*"],
    "method": ["GET", "HEAD", "PUT", "POST"],
    "responseHeader": ["Content-Type"],
    "maxAgeSeconds": 3600
  }
]
EOF

    gsutil cors set /tmp/cors.json "gs://$bucket_name"
    rm /tmp/cors.json

    # Grant service account access
    local sa_email="ap2-expense-sa@${GCP_PROJECT_ID}.iam.gserviceaccount.com"
    gsutil iam ch "serviceAccount:$sa_email:objectAdmin" "gs://$bucket_name"

    log_success "Receipts bucket created and configured"
}

# Create backups bucket
create_backups_bucket() {
    local bucket_name="${GCP_PROJECT_ID}-ap2-expense-backups"

    log_info "Creating backups bucket: $bucket_name"

    if gsutil ls -b "gs://$bucket_name" &>/dev/null; then
        log_warning "Bucket already exists"
        return 0
    fi

    # Create bucket
    gsutil mb \
        -p "$GCP_PROJECT_ID" \
        -l "$GCP_REGION" \
        -b on \
        "gs://$bucket_name"

    # Set lifecycle: keep for 90 days, then delete
    cat > /tmp/backups-lifecycle.json <<'EOF'
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 90}
      }
    ]
  }
}
EOF

    gsutil lifecycle set /tmp/backups-lifecycle.json "gs://$bucket_name"
    rm /tmp/backups-lifecycle.json

    # Enable versioning
    gsutil versioning set on "gs://$bucket_name"

    # Grant service account access
    local sa_email="ap2-expense-sa@${GCP_PROJECT_ID}.iam.gserviceaccount.com"
    gsutil iam ch "serviceAccount:$sa_email:objectAdmin" "gs://$bucket_name"

    log_success "Backups bucket created and configured"
}

# Create assets bucket (for marketplace images, etc.)
create_assets_bucket() {
    local bucket_name="${GCP_PROJECT_ID}-ap2-expense-assets"

    log_info "Creating assets bucket: $bucket_name"

    if gsutil ls -b "gs://$bucket_name" &>/dev/null; then
        log_warning "Bucket already exists"
        return 0
    fi

    # Create bucket
    gsutil mb \
        -p "$GCP_PROJECT_ID" \
        -l "$GCP_REGION" \
        -b on \
        "gs://$bucket_name"

    # Make bucket publicly readable for assets
    gsutil iam ch allUsers:objectViewer "gs://$bucket_name"

    # No lifecycle policy - keep assets indefinitely

    # Grant service account admin access
    local sa_email="ap2-expense-sa@${GCP_PROJECT_ID}.iam.gserviceaccount.com"
    gsutil iam ch "serviceAccount:$sa_email:objectAdmin" "gs://$bucket_name"

    log_success "Assets bucket created and configured"
}

# Update backend config to use Cloud Storage
update_backend_config() {
    log_info "Updating backend configuration..."

    local receipts_bucket="${GCP_PROJECT_ID}-ap2-expense-receipts"

    # Add to ConfigMap
    log_info "Add this to your k8s/configmap.yaml:"
    echo ""
    echo "  GCS_RECEIPTS_BUCKET: \"$receipts_bucket\""
    echo "  GCS_BACKUPS_BUCKET: \"${GCP_PROJECT_ID}-ap2-expense-backups\""
    echo ""

    log_success "Configuration updated"
}

# Print summary
print_summary() {
    echo ""
    log_success "========================================="
    log_success "Cloud Storage Setup Complete!"
    log_success "========================================="
    echo ""
    log_info "Created buckets:"
    echo "  1. ${GCP_PROJECT_ID}-ap2-expense-receipts (user uploads)"
    echo "  2. ${GCP_PROJECT_ID}-ap2-expense-backups (database backups)"
    echo "  3. ${GCP_PROJECT_ID}-ap2-expense-assets (public assets)"
    echo ""
    log_info "Features configured:"
    echo "  - Lifecycle policies (auto-archival and deletion)"
    echo "  - Versioning enabled (protection against accidental deletion)"
    echo "  - CORS enabled for frontend uploads"
    echo "  - IAM permissions granted to service account"
    echo ""
    log_info "Next steps:"
    echo "  1. Update k8s/configmap.yaml with bucket names"
    echo "  2. Implement receipt upload in backend code"
    echo "  3. Test receipt upload functionality"
    echo ""
}

# Main execution
main() {
    echo ""
    log_info "========================================="
    log_info "Cloud Storage Setup"
    log_info "========================================="
    echo ""

    check_env_vars
    create_receipts_bucket
    create_backups_bucket
    create_assets_bucket
    update_backend_config
    print_summary
}

main "$@"
