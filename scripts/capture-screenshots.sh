#!/bin/bash

# ============================================================================
# Screenshot Capture Automation Helper
# ============================================================================
#
# Purpose: Automate screenshot capture for Intuit App Store submission
# Priority: HIGH
# Usage: ./scripts/capture-screenshots.sh [--auto]
#
# Prerequisites:
# - Backend server running: cd backend && uvicorn src.api:app --reload
# - Frontend server running: cd frontend && npm run dev
# - Demo data seeded: python backend/seed_screenshot_data.py
# - Browser: Chrome/Firefox with window set to 1280x800
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
FRONTEND_URL=${FRONTEND_URL:-http://localhost:5173}
BACKEND_URL=${BACKEND_URL:-http://localhost:8000}
OUTPUT_DIR="marketplace/screenshots"
STAGING_DIR="screenshots/staging"
AUTO_MODE=${1:-}

# Screenshot specifications
declare -A SCREENSHOTS=(
    ["1_dashboard"]="Dashboard Overview - Shows expense summary, recent expenses, pending approvals"
    ["2_expenses"]="Expense List - Complete expense tracking with filters and search"
    ["3_create"]="Create Expense - Easy expense submission with receipt upload"
    ["4_approval"]="Approval Workflow - Manager approval interface with multi-select"
    ["5_reports"]="Reports & Analytics - Budget tracking and spending insights"
    ["6_organizations"]="Organization Management - Multi-tenant organization setup"
    ["7_admin"]="Admin Panel - User management and permissions"
    ["8_mobile"]="Mobile Responsive - Works on all devices"
)

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

check_prerequisites() {
    print_header "Checking Prerequisites"

    # Check backend
    if curl -s -f "$BACKEND_URL/health" > /dev/null 2>&1; then
        print_success "Backend server is running at $BACKEND_URL"
    else
        print_error "Backend server is not running"
        echo "Start with: cd backend && uvicorn src.api:app --reload"
        return 1
    fi

    # Check frontend
    if curl -s -f "$FRONTEND_URL" > /dev/null 2>&1; then
        print_success "Frontend server is running at $FRONTEND_URL"
    else
        print_error "Frontend server is not running"
        echo "Start with: cd frontend && npm run dev"
        return 1
    fi

    # Check directories
    mkdir -p "$OUTPUT_DIR"
    mkdir -p "$STAGING_DIR"
    print_success "Output directories created"

    # Check demo data
    echo ""
    print_warning "Have you seeded demo data? Run: python backend/seed_screenshot_data.py"
    if [ "$AUTO_MODE" != "--auto" ]; then
        read -p "Press Enter to continue or Ctrl+C to abort..."
    fi

    echo ""
}

display_credentials() {
    print_header "Demo User Credentials"
    echo ""
    echo "All users have password: Demo123!"
    echo ""
    echo -e "${GREEN}👤 sarah.admin@acme.com${NC}    - Admin/Owner (use for screenshots 6, 7)"
    echo -e "${BLUE}👤 mike.manager@acme.com${NC}   - Manager (use for screenshot 4)"
    echo -e "${YELLOW}👤 john.employee@acme.com${NC}  - Employee (use for screenshots 1, 2, 3, 5)"
    echo ""
}

screenshot_instructions() {
    local num=$1
    local name=$2
    local description=$3

    print_header "Screenshot $num: $name"
    echo ""
    echo "Description: $description"
    echo "Output: $OUTPUT_DIR/${num}_${name}.png"
    echo ""

    case $num in
        1)
            echo "Steps:"
            echo "1. Login as john.employee@acme.com"
            echo "2. Navigate to dashboard: $FRONTEND_URL/dashboard"
            echo "3. Ensure you see:"
            echo "   - Total expenses chart"
            echo "   - Recent expenses list (should show 10 expenses)"
            echo "   - Pending approvals count (should be 0 for employee)"
            echo "   - Budget overview (3 budgets visible)"
            echo "4. Set browser window to exactly 1280x800"
            echo "5. Take screenshot"
            ;;
        2)
            echo "Steps:"
            echo "1. Stay logged in as john.employee@acme.com"
            echo "2. Navigate to expenses: $FRONTEND_URL/expenses"
            echo "3. Ensure you see:"
            echo "   - List of expenses with status badges"
            echo "   - Filter by category (Office Supplies, Travel, Meals, etc.)"
            echo "   - Search bar"
            echo "   - Status filters (All, Pending, Approved, Rejected)"
            echo "4. Apply a filter to show variety"
            echo "5. Take screenshot"
            ;;
        3)
            echo "Steps:"
            echo "1. Stay logged in as john.employee@acme.com"
            echo "2. Navigate to create expense: $FRONTEND_URL/expenses/new"
            echo "3. Fill in sample data:"
            echo "   - Vendor: Target"
            echo "   - Amount: 89.99"
            echo "   - Category: Office Supplies"
            echo "   - Description: Desk organizers and supplies"
            echo "   - Date: Today"
            echo "4. Show file upload area (don't upload)"
            echo "5. Take screenshot before submitting"
            ;;
        4)
            echo "Steps:"
            echo "1. Logout and login as mike.manager@acme.com"
            echo "2. Navigate to approvals: $FRONTEND_URL/approvals"
            echo "3. Ensure you see:"
            echo "   - List of pending expenses (should show 2 from demo data)"
            echo "   - Expense details (vendor, amount, category)"
            echo "   - Approve/Reject buttons"
            echo "   - Bulk actions checkbox"
            echo "4. Select one expense (checkbox checked)"
            echo "5. Take screenshot"
            ;;
        5)
            echo "Steps:"
            echo "1. Logout and login as john.employee@acme.com"
            echo "2. Navigate to reports: $FRONTEND_URL/reports"
            echo "3. Ensure you see:"
            echo "   - Budget vs Actual chart"
            echo "   - Spending by category (pie chart)"
            echo "   - Monthly trend line chart"
            echo "   - Budget cards (Travel, Software, Office Supplies)"
            echo "4. Select 'Last 30 days' filter"
            echo "5. Take screenshot"
            ;;
        6)
            echo "Steps:"
            echo "1. Logout and login as sarah.admin@acme.com"
            echo "2. Navigate to organizations: $FRONTEND_URL/organizations"
            echo "3. Ensure you see:"
            echo "   - Acme Corporation organization card"
            echo "   - Member count (3 members)"
            echo "   - Subscription tier (FREE or PROFESSIONAL)"
            echo "   - Settings button"
            echo "4. Click 'View Details' to show org settings"
            echo "5. Take screenshot showing org details page"
            ;;
        7)
            echo "Steps:"
            echo "1. Stay logged in as sarah.admin@acme.com"
            echo "2. Navigate to admin: $FRONTEND_URL/admin/users"
            echo "3. Ensure you see:"
            echo "   - User list (3 users: Sarah, Mike, John)"
            echo "   - Roles displayed (Admin, Manager, Employee)"
            echo "   - Active status indicators"
            echo "   - Invite user button"
            echo "4. Show user permissions or role management"
            echo "5. Take screenshot"
            ;;
        8)
            echo "Steps:"
            echo "1. Stay logged in (any user)"
            echo "2. Open browser DevTools (F12)"
            echo "3. Click 'Toggle device toolbar' (Ctrl+Shift+M)"
            echo "4. Select 'iPhone 12 Pro' or similar (390x844)"
            echo "5. Navigate to dashboard: $FRONTEND_URL/dashboard"
            echo "6. Ensure mobile menu (hamburger) is visible"
            echo "7. Take screenshot showing mobile layout"
            echo ""
            print_warning "For this screenshot, use 390x844 resolution (mobile)"
            ;;
    esac

    echo ""
    if [ "$AUTO_MODE" != "--auto" ]; then
        read -p "Press Enter when screenshot is taken..."
    fi
    echo ""
}

