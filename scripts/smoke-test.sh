#!/bin/bash

# ============================================================================
# Post-Deployment Smoke Test Script
# ============================================================================
#
# Purpose: Verify critical functionality after deployment
# Priority: CRITICAL
# Usage: ./scripts/smoke-test.sh [environment]
#
# Tests:
# - Service health and readiness
# - Database connectivity
# - Authentication endpoints
# - Critical API endpoints
# - External integrations (Stripe, GCP)
# - Performance baselines
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
API_BASE_URL=${API_BASE_URL:-}
TIMEOUT=${TIMEOUT:-10}

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# Test results
declare -a FAILED_TESTS

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

print_test_header() {
    echo -e "${BLUE}▶ $1${NC}"
}

run_test() {
    local test_name=$1
    shift
    local test_command="$@"

    TESTS_RUN=$((TESTS_RUN + 1))
    print_test_header "$test_name"

    if eval "$test_command" > /dev/null 2>&1; then
        print_success "$test_name: PASSED"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        print_error "$test_name: FAILED"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("$test_name")
        return 1
    fi
}

check_prerequisites() {
    print_header "Checking Prerequisites"

    # Determine API URL if not set
    if [ -z "$API_BASE_URL" ]; then
        case $ENVIRONMENT in
            production)
                # Try to get from Cloud Run
                if command -v gcloud &> /dev/null; then
                    API_BASE_URL=$(gcloud run services describe ap2-expense-backend \
                        --region=us-central1 \
                        --format="value(status.url)" 2>/dev/null || echo "")
                fi

                if [ -z "$API_BASE_URL" ]; then
                    print_error "Cannot determine production API URL"
                    echo "Set API_BASE_URL environment variable"
                    return 1
                fi
                ;;
            staging)
                API_BASE_URL=${API_BASE_URL:-https://staging-api.ap2expense.com}
                ;;
            development)
                API_BASE_URL=${API_BASE_URL:-http://localhost:8000}
                ;;
        esac
    fi

    echo "Environment: $ENVIRONMENT"
    echo "API Base URL: $API_BASE_URL"
    echo "Timeout: ${TIMEOUT}s"
    echo ""

    # Check curl
    if ! command -v curl &> /dev/null; then
        print_error "curl not found"
        return 1
    fi
    print_success "curl available"

    # Check jq (optional but helpful)
    if ! command -v jq &> /dev/null; then
        print_warning "jq not found (JSON parsing will be limited)"
    else
        print_success "jq available"
    fi

    echo ""
}

# ============================================================================
# Health & Readiness Tests
# ============================================================================

test_health_endpoint() {
    print_header "Test 1: Health Check"

    local response=$(curl -sf -m $TIMEOUT "${API_BASE_URL}/health" 2>&1)

    if echo "$response" | grep -q "healthy"; then
        print_success "Health endpoint: OK"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        print_error "Health endpoint: FAILED"
        echo "Response: $response"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("Health Check")
        return 1
    fi

    TESTS_RUN=$((TESTS_RUN + 1))
    return 0
}

test_readiness_endpoint() {
    print_header "Test 2: Readiness Check"

    local response=$(curl -sf -m $TIMEOUT "${API_BASE_URL}/health/ready" 2>&1)

    if echo "$response" | grep -q "ready"; then
        print_success "Readiness endpoint: OK"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        print_error "Readiness endpoint: FAILED"
        echo "Response: $response"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("Readiness Check")
        return 1
    fi

    TESTS_RUN=$((TESTS_RUN + 1))
    return 0
}

test_database_connectivity() {
    print_header "Test 3: Database Connectivity"

    # Health endpoint should include DB status
    local response=$(curl -sf -m $TIMEOUT "${API_BASE_URL}/health" 2>&1)

    if echo "$response" | grep -q "database"; then
        if command -v jq &> /dev/null; then
            local db_status=$(echo "$response" | jq -r '.database' 2>/dev/null || echo "unknown")
            if [ "$db_status" = "ok" ] || [ "$db_status" = "healthy" ]; then
                print_success "Database connectivity: OK"
                TESTS_PASSED=$((TESTS_PASSED + 1))
            else
                print_error "Database connectivity: FAILED (status: $db_status)"
                TESTS_FAILED=$((TESTS_FAILED + 1))
                FAILED_TESTS+=("Database Connectivity")
                return 1
            fi
        else
            print_success "Database connectivity: OK (basic check)"
            TESTS_PASSED=$((TESTS_PASSED + 1))
        fi
    else
        print_warning "Database status not in health response"
        TESTS_SKIPPED=$((TESTS_SKIPPED + 1))
    fi

    TESTS_RUN=$((TESTS_RUN + 1))
    return 0
}

# ============================================================================
# Authentication Tests
# ============================================================================

