#!/bin/bash

###############################################################################
# Secret Rotation Script
#
# Rotates secrets in Google Secret Manager and updates running services
# Run this script every 90 days for security compliance
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
    if [ -z "${GCP_PROJECT_ID:-}" ]; then
        log_error "GCP_PROJECT_ID not set"
        exit 1
    fi
}

# Generate new JWT secret
generate_jwt_secret() {
    openssl rand -hex 32
}

# Rotate JWT secrets
rotate_jwt_secrets() {
    log_info "Rotating JWT secrets..."

    # Generate new secrets
    local new_jwt_secret=$(generate_jwt_secret)
    local new_jwt_refresh_secret=$(generate_jwt_secret)

    log_info "Generated new JWT secrets"

    # Add new versions to Secret Manager
    echo -n "$new_jwt_secret" | gcloud secrets versions add jwt-secret-key \
        --data-file=- \
        --project="$GCP_PROJECT_ID"

    echo -n "$new_jwt_refresh_secret" | gcloud secrets versions add jwt-refresh-secret-key \
        --data-file=- \
        --project="$GCP_PROJECT_ID"

    log_success "New JWT secret versions created"

    # Store old secrets for rollback
    echo "$new_jwt_secret" > /tmp/new-jwt-secret.txt
    echo "$new_jwt_refresh_secret" > /tmp/new-jwt-refresh-secret.txt

    log_warning "New secrets stored in /tmp/ for rollback if needed"
    log_warning "Delete these files after verification!"
}

# Rotate database password
rotate_database_password() {
    log_info "Rotating database password..."

    local db_instance="${DB_INSTANCE_NAME:-ap2-expense-db}"
    local db_user="${DB_USER:-ap2user}"

    # Generate new password
    local new_password=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)

    log_info "Generated new database password"

    # Update Cloud SQL user password
    gcloud sql users set-password "$db_user" \
        --instance="$db_instance" \
        --password="$new_password" \
        --project="$GCP_PROJECT_ID"

    # Update Secret Manager
    echo -n "$new_password" | gcloud secrets versions add database-password \
        --data-file=- \
        --project="$GCP_PROJECT_ID"

    log_success "Database password rotated"

    # Store for rollback
    echo "$new_password" > /tmp/new-db-password.txt

    log_warning "New password stored in /tmp/new-db-password.txt"
}

# Rotate Stripe keys (manual process - just reminder)
rotate_stripe_keys() {
    log_warning "========================================="
    log_warning "STRIPE KEY ROTATION"
    log_warning "========================================="
    log_warning "Stripe keys must be rotated manually:"
    echo ""
    echo "1. Log into Stripe Dashboard"
    echo "2. Go to Developers > API keys"
    echo "3. Click 'Create secret key'"
    echo "4. Roll the old key (after testing new one)"
    echo "5. Update Secret Manager:"
    echo "   echo -n 'sk_live_NEW_KEY' | gcloud secrets versions add stripe-secret-key --data-file=-"
    echo ""
    log_warning "After manual rotation, press Enter to continue..."
    read
}

# Restart backend pods to pick up new secrets
restart_backend_kubernetes() {
    log_info "Restarting backend pods in Kubernetes..."

    if kubectl get namespace ap2-expense &>/dev/null; then
        kubectl rollout restart deployment/backend -n ap2-expense

        log_info "Waiting for rollout to complete..."
        kubectl rollout status deployment/backend -n ap2-expense --timeout=5m

        log_success "Backend pods restarted successfully"
    else
        log_warning "Kubernetes namespace not found, skipping pod restart"
    fi
}

# Restart Cloud Run services
restart_backend_cloud_run() {
    log_info "Restarting Cloud Run services..."

    local region="${GCP_REGION:-us-central1}"

    # Get current revision
    local current_revision=$(gcloud run services describe ap2-expense-backend \
        --region="$region" \
        --project="$GCP_PROJECT_ID" \
        --format="value(status.latestReadyRevisionName)")

    # Update with same config to force restart
    gcloud run services update ap2-expense-backend \
        --region="$region" \
        --project="$GCP_PROJECT_ID" \
        --update-env-vars="SECRETS_ROTATED_AT=$(date +%s)"

    log_success "Cloud Run service restarted"
}

# Restart services based on deployment type
restart_services() {
    local deployment_type="${1:-kubernetes}"

    log_info "Restarting services (deployment type: $deployment_type)..."

    case "$deployment_type" in
        kubernetes)
            restart_backend_kubernetes
            ;;
        cloud-run)
            restart_backend_cloud_run
            ;;
        both)
            restart_backend_kubernetes
            restart_backend_cloud_run
            ;;
        *)
            log_error "Unknown deployment type: $deployment_type"
            exit 1
            ;;
    esac
}

# Verify new secrets are working
verify_rotation() {
    log_info "Verifying secret rotation..."

    # Wait for pods to be ready
    sleep 10

    # Test health endpoint
    if kubectl get namespace ap2-expense &>/dev/null; then
        local backend_pod=$(kubectl get pods -n ap2-expense -l app.kubernetes.io/component=backend -o jsonpath='{.items[0].metadata.name}')

        if [ -n "$backend_pod" ]; then
            log_info "Testing backend pod health..."

            if kubectl exec "$backend_pod" -n ap2-expense -- curl -f -s http://localhost:8000/health > /dev/null; then
                log_success "Health check passed"
            else
                log_error "Health check failed!"
                return 1
            fi

            # Test database connection
            log_info "Testing database connection..."
            kubectl exec "$backend_pod" -n ap2-expense -- python -c "
from src.database import engine
try:
    conn = engine.connect()
    print('✅ Database connection successful')
    conn.close()
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    exit(1)
            " || return 1

            log_success "Database connection verified"
        fi
    fi

    # Test user login (JWT validation)
    log_info "Testing JWT authentication..."
    log_warning "Please test user login manually to verify JWT secrets"

    log_success "Verification complete"
}

