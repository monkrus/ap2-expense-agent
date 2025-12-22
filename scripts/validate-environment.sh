#!/bin/bash

# ============================================================================
# Environment Variable Validation Script
# ============================================================================
#
# Purpose: Validate all required environment variables before deployment
# Priority: CRITICAL
# Run: ./scripts/validate-environment.sh [production|staging|development]
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
ENVIRONMENT=${1:-development}
STRICT_MODE=${STRICT_MODE:-false}

# Counters
TOTAL_VARS=0
VALID_VARS=0
MISSING_VARS=0
INVALID_VARS=0

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

check_var() {
    local var_name=$1
    local required=$2
    local pattern=$3
    local description=$4

    TOTAL_VARS=$((TOTAL_VARS + 1))

    if [ -z "${!var_name:-}" ]; then
        if [ "$required" = "true" ]; then
            print_error "$var_name: MISSING (required)"
            MISSING_VARS=$((MISSING_VARS + 1))
            return 1
        else
            print_warning "$var_name: Not set (optional)"
            return 0
        fi
    fi

    # Validate pattern if provided
    if [ -n "$pattern" ]; then
        if [[ ! "${!var_name}" =~ $pattern ]]; then
            print_error "$var_name: INVALID format"
            INVALID_VARS=$((INVALID_VARS + 1))
            return 1
        fi
    fi

    # Mask sensitive values
    local display_value="${!var_name}"
    if [[ "$var_name" =~ (SECRET|KEY|PASSWORD|TOKEN) ]]; then
        local len=${#display_value}
        display_value="****${display_value: -4}"
    fi

    print_success "$var_name: ${display_value:0:50}..."
    VALID_VARS=$((VALID_VARS + 1))
    return 0
}

print_header "Environment Validation - $ENVIRONMENT"
echo ""

# ============================================================================
# Core Application Variables
# ============================================================================

print_header "Core Application"
check_var "ENVIRONMENT" true "^(development|staging|production)$" "Deployment environment"
check_var "APP_VERSION" false "^v?[0-9]+\\.[0-9]+\\.[0-9]+$" "Application version"
check_var "LOG_LEVEL" false "^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$" "Logging level"
check_var "FRONTEND_URL" true "^https?://" "Frontend URL"
echo ""

# ============================================================================
# Database Configuration
# ============================================================================

print_header "Database"
check_var "DATABASE_URL" true "^(postgresql|sqlite)://" "Database connection string"
check_var "REDIS_URL" false "^redis://" "Redis connection string"
check_var "DB_POOL_SIZE" false "^[0-9]+$" "Database connection pool size"
echo ""

# ============================================================================
# JWT & Authentication
# ============================================================================

print_header "Authentication & Security"
check_var "JWT_SECRET" true "^.{32,}$" "JWT secret (min 32 chars)"
check_var "JWT_ALGORITHM" false "^HS(256|384|512)$" "JWT algorithm"
check_var "JWT_EXPIRATION_MINUTES" false "^[0-9]+$" "JWT expiration (minutes)"
echo ""

# ============================================================================
# Stripe Integration
# ============================================================================

print_header "Stripe Payment Processing"
if [ "$ENVIRONMENT" = "production" ]; then
    check_var "STRIPE_API_KEY" true "^sk_live_" "Stripe API key (production)"
else
    check_var "STRIPE_API_KEY" true "^sk_test_" "Stripe API key (test)"
fi
check_var "STRIPE_WEBHOOK_SECRET" true "^whsec_" "Stripe webhook secret"
check_var "STRIPE_PRICE_ID_STARTER" false "^price_" "Stripe price ID - Starter"
check_var "STRIPE_PRICE_ID_PROFESSIONAL" false "^price_" "Stripe price ID - Professional"
check_var "STRIPE_PRICE_ID_ENTERPRISE" false "^price_" "Stripe price ID - Enterprise"
echo ""

# ============================================================================
# Google Cloud Platform
# ============================================================================

print_header "Google Cloud Platform"
check_var "GCP_PROJECT_ID" true "^[a-z][a-z0-9-]{4,28}[a-z0-9]$" "GCP project ID"
check_var "GCP_SERVICE_ACCOUNT_PATH" false "\\.(json|JSON)$" "GCP service account JSON path"
check_var "GCP_KMS_KEY_RING" false "" "Cloud KMS key ring"
check_var "GCP_KMS_KEY_NAME" false "" "Cloud KMS key name"
check_var "GCP_STORAGE_BUCKET" false "" "Cloud Storage bucket for receipts"
echo ""

# ============================================================================
# GCP Marketplace
# ============================================================================

print_header "GCP Marketplace"
check_var "GCP_WEBHOOK_SECRET" false "" "GCP Marketplace webhook secret"
check_var "GCP_WEBHOOK_AUDIENCE" false "^https://" "GCP webhook audience URL"
echo ""

# ============================================================================
# Monitoring & Alerting
# ============================================================================

print_header "Monitoring & Alerting"
if [ "$ENVIRONMENT" = "production" ]; then
    check_var "SLACK_WEBHOOK_URL" true "^https://hooks\\.slack\\.com/" "Slack webhook URL"
    check_var "PAGERDUTY_INTEGRATION_KEY" true "^[a-f0-9]{32}$" "PagerDuty integration key"
else
    check_var "SLACK_WEBHOOK_URL" false "^https://hooks\\.slack\\.com/" "Slack webhook URL"
    check_var "PAGERDUTY_INTEGRATION_KEY" false "" "PagerDuty integration key"
fi
echo ""

# ============================================================================
# Email Configuration
# ============================================================================

print_header "Email Service"
check_var "SMTP_HOST" false "" "SMTP server host"
check_var "SMTP_PORT" false "^[0-9]+$" "SMTP server port"
check_var "SMTP_USERNAME" false "" "SMTP username"
check_var "SMTP_PASSWORD" false "" "SMTP password"
check_var "EMAIL_FROM" false "^[^@]+@[^@]+\\.[^@]+$" "From email address"
echo ""

# ============================================================================
# Rate Limiting
# ============================================================================

print_header "Rate Limiting"
check_var "RATE_LIMIT_ENABLED" false "^(true|false)$" "Rate limiting enabled"
check_var "RATE_LIMIT_LOGIN" false "^[0-9]+/(minute|hour|day)$" "Login rate limit"
echo ""

# ============================================================================
# Summary
# ============================================================================

print_header "Validation Summary"
echo "Environment: $ENVIRONMENT"
echo "Total variables checked: $TOTAL_VARS"
echo -e "${GREEN}Valid: $VALID_VARS${NC}"
echo -e "${YELLOW}Optional (not set): $((TOTAL_VARS - VALID_VARS - MISSING_VARS - INVALID_VARS))${NC}"
if [ $MISSING_VARS -gt 0 ]; then
    echo -e "${RED}Missing (required): $MISSING_VARS${NC}"
fi
if [ $INVALID_VARS -gt 0 ]; then
    echo -e "${RED}Invalid format: $INVALID_VARS${NC}"
fi
echo ""

# ============================================================================
# Exit Code
# ============================================================================

if [ $MISSING_VARS -gt 0 ] || [ $INVALID_VARS -gt 0 ]; then
    print_error "Environment validation FAILED"
    echo ""
    echo "Fix the issues above before deploying to $ENVIRONMENT"
    exit 1
else
    print_success "Environment validation PASSED ✓"
    echo ""
    echo "Environment is ready for deployment to $ENVIRONMENT"
    exit 0
fi
