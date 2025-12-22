#!/bin/bash
# AP2 Expense Management - API Test Collection
# Comprehensive test collection for all major API endpoints
# Usage: ./api_test_collection.sh

set -e

# Configuration
BASE_URL="http://localhost:8000"
ADMIN_USER="adminfree"
ADMIN_PASS="Testme1!"
EMP_USER="adminfree"
EMP_PASS="Testme1!"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo "================================================================"
echo "   AP2 Expense Management - API Test Collection"
echo "================================================================"
echo ""
echo "Base URL: $BASE_URL"
echo ""

# Function to print section header
section() {
  echo ""
  echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo "${BLUE}$1${NC}"
  echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo ""
}

# Function to test endpoint
test_endpoint() {
  local method=$1
  local endpoint=$2
  local description=$3
  echo "  ${method} ${endpoint}"
  echo "      → ${description}"
}

#========================
# AUTHENTICATION TESTS
#========================
section "1. AUTHENTICATION & USER MANAGEMENT"

test_endpoint "POST" "/api/v1/auth/register" "Register new user"
cat << 'EOF'
curl -X POST $BASE_URL/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "newuser@example.com",
    "password": "SecurePass123!",
    "full_name": "New User"
  }'
EOF
echo ""

test_endpoint "POST" "/api/v1/auth/login" "Login and get JWT token"
cat << 'EOF'
curl -X POST $BASE_URL/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "adminfree",
    "password": "Testme1!"
  }'
# Save token: TOKEN=$(above_command | jq -r '.access_token')
EOF
echo ""

test_endpoint "GET" "/api/v1/auth/me" "Get current user info"
cat << 'EOF'
curl -X GET $BASE_URL/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"
EOF
echo ""

test_endpoint "POST" "/api/v1/auth/password/change" "Change password"
cat << 'EOF'
curl -X POST $BASE_URL/api/v1/auth/password/change \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "current_password": "OldPass123!",
    "new_password": "NewPass123!"
  }'
EOF
echo ""

test_endpoint "POST" "/api/v1/auth/logout" "Logout"
cat << 'EOF'
curl -X POST $BASE_URL/api/v1/auth/logout \
  -H "Authorization: Bearer $TOKEN"
EOF
echo ""

#========================
# EXPENSE MANAGEMENT
#========================
section "2. EXPENSE MANAGEMENT"

test_endpoint "POST" "/api/v1/expenses" "Submit new expense"
cat << 'EOF'
curl -X POST $BASE_URL/api/v1/expenses \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $EMP_TOKEN" \
  -d '{
    "user_id": "'$USER_ID'",
    "amount": 125.50,
    "vendor": "Starbucks Coffee",
    "category": "Meals",
    "description": "Team meeting breakfast",
    "date": "2025-11-12"
  }'
# Note: Categories: Travel, Meals, Software, "Office Supplies", Other
EOF
echo ""

test_endpoint "GET" "/api/v1/expenses/report" "Get user's expense report"
cat << 'EOF'
curl -X GET $BASE_URL/api/v1/expenses/report \
  -H "Authorization: Bearer $EMP_TOKEN"
EOF
echo ""

test_endpoint "PUT" "/api/v1/expenses/{id}" "Update expense (pending only)"
cat << 'EOF'
curl -X PUT $BASE_URL/api/v1/expenses/$EXPENSE_ID \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $EMP_TOKEN" \
  -d '{
    "amount": 150.00,
    "vendor": "Updated Vendor",
    "category": "Meals",
    "description": "Updated description"
  }'
EOF
echo ""

test_endpoint "DELETE" "/api/v1/expenses/{id}/withdraw" "Withdraw pending expense"
cat << 'EOF'
curl -X DELETE $BASE_URL/api/v1/expenses/$EXPENSE_ID/withdraw \
  -H "Authorization: Bearer $EMP_TOKEN"
EOF
echo ""

test_endpoint "POST" "/api/v1/expenses/{id}/comments" "Add comment to expense"
cat << 'EOF'
curl -X POST $BASE_URL/api/v1/expenses/$EXPENSE_ID/comments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "comment": "Please review this urgently"
  }'
EOF
echo ""

test_endpoint "GET" "/api/v1/expenses/{id}/comments" "Get expense comments"
cat << 'EOF'
curl -X GET $BASE_URL/api/v1/expenses/$EXPENSE_ID/comments \
  -H "Authorization: Bearer $TOKEN"
EOF
echo ""

#========================
# ADMIN - EXPENSE APPROVAL
#========================
section "3. ADMIN - EXPENSE APPROVAL"

test_endpoint "GET" "/api/v1/expenses/all-pending" "Get all pending expenses (Admin)"
cat << 'EOF'
curl -X GET $BASE_URL/api/v1/expenses/all-pending \
  -H "Authorization: Bearer $ADMIN_TOKEN"
EOF
echo ""