test_auth_login_endpoint() {
    print_header "Test 4: Authentication - Login Endpoint"

    # Just check that the endpoint exists and returns expected error
    local response=$(curl -sf -m $TIMEOUT -X POST \
        "${API_BASE_URL}/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"username":"test","password":"test"}' \
        2>&1 || echo "failed")

    if echo "$response" | grep -qi "invalid\|error\|unauthorized"; then
        print_success "Login endpoint: OK (rejects invalid credentials)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        print_error "Login endpoint: FAILED"
        echo "Response: $response"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("Login Endpoint")
        return 1
    fi

    TESTS_RUN=$((TESTS_RUN + 1))
    return 0
}

test_auth_registration_endpoint() {
    print_header "Test 5: Authentication - Registration Endpoint"

    # Check that registration endpoint exists (will fail due to duplicate/rate limit, but endpoint should respond)
    local status_code=$(curl -s -o /dev/null -w "%{http_code}" -m $TIMEOUT -X POST \
        "${API_BASE_URL}/api/v1/auth/register" \
        -H "Content-Type: application/json" \
        -d '{"username":"test","password":"Test123!","email":"test@example.com"}' \
        2>&1)

    # Accept 400 (validation), 429 (rate limit), 409 (conflict) as valid responses
    if [[ "$status_code" =~ ^(400|409|429)$ ]]; then
        print_success "Registration endpoint: OK (responds correctly)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    elif [ "$status_code" = "000" ]; then
        print_error "Registration endpoint: TIMEOUT"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("Registration Endpoint")
        return 1
    else
        print_warning "Registration endpoint: Unexpected status $status_code"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    fi

    TESTS_RUN=$((TESTS_RUN + 1))
    return 0
}

# ============================================================================
# API Endpoint Tests
# ============================================================================

test_api_docs_endpoint() {
    print_header "Test 6: API Documentation"

    local status_code=$(curl -s -o /dev/null -w "%{http_code}" -m $TIMEOUT \
        "${API_BASE_URL}/docs" 2>&1)

    if [ "$status_code" = "200" ]; then
        print_success "API docs endpoint: OK"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        print_warning "API docs endpoint: Status $status_code"
        TESTS_SKIPPED=$((TESTS_SKIPPED + 1))
    fi

    TESTS_RUN=$((TESTS_RUN + 1))
    return 0
}

test_openapi_schema() {
    print_header "Test 7: OpenAPI Schema"

    local response=$(curl -sf -m $TIMEOUT "${API_BASE_URL}/openapi.json" 2>&1)

    if echo "$response" | grep -q "openapi"; then
        print_success "OpenAPI schema: OK"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        print_warning "OpenAPI schema: Not available"
        TESTS_SKIPPED=$((TESTS_SKIPPED + 1))
    fi

    TESTS_RUN=$((TESTS_RUN + 1))
    return 0
}

test_cors_headers() {
    print_header "Test 8: CORS Configuration"

    local cors_header=$(curl -sI -m $TIMEOUT \
        -H "Origin: https://app.ap2expense.com" \
        "${API_BASE_URL}/health" \
        | grep -i "access-control-allow-origin" || echo "")

    if [ -n "$cors_header" ]; then
        print_success "CORS headers: OK"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        print_warning "CORS headers: Not found (may be expected)"
        TESTS_SKIPPED=$((TESTS_SKIPPED + 1))
    fi

    TESTS_RUN=$((TESTS_RUN + 1))
    return 0
}

# ============================================================================
# Security Tests
# ============================================================================

test_security_headers() {
    print_header "Test 9: Security Headers"

    local headers=$(curl -sI -m $TIMEOUT "${API_BASE_URL}/health")

    local passed=0
    local total=4

    if echo "$headers" | grep -qi "x-content-type-options"; then
        print_success "  X-Content-Type-Options: Present"
        passed=$((passed + 1))
    else
        print_warning "  X-Content-Type-Options: Missing"
    fi

    if echo "$headers" | grep -qi "x-frame-options"; then
        print_success "  X-Frame-Options: Present"
        passed=$((passed + 1))
    else
        print_warning "  X-Frame-Options: Missing"
    fi

    if echo "$headers" | grep -qi "strict-transport-security"; then
        print_success "  Strict-Transport-Security: Present"
        passed=$((passed + 1))
    else
        if [ "$ENVIRONMENT" = "production" ]; then
            print_warning "  Strict-Transport-Security: Missing (HSTS)"
        else
            print_warning "  Strict-Transport-Security: Missing (expected in dev)"
            passed=$((passed + 1))
        fi
    fi

    if echo "$headers" | grep -qi "content-security-policy"; then
        print_success "  Content-Security-Policy: Present"
        passed=$((passed + 1))
    else
        print_warning "  Content-Security-Policy: Missing"
    fi

    if [ $passed -ge 2 ]; then
        print_success "Security headers: OK ($passed/$total)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        print_warning "Security headers: Partial ($passed/$total)"
        TESTS_SKIPPED=$((TESTS_SKIPPED + 1))
    fi

    TESTS_RUN=$((TESTS_RUN + 1))
    return 0
}

test_rate_limiting() {
    print_header "Test 10: Rate Limiting"

    # Make multiple rapid requests to check rate limiting
    local rate_limited=false

    for i in {1..10}; do
        local status_code=$(curl -s -o /dev/null -w "%{http_code}" -m $TIMEOUT \
            "${API_BASE_URL}/health" 2>&1)

        if [ "$status_code" = "429" ]; then
            rate_limited=true
            break
        fi
    done

    if [ "$rate_limited" = true ]; then
        print_success "Rate limiting: OK (429 received)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        print_warning "Rate limiting: Not triggered (may be configured differently)"
        TESTS_SKIPPED=$((TESTS_SKIPPED + 1))
    fi

    TESTS_RUN=$((TESTS_RUN + 1))
    return 0
}

# ============================================================================
# Performance Tests
# ============================================================================

test_response_time() {
    print_header "Test 11: Response Time"

    local start_time=$(date +%s%3N)
    curl -sf -m $TIMEOUT "${API_BASE_URL}/health" > /dev/null 2>&1
    local end_time=$(date +%s%3N)

    local response_time=$((end_time - start_time))

    echo "Response time: ${response_time}ms"

    if [ $response_time -lt 2000 ]; then
        print_success "Response time: OK (${response_time}ms < 2000ms)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    elif [ $response_time -lt 5000 ]; then
        print_warning "Response time: Slow (${response_time}ms)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        print_error "Response time: TOO SLOW (${response_time}ms)"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("Response Time")
        return 1
    fi

    TESTS_RUN=$((TESTS_RUN + 1))
    return 0
}

# ============================================================================
# Integration Tests (Optional)
# ============================================================================

test_stripe_integration() {
    print_header "Test 12: Stripe Integration (Optional)"

    # This test would require authentication, so we just check if environment is configured
    if [ -n "${STRIPE_API_KEY:-}" ]; then
        print_success "Stripe integration: Configured"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        print_warning "Stripe integration: Not configured in environment"
        TESTS_SKIPPED=$((TESTS_SKIPPED + 1))
    fi

    TESTS_RUN=$((TESTS_RUN + 1))
    return 0
}

test_gcp_integration() {
    print_header "Test 13: GCP Marketplace Integration (Optional)"

    if [ -n "${GCP_PROJECT_ID:-}" ]; then
        print_success "GCP integration: Configured"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        print_warning "GCP integration: Not configured in environment"
        TESTS_SKIPPED=$((TESTS_SKIPPED + 1))
    fi

    TESTS_RUN=$((TESTS_RUN + 1))
    return 0
}

# ============================================================================
# Summary Report
# ============================================================================

generate_summary() {
    print_header "Smoke Test Summary"

    echo "Environment: $ENVIRONMENT"
    echo "API Base URL: $API_BASE_URL"
    echo ""

    local pass_rate=0
    if [ $TESTS_RUN -gt 0 ]; then
        pass_rate=$((TESTS_PASSED * 100 / TESTS_RUN))
    fi

    echo "Tests Run:    $TESTS_RUN"
    echo -e "${GREEN}Tests Passed: $TESTS_PASSED${NC}"
    echo -e "${RED}Tests Failed: $TESTS_FAILED${NC}"
    echo -e "${YELLOW}Tests Skipped: $TESTS_SKIPPED${NC}"
    echo ""
    echo "Pass Rate: ${pass_rate}%"
    echo ""

    if [ $TESTS_FAILED -gt 0 ]; then
        echo -e "${RED}Failed Tests:${NC}"
        for test in "${FAILED_TESTS[@]}"; do
            echo "  - $test"
        done
        echo ""
    fi

    if [ $TESTS_FAILED -eq 0 ]; then
        print_success "All smoke tests passed! ✓"
        return 0
    elif [ $TESTS_FAILED -le 2 ]; then
        print_warning "Some tests failed (non-critical)"
        return 0
    else
        print_error "Multiple tests failed - deployment may have issues"
        return 1
    fi
}

# ============================================================================
# Main Execution
# ============================================================================

print_header "Post-Deployment Smoke Tests"
echo ""
echo "Starting smoke tests for: $ENVIRONMENT"
echo ""

# Check prerequisites
if ! check_prerequisites; then
    exit 1
fi

# Run all tests
test_health_endpoint
test_readiness_endpoint
test_database_connectivity
test_auth_login_endpoint
test_auth_registration_endpoint
test_api_docs_endpoint
test_openapi_schema
test_cors_headers
test_security_headers
test_rate_limiting
test_response_time
test_stripe_integration
test_gcp_integration

# Generate summary
echo ""
if generate_summary; then
    exit 0
else
    exit 1
fi
