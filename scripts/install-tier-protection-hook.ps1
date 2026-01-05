# Install Tier Limits Protection Pre-Commit Hook (PowerShell Version)
# For Windows users

$ErrorActionPreference = "Stop"

$HOOK_DIR = ".git\hooks"
$HOOK_FILE = "$HOOK_DIR\pre-commit"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installing Tier Limits Protection Hook" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path ".git")) {
    Write-Host "[ERROR] Not in a git repository root" -ForegroundColor Red
    Write-Host "Please run this script from the project root directory" -ForegroundColor Yellow
    exit 1
}

# Create hooks directory if it doesn't exist
if (-not (Test-Path $HOOK_DIR)) {
    Write-Host "Creating .git\hooks directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $HOOK_DIR -Force | Out-Null
}

# Check if pre-commit hook already exists
if (Test-Path $HOOK_FILE) {
    Write-Host "[WARNING] Pre-commit hook already exists" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Cyan
    Write-Host "  1. Backup and replace"
    Write-Host "  2. Append tier protection to existing hook"
    Write-Host "  3. Cancel"
    Write-Host ""

    $option = Read-Host "Select option (1-3)"

    switch ($option) {
        "1" {
            Write-Host "Backing up existing hook to pre-commit.backup..." -ForegroundColor Yellow
            Copy-Item $HOOK_FILE "$HOOK_FILE.backup" -Force
        }
        "2" {
            Write-Host "Appending tier protection to existing hook..." -ForegroundColor Yellow

            $appendContent = @'

# ===========================================
# TIER LIMITS PROTECTION
# Added by install-tier-protection-hook.ps1
# ===========================================

Write-Host ""
Write-Host "Checking tier limits protection..." -ForegroundColor Cyan

# Check if tier-related files have been modified
$TIER_FILES_CHANGED = $false

$tierFiles = @(
    "backend/seed_billing_tiers.py",
    "frontend/src/config/constants.js",
    "backend/src/billing/tier_limit_guardian.py"
)

foreach ($file in $tierFiles) {
    $staged = git diff --cached --name-only | Select-String -Pattern "^$file$"
    if ($staged) {
        $TIER_FILES_CHANGED = $true
        Write-Host "[WARNING] Detected changes to $file" -ForegroundColor Yellow
    }
}

if ($TIER_FILES_CHANGED) {
    Write-Host ""
    Write-Host "[WARNING] TIER LIMIT PROTECTION ACTIVATED" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Tier limit files have been modified."
    Write-Host "Running validation tests..."
    Write-Host ""

    # Run tier limit verification
    Push-Location backend

    python seed_billing_tiers.py --verify
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "[FAIL] TIER LIMIT VERIFICATION FAILED" -ForegroundColor Red
        Write-Host ""
        Write-Host "Tier limits in database do not match official specification."
        Write-Host ""
        Write-Host "REQUIRED ACTIONS:"
        Write-Host "  1. Verify you have approval from Product, Finance, and Legal"
        Write-Host "  2. Ensure both backend and frontend limits are synchronized"
        Write-Host "  3. Update TIER_LIMITS_PROTECTION.md documentation"
        Write-Host "  4. Run: python backend/seed_billing_tiers.py --force"
        Write-Host ""
        Write-Host "To bypass this check (EMERGENCY ONLY):"
        Write-Host "  git commit --no-verify"
        Write-Host ""
        Pop-Location
        exit 1
    }

    # Run enforcement tests
    python test_tier_limits_enforcement.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "[FAIL] TIER LIMIT TESTS FAILED" -ForegroundColor Red
        Write-Host ""
        Write-Host "Some tier limit tests failed."
        Write-Host "Review test output above and fix issues."
        Write-Host ""
        Write-Host "To bypass (EMERGENCY ONLY): git commit --no-verify"
        Write-Host ""
        Pop-Location
        exit 1
    }

    Pop-Location

    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "[PASS] Tier Limits Verification Passed" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "[IMPORTANT] Tier limit changes require approval from:" -ForegroundColor Yellow
    Write-Host "  [ ] Product Manager"
    Write-Host "  [ ] Finance Team"
    Write-Host "  [ ] Legal Team"
    Write-Host "  [ ] Engineering Lead"
    Write-Host ""

    $approval = Read-Host "Have you obtained all required approvals? (y/n)"

    if ($approval -ne "y" -and $approval -ne "Y") {
        Write-Host ""
        Write-Host "[FAIL] Commit aborted - approvals required" -ForegroundColor Red
        Write-Host ""
        Write-Host "To bypass (EMERGENCY ONLY): git commit --no-verify"
        Write-Host ""
        exit 1
    }

    Write-Host ""
    Write-Host "[PASS] Proceeding with commit" -ForegroundColor Green
    Write-Host ""
}

# End of tier limits protection
'@
            Add-Content -Path $HOOK_FILE -Value $appendContent
            Write-Host "[PASS] Tier protection appended to existing hook" -ForegroundColor Green
            exit 0
        }
        "3" {
            Write-Host "Installation cancelled" -ForegroundColor Yellow
            exit 0
        }
        default {
            Write-Host "Invalid option" -ForegroundColor Red
            exit 1
        }
    }
}

