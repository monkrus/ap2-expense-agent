#!/bin/bash

###############################################################################
# Disaster Recovery Script
#
# Handles disaster recovery scenarios including:
# - Database restoration from backup
# - Application redeployment
# - Configuration recovery
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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check gcloud
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI not found"
        exit 1
    fi

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found"
        exit 1
    fi

    # Check environment variables
    local required_vars=("GCP_PROJECT_ID" "GCP_REGION" "DB_INSTANCE_NAME")
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            log_error "Required environment variable not set: $var"
            exit 1
        fi
    done

    log_success "Prerequisites check passed"
}

# List available backups
list_available_backups() {
    log_info "Available backups:"
    echo ""

    gcloud sql backups list \
        --instance="$DB_INSTANCE_NAME" \
        --project="$GCP_PROJECT_ID" \
        --limit=20 \
        --format="table(id, windowStartTime, status, type)"

    echo ""
}

# Restore database from backup
restore_database() {
    local backup_id=$1

    log_warning "========================================="
    log_warning "DATABASE RESTORATION"
    log_warning "========================================="
    log_warning "This will OVERWRITE the current database!"
    log_warning "Instance: $DB_INSTANCE_NAME"
    log_warning "Backup ID: $backup_id"
    echo ""

    read -p "Are you sure you want to continue? (type 'yes' to confirm): " confirm

    if [ "$confirm" != "yes" ]; then
        log_info "Restoration cancelled"
        return 1
    fi

    log_info "Starting database restoration..."

    # Restore backup
    gcloud sql backups restore "$backup_id" \
        --backup-instance="$DB_INSTANCE_NAME" \
        --instance="$DB_INSTANCE_NAME" \
        --project="$GCP_PROJECT_ID"

    log_success "Database restored successfully"

    # Restart backend pods to reconnect
    restart_backend_pods
}

# Restore from exported SQL file
restore_from_export() {
    local export_file=$1

    log_warning "Restoring from export file: $export_file"

    # Import SQL file
    gcloud sql import sql "$DB_INSTANCE_NAME" \
        "$export_file" \
        --database="${DB_NAME:-ap2_expense}" \
        --project="$GCP_PROJECT_ID"

    log_success "Database imported successfully"
    restart_backend_pods
}

# Restart backend pods to force reconnection
restart_backend_pods() {
    log_info "Restarting backend pods..."

    if kubectl get namespace ap2-expense &>/dev/null; then
        kubectl rollout restart deployment/backend -n ap2-expense
        kubectl rollout status deployment/backend -n ap2-expense --timeout=5m
        log_success "Backend pods restarted"
    else
        log_warning "Kubernetes namespace not found, skipping pod restart"
    fi
}

# Redeploy application
redeploy_application() {
    log_info "Redeploying application..."

    local deployment_method="${1:-kubernetes}"

    case "$deployment_method" in
        kubernetes)
            redeploy_kubernetes
            ;;
        cloud-run)
            redeploy_cloud_run
            ;;
        helm)
            redeploy_helm
            ;;
        *)
            log_error "Unknown deployment method: $deployment_method"
            exit 1
            ;;
    esac
}

# Redeploy Kubernetes
redeploy_kubernetes() {
    log_info "Redeploying Kubernetes resources..."

    # Apply all manifests
    kubectl apply -f k8s/namespace.yaml
    kubectl apply -f k8s/configmap.yaml
    kubectl apply -f k8s/secrets.yaml
    kubectl apply -f k8s/serviceaccount.yaml
    kubectl apply -f k8s/backend-deployment.yaml
    kubectl apply -f k8s/frontend-deployment.yaml
    kubectl apply -f k8s/backend-service.yaml
    kubectl apply -f k8s/frontend-service.yaml
    kubectl apply -f k8s/hpa.yaml
    kubectl apply -f k8s/ingress.yaml

    # Wait for deployments
    kubectl rollout status deployment/backend -n ap2-expense --timeout=10m
    kubectl rollout status deployment/frontend -n ap2-expense --timeout=10m

    log_success "Kubernetes deployment complete"
}

# Redeploy Cloud Run
redeploy_cloud_run() {
    log_info "Redeploying Cloud Run services..."

    # Trigger Cloud Build
    gcloud builds submit \
        --config=cloudbuild.yaml \
        --project="$GCP_PROJECT_ID"

    log_success "Cloud Run deployment complete"
}

# Redeploy Helm
redeploy_helm() {
    log_info "Redeploying Helm chart..."

    helm upgrade ap2-expense ./helm/ap2-expense \
        --namespace=ap2-expense \
        --values=helm/ap2-expense/values.production.yaml \
        --wait \
        --timeout=10m

    log_success "Helm deployment complete"
}

