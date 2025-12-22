#!/bin/bash

###############################################################################
# Pre-Deployment Validation Script
#
# Validates that all prerequisites are met before deploying to GCP
# Run this before any deployment to catch configuration issues early
###############################################################################

set -euo pipefail

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

# Counters
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNING=0

# Check command exists
check_command() {
    local cmd=$1
    local name=$2

    if command -v "$cmd" &> /dev/null; then
        local version=$("$cmd" --version 2>&1 | head -n1)
        log_success "$name installed: $version"
        ((CHECKS_PASSED++))
        return 0
    else
        log_error "$name not found"
        ((CHECKS_FAILED++))
        return 1
    fi
}

# Check environment variable
check_env_var() {
    local var=$1
    local description=$2
    local allow_empty=${3:-false}

    if [ -z "${!var:-}" ]; then
        log_error "$description ($var) not set"
        ((CHECKS_FAILED++))
        return 1
    elif [ "$allow_empty" = "false" ] && ([ "${!var}" = "your-project-id-here" ] || [ "${!var}" = "your-domain.com" ]); then
        log_error "$description ($var) contains placeholder value: ${!var}"
        ((CHECKS_FAILED++))
        return 1
    else
        log_success "$description set: ${!var}"
        ((CHECKS_PASSED++))
        return 0
    fi
}

# Check GCP project access
check_gcp_project() {
    log_info "Checking GCP project access..."

    if gcloud projects describe "$GCP_PROJECT_ID" &>/dev/null; then
        log_success "GCP project accessible: $GCP_PROJECT_ID"
        ((CHECKS_PASSED++))
    else
        log_error "Cannot access GCP project: $GCP_PROJECT_ID"
        ((CHECKS_FAILED++))
        return 1
    fi
}

# Check GCP APIs
check_gcp_apis() {
    log_info "Checking required GCP APIs..."

    local required_apis=(
        "container.googleapis.com"
        "sqladmin.googleapis.com"
        "secretmanager.googleapis.com"
        "cloudkms.googleapis.com"
        "cloudbuild.googleapis.com"
        "run.googleapis.com"
    )

    local apis_status=$(gcloud services list --enabled --project="$GCP_PROJECT_ID" --format="value(config.name)")

    for api in "${required_apis[@]}"; do
        if echo "$apis_status" | grep -q "$api"; then
            log_success "API enabled: $api"
            ((CHECKS_PASSED++))
        else
            log_warning "API not enabled: $api"
            ((CHECKS_WARNING++))
        fi
    done
}

# Check service account exists
check_service_account() {
    log_info "Checking service account..."

    local sa_email="ap2-expense-sa@${GCP_PROJECT_ID}.iam.gserviceaccount.com"

    if gcloud iam service-accounts describe "$sa_email" --project="$GCP_PROJECT_ID" &>/dev/null; then
        log_success "Service account exists: $sa_email"
        ((CHECKS_PASSED++))
    else
        log_warning "Service account not found: $sa_email"
        log_info "Run: ./scripts/setup-gcp-project.sh"
        ((CHECKS_WARNING++))
    fi
}

# Check Cloud SQL instance
check_cloudsql() {
    log_info "Checking Cloud SQL instance..."

    local db_instance="${DB_INSTANCE_NAME:-ap2-expense-db}"

    if gcloud sql instances describe "$db_instance" --project="$GCP_PROJECT_ID" &>/dev/null; then
        log_success "Cloud SQL instance exists: $db_instance"
        ((CHECKS_PASSED++))
    else
        log_warning "Cloud SQL instance not found: $db_instance"
        log_info "Run: ./scripts/setup-gcp-project.sh"
        ((CHECKS_WARNING++))
    fi
}

# Check secrets exist
check_secrets() {
    log_info "Checking Secret Manager secrets..."

    local required_secrets=(
        "jwt-secret-key"
        "jwt-refresh-secret-key"
        "database-password"
    )

    for secret in "${required_secrets[@]}"; do
        if gcloud secrets describe "$secret" --project="$GCP_PROJECT_ID" &>/dev/null; then
            log_success "Secret exists: $secret"
            ((CHECKS_PASSED++))
        else
            log_warning "Secret not found: $secret"
            ((CHECKS_WARNING++))
        fi
    done
}

