#!/bin/bash

###############################################################################
# Update Kubernetes Configuration Files
#
# This script replaces placeholder values in Kubernetes manifests with
# actual values from environment variables.
#
# Prerequisites:
# - Source .env.deployment file before running this script
###############################################################################

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check required environment variables
check_env_vars() {
    local required_vars=(
        "GCP_PROJECT_ID"
        "APP_DOMAIN"
    )

    local missing_vars=()

    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            missing_vars+=("$var")
        fi
    done

    if [ ${#missing_vars[@]} -gt 0 ]; then
        log_error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        exit 1
    fi
}

# Update file with sed (cross-platform compatible)
update_placeholder() {
    local file=$1
    local placeholder=$2
    local value=$3

    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s|$placeholder|$value|g" "$file"
    else
        # Linux
        sed -i "s|$placeholder|$value|g" "$file"
    fi
}

# Update Kubernetes manifests
update_k8s_files() {
    log_info "Updating Kubernetes manifests in k8s/ directory..."

    local files=(
        "k8s/backend-deployment.yaml"
        "k8s/frontend-deployment.yaml"
        "k8s/billing-cronjob.yaml"
        "k8s/ingress.yaml"
        "k8s/serviceaccount.yaml"
    )

    for file in "${files[@]}"; do
        if [ ! -f "$file" ]; then
            log_error "File not found: $file"
            continue
        fi

        log_info "  Updating $file"

        # Replace project ID
        update_placeholder "$file" "YOUR_PROJECT_ID" "$GCP_PROJECT_ID"

        # Replace domain
        update_placeholder "$file" "your-domain.com" "$APP_DOMAIN"
    done

    log_success "Kubernetes manifests updated"
}

# Update Helm values
update_helm_values() {
    log_info "Updating Helm values file..."

    local helm_file="helm/ap2-expense/values.yaml"

    if [ ! -f "$helm_file" ]; then
        log_error "Helm values file not found: $helm_file"
        return 1
    fi

    # Create production copy
    cp "$helm_file" "helm/ap2-expense/values.production.yaml"

    local prod_file="helm/ap2-expense/values.production.yaml"

    log_info "  Updating $prod_file"

    # Replace project ID
    update_placeholder "$prod_file" "YOUR_PROJECT_ID" "$GCP_PROJECT_ID"

    # Replace domain
    update_placeholder "$prod_file" "your-domain.com" "$APP_DOMAIN"

    log_success "Helm values updated: $prod_file"
}

# Update cloudbuild.yaml
update_cloudbuild() {
    log_info "Updating cloudbuild.yaml..."

    local file="cloudbuild.yaml"

    if [ ! -f "$file" ]; then
        log_error "File not found: $file"
        return 1
    fi

    # Note: Cloud Build automatically substitutes $PROJECT_ID
    # But we'll update any YOUR_PROJECT_ID placeholders just in case

    update_placeholder "$file" "YOUR_PROJECT_ID" "$GCP_PROJECT_ID"

    log_success "cloudbuild.yaml updated"
}

# Update monitoring alerts
update_monitoring() {
    log_info "Updating monitoring alert policies..."

    local file="monitoring/alerts/alert-policies.yaml"

    if [ ! -f "$file" ]; then
        log_error "File not found: $file"
        return 1
    fi

    update_placeholder "$file" "YOUR_PROJECT_ID" "$GCP_PROJECT_ID"

    log_success "Monitoring alerts updated"
    log_info "⚠️  Remember to update YOUR_CHANNEL_ID with actual notification channel IDs"
}

# Update security policies
update_security() {
    log_info "Updating security configurations..."

    local files=(
        "security/cloud-armor-policy.yaml"
        "security/network-policy.yaml"
    )

    for file in "${files[@]}"; do
        if [ ! -f "$file" ]; then
            continue
        fi

        log_info "  Updating $file"
        update_placeholder "$file" "YOUR_PROJECT_ID" "$GCP_PROJECT_ID"
    done

    log_success "Security configurations updated"
}

# Create .env file for local development
create_dotenv() {
    log_info "Creating .env file for local development..."

    cat > .env <<EOF
# Environment
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=debug

# Frontend
FRONTEND_URL=http://localhost:5173
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost

# Database (local SQLite for development)
DATABASE_URL=sqlite:///./test.db

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# JWT Secrets (development only - DO NOT use in production)
JWT_SECRET=$(openssl rand -hex 32)
JWT_REFRESH_SECRET=$(openssl rand -hex 32)

# GCP Configuration (for local testing with real GCP services)
GCP_PROJECT_ID=$GCP_PROJECT_ID
GOOGLE_CLOUD_PROJECT=$GCP_PROJECT_ID
GCP_KMS_LOCATION=us-central1
GCP_KMS_KEYRING=ap2-expense-keyring
GCP_KMS_SIGNING_KEY=ap2-mandate-signing-key

# Google AI (optional - for AI features)
GOOGLE_API_KEY=
GOOGLE_GENAI_USE_VERTEXAI=false

# Stripe payment processor (AP2 optional)
STRIPE_SECRET_KEY=sk_test_

# Email (optional)
SMTP_SERVER=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
FROM_EMAIL=noreply@localhost

# Feature Flags
ENABLE_BILLING=false
ENABLE_GCP_MARKETPLACE=false
NOTIFICATIONS_ENABLED=false

# Connection Pooling
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_RECYCLE=3600

# Security
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION_MINUTES=30
PASSWORD_RESET_EXPIRATION_HOURS=1
SESSION_EXPIRATION_HOURS=24

# Data Retention
AUDIT_LOG_RETENTION_DAYS=90
SESSION_RETENTION_DAYS=30
REVOKED_TOKEN_RETENTION_DAYS=7
EOF

    log_success ".env file created for local development"
}

# Print summary
print_summary() {
    echo ""
    log_success "========================================="
    log_success "Configuration Update Complete!"
    log_success "========================================="
    echo ""
    log_info "Updated files:"
    echo "  - k8s/*.yaml"
    echo "  - helm/ap2-expense/values.production.yaml"
    echo "  - cloudbuild.yaml"
    echo "  - monitoring/alerts/alert-policies.yaml"
    echo "  - security/*.yaml"
    echo "  - .env (local development)"
    echo ""
    log_info "⚠️  Manual steps still required:"
    echo "  1. Update notification channel IDs in monitoring/alerts/alert-policies.yaml"
    echo "  2. Update secrets in k8s/secrets.yaml or use Secret Manager"
    echo "  3. Review and commit changes to version control"
    echo ""
}

# Main execution
main() {
    echo ""
    log_info "========================================="
    log_info "Updating Configuration Files"
    log_info "========================================="
    echo ""

    check_env_vars
    update_k8s_files
    update_helm_values
    update_cloudbuild
    update_monitoring
    update_security
    create_dotenv
    print_summary
}

main "$@"