test_endpoint "POST" "/api/v1/expenses/approve" "Approve expense"
cat << 'EOF'
curl -X POST $BASE_URL/api/v1/expenses/approve \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "expense_id": "'$EXPENSE_ID'",
    "approver_id": "'$ADMIN_ID'"
  }'
EOF
echo ""

test_endpoint "POST" "/api/v1/expenses/reject" "Reject expense"
cat << 'EOF'
curl -X POST $BASE_URL/api/v1/expenses/reject \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "expense_id": "'$EXPENSE_ID'",
    "approver_id": "'$ADMIN_ID'",
    "rejection_reason": "Exceeds policy limits"
  }'
EOF
echo ""

test_endpoint "POST" "/api/v1/expenses/bulk-approve" "Bulk approve expenses"
cat << 'EOF'
curl -X POST $BASE_URL/api/v1/expenses/bulk-approve \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "expense_ids": ["id1", "id2", "id3"]
  }'
EOF
echo ""

test_endpoint "POST" "/api/v1/expenses/bulk-reject" "Bulk reject expenses"
cat << 'EOF'
curl -X POST $BASE_URL/api/v1/expenses/bulk-reject \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "expense_ids": ["id1", "id2"],
    "rejection_reason": "Policy violation"
  }'
EOF
echo ""

#========================
# RECEIPTS
#========================
section "4. RECEIPT MANAGEMENT"

test_endpoint "POST" "/api/v1/receipts/upload/{expense_id}" "Upload receipt"
cat << 'EOF'
curl -X POST $BASE_URL/api/v1/receipts/upload/$EXPENSE_ID \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@receipt.jpg"
EOF
echo ""

test_endpoint "GET" "/api/v1/receipts/{expense_id}" "Get receipts for expense"
cat << 'EOF'
curl -X GET $BASE_URL/api/v1/receipts/$EXPENSE_ID \
  -H "Authorization: Bearer $TOKEN"
EOF
echo ""

test_endpoint "GET" "/api/v1/receipts/download/{receipt_id}" "Download receipt"
cat << 'EOF'
curl -X GET $BASE_URL/api/v1/receipts/download/$RECEIPT_ID \
  -H "Authorization: Bearer $TOKEN" \
  --output receipt.jpg
EOF
echo ""

test_endpoint "DELETE" "/api/v1/receipts/{receipt_id}" "Delete receipt"
cat << 'EOF'
curl -X DELETE $BASE_URL/api/v1/receipts/$RECEIPT_ID \
  -H "Authorization: Bearer $TOKEN"
EOF
echo ""

#========================
# AP2 PROTOCOL
#========================
section "5. AP2 PROTOCOL & AUDIT TRAIL"

test_endpoint "GET" "/api/v1/audit/{transaction_id}" "Get audit trail"
cat << 'EOF'
curl -X GET $BASE_URL/api/v1/audit/$TRANSACTION_ID \
  -H "Authorization: Bearer $ADMIN_TOKEN"
EOF
echo ""

test_endpoint "GET" "/api/ap2/stats" "Get AP2 statistics"
cat << 'EOF'
curl -X GET $BASE_URL/api/ap2/stats \
  -H "Authorization: Bearer $ADMIN_TOKEN"
EOF
echo ""

test_endpoint "GET" "/api/ap2/user/mandates" "Get user's mandates"
cat << 'EOF'
curl -X GET $BASE_URL/api/ap2/user/mandates \
  -H "Authorization: Bearer $TOKEN"
EOF
echo ""

#========================
# ADMIN DASHBOARD
#========================
section "6. ADMIN DASHBOARD & STATISTICS"

test_endpoint "GET" "/api/v1/admin/dashboard/stats" "Get dashboard statistics"
cat << 'EOF'
curl -X GET $BASE_URL/api/v1/admin/dashboard/stats \
  -H "Authorization: Bearer $ADMIN_TOKEN"
EOF
echo ""

test_endpoint "GET" "/api/v1/admin/users" "List all users"
cat << 'EOF'
curl -X GET $BASE_URL/api/v1/admin/users \
  -H "Authorization: Bearer $ADMIN_TOKEN"
EOF
echo ""

test_endpoint "GET" "/api/v1/admin/expenses" "Get all expenses"
cat << 'EOF'
curl -X GET $BASE_URL/api/v1/admin/expenses \
  -H "Authorization: Bearer $ADMIN_TOKEN"
EOF
echo ""

test_endpoint "GET" "/api/v1/admin/system/health" "System health check"
cat << 'EOF'
curl -X GET $BASE_URL/api/v1/admin/system/health \
  -H "Authorization: Bearer $ADMIN_TOKEN"
EOF
echo ""

#========================
# USER MANAGEMENT
#========================
section "7. ADMIN - USER MANAGEMENT"

test_endpoint "POST" "/api/v1/admin/users/create" "Create new user (Admin)"
cat << 'EOF'
curl -X POST $BASE_URL/api/v1/admin/users/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "username": "manager1",
    "email": "manager1@example.com",
    "password": "Manager123!",
    "full_name": "Manager One",
    "role": "manager"
  }'