# Check KMS keyring
check_kms() {
    log_info "Checking Cloud KMS..."

    local keyring="${KMS_KEYRING:-ap2-expense-keyring}"
    local key="${KMS_KEY:-ap2-mandate-signing-key}"

    if gcloud kms keyrings describe "$keyring" --location="$GCP_REGION" --project="$GCP_PROJECT_ID" &>/dev/null; then
        log_success "KMS keyring exists: $keyring"
        ((CHECKS_PASSED++))

        if gcloud kms keys describe "$key" --keyring="$keyring" --location="$GCP_REGION" --project="$GCP_PROJECT_ID" &>/dev/null; then
            log_success "KMS key exists: $key"
            ((CHECKS_PASSED++))
        else
            log_warning "KMS key not found: $key"
            ((CHECKS_WARNING++))
        fi
    else
        log_warning "KMS keyring not found: $keyring"
        ((CHECKS_WARNING++))
    fi
}

# Check Cloud Storage buckets
check_storage() {
    log_info "Checking Cloud Storage buckets..."

    local receipts_bucket="${GCP_PROJECT_ID}-ap2-expense-receipts"
    local backups_bucket="${GCP_PROJECT_ID}-ap2-expense-backups"

    if gsutil ls -b "gs://$receipts_bucket" &>/dev/null; then
        log_success "Receipts bucket exists: $receipts_bucket"
        ((CHECKS_PASSED++))
    else
        log_warning "Receipts bucket not found: $receipts_bucket"
        ((CHECKS_WARNING++))
    fi

    if gsutil ls -b "gs://$backups_bucket" &>/dev/null; then
        log_success "Backups bucket exists: $backups_bucket"
        ((CHECKS_PASSED++))
    else
        log_warning "Backups bucket not found: $backups_bucket"
        ((CHECKS_WARNING++))
    fi
}

# Check Docker images
check_docker_images() {
    log_info "Checking Docker images in GCR..."

    local backend_image="gcr.io/${GCP_PROJECT_ID}/ap2-expense-backend"
    local frontend_image="gcr.io/${GCP_PROJECT_ID}/ap2-expense-frontend"

    if gcloud container images describe "${backend_image}:latest" --project="$GCP_PROJECT_ID" &>/dev/null; then
        log_success "Backend image exists in GCR"
        ((CHECKS_PASSED++))
    else
        log_warning "Backend image not found in GCR"
        log_info "Build with: gcloud builds submit --config=cloudbuild.yaml"
        ((CHECKS_WARNING++))
    fi

    if gcloud container images describe "${frontend_image}:latest" --project="$GCP_PROJECT_ID" &>/dev/null; then
        log_success "Frontend image exists in GCR"
        ((CHECKS_PASSED++))
    else
        log_warning "Frontend image not found in GCR"
        ((CHECKS_WARNING++))
    fi
}

# Check configuration files
check_config_files() {
    log_info "Checking configuration files..."

    local files=(
        "k8s/backend-deployment.yaml"
        "k8s/frontend-deployment.yaml"
        "k8s/configmap.yaml"
        "k8s/secrets.yaml"
        "cloudbuild.yaml"
    )

    for file in "${files[@]}"; do
        if [ -f "$file" ]; then
            # Check for placeholders
            if grep -q "YOUR_PROJECT_ID" "$file"; then
                log_warning "$file contains YOUR_PROJECT_ID placeholder"
                ((CHECKS_WARNING++))
            else
                log_success "$file configured"
                ((CHECKS_PASSED++))
            fi
        else
            log_error "$file not found"
            ((CHECKS_FAILED++))
        fi
    done
}

# Check DNS configuration
check_dns() {
    log_info "Checking DNS configuration..."

    local domain="${APP_DOMAIN:-}"

    if [ -z "$domain" ] || [ "$domain" = "your-domain.com" ]; then
        log_warning "Domain not configured"
        ((CHECKS_WARNING++))
        return 0
    fi

    # Try to resolve domain
    if host "$domain" &>/dev/null; then
        local ip=$(host "$domain" | grep "has address" | awk '{print $4}' | head -n1)
        log_success "Domain resolves: $domain → $ip"
        ((CHECKS_PASSED++))
    else
        log_warning "Domain does not resolve: $domain"
        log_info "Configure DNS after reserving static IP"
        ((CHECKS_WARNING++))
    fi
}

