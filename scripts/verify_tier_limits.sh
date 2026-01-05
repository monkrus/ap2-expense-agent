#!/bin/bash
# Tier Limits Verification Script
# This script verifies that tier limits match the official specification
# Run this before commits that modify tier-related files

set -e

echo "=========================================="
echo "Tier Limits Verification"
echo "=========================================="

# Check if tier-related files have been modified
TIER_FILES_CHANGED=false

if git diff --cached --name-only | grep -q "seed_billing_tiers.py"; then
    echo "⚠️  Detected changes to seed_billing_tiers.py"
    TIER_FILES_CHANGED=true
fi

if git diff --cached --name-only | grep -q "frontend/src/config/constants.js"; then
    echo "⚠️  Detected changes to frontend constants.js"
    TIER_FILES_CHANGED=true
fi

if [ "$TIER_FILES_CHANGED" = false ]; then
    echo "✓ No tier limit files modified"
    exit 0
fi

echo ""
echo "⚠️  TIER LIMIT PROTECTION ACTIVATED ⚠️"
echo ""
echo "Tier limit files have been modified."
echo "Running validation tests..."
echo ""

# Run tier limit tests
cd backend
python seed_billing_tiers.py --verify

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ TIER LIMIT VERIFICATION FAILED"
    echo ""
    echo "Tier limits in database do not match official specification."
    echo "Please run: python backend/seed_billing_tiers.py --force"
    echo ""
    echo "If you are intentionally changing tier limits, ensure:"
    echo "  1. You have approval from Product, Finance, and Legal"
    echo "  2. Both backend/seed_billing_tiers.py and frontend/src/config/constants.js are updated"
    echo "  3. TIER_LIMITS_PROTECTION.md is updated"
    echo ""
    echo "To bypass this check (EMERGENCY ONLY):"
    echo "  git commit --no-verify"
    echo ""
    exit 1
fi

# Run enforcement tests
python test_tier_limits_enforcement.py

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ TIER LIMIT ENFORCEMENT TESTS FAILED"
    echo ""
    echo "Some tier limit tests failed."
    echo "Review test output above and fix issues before committing."
    echo ""
    exit 1
fi

echo ""
echo "=========================================="
echo "✓ Tier Limits Verification Passed"
echo "=========================================="
echo ""
echo "REMINDER: Tier limit changes require approval from:"
echo "  - Product Manager"
echo "  - Finance Team"
echo "  - Legal Team"
echo "  - Engineering Lead"
echo ""
echo "Have you obtained all required approvals? (y/n)"
read -r response

if [[ ! "$response" =~ ^[Yy]$ ]]; then
    echo ""
    echo "❌ Commit aborted - approvals required"
    echo ""
    exit 1
fi

echo ""
echo "✓ Proceeding with commit"
echo ""

exit 0