EOF
echo ""

test_endpoint "PATCH" "/api/v1/admin/users/{id}/role" "Change user role"
cat << 'EOF'
curl -X PATCH $BASE_URL/api/v1/admin/users/$USER_ID/role \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "role": "manager"
  }'
EOF
echo ""

test_endpoint "POST" "/api/v1/admin/users/{id}/suspend" "Suspend user"
cat << 'EOF'
curl -X POST $BASE_URL/api/v1/admin/users/$USER_ID/suspend \
  -H "Authorization: Bearer $ADMIN_TOKEN"
EOF
echo ""

test_endpoint "POST" "/api/v1/admin/users/{id}/unlock" "Unlock user account"
cat << 'EOF'
curl -X POST $BASE_URL/api/v1/admin/users/$USER_ID/unlock \
  -H "Authorization: Bearer $ADMIN_TOKEN"
EOF
echo ""

#========================
# BILLING & SUBSCRIPTIONS
#========================
section "8. BILLING & SUBSCRIPTIONS"

test_endpoint "GET" "/api/billing/org/tiers" "Get billing tiers"
cat << 'EOF'
curl -X GET $BASE_URL/api/billing/org/tiers \
  -H "Authorization: Bearer $TOKEN"
EOF
echo ""

test_endpoint "GET" "/api/billing/org/tiers/{name}" "Get specific tier"
cat << 'EOF'
curl -X GET $BASE_URL/api/billing/org/tiers/professional \
  -H "Authorization: Bearer $TOKEN"
EOF
echo ""

test_endpoint "GET" "/api/billing/org/subscription" "Get current subscription"
cat << 'EOF'
curl -X GET $BASE_URL/api/billing/org/subscription \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Organization-Id: $ORG_ID"
EOF
echo ""

test_endpoint "POST" "/api/billing/org/subscription" "Create subscription"
cat << 'EOF'
curl -X POST $BASE_URL/api/billing/org/subscription \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Organization-Id: $ORG_ID" \
  -d '{
    "tier_name": "professional"
  }'
EOF
echo ""

test_endpoint "GET" "/api/billing/org/usage/monthly" "Get usage statistics"
cat << 'EOF'
curl -X GET $BASE_URL/api/billing/org/usage/monthly \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Organization-Id: $ORG_ID"
EOF
echo ""

#========================
# ORGANIZATIONS
#========================
section "9. ORGANIZATION MANAGEMENT"

test_endpoint "POST" "/api/v1/organizations" "Create organization"
cat << 'EOF'
curl -X POST $BASE_URL/api/v1/organizations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Acme Corp",
    "description": "Main organization"
  }'
EOF
echo ""

test_endpoint "GET" "/api/v1/organizations" "List user's organizations"
cat << 'EOF'
curl -X GET $BASE_URL/api/v1/organizations \
  -H "Authorization: Bearer $TOKEN"
EOF
echo ""

test_endpoint "POST" "/api/v1/organizations/{id}/invitations" "Invite member"
cat << 'EOF'
curl -X POST $BASE_URL/api/v1/organizations/$ORG_ID/invitations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "email": "newmember@example.com",
    "role": "member"
  }'
EOF
echo ""

test_endpoint "GET" "/api/v1/organizations/{id}/members" "List organization members"
cat << 'EOF'
curl -X GET $BASE_URL/api/v1/organizations/$ORG_ID/members \
  -H "Authorization: Bearer $TOKEN"
EOF
echo ""

#========================
# SYSTEM
#========================
section "10. SYSTEM & HEALTH"

test_endpoint "GET" "/health" "Health check"
cat << 'EOF'
curl -X GET $BASE_URL/health
EOF
echo ""

test_endpoint "GET" "/docs" "API Documentation (Swagger UI)"
echo "  Open in browser: $BASE_URL/docs"
echo ""

test_endpoint "GET" "/openapi.json" "OpenAPI specification"
cat << 'EOF'
curl -X GET $BASE_URL/openapi.json
EOF
echo ""

#========================
# SUMMARY
#========================
section "TEST COLLECTION COMPLETE"

echo "${GREEN}✓ All API endpoints documented${NC}"
echo ""
echo "Quick Start:"
echo "1. Login to get token:"
echo "   TOKEN=\$(curl -s -X POST $BASE_URL/api/v1/auth/login -H 'Content-Type: application/json' -d '{\"username\":\"adminfree\",\"password\":\"Testme1!\"}' | jq -r '.access_token')"
echo ""
echo "2. Use token in requests:"
echo "   curl -H \"Authorization: Bearer \$TOKEN\" $BASE_URL/api/v1/expenses/report"
echo ""
echo "3. View full documentation:"
echo "   Open $BASE_URL/docs in your browser"
echo ""
echo "================================================================"
