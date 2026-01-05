# Complete Protection Setup Verification Script (PowerShell)
# Verifies all 13 protection layers are active and functional

$ErrorActionPreference = "Continue"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "AP2 EXPENSE AGENT - Protection Verification" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$Failed = 0
$Passed = 0

# Check 1: Git pre-commit hook exists
Write-Host "Checking git pre-commit hook... " -NoNewline
if (Test-Path ".git\hooks\pre-commit") {
    Write-Host "[PASS]" -ForegroundColor Green
    $Passed++
} else {
    Write-Host "[FAIL]" -ForegroundColor Red
    Write-Host "  Run: .\scripts\install-tier-protection-hook.ps1" -ForegroundColor Yellow
    $Failed++
}

# Check 2: Tier limit guardian exists
Write-Host "Checking tier limit guardian... " -NoNewline
if (Test-Path "backend\src\billing\tier_limit_guardian.py") {
    Write-Host "[PASS]" -ForegroundColor Green
    $Passed++
} else {
    Write-Host "[FAIL]" -ForegroundColor Red
    $Failed++
}

# Check 3: Baseline specification exists
Write-Host "Checking baseline specification... " -NoNewline
if (Test-Path "backend\FUNCTIONALITY_BASELINE.json") {
    Write-Host "[PASS]" -ForegroundColor Green
    $Passed++
} else {
    Write-Host "[FAIL]" -ForegroundColor Red
    $Failed++
}

# Check 4: CI/CD workflow exists
Write-Host "Checking CI/CD workflow... " -NoNewline
if (Test-Path ".github\workflows\tier-limits-validation.yml") {
    Write-Host "[PASS]" -ForegroundColor Green
    $Passed++
} else {
    Write-Host "[FAIL]" -ForegroundColor Red
    $Failed++
}

# Check 5: Tier limit tests exist
Write-Host "Checking tier limit tests... " -NoNewline
if (Test-Path "backend\test_tier_limits_enforcement.py") {
    Write-Host "[PASS]" -ForegroundColor Green
    $Passed++
} else {
    Write-Host "[FAIL]" -ForegroundColor Red
    $Failed++
}

# Check 6: Functionality tests exist
Write-Host "Checking functionality tests... " -NoNewline
if (Test-Path "backend\test_critical_functionality_integrity.py") {
    Write-Host "[PASS]" -ForegroundColor Green
    $Passed++
} else {
    Write-Host "[FAIL]" -ForegroundColor Red
    $Failed++
}

# Check 7: Baseline validator exists
Write-Host "Checking baseline validator... " -NoNewline
if (Test-Path "backend\validate_against_baseline.py") {
    Write-Host "[PASS]" -ForegroundColor Green
    $Passed++
} else {
    Write-Host "[FAIL]" -ForegroundColor Red
    $Failed++
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "PROTECTION SETUP SUMMARY" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Files checked: $($Passed + $Failed)"
Write-Host "  [PASS] Passed: $Passed" -ForegroundColor Green
Write-Host "  [FAIL] Failed: $Failed" -ForegroundColor Red
Write-Host ""

if ($Failed -eq 0) {
    Write-Host "[SUCCESS] All protection files are in place!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Run: cd backend; python seed_billing_tiers.py --verify"
    Write-Host "  2. Run: cd backend; python test_tier_limits_enforcement.py"
    Write-Host "  3. Run: cd backend; python test_critical_functionality_integrity.py"
    Write-Host ""
    exit 0
} else {
    Write-Host "[ERROR] Protection setup incomplete" -ForegroundColor Red
    Write-Host ""
    Write-Host "Fix missing files before deploying to production" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}