# Verify application health
verify_health() {
    log_info "Verifying application health..."

    # Check backend pods
    if kubectl get namespace ap2-expense &>/dev/null; then
        local backend_pods=$(kubectl get pods -n ap2-expense -l app.kubernetes.io/component=backend --field-selector=status.phase=Running -o json | jq -r '.items | length')
        log_info "Backend pods running: $backend_pods"

        if [ "$backend_pods" -lt 1 ]; then
            log_error "No backend pods running!"
            return 1
        fi
    fi

    # Test health endpoint
    local ingress_ip=$(kubectl get ingress ap2-expense-ingress -n ap2-expense -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")

    if [ -n "$ingress_ip" ]; then
        log_info "Testing health endpoint at $ingress_ip..."
        if curl -f -s "http://${ingress_ip}/api/health" > /dev/null; then
            log_success "Health check passed"
        else
            log_warning "Health check failed (may need time to propagate)"
        fi
    else
        log_warning "Ingress IP not yet assigned"
    fi

    # Check database connectivity
    log_info "Checking database connectivity..."
    local backend_pod=$(kubectl get pods -n ap2-expense -l app.kubernetes.io/component=backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

    if [ -n "$backend_pod" ]; then
        kubectl exec -it "$backend_pod" -n ap2-expense -- python -c "
from src.database import engine
try:
    conn = engine.connect()
    print('✅ Database connection successful')
    conn.close()
except Exception as e:
    print(f'❌ Database connection failed: {e}')
        " || log_warning "Could not verify database connection"
    fi

    log_success "Health verification complete"
}

# Create recovery report
create_recovery_report() {
    local recovery_type=$1
    local timestamp=$(date +%Y-%m-%d\ %H:%M:%S)

    log_info "Creating recovery report..."

    cat > "/tmp/recovery-report-$(date +%Y%m%d-%H%M%S).txt" <<EOF
========================================
DISASTER RECOVERY REPORT
========================================

Recovery Type: $recovery_type
Timestamp: $timestamp
Project: $GCP_PROJECT_ID
Database Instance: $DB_INSTANCE_NAME
Performed By: $(whoami)
Hostname: $(hostname)

========================================
ACTIONS TAKEN
========================================

$(cat /tmp/recovery-actions.log 2>/dev/null || echo "No actions logged")

========================================
POST-RECOVERY STATUS
========================================

Backend Pods:
$(kubectl get pods -n ap2-expense -l app.kubernetes.io/component=backend 2>/dev/null || echo "N/A")

Frontend Pods:
$(kubectl get pods -n ap2-expense -l app.kubernetes.io/component=frontend 2>/dev/null || echo "N/A")

Services:
$(kubectl get svc -n ap2-expense 2>/dev/null || echo "N/A")

========================================
NEXT STEPS
========================================

1. Verify application functionality manually
2. Check monitoring dashboards for errors
3. Review logs for any issues
4. Notify stakeholders of recovery completion
5. Document root cause (if applicable)
6. Update runbooks if process has changed

========================================
EOF

    log_success "Recovery report created: /tmp/recovery-report-$(date +%Y%m%d-%H%M%S).txt"
}

# Print usage
print_usage() {
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  list-backups                 - List available database backups"
    echo "  restore-db <backup-id>       - Restore database from backup"
    echo "  restore-export <gs://path>   - Restore from exported SQL file"
    echo "  redeploy <method>            - Redeploy application (kubernetes|cloud-run|helm)"
    echo "  verify-health                - Verify application health"
    echo "  full-recovery <backup-id>    - Complete disaster recovery (restore DB + redeploy)"
    echo ""
}

# Full disaster recovery procedure
full_disaster_recovery() {
    local backup_id=$1
    local deployment_method="${2:-kubernetes}"

    log_warning "========================================="
    log_warning "FULL DISASTER RECOVERY"
    log_warning "========================================="
    log_warning "This will:"
    log_warning "  1. Restore database from backup: $backup_id"
    log_warning "  2. Redeploy application: $deployment_method"
    log_warning "  3. Verify health"
    echo ""

    read -p "Are you sure you want to continue? (type 'yes' to confirm): " confirm

    if [ "$confirm" != "yes" ]; then
        log_info "Recovery cancelled"
        return 1
    fi

    # Start logging
    exec > >(tee -a /tmp/recovery-actions.log)
    exec 2>&1

    log_info "Starting full disaster recovery at $(date)"

    # Step 1: Restore database
    restore_database "$backup_id"

    # Step 2: Redeploy application
    redeploy_application "$deployment_method"

    # Step 3: Verify health
    sleep 30  # Wait for services to stabilize
    verify_health

    # Create report
    create_recovery_report "full-recovery"

    log_success "========================================="
    log_success "DISASTER RECOVERY COMPLETE"
    log_success "========================================="
}

# Main execution
main() {
    local command="${1:-}"

    if [ -z "$command" ]; then
        print_usage
        exit 1
    fi

    echo ""
    log_info "========================================="
    log_info "Disaster Recovery Tool"
    log_info "========================================="
    echo ""

    check_prerequisites

    case "$command" in
        list-backups)
            list_available_backups
            ;;
        restore-db)
            if [ -z "${2:-}" ]; then
                log_error "Usage: $0 restore-db <backup-id>"
                exit 1
            fi
            restore_database "$2"
            ;;
        restore-export)
            if [ -z "${2:-}" ]; then
                log_error "Usage: $0 restore-export <gs://path>"
                exit 1
            fi
            restore_from_export "$2"
            ;;
        redeploy)
            redeploy_application "${2:-kubernetes}"
            ;;
        verify-health)
            verify_health
            ;;
        full-recovery)
            if [ -z "${2:-}" ]; then
                log_error "Usage: $0 full-recovery <backup-id> [deployment-method]"
                exit 1
            fi
            full_disaster_recovery "$2" "${3:-kubernetes}"
            ;;
        *)
            log_error "Unknown command: $command"
            print_usage
            exit 1
            ;;
    esac
}

main "$@"
