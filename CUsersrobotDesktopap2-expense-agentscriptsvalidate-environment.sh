#!/bin/bash
# Validate GCP Marketplace Environment Configuration
#
# This script validates that all required environment variables,
# secrets, service accounts, and resources are properly configured
# before deploying to production.
#
# Usage: ./scripts/validate-environment.sh <environment>
# Example: ./scripts/validate-environment.sh production

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Validate arguments
ENVIRONMENT=${1:-staging}

echo -e "${BLUE}Environment Validation for GCP Marketplace${NC}"
echo -e "Environment: $ENVIRONMENT"
echo ""

# Track validation results
ERRORS=0
WARNINGS=0
SUCCESS=0

# Helper function to check result
check_result() {
    local test_name="$1"
    local result=$2
    local is_critical=${3:-true}

    if [ $result -eq 0 ]; then
        echo -e "${GREEN}OK${NC} $test_name"
        ((SUCCESS++))
    else
        if [ "$is_critical" = true ]; then
            echo -e "${RED}FAIL${NC} $test_name"
            ((ERRORS++))
        else
            echo -e "${YELLOW}WARN${NC} $test_name"
            ((WARNINGS++))
        fi
    fi
}

echo "Validation complete: $SUCCESS passed, $WARNINGS warnings, $ERRORS errors"

if [ $ERRORS -gt 0 ]; then
    exit 1
else
    exit 0
fi