# Check kubectl access (if using K8s)
check_kubectl() {
    log_info "Checking Kubernetes access..."

    if kubectl cluster-info &>/dev/null; then
        local cluster=$(kubectl config current-context)
        log_success "kubectl configured: $cluster"
        ((CHECKS_PASSED++))

        # Check if namespace exists
        if kubectl get namespace ap2-expense &>/dev/null; then
            log_success "Namespace exists: ap2-expense"
            ((CHECKS_PASSED++))
        else
            log_info "Namespace will be created during deployment"
        fi
    else
        log_info "kubectl not configured (OK if using Cloud Run)"
    fi
}

# Check local development environment
check_local_dev() {
    log_info "Checking local development setup..."

    if [ -f ".env" ]; then
        log_success ".env file exists for local development"
        ((CHECKS_PASSED++))
    else
        log_info ".env file not found (not required for deployment)"
    fi

    if [ -f "backend/requirements.txt" ]; then
        log_success "Backend requirements.txt found"
        ((CHECKS_PASSED++))
    else
        log_error "Backend requirements.txt not found"
        ((CHECKS_FAILED++))
    fi

    if [ -f "frontend/package.json" ]; then
        log_success "Frontend package.json found"
        ((CHECKS_PASSED++))
    else
        log_error "Frontend package.json not found"
        ((CHECKS_FAILED++))
    fi
}

# Print summary
print_summary() {
    echo ""
    echo "========================================="
    echo "PRE-DEPLOYMENT CHECK SUMMARY"
    echo "========================================="
    echo ""
    echo -e "${GREEN}Passed:${NC}    $CHECKS_PASSED"
    echo -e "${YELLOW}Warnings:${NC}  $CHECKS_WARNING"
    echo -e "${RED}Failed:${NC}    $CHECKS_FAILED"
    echo ""

    if [ $CHECKS_FAILED -eq 0 ] && [ $CHECKS_WARNING -eq 0 ]; then
        log_success "All checks passed! Ready for deployment 🚀"
        echo ""
        echo "Next steps:"
        echo "  1. Deploy with Cloud Build: gcloud builds submit"
        echo "  2. Or deploy to K8s: kubectl apply -f k8s/"
        echo "  3. Or use Helm: helm install ap2-expense ./helm/ap2-expense"
        return 0
    elif [ $CHECKS_FAILED -eq 0 ]; then
        log_warning "Some warnings detected, but deployment can proceed"
        echo ""
        echo "Warnings are typically about missing optional resources"
        echo "Review warnings above and address if needed"
        return 0
    else
        log_error "Critical issues detected! Fix errors before deploying"
        echo ""
        echo "Common fixes:"
        echo "  - Run: ./scripts/setup-gcp-project.sh"
        echo "  - Run: ./scripts/update-k8s-configs.sh"
        echo "  - Check environment variables in .env.deployment"
        return 1
    fi
}

# Main execution
main() {
    echo ""
    echo "========================================="
    echo "AP2 Expense Agent - Pre-Deployment Check"
    echo "========================================="
    echo ""

    # Check required tools
    log_info "=== Checking Required Tools ==="
    check_command "gcloud" "Google Cloud SDK"
    check_command "kubectl" "Kubectl"
    check_command "docker" "Docker"
    check_command "git" "Git"
    echo ""

    # Check environment variables
    log_info "=== Checking Environment Variables ==="
    check_env_var "GCP_PROJECT_ID" "GCP Project ID"
    check_env_var "GCP_REGION" "GCP Region"
    check_env_var "APP_DOMAIN" "Application Domain" "true"
    echo ""

    # Check GCP resources
    log_info "=== Checking GCP Resources ==="
    check_gcp_project
    check_gcp_apis
    check_service_account
    check_cloudsql
    check_secrets
    check_kms
    check_storage
    echo ""

    # Check images
    log_info "=== Checking Container Images ==="
    check_docker_images
    echo ""

    # Check configurations
    log_info "=== Checking Configuration Files ==="
    check_config_files
    echo ""

    # Check DNS
    log_info "=== Checking DNS ==="
    check_dns
    echo ""

    # Check K8s (if applicable)
    log_info "=== Checking Kubernetes ==="
    check_kubectl
    echo ""

    # Check local dev
    log_info "=== Checking Local Development Setup ==="
    check_local_dev
    echo ""

    # Print summary and exit
    if print_summary; then
        exit 0
    else
        exit 1
    fi
}

main "$@"