verify_screenshot() {
    local num=$1
    local name=$2
    local filename="${OUTPUT_DIR}/${num}_${name}.png"

    if [ -f "$filename" ]; then
        local size=$(stat -c%s "$filename" 2>/dev/null || stat -f%z "$filename" 2>/dev/null || echo "0")
        if [ "$size" -gt 10000 ]; then
            print_success "Screenshot saved: $filename ($(numfmt --to=iec-i --suffix=B $size 2>/dev/null || echo "${size}B"))"
            return 0
        else
            print_warning "Screenshot file is too small: $filename"
            return 1
        fi
    else
        print_warning "Screenshot not found: $filename"
        echo "Please save your screenshot to: $filename"
        if [ "$AUTO_MODE" != "--auto" ]; then
            read -p "Press Enter when file is saved..."
            verify_screenshot "$num" "$name"
        fi
        return 1
    fi
}

# ============================================================================
# Main Execution
# ============================================================================

print_header "Intuit App Store Screenshot Capture Helper"
echo ""
echo "This script will guide you through capturing all 8 required screenshots."
echo "Each screenshot has specific requirements (1280x800 resolution, PNG format)."
echo ""

# Check prerequisites
check_prerequisites

# Display credentials
display_credentials

# Capture each screenshot
for key in {1..8}; do
    case $key in
        1) name="dashboard" ;;
        2) name="expenses" ;;
        3) name="create" ;;
        4) name="approval" ;;
        5) name="reports" ;;
        6) name="organizations" ;;
        7) name="admin" ;;
        8) name="mobile" ;;
    esac

    description="${SCREENSHOTS[${key}_${name}]}"
    screenshot_instructions "$key" "$name" "$description"

    if [ "$AUTO_MODE" != "--auto" ]; then
        verify_screenshot "$key" "$name"
    fi
done

# ============================================================================
# Final Summary
# ============================================================================

print_header "Screenshot Capture Complete!"
echo ""
echo "Next Steps:"
echo ""
echo "1. Review all screenshots in: $OUTPUT_DIR"
echo "2. Verify image quality (clear text, good contrast)"
echo "3. Check resolution: Should be 1280x800 (or 390x844 for mobile)"
echo "4. Optimize file sizes: Use tools like TinyPNG or ImageOptim"
echo "5. Upload to Intuit Developer Portal"
echo ""
echo "Screenshot checklist:"

count=0
for key in {1..8}; do
    case $key in
        1) name="dashboard" ;;
        2) name="expenses" ;;
        3) name="create" ;;
        4) name="approval" ;;
        5) name="reports" ;;
        6) name="organizations" ;;
        7) name="admin" ;;
        8) name="mobile" ;;
    esac

    filename="${OUTPUT_DIR}/${key}_${name}.png"
    if [ -f "$filename" ]; then
        print_success "$key. $name.png"
        count=$((count + 1))
    else
        print_error "$key. $name.png (missing)"
    fi
done

echo ""
if [ $count -eq 8 ]; then
    print_success "All screenshots captured! ($count/8)"
else
    print_warning "Some screenshots are missing ($count/8)"
fi

echo ""
echo "For detailed screenshot requirements, see:"
echo "  - MARKETPLACE_ASSET_CREATION_GUIDE.md"
echo "  - marketplace/ASSETS_CHECKLIST.md"
echo ""

exit 0