# Create new pre-commit hook
$hookContent = @'
#!/bin/sh
# Pre-commit hook with tier limits protection
# This script runs in Git Bash on Windows, so we use bash syntax

echo "Running pre-commit checks..."

# ===========================================
# TIER LIMITS PROTECTION
# ===========================================

echo ""
echo "Checking tier limits protection..."

# Check if tier-related files have been modified
TIER_FILES_CHANGED=false

for file in backend/seed_billing_tiers.py \
            frontend/src/config/constants.js \
            backend/src/billing/tier_limit_guardian.py; do
    if git diff --cached --name-only | grep -q "^$file$"; then
        TIER_FILES_CHANGED=true
        echo "[WARNING] Detected changes to $file"
    fi
done

if [ "$TIER_FILES_CHANGED" = true ]; then
    echo ""
    echo "[WARNING] TIER LIMIT PROTECTION ACTIVATED"
    echo ""
    echo "Tier limit files have been modified."
    echo "Running validation tests..."
    echo ""

    # Run tier limit verification
    cd backend

    python seed_billing_tiers.py --verify
    if [ $? -ne 0 ]; then
        echo ""
        echo "[FAIL] TIER LIMIT VERIFICATION FAILED"
        echo ""
        echo "Tier limits in database do not match official specification."
        echo ""
        echo "REQUIRED ACTIONS:"
        echo "  1. Verify you have approval from Product, Finance, and Legal"
        echo "  2. Ensure both backend and frontend limits are synchronized"
        echo "  3. Update TIER_LIMITS_PROTECTION.md documentation"
        echo "  4. Run: python backend/seed_billing_tiers.py --force"
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
        echo "[FAIL] TIER LIMIT TESTS FAILED"
        echo ""
        echo "Some tier limit tests failed."
        echo "Review test output above and fix issues."
        echo ""
        echo "To bypass (EMERGENCY ONLY): git commit --no-verify"
        echo ""
        exit 1
    fi

    cd ..

    echo ""
    echo "=========================================="
    echo "[PASS] Tier Limits Verification Passed"
    echo "=========================================="
    echo ""
    echo "[IMPORTANT] Tier limit changes require approval from:"
    echo "  [ ] Product Manager"
    echo "  [ ] Finance Team"
    echo "  [ ] Legal Team"
    echo "  [ ] Engineering Lead"
    echo ""
    read -p "Have you obtained all required approvals? (y/n) " -n 1 -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "[FAIL] Commit aborted - approvals required"
        echo ""
        echo "To bypass (EMERGENCY ONLY): git commit --no-verify"
        echo ""
        exit 1
    fi

    echo ""
    echo "[PASS] Proceeding with commit"
    echo ""
fi

echo "[PASS] Pre-commit checks passed"
exit 0
'@

Set-Content -Path $HOOK_FILE -Value $hookContent -NoNewline

Write-Host "[PASS] Pre-commit hook installed successfully" -ForegroundColor Green
Write-Host ""
Write-Host "Location: $HOOK_FILE" -ForegroundColor Cyan
Write-Host ""
Write-Host "The hook will:" -ForegroundColor Cyan
Write-Host "  - Detect changes to tier limit files"
Write-Host "  - Run automated validation tests"
Write-Host "  - Require approval confirmation"
Write-Host "  - Block commits if verification fails"
Write-Host ""
Write-Host "To bypass in emergencies: git commit --no-verify" -ForegroundColor Yellow
Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "Installation Complete" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Testing the hook..." -ForegroundColor Cyan
Write-Host ""

# Test if Git Bash is available (hooks run in Git Bash on Windows)
$gitBash = where.exe sh 2>$null
if ($gitBash) {
    Write-Host "[PASS] Git Bash found: $gitBash" -ForegroundColor Green
    Write-Host "[PASS] Pre-commit hook will work correctly" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Git Bash (sh) not found in PATH" -ForegroundColor Yellow
    Write-Host "The hook requires Git Bash to run." -ForegroundColor Yellow
    Write-Host "Make sure Git for Windows is properly installed." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "You can now commit files. The hook will automatically:" -ForegroundColor Cyan
Write-Host "  1. Check if tier limit files are modified"
Write-Host "  2. Run validation tests"
Write-Host "  3. Ask for approval confirmation"
Write-Host ""
