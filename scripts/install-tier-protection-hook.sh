#!/bin/bash
# Install tier limits protection pre-commit hook

set -e

HOOK_DIR=".git/hooks"
HOOK_FILE="$HOOK_DIR/pre-commit"

echo "========================================"
echo "Installing Tier Limits Protection Hook"
echo "========================================"
echo ""

# Create hooks directory if it doesn't exist
if [ ! -d "$HOOK_DIR" ]; then
    echo "Creating .git/hooks directory..."
    mkdir -p "$HOOK_DIR"
fi

# Check if pre-commit hook already exists
if [ -f "$HOOK_FILE" ]; then
    echo "⚠️  Pre-commit hook already exists"
    echo ""
    echo "Options:"
    echo "  1. Backup and replace"
    echo "  2. Append tier protection to existing hook"
    echo "  3. Cancel"
    echo ""
    read -p "Select option (1-3): " option

    case $option in
        1)
            echo "Backing up existing hook to pre-commit.backup..."
            cp "$HOOK_FILE" "$HOOK_FILE.backup"
            ;;
        2)
            echo "Appending tier protection to existing hook..."
            cat >> "$HOOK_FILE" << 'HOOK_EOF'

# ===========================================
# TIER LIMITS PROTECTION
# Added by install-tier-protection-hook.sh
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
        echo "⚠️  Detected changes to $file"
    fi
done

if [ "$TIER_FILES_CHANGED" = true ]; then
    echo ""
    echo "⚠️  TIER LIMIT PROTECTION ACTIVATED ⚠️"
    echo ""
    echo "Tier limit files have been modified."
    echo "Running validation tests..."
    echo ""

    # Run tier limit verification
    cd backend
    python seed_billing_tiers.py --verify

    if [ $? -ne 0 ]; then
        echo ""
        echo "❌ TIER LIMIT VERIFICATION FAILED"
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
        echo "❌ TIER LIMIT TESTS FAILED"
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
    echo "✓ Tier Limits Verification Passed"
    echo "=========================================="
    echo ""
    echo "⚠️  IMPORTANT: Tier limit changes require approval from:"
    echo "  ☐ Product Manager"
    echo "  ☐ Finance Team"
    echo "  ☐ Legal Team"
    echo "  ☐ Engineering Lead"
    echo ""
    read -p "Have you obtained all required approvals? (y/n) " -n 1 -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "❌ Commit aborted - approvals required"
        echo ""
        echo "To bypass (EMERGENCY ONLY): git commit --no-verify"
        echo ""
        exit 1
    fi

    echo ""
    echo "✓ Proceeding with commit"
    echo ""
fi

# End of tier limits protection
HOOK_EOF
            chmod +x "$HOOK_FILE"
            echo "✓ Tier protection appended to existing hook"
            exit 0
            ;;
        3)
            echo "Installation cancelled"
            exit 0
            ;;
        *)
            echo "Invalid option"
            exit 1
            ;;
    esac
fi

# Create new pre-commit hook
cat > "$HOOK_FILE" << 'HOOK_EOF'
#!/bin/bash
# Pre-commit hook with tier limits protection

set -e

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
        echo "⚠️  Detected changes to $file"
    fi
done

if [ "$TIER_FILES_CHANGED" = true ]; then
    echo ""
    echo "⚠️  TIER LIMIT PROTECTION ACTIVATED ⚠️"
    echo ""
    echo "Tier limit files have been modified."
    echo "Running validation tests..."
    echo ""

    # Run tier limit verification
    cd backend
    python seed_billing_tiers.py --verify

    if [ $? -ne 0 ]; then
        echo ""
        echo "❌ TIER LIMIT VERIFICATION FAILED"
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
        echo "❌ TIER LIMIT TESTS FAILED"
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
    echo "✓ Tier Limits Verification Passed"
    echo "=========================================="
    echo ""
    echo "⚠️  IMPORTANT: Tier limit changes require approval from:"
    echo "  ☐ Product Manager"
    echo "  ☐ Finance Team"
    echo "  ☐ Legal Team"
    echo "  ☐ Engineering Lead"
    echo ""
    read -p "Have you obtained all required approvals? (y/n) " -n 1 -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "❌ Commit aborted - approvals required"
        echo ""
        echo "To bypass (EMERGENCY ONLY): git commit --no-verify"
        echo ""
        exit 1
    fi

    echo ""
    echo "✓ Proceeding with commit"
    echo ""
fi

echo "✓ Pre-commit checks passed"
exit 0
HOOK_EOF

# Make hook executable
chmod +x "$HOOK_FILE"

echo "✓ Pre-commit hook installed successfully"
echo ""
echo "Location: $HOOK_FILE"
echo ""
echo "The hook will:"
echo "  - Detect changes to tier limit files"
echo "  - Run automated validation tests"
echo "  - Require approval confirmation"
echo "  - Block commits if verification fails"
echo ""
echo "To bypass in emergencies: git commit --no-verify"
echo ""
echo "=========================================="
echo "Installation Complete"
echo "=========================================="