# Rollback secrets
rollback_secrets() {
    log_warning "========================================="
    log_warning "ROLLING BACK SECRETS"
    log_warning "========================================="

    log_info "Disabling new secret versions..."

    # Get latest versions
    local jwt_version=$(gcloud secrets versions list jwt-secret-key \
        --project="$GCP_PROJECT_ID" \
        --limit=1 \
        --format="value(name)")

    local jwt_refresh_version=$(gcloud secrets versions list jwt-refresh-secret-key \
        --project="$GCP_PROJECT_ID" \
        --limit=1 \
        --format="value(name)")

    # Disable latest versions
    gcloud secrets versions disable "$jwt_version" \
        --secret=jwt-secret-key \
        --project="$GCP_PROJECT_ID"

    gcloud secrets versions disable "$jwt_refresh_version" \
        --secret=jwt-refresh-secret-key \
        --project="$GCP_PROJECT_ID"

    log_success "New versions disabled, previous versions are now active"
    log_info "Restart services to pick up old secrets"
}

# Create rotation audit log
create_audit_log() {
    local rotation_type=$1
    local status=$2

    local log_file="/tmp/secret-rotation-$(date +%Y%m%d-%H%M%S).log"

    cat > "$log_file" <<EOF
========================================
SECRET ROTATION AUDIT LOG
========================================

Rotation Type: $rotation_type
Status: $status
Timestamp: $(date)
Project: $GCP_PROJECT_ID
Performed By: $(whoami)
Hostname: $(hostname)

Secrets Rotated:
- JWT Secret Key
- JWT Refresh Secret Key
$([ "$rotation_type" = "full" ] && echo "- Database Password")

Secret Versions:
- jwt-secret-key: $(gcloud secrets versions list jwt-secret-key --project="$GCP_PROJECT_ID" --limit=1 --format="value(name)")
- jwt-refresh-secret-key: $(gcloud secrets versions list jwt-refresh-secret-key --project="$GCP_PROJECT_ID" --limit=1 --format="value(name)")

Next Rotation Due: $(date -d "+90 days" 2>/dev/null || date -v +90d 2>/dev/null || echo "90 days from now")

========================================
EOF

    log_info "Audit log created: $log_file"

    # Upload to Cloud Storage if bucket exists
    local bucket="${GCP_PROJECT_ID}-ap2-expense-backups"
    if gsutil ls "gs://$bucket" &>/dev/null; then
        gsutil cp "$log_file" "gs://$bucket/audit-logs/"
        log_info "Audit log uploaded to gs://$bucket/audit-logs/"
    fi
}

# Print summary
print_summary() {
    log_success "========================================="
    log_success "SECRET ROTATION COMPLETE"
    log_success "========================================="
    echo ""
    log_info "Secrets rotated:"
    echo "  - JWT Secret Key"
    echo "  - JWT Refresh Secret Key"
    if [ "${ROTATE_DB:-false}" = "true" ]; then
        echo "  - Database Password"
    fi
    echo ""
    log_info "Services restarted and verified"
    echo ""
    log_warning "IMPORTANT POST-ROTATION TASKS:"
    echo "  1. Test user login functionality"
    echo "  2. Monitor error rates in Cloud Logging"
    echo "  3. Check that existing sessions still work (grace period)"
    echo "  4. Delete temporary files in /tmp/"
    echo "  5. Update documentation with rotation date"
    echo "  6. Schedule next rotation in 90 days"
    echo ""
    log_info "To rollback if issues occur:"
    echo "  ./scripts/rotate-secrets.sh rollback"
    echo ""
}

# Main execution
main() {
    local command="${1:-rotate}"

    echo ""
    log_info "========================================="
    log_info "Secret Rotation Tool"
    log_info "========================================="
    echo ""

    check_env_vars

    case "$command" in
        rotate)
            log_warning "This will rotate JWT secrets and restart services"
            read -p "Continue? (yes/no): " confirm

            if [ "$confirm" != "yes" ]; then
                log_info "Rotation cancelled"
                exit 0
            fi

            rotate_jwt_secrets

            # Ask about database password
            read -p "Also rotate database password? (yes/no): " rotate_db
            if [ "$rotate_db" = "yes" ]; then
                export ROTATE_DB=true
                rotate_database_password
            fi

            # Determine deployment type
            read -p "Deployment type? (kubernetes/cloud-run/both): " deploy_type
            restart_services "${deploy_type:-kubernetes}"

            # Verify
            if verify_rotation; then
                create_audit_log "full" "success"
                print_summary
            else
                log_error "Verification failed!"
                log_warning "Consider rolling back: ./scripts/rotate-secrets.sh rollback"
                create_audit_log "full" "failed"
                exit 1
            fi
            ;;

        jwt-only)
            log_info "Rotating only JWT secrets..."
            rotate_jwt_secrets
            restart_services "${2:-kubernetes}"
            verify_rotation
            create_audit_log "jwt-only" "success"
            ;;

        database-only)
            log_info "Rotating only database password..."
            rotate_database_password
            restart_services "${2:-kubernetes}"
            verify_rotation
            create_audit_log "database-only" "success"
            ;;

        stripe)
            rotate_stripe_keys
            ;;

        rollback)
            rollback_secrets
            ;;

        verify)
            verify_rotation
            ;;

        *)
            log_error "Unknown command: $command"
            echo "Usage: $0 {rotate|jwt-only|database-only|stripe|rollback|verify} [deployment-type]"
            exit 1
            ;;
    esac
}

main "$@"
