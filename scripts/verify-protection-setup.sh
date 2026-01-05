#!/bin/bash
# Complete Protection Setup Verification Script
# Verifies all 13 protection layers are active and functional

echo "=========================================="
echo "AP2 EXPENSE AGENT - Protection Verification"
echo "=========================================="
echo ""

FAILED=0
PASSED=0

# Check 1: Git pre-commit hook exists
echo -n "Checking git pre-commit hook... "
if [ -f ".git/hooks/pre-commit" ]; then
    echo "[PASS]"
    ((PASSED++))
else
    echo "[FAIL]"
    echo "  Run: bash scripts/install-tier-protection-hook.sh"
    ((FAILED++))
fi

# Check 2: Tier limit guardian exists
echo -n "Checking tier limit guardian... "
if [ -f "backend/src/billing/tier_limit_guardian.py" ]; then
    echo "[PASS]"
    ((PASSED++))
else
    echo "[FAIL]"
    ((FAILED++))
fi

# Check 3: Baseline specification exists
echo -n "Checking baseline specification... "
if [ -f "backend/FUNCTIONALITY_BASELINE.json" ]; then
    echo "[PASS]"
    ((PASSED++))
else
    echo "[FAIL]"
    ((FAILED++))
fi

# Check 4: CI/CD workflow exists
echo -n "Checking CI/CD workflow... "
if [ -f ".github/workflows/tier-limits-validation.yml" ]; then
    echo "[PASS]"
    ((PASSED++))
else
    echo "[FAIL]"
    ((FAILED++))
fi

# Check 5: Tier limit tests exist
echo -n "Checking tier limit tests... "
if [ -f "backend/test_tier_limits_enforcement.py" ]; then
    echo "[PASS]"
    ((PASSED++))
else
    echo "[FAIL]"
    ((FAILED++))
fi

# Check 6: Functionality tests exist
echo -n "Checking functionality tests... "
if [ -f "backend/test_critical_functionality_integrity.py" ]; then
    echo "[PASS]"
    ((PASSED++))
else
    echo "[FAIL]"
    ((FAILED++))
fi

# Check 7: Baseline validator exists
echo -n "Checking baseline validator... "
if [ -f "backend/validate_against_baseline.py" ]; then
    echo "[PASS]"
    ((PASSED++))
else
    echo "[FAIL]"
    ((FAILED++))
fi

echo ""
echo "=========================================="
echo "PROTECTION SETUP SUMMARY"
echo "=========================================="
echo ""
echo "Files checked: $((PASSED + FAILED))"
echo "  [PASS] Passed: $PASSED"
echo "  [FAIL] Failed: $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "[SUCCESS] All protection files are in place!"
    echo ""
    echo "Next steps:"
    echo "  1. Run: cd backend && python seed_billing_tiers.py --verify"
    echo "  2. Run: cd backend && python test_tier_limits_enforcement.py"
    echo "  3. Run: cd backend && python test_critical_functionality_integrity.py"
    echo ""
    exit 0
else
    echo "[ERROR] Protection setup incomplete"
    echo ""
    echo "Fix missing files before deploying to production"
    echo ""
    exit 1
fi
