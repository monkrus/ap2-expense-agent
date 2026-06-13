# AP2 Automation - Manual Test Guide

## Overview
This manual test guide covers the AP2 (Agent Payments Protocol) automation features, including Intent Mandates, auto-approval workflows, constraint matching, and the complete AP2 payment flow.

**Target Auto-Approval Rate**: 60-70% of routine expenses

---

## Prerequisites

### System Requirements
- Backend running: http://localhost:8000
- Frontend running: http://localhost:5173
- Database initialized with test users
- Google Cloud KMS configured (for cryptographic signing)

### Test Credentials

#### Test User 1 (Employee)
- **Username**: `user1`
- **Email**: user1@example.com
- **Password**: `Passowrd123!`
- **Role**: USER/EMPLOYEE
- **Tier**: Professional (500 AP2 transactions/month)

#### Test User 2 (Admin)
- **Username**: `adminfree`
- **Email**: admin@example.com
- **Password**: `Passowrd123!`
- **Role**: ADMIN
- **Tier**: Free (20 AP2 transactions/month)

---

## Test Sections

- [Section 1: Intent Mandate Creation](#section-1-intent-mandate-creation)
- [Section 2: Intent Mandate Management](#section-2-intent-mandate-management)
- [Section 3: Auto-Approval Workflow](#section-3-auto-approval-workflow)
- [Section 4: Three-Tier Approval Hierarchy](#section-4-three-tier-approval-hierarchy)
- [Section 5: Constraint Matching](#section-5-constraint-matching)
- [Section 6: Monthly Limit Tracking](#section-6-monthly-limit-tracking)
- [Section 7: Complete AP2 Flow](#section-7-complete-ap2-flow)
- [Section 8: UI/UX Testing](#section-8-uiux-testing)
- [Section 9: Security Features](#section-9-security-features)
- [Section 10: Billing & Usage Tracking](#section-10-billing--usage-tracking)
- [Section 11: GDPR Compliance](#section-11-gdpr-compliance)
- [Section 12: Error Handling](#section-12-error-handling)
- [Section 13: Edge Cases](#section-13-edge-cases)

---

## Section 1: Intent Mandate Creation

### Test 1.1: Create Basic Intent Mandate via API

**Objective**: Verify Intent Mandate creation with basic constraints

**Steps**:
1. Login as `user1`
2. Get access token from login response
3. Make API call:
```bash
curl -X POST "http://localhost:8000/api/ap2/intent-mandate" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "constraints": {
      "max_amount": 200.00,
      "monthly_limit": 1000.00,
      "category": "OFFICE_SUPPLIES",
      "merchant": "Amazon"
    },
    "expiration": "2026-02-22T23:59:59"
  }'
```

**Expected Results**:
- [ ] Status code: 201 Created
- [ ] Response includes `intent_mandate_id`
- [ ] Response includes `signature` (base64-encoded)
- [ ] Response shows `status: "active"`
- [ ] Expiration date matches request
- [ ] All constraints are saved correctly

**Verification**:
```bash
# Verify mandate was created
curl -X GET "http://localhost:8000/api/ap2/user/mandates" \
  -H "Authorization: Bearer {token}"
```

---

### Test 1.2: Create Intent Mandate with Multiple Merchants

**Objective**: Verify Intent Mandate supports multiple merchants

**Steps**:
1. Login as `user1`
2. Create Intent Mandate:
```json
{
  "constraints": {
    "max_amount": 500.00,
    "monthly_limit": 2000.00,
    "category": "SOFTWARE",
    "merchants": ["Microsoft", "Adobe", "Atlassian"]
  },
  "expiration": "2026-02-22T23:59:59"
}
```

**Expected Results**:
- [ ] Status code: 201 Created
- [ ] Merchants array contains all 3 vendors
- [ ] Can be used for expenses from any listed merchant
- [ ] Single category constraint is enforced

---

### Test 1.3: Create Intent Mandate with Multiple Categories

**Objective**: Verify Intent Mandate supports multiple categories

**Steps**:
1. Login as `user1`
2. Create Intent Mandate:
```json
{
  "constraints": {
    "max_amount": 300.00,
    "monthly_limit": 1500.00,
    "categories": ["OFFICE_SUPPLIES", "TRAVEL", "MEALS"],
    "merchant": "Costco"
  },
  "expiration": "2026-02-22T23:59:59"
}
```

**Expected Results**:
- [ ] Status code: 201 Created
- [ ] Categories array contains all 3 categories
- [ ] Can be used for expenses in any listed category
- [ ] Single merchant constraint is enforced

---

### Test 1.4: Create Intent Mandate with No Expiration (Default)

**Objective**: Verify default expiration is set (24 hours)

**Steps**:
1. Login as `user1`
2. Create Intent Mandate without expiration field:
```json
{
  "constraints": {
    "max_amount": 100.00,
    "category": "OFFICE_SUPPLIES"
  }
}
```

**Expected Results**:
- [ ] Status code: 201 Created
- [ ] Expiration is set to current_time + 24 hours
- [ ] Mandate is marked as `active`

---

### Test 1.5: Attempt to Create Intent Mandate with Invalid Constraints

**Objective**: Verify input validation

**Test Cases**:

**1.5a: Negative max_amount**
```json
{"constraints": {"max_amount": -50.00}}
```
- [ ] Expected: 400 Bad Request
- [ ] Error message: "max_amount must be positive"

**1.5b: Monthly limit less than max_amount**
```json
{"constraints": {"max_amount": 500.00, "monthly_limit": 100.00}}
```
- [ ] Expected: 400 Bad Request
- [ ] Error message: "monthly_limit must be >= max_amount"

**1.5c: Invalid category**
```json
{"constraints": {"category": "INVALID_CATEGORY"}}
```
- [ ] Expected: 400 Bad Request
- [ ] Error message: "Invalid category"

**1.5d: Expiration in the past**
```json
{"expiration": "2020-01-01T00:00:00"}
```
- [ ] Expected: 400 Bad Request
- [ ] Error message: "Expiration must be in the future"

---

### Test 1.6: Create Intent Mandate - Billing Limit Check

**Objective**: Verify AP2 transaction limit enforcement

**Steps**:
1. Login as `adminfree` (Free tier: 20 AP2 transactions/month)
2. Create 20 Intent Mandates successfully
3. Attempt to create 21st Intent Mandate

**Expected Results**:
- [ ] First 20 mandates: 201 Created
- [ ] 21st mandate: 402 Payment Required
- [ ] Error message: "AP2 transaction limit exceeded for your tier"
- [ ] Suggestion to upgrade tier in response

---

## Section 2: Intent Mandate Management

### Test 2.1: List All User Mandates

**Objective**: Verify mandate listing endpoint

**Steps**:
1. Login as `user1`
2. Create 5 Intent Mandates with different statuses:
   - 2 active mandates (future expiration)
   - 1 expired mandate (past expiration)
   - 1 used mandate (used in expense approval)
   - 1 revoked mandate
3. Call GET `/api/ap2/user/mandates`

**Expected Results**:
- [ ] Returns all 5 mandates
- [ ] Each mandate shows correct status
- [ ] Mandates are sorted by creation date (newest first)
- [ ] Response includes mandate IDs, constraints, status, expiration

---

### Test 2.2: Filter Mandates by Status

**Objective**: Verify status filtering (if supported in UI)

**Steps**:
1. Login as `user1`
2. Navigate to AI Assistant page
3. Go to "Mandates" tab
4. Apply status filters:
   - Filter: "Active" only
   - Filter: "Expired" only
   - Filter: "All"

**Expected Results**:
- [ ] "Active" filter shows only active mandates
- [ ] "Expired" filter shows only expired mandates
- [ ] "All" filter shows all mandates
- [ ] Count badges match filtered results

---

### Test 2.3: View Mandate Details

**Objective**: Verify detailed mandate view

**Steps**:
1. Login as `user1`
2. Navigate to AI Assistant > Mandates tab
3. Click on a specific mandate to expand details

**Expected Results**:
- [ ] Displays all constraints with icons
- [ ] Shows max amount per expense
- [ ] Shows monthly limit
- [ ] Shows allowed categories
- [ ] Shows allowed merchants
- [ ] Shows expiration date/time
- [ ] Shows current status
- [ ] Shows creation timestamp
- [ ] Shows mandate ID

---

### Test 2.4: Delete/Revoke Intent Mandate

**Objective**: Verify mandate revocation

**Steps**:
1. Login as `user1`
2. Create a new Intent Mandate
3. Navigate to AI Assistant > Mandates tab
4. Find the mandate and click "Delete" or "Revoke"
5. Confirm deletion in confirmation dialog

**Expected Results**:
- [ ] Confirmation dialog appears
- [ ] After confirmation, mandate status changes to "revoked"
- [ ] Mandate still appears in list but marked as revoked
- [ ] Cannot be used for future auto-approvals
- [ ] Success message displayed

**Verification**:
```bash
curl -X GET "http://localhost:8000/api/ap2/user/mandates" \
  -H "Authorization: Bearer {token}"
```
- [ ] Mandate status shows "revoked"

---

### Test 2.5: Attempt to Delete Another User's Mandate

**Objective**: Verify access control on mandate revocation

**Steps**:
1. Login as `user1` and create an Intent Mandate
2. Note the mandate ID
3. Logout and login as `adminfree`
4. Attempt to revoke user1's mandate:
```bash
curl -X POST "http://localhost:8000/api/ap2/intent-mandate/{user1_mandate_id}/revoke" \
  -H "Authorization: Bearer {adminfree_token}"
```

**Expected Results**:
- [ ] Status code: 403 Forbidden
- [ ] Error message: "You can only revoke your own mandates"
- [ ] Mandate remains active in user1's account

---

### Test 2.6: Check Mandate Status

**Objective**: Verify status endpoint

**Steps**:
1. Login as `user1`
2. Create an Intent Mandate
3. Call status endpoint:
```bash
curl -X GET "http://localhost:8000/api/ap2/intent-mandate/{id}/status" \
  -H "Authorization: Bearer {token}"
```

**Expected Results**:
- [ ] Returns current status: "active", "expired", "used", or "revoked"
- [ ] Includes expiration info
- [ ] Includes usage count (if tracked)

---

## Section 3: Auto-Approval Workflow

### Test 3.1: Basic Auto-Approval via Intent Mandate

**Objective**: Verify end-to-end auto-approval

**Steps**:
1. Login as `user1`
2. Create Intent Mandate:
```json
{
  "constraints": {
    "max_amount": 200.00,
    "monthly_limit": 1000.00,
    "category": "OFFICE_SUPPLIES",
    "merchant": "Amazon"
  }
}
```
3. Submit expense that matches mandate:
```json
{
  "amount": 45.99,
  "vendor": "Amazon",
  "category": "OFFICE_SUPPLIES",
  "description": "Keyboard and mouse"
}
```

**Expected Results**:
- [ ] Expense status: APPROVED (not PENDING)
- [ ] auto_approved: true
- [ ] auto_approved_via: "intent_mandate"
- [ ] intent_mandate_id is populated
- [ ] Response message: "✨ Auto-approved by AI agent via Intent Mandate (AP2)"
- [ ] Cart Mandate created
- [ ] Payment Mandate created
- [ ] AP2 transaction counted toward billing

**Verification**:
```bash
# Check expense details
curl -X GET "http://localhost:8000/api/v1/expenses/{expense_id}" \
  -H "Authorization: Bearer {token}"
```
- [ ] Verify all AP2 fields are populated

---

### Test 3.2: Auto-Approval with Exact Max Amount

**Objective**: Verify boundary condition (amount == max_amount)

**Steps**:
1. Create Intent Mandate with max_amount: 100.00
2. Submit expense with amount: 100.00 (exact match)

**Expected Results**:
- [ ] Expense is auto-approved
- [ ] No "exceeds limit" error

---

### Test 3.3: Auto-Approval Rejection - Amount Exceeds Limit

**Objective**: Verify amount constraint enforcement

**Steps**:
1. Create Intent Mandate with max_amount: 100.00
2. Submit expense with amount: 100.01 (exceeds by $0.01)

**Expected Results**:
- [ ] Expense status: PENDING (not auto-approved)
- [ ] auto_approved: false
- [ ] Falls back to Tier 2 or Tier 3 approval
- [ ] No Intent Mandate linked

---

### Test 3.4: Auto-Approval Rejection - Wrong Category

**Objective**: Verify category constraint enforcement

**Steps**:
1. Create Intent Mandate for category: "OFFICE_SUPPLIES"
2. Submit expense with category: "TRAVEL"

**Expected Results**:
- [ ] Expense status: PENDING
- [ ] auto_approved: false
- [ ] Mandate not matched

---

### Test 3.5: Auto-Approval Rejection - Wrong Merchant

**Objective**: Verify merchant constraint enforcement

**Steps**:
1. Create Intent Mandate for merchant: "Amazon"
2. Submit expense with vendor: "Microsoft"

**Expected Results**:
- [ ] Expense status: PENDING
- [ ] auto_approved: false
- [ ] Mandate not matched

---

### Test 3.6: Auto-Approval with Case-Insensitive Matching

**Objective**: Verify case-insensitive category and merchant matching

**Steps**:
1. Create Intent Mandate:
   - merchant: "amazon" (lowercase)
   - category: "office_supplies" (lowercase)
2. Submit expense:
   - vendor: "AMAZON" (uppercase)
   - category: "OFFICE_SUPPLIES" (uppercase)

**Expected Results**:
- [ ] Expense is auto-approved
- [ ] Case differences don't prevent matching

---

## Section 4: Three-Tier Approval Hierarchy

### Test 4.1: Tier 1 - Intent Mandate Auto-Approval

**Objective**: Verify Intent Mandate is checked first

**Setup**:
1. Create Intent Mandate for user1:
   - merchant: "Amazon"
   - category: "OFFICE_SUPPLIES"
   - max_amount: 200
2. Create Approval Policy for org:
   - All OFFICE_SUPPLIES expenses auto-approved

**Steps**:
1. Submit expense matching both Intent Mandate and Approval Policy
2. Check which approval method was used

**Expected Results**:
- [ ] auto_approved: true
- [ ] auto_approved_via: "intent_mandate" (NOT "approval_policy")
- [ ] Intent Mandate takes precedence
- [ ] AP2 transaction counted

---

### Test 4.2: Tier 2 - Approval Policy Fallback

**Objective**: Verify Approval Policy is checked when Intent Mandate doesn't match

**Setup**:
1. Create Intent Mandate for user1:
   - merchant: "Amazon"
   - max_amount: 100
2. Create Approval Policy:
   - All SOFTWARE expenses under $500 auto-approved

**Steps**:
1. Submit SOFTWARE expense from Microsoft for $200
   - Doesn't match Intent Mandate (wrong merchant/category)
   - Matches Approval Policy

**Expected Results**:
- [ ] auto_approved: true
- [ ] auto_approved_via: "approval_policy"
- [ ] approval_policy_id is populated
- [ ] NO AP2 transaction counted
- [ ] No Cart/Payment Mandates created

---

### Test 4.3: Tier 3 - Manual Approval Default

**Objective**: Verify manual approval when neither Tier 1 nor Tier 2 match

**Setup**:
1. No matching Intent Mandates
2. No matching Approval Policies

**Steps**:
1. Submit expense that matches no automation rules

**Expected Results**:
- [ ] Expense status: PENDING
- [ ] auto_approved: false
- [ ] auto_approved_via: null
- [ ] Requires manual manager approval

---

### Test 4.4: Multiple Intent Mandates - First Match Wins

**Objective**: Verify behavior when multiple Intent Mandates match

**Setup**:
1. Create Intent Mandate A:
   - merchant: "Amazon"
   - max_amount: 100
   - monthly_limit: 500
2. Create Intent Mandate B:
   - category: "OFFICE_SUPPLIES"
   - max_amount: 200
   - monthly_limit: 1000

**Steps**:
1. Submit expense:
   - vendor: "Amazon"
   - category: "OFFICE_SUPPLIES"
   - amount: 75
   - (Matches both mandates)

**Expected Results**:
- [ ] Expense is auto-approved
- [ ] Uses the first matching mandate (implementation-defined order)
- [ ] Only one mandate's monthly_limit is affected

---

## Section 5: Constraint Matching

### Test 5.1: Single Category Constraint

**Objective**: Verify single category matching

**Steps**:
1. Create Intent Mandate with constraint:
```json
{"category": "OFFICE_SUPPLIES"}
```
2. Test expenses:
   - OFFICE_SUPPLIES → should match
   - TRAVEL → should not match

**Expected Results**:
- [ ] Only OFFICE_SUPPLIES expenses auto-approved
- [ ] Other categories go to manual approval

---

### Test 5.2: Multiple Categories Constraint (Whitelist)

**Objective**: Verify category whitelist matching

**Steps**:
1. Create Intent Mandate:
```json
{"categories": ["OFFICE_SUPPLIES", "SOFTWARE", "TRAVEL"]}
```
2. Test expenses:
   - OFFICE_SUPPLIES → should match
   - SOFTWARE → should match
   - TRAVEL → should match
   - MEALS → should not match

**Expected Results**:
- [ ] All 3 whitelisted categories auto-approved
- [ ] Non-whitelisted categories rejected

---

### Test 5.3: Single Merchant Constraint

**Objective**: Verify single merchant matching

**Steps**:
1. Create Intent Mandate:
```json
{"merchant": "Amazon"}
```
2. Test expenses:
   - vendor: "Amazon" → should match
   - vendor: "Microsoft" → should not match

**Expected Results**:
- [ ] Only Amazon expenses auto-approved
- [ ] Other vendors rejected

---

### Test 5.4: Multiple Merchants Constraint (Whitelist)

**Objective**: Verify merchant whitelist matching

**Steps**:
1. Create Intent Mandate:
```json
{"merchants": ["Amazon", "Microsoft", "Adobe"]}
```
2. Test expenses:
   - vendor: "Amazon" → should match
   - vendor: "Microsoft" → should match
   - vendor: "Adobe" → should match
   - vendor: "Atlassian" → should not match

**Expected Results**:
- [ ] All 3 whitelisted merchants auto-approved
- [ ] Non-whitelisted merchants rejected

---

### Test 5.5: Combined Constraints (AND logic)

**Objective**: Verify ALL constraints must be satisfied

**Steps**:
1. Create Intent Mandate:
```json
{
  "max_amount": 200.00,
  "category": "OFFICE_SUPPLIES",
  "merchant": "Amazon"
}
```
2. Test expenses:

| Amount | Vendor    | Category        | Should Match? |
|--------|-----------|-----------------|---------------|
| $50    | Amazon    | OFFICE_SUPPLIES | ✅ Yes        |
| $250   | Amazon    | OFFICE_SUPPLIES | ❌ No (amount)|
| $50    | Microsoft | OFFICE_SUPPLIES | ❌ No (vendor)|
| $50    | Amazon    | TRAVEL          | ❌ No (category)|

**Expected Results**:
- [ ] Only row 1 is auto-approved
- [ ] All other rows fail constraint checks

---

## Section 6: Monthly Limit Tracking

### Test 6.1: Monthly Limit - Within Limit

**Objective**: Verify monthly spending tracking

**Steps**:
1. Create Intent Mandate:
```json
{
  "max_amount": 100.00,
  "monthly_limit": 500.00,
  "category": "OFFICE_SUPPLIES"
}
```
2. Submit expenses (same month):
   - Expense 1: $100 → Total: $100
   - Expense 2: $100 → Total: $200
   - Expense 3: $100 → Total: $300
   - Expense 4: $100 → Total: $400

**Expected Results**:
- [ ] All 4 expenses auto-approved
- [ ] Total monthly usage: $400 (under $500 limit)

---

### Test 6.2: Monthly Limit - Exceeds Limit

**Objective**: Verify monthly limit enforcement

**Steps**:
1. Use mandate from Test 6.1 (monthly_limit: 500)
2. Current usage: $400
3. Submit expense 5: $150

**Expected Results**:
- [ ] Expense 5 is REJECTED (would total $550)
- [ ] Status: PENDING (not auto-approved)
- [ ] Error log: "Monthly limit would be exceeded"

---

### Test 6.3: Monthly Limit - Exact Limit

**Objective**: Verify boundary condition (usage == monthly_limit)

**Steps**:
1. Current monthly usage: $400
2. Monthly limit: $500
3. Submit expense: $100 (would total exactly $500)

**Expected Results**:
- [ ] Expense is auto-approved
- [ ] Total monthly usage: $500
- [ ] Next expense should be rejected

---

### Test 6.4: Monthly Limit - Reset Next Month

**Objective**: Verify monthly limit resets

**Setup**:
- This test requires waiting for month rollover OR manually adjusting dates in database

**Steps**:
1. Mandate has monthly_limit: $500
2. Spend $500 in January (limit reached)
3. Submit expense in February

**Expected Results**:
- [ ] February expense is auto-approved
- [ ] Monthly usage counter reset to $0 at month start

**Alternative (Database Manipulation)**:
```sql
UPDATE expenses
SET date = '2026-01-15'
WHERE intent_mandate_id = '{mandate_id}';

-- Now submit new expense with current date
```
- [ ] New expense treats January as separate month
- [ ] Auto-approval works again

---

### Test 6.5: Multiple Mandates - Separate Monthly Limits

**Objective**: Verify each mandate tracks its own monthly limit

**Steps**:
1. Create Mandate A:
   - merchant: "Amazon"
   - monthly_limit: $500
2. Create Mandate B:
   - merchant: "Microsoft"
   - monthly_limit: $300
3. Submit expenses:
   - $400 from Amazon (uses Mandate A)
   - $250 from Microsoft (uses Mandate B)

**Expected Results**:
- [ ] Both expenses auto-approved
- [ ] Mandate A usage: $400/$500
- [ ] Mandate B usage: $250/$300
- [ ] Limits tracked independently

---

## Section 7: Complete AP2 Flow

### Test 7.1: Complete AP2 Flow - Success Path

**Objective**: Verify all 4 steps of AP2 protocol

**Steps**:
1. Login as `user1`
2. Call complete flow endpoint:
```bash
curl -X POST "http://localhost:8000/api/ap2/complete-flow" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {
        "description": "Office chair",
        "amount": 299.99,
        "category": "OFFICE_SUPPLIES"
      }
    ],
    "merchant": "Amazon",
    "constraints": {
      "max_amount": 500.00,
      "monthly_limit": 2000.00,
      "category": "OFFICE_SUPPLIES",
      "merchant": "Amazon"
    }
  }'
```

**Expected Results**:
- [ ] Status: 200 OK
- [ ] Response includes:
  - `intent_mandate_id`
  - `cart_mandate_id`
  - `payment_mandate_id`
  - `payment_result` with success status
  - `ap2_flow_complete: true`
- [ ] All 4 AP2 steps completed:
  1. Intent Mandate created
  2. Cart Mandate created
  3. Payment Mandate created
  4. Payment executed (if Stripe configured)

**Verification**:
```bash
# Check all mandates exist
curl -X GET "http://localhost:8000/api/ap2/user/mandates" \
  -H "Authorization: Bearer {token}"
```
- [ ] All 3 mandate types present in database

---

### Test 7.2: Complete AP2 Flow - Billing Limit Exceeded

**Objective**: Verify flow stops if AP2 transaction limit exceeded

**Steps**:
1. Login as `adminfree` (Free tier: 20 transactions/month)
2. Use up all 20 AP2 transactions
3. Attempt complete flow (21st transaction)

**Expected Results**:
- [ ] Status: 402 Payment Required
- [ ] Error: "AP2 transaction limit exceeded"
- [ ] Suggestion to upgrade tier
- [ ] No mandates created
- [ ] No payment executed

---

### Test 7.3: Cart Mandate Creation - Multiple Items

**Objective**: Verify Cart Mandate handles multiple items

**Steps**:
1. Create Intent Mandate first
2. Create Cart Mandate:
```json
{
  "intent_mandate_id": "{id}",
  "items": [
    {"description": "Keyboard", "amount": 79.99, "category": "OFFICE_SUPPLIES"},
    {"description": "Mouse", "amount": 39.99, "category": "OFFICE_SUPPLIES"},
    {"description": "Monitor", "amount": 249.99, "category": "OFFICE_SUPPLIES"}
  ],
  "merchant": "Amazon"
}
```

**Expected Results**:
- [ ] Status: 201 Created
- [ ] All 3 items stored in Cart Mandate
- [ ] Total calculated: $369.97
- [ ] Items count: 3

---

### Test 7.4: Payment Mandate Creation

**Objective**: Verify Payment Mandate creation and audit trail

**Steps**:
1. Create Intent Mandate
2. Create Cart Mandate
3. Create Payment Mandate:
```json
{
  "cart_mandate_id": "{id}",
  "payment_method": "stripe",
  "stripe_customer_id": "cus_test123"
}
```

**Expected Results**:
- [ ] Status: 201 Created
- [ ] payment_mandate_id returned
- [ ] Audit trail includes:
  - cart_mandate_id
  - intent_mandate_id
  - timestamp
  - payment_method
  - total_amount
  - merchant
  - items_count

---

### Test 7.5: Execute Payment via Stripe

**Objective**: Verify payment execution (requires Stripe test mode)

**Prerequisites**:
- Stripe test API keys configured
- Test credit card: 4242 4242 4242 4242

**Steps**:
1. Complete AP2 flow through Payment Mandate creation
2. Call execute-payment endpoint:
```json
{
  "payment_mandate_id": "{id}",
  "stripe_payment_method_id": "pm_card_visa",
  "nonce": "unique-nonce-12345",
  "timestamp": "2026-01-22T15:30:00Z"
}
```

**Expected Results**:
- [ ] Status: 200 OK
- [ ] Payment result shows success: true
- [ ] Stripe transaction_id returned
- [ ] Payment Mandate updated with processor response
- [ ] Nonce marked as used (replay prevention)

---

## Section 8: UI/UX Testing

### Test 8.1: Navigate to AI Assistant Page

**Objective**: Verify AI Assistant page is accessible

**Steps**:
1. Login as `user1`
2. Look for "AI Assistant" link in navigation
3. Click to navigate to page

**Expected Results**:
- [ ] AI Assistant link visible in main navigation
- [ ] Page loads: http://localhost:5173/ai-assistant (or similar)
- [ ] No console errors
- [ ] Dashboard displays correctly

**Known Issue**: As of test date, AI Assistant may not be in main nav - may need direct URL access

---

### Test 8.2: AI Assistant Dashboard - Quick Stats

**Objective**: Verify dashboard statistics display

**Steps**:
1. Navigate to AI Assistant page
2. Check quick stats section

**Expected Results**:
- [ ] Shows "Active Mandates" count
- [ ] Shows "Total Processed" amount
- [ ] Stats update in real-time
- [ ] Icons and formatting correct

---

### Test 8.3: Mandates Tab - View All Mandates

**Objective**: Verify mandates list view

**Steps**:
1. Navigate to AI Assistant > Mandates tab
2. View mandate cards

**Expected Results**:
- [ ] All mandates displayed as cards
- [ ] Each card shows:
  - Merchant name
  - Category
  - Max amount
  - Monthly limit
  - Expiration date
  - Status badge (active/expired/revoked)
- [ ] Cards are expandable
- [ ] Icons used for visual clarity

---

### Test 8.4: Mandates Tab - Filter by Status

**Objective**: Verify status filtering UI

**Steps**:
1. Navigate to Mandates tab
2. Use status filter dropdown
3. Select "Active"
4. Select "Expired"
5. Select "All"

**Expected Results**:
- [ ] Filter dropdown works
- [ ] Only selected status shown
- [ ] Count badge updates
- [ ] No layout issues

---

### Test 8.5: Create Mandate via Constraint Builder

**Objective**: Verify visual mandate creation UI

**Steps**:
1. Navigate to AI Assistant page
2. Look for "Create Intent Mandate" button
3. Open Constraint Builder UI
4. Fill in fields:
   - Max Amount: $200
   - Monthly Limit: $1000
   - Category: OFFICE_SUPPLIES (dropdown)
   - Merchant: Amazon (dropdown or input)
   - Expiration: Date picker
5. Click "Create"

**Expected Results**:
- [ ] Form validation works
- [ ] Dropdowns populated correctly
- [ ] Date picker functional
- [ ] Success message on creation
- [ ] New mandate appears in list immediately
- [ ] No page refresh needed

---

### Test 8.6: Activity Monitor - Transaction History

**Objective**: Verify AP2 activity monitoring

**Steps**:
1. Navigate to AI Assistant > Activity tab
2. View transaction history

**Expected Results**:
- [ ] Shows auto-approved expenses
- [ ] Each entry displays:
  - Expense description
  - Amount
  - Merchant
  - Category
  - Timestamp
  - Intent Mandate used
- [ ] Sorted by date (newest first)
- [ ] Real-time updates

---

### Test 8.7: Settings Tab - AP2 Configuration

**Objective**: Verify AP2 settings page

**Steps**:
1. Navigate to AI Assistant > Settings tab
2. Check available settings

**Expected Results**:
- [ ] Default expiration time setting
- [ ] Enable/disable AP2 toggle
- [ ] Usage statistics
- [ ] Billing tier information
- [ ] Transaction limit display

---

### Test 8.8: Mobile Responsiveness

**Objective**: Verify mobile UI

**Steps**:
1. Open AI Assistant page on mobile device or resize browser to 375px width
2. Test all tabs and features

**Expected Results**:
- [ ] Layout adapts to small screen
- [ ] Mandate cards stack vertically
- [ ] Navigation collapses to hamburger menu
- [ ] Forms are usable
- [ ] No horizontal scrolling
- [ ] Touch targets are adequate size (min 44px)

---

## Section 9: Security Features

### Test 9.1: Cryptographic Signing - Verify Signature

**Objective**: Verify Intent Mandate is cryptographically signed

**Steps**:
1. Create Intent Mandate
2. Check response for `signature` field
3. Verify signature is base64-encoded
4. (Advanced) Use Google Cloud KMS public key to verify signature

**Expected Results**:
- [ ] Signature field present
- [ ] Base64-encoded string
- [ ] Signature verifies with KMS public key
- [ ] Tamper detection works (if implementation supports)

---

### Test 9.2: Access Control - Own Mandates Only

**Objective**: Verify users can only access their own mandates

**Steps**:
1. User1 creates Intent Mandate (ID: mandate_1)
2. User2 attempts to view mandate_1:
```bash
curl -X GET "http://localhost:8000/api/ap2/intent-mandate/mandate_1" \
  -H "Authorization: Bearer {user2_token}"
```

**Expected Results**:
- [ ] Status: 403 Forbidden
- [ ] Error: "Access denied"
- [ ] User2 cannot see user1's mandate

---

### Test 9.3: Replay Attack Prevention - Nonce Validation

**Objective**: Verify nonce cannot be reused

**Steps**:
1. Execute payment with nonce: "test-nonce-123"
2. Attempt to execute another payment with same nonce

**Expected Results**:
- [ ] First payment: 200 OK
- [ ] Second payment: 400 Bad Request
- [ ] Error: "Nonce has already been used"

---

### Test 9.4: Timestamp Validation

**Objective**: Verify timestamp is within acceptable window

**Steps**:
1. Attempt payment with timestamp 10 minutes in the past
2. Attempt payment with timestamp 10 minutes in the future

**Expected Results**:
- [ ] Both rejected: 400 Bad Request
- [ ] Error: "Timestamp outside acceptable range"
- [ ] Acceptable window: ±5 minutes from server time

---

### Test 9.5: Rate Limiting

**Objective**: Verify rate limits on AP2 endpoints

**Limits** (from code review):
- Intent Mandate creation: 20/min
- Payment execution: 10/min
- Complete flow: 5/min

**Steps**:
1. Make 21 Intent Mandate creation requests in 1 minute

**Expected Results**:
- [ ] First 20 requests: 201 Created
- [ ] 21st request: 429 Too Many Requests
- [ ] Error: "Rate limit exceeded"
- [ ] Retry-After header present

---

## Section 10: Billing & Usage Tracking

### Test 10.1: AP2 Transaction Counted

**Objective**: Verify AP2 usage is tracked

**Steps**:
1. Check initial AP2 usage count:
```bash
curl -X GET "http://localhost:8000/api/ap2/stats" \
  -H "Authorization: Bearer {token}"
```
2. Submit expense that triggers Intent Mandate auto-approval
3. Check updated usage count

**Expected Results**:
- [ ] Usage count increases by 1
- [ ] Usage type: "ap2_transaction"
- [ ] Metadata includes: merchant, intent_mandate_id, source

---

### Test 10.2: Non-AP2 Auto-Approval Not Counted

**Objective**: Verify Approval Policy auto-approval doesn't count as AP2

**Steps**:
1. Check AP2 usage count
2. Submit expense auto-approved via Approval Policy (not Intent Mandate)
3. Check AP2 usage count again

**Expected Results**:
- [ ] AP2 usage count unchanged
- [ ] Only Intent Mandate approvals count toward AP2 limit

---

### Test 10.3: Tier Limit Enforcement - Free Tier

**Objective**: Verify Free tier 20 transaction limit

**Steps**:
1. Login as Free tier user
2. Create 20 Intent Mandates and auto-approve 20 expenses
3. Attempt 21st auto-approval

**Expected Results**:
- [ ] First 20: Auto-approved
- [ ] 21st: Reverts to manual approval (or 402 error)
- [ ] Warning message about tier limit

---

### Test 10.4: Tier Limit Enforcement - Professional Tier

**Objective**: Verify Professional tier 500 transaction limit

**Steps**:
1. Login as Professional tier user
2. Simulate 500 AP2 transactions (use script if needed)
3. Attempt 501st transaction

**Expected Results**:
- [ ] First 500: Success
- [ ] 501st: 402 Payment Required
- [ ] Suggestion to upgrade to Enterprise

---

### Test 10.5: Usage Statistics API

**Objective**: Verify usage stats endpoint

**Steps**:
1. Call stats endpoint:
```bash
curl -X GET "http://localhost:8000/api/ap2/stats" \
  -H "Authorization: Bearer {token}"
```

**Expected Results**:
- [ ] Returns usage breakdown:
  - Total AP2 transactions this month
  - Tier limit
  - Remaining transactions
  - Auto-approval rate (%)
  - Most used categories
  - Most used merchants

---

## Section 11: GDPR Compliance

### Test 11.1: Revoke Intent Mandate (Withdraw Consent)

**Objective**: Verify GDPR Article 7.3 compliance

**Steps**:
1. Create Intent Mandate
2. Revoke mandate:
```bash
curl -X POST "http://localhost:8000/api/ap2/intent-mandate/{id}/revoke" \
  -H "Authorization: Bearer {token}"
```

**Expected Results**:
- [ ] Status: 200 OK
- [ ] Mandate status changed to "revoked"
- [ ] Revocation timestamp recorded
- [ ] Cannot be undone
- [ ] Future expenses will not match this mandate

---

### Test 11.2: Cascade Revocation

**Objective**: Verify revoking Intent Mandate revokes dependent mandates

**Steps**:
1. Complete full AP2 flow (creates Intent, Cart, Payment Mandates)
2. Revoke Intent Mandate
3. Check status of Cart and Payment Mandates

**Expected Results**:
- [ ] Intent Mandate: revoked
- [ ] Cart Mandate: revoked (cascaded)
- [ ] Payment Mandate: revoked (cascaded)
- [ ] All marked with same revocation timestamp

---

### Test 11.3: Revocation Audit Trail

**Objective**: Verify immutable audit log

**Steps**:
1. Create and revoke Intent Mandate
2. Check database for audit trail
3. Attempt to delete revoked mandate

**Expected Results**:
- [ ] Revocation event logged
- [ ] Includes: timestamp, user_id, mandate_id, reason
- [ ] Revoked mandates remain in database (soft delete)
- [ ] Cannot be permanently deleted (immutable)

---

### Test 11.4: Revoke Cart Mandate Independently

**Objective**: Verify Cart Mandate can be revoked separately

**Steps**:
1. Create Intent and Cart Mandates
2. Revoke only Cart Mandate:
```bash
curl -X POST "http://localhost:8000/api/ap2/cart-mandate/{id}/revoke" \
  -H "Authorization: Bearer {token}"
```

**Expected Results**:
- [ ] Cart Mandate: revoked
- [ ] Intent Mandate: still active
- [ ] Can create new Cart Mandate using same Intent Mandate

---

### Test 11.5: Revoke Payment Mandate

**Objective**: Verify Payment Mandate revocation

**Steps**:
1. Create all 3 mandate types
2. Revoke Payment Mandate before payment execution

**Expected Results**:
- [ ] Payment Mandate: revoked
- [ ] Payment execution blocked
- [ ] Cart and Intent Mandates: still active
- [ ] Can create new Payment Mandate

---

## Section 12: Error Handling

### Test 12.1: Expired Intent Mandate

**Objective**: Verify expired mandates are not used

**Steps**:
1. Create Intent Mandate with expiration: "2026-01-22T10:00:00"
2. Wait until after expiration (or manually adjust system time)
3. Submit matching expense

**Expected Results**:
- [ ] Mandate status: "expired"
- [ ] Expense not auto-approved
- [ ] Falls back to Tier 2/3
- [ ] Log message: "Intent Mandate expired"

---

### Test 12.2: Invalid Intent Mandate ID

**Objective**: Verify error handling for non-existent mandate

**Steps**:
1. Attempt to create Cart Mandate with fake Intent Mandate ID:
```json
{"intent_mandate_id": "00000000-0000-0000-0000-000000000000"}
```

**Expected Results**:
- [ ] Status: 404 Not Found
- [ ] Error: "Intent Mandate not found"

---

### Test 12.3: Duplicate Expense Submission

**Objective**: Verify duplicate prevention

**Steps**:
1. Submit expense
2. Immediately submit identical expense (within 10 seconds)

**Expected Results**:
- [ ] First submission: Success
- [ ] Second submission: 409 Conflict
- [ ] Error: "Duplicate expense detected"

---

### Test 12.4: Invalid Expense Data

**Objective**: Verify expense validation

**Test Cases**:

**12.4a: Missing required fields**
```json
{"amount": 50.00}  // missing vendor, category
```
- [ ] 400 Bad Request
- [ ] Error lists missing fields

**12.4b: Negative amount**
```json
{"amount": -50.00, "vendor": "Amazon", "category": "OFFICE_SUPPLIES"}
```
- [ ] 400 Bad Request
- [ ] Error: "Amount must be positive"

**12.4c: Invalid date**
```json
{"date": "2026-13-45", ...}
```
- [ ] 400 Bad Request
- [ ] Error: "Invalid date format"

---

### Test 12.5: Stripe Payment Failure

**Objective**: Verify handling of payment processor errors

**Steps**:
1. Complete AP2 flow
2. Execute payment with invalid payment method ID

**Expected Results**:
- [ ] Status: 400 or 500
- [ ] Error includes Stripe error message
- [ ] Payment Mandate updated with failure status
- [ ] Can retry payment

---

### Test 12.6: Google Cloud KMS Unavailable

**Objective**: Verify graceful degradation when KMS is down

**Steps**:
1. (Requires test environment) Disable KMS service
2. Attempt to create Intent Mandate

**Expected Results**:
- [ ] Status: 503 Service Unavailable
- [ ] Error: "Signing service unavailable"
- [ ] User-friendly error message
- [ ] Mandate not created (integrity maintained)

---

## Section 13: Edge Cases

### Test 13.1: Zero Amount Expense

**Objective**: Verify handling of $0 expenses

**Steps**:
1. Submit expense with amount: 0.00

**Expected Results**:
- [ ] 400 Bad Request
- [ ] Error: "Amount must be greater than zero"

---

### Test 13.2: Very Large Amount

**Objective**: Verify handling of large amounts

**Steps**:
1. Create Intent Mandate with max_amount: 999999.99
2. Submit expense for $500,000

**Expected Results**:
- [ ] Auto-approved if all constraints match
- [ ] No overflow errors
- [ ] Correctly stored in database

---

### Test 13.3: Special Characters in Merchant Name

**Objective**: Verify merchant name handling

**Steps**:
1. Create Intent Mandate with merchant: "Café & Co."
2. Submit expense with vendor: "Café & Co."

**Expected Results**:
- [ ] Matching works correctly
- [ ] Special characters preserved
- [ ] No encoding issues

---

### Test 13.4: Multiple Expenses in Quick Succession

**Objective**: Verify concurrent expense handling

**Steps**:
1. Submit 10 expenses simultaneously (use parallel requests)
2. All match same Intent Mandate with monthly_limit: $1000

**Expected Results**:
- [ ] All expenses processed
- [ ] No race conditions
- [ ] Monthly limit accurately tracked
- [ ] No double-counting

---

### Test 13.5: Expense Submitted Before Intent Mandate Created

**Objective**: Verify timing dependency

**Steps**:
1. Submit expense first
2. Create matching Intent Mandate after

**Expected Results**:
- [ ] Expense remains PENDING (not retroactively approved)
- [ ] Only new expenses use the mandate

---

### Test 13.6: Intent Mandate with No Constraints

**Objective**: Verify minimum constraint requirement

**Steps**:
1. Attempt to create Intent Mandate with empty constraints:
```json
{"constraints": {}}
```

**Expected Results**:
- [ ] 400 Bad Request
- [ ] Error: "At least one constraint required"

---

### Test 13.7: Deleted Organization

**Objective**: Verify mandate handling when org is deleted

**Setup**:
1. Create Intent Mandate
2. Admin deletes organization

**Expected Results**:
- [ ] All mandates cascade-deleted OR marked as revoked
- [ ] Cannot use mandates from deleted org
- [ ] No orphaned records

---

### Test 13.8: User Role Change

**Objective**: Verify mandate ownership after role change

**Steps**:
1. User creates Intent Mandate as EMPLOYEE
2. User promoted to ADMIN
3. Check mandate ownership

**Expected Results**:
- [ ] Mandate still owned by user
- [ ] Still usable
- [ ] No access issues

---

## Test Results Summary

| Section | Total Tests | Passed | Failed | Skipped | Notes |
|---------|-------------|--------|--------|---------|-------|
| 1. Intent Mandate Creation | 6 | | | | |
| 2. Intent Mandate Management | 6 | | | | |
| 3. Auto-Approval Workflow | 6 | | | | |
| 4. Three-Tier Hierarchy | 4 | | | | |
| 5. Constraint Matching | 5 | | | | |
| 6. Monthly Limit Tracking | 5 | | | | |
| 7. Complete AP2 Flow | 5 | | | | |
| 8. UI/UX Testing | 8 | | | | |
| 9. Security Features | 5 | | | | |
| 10. Billing & Usage | 5 | | | | |
| 11. GDPR Compliance | 5 | | | | |
| 12. Error Handling | 6 | | | | |
| 13. Edge Cases | 8 | | | | |
| **TOTAL** | **74** | | | | |

---

## Testing Checklist

### Prerequisites Setup
- [ ] Backend running on http://localhost:8000
- [ ] Frontend running on http://localhost:5173
- [ ] Database initialized
- [ ] Test users created (user1, adminfree)
- [ ] Google Cloud KMS configured
- [ ] Stripe test mode configured (optional)

### Testing Order (Recommended)
1. [ ] Section 1: Intent Mandate Creation (API foundation)
2. [ ] Section 2: Intent Mandate Management (CRUD operations)
3. [ ] Section 3: Auto-Approval Workflow (core feature)
4. [ ] Section 4: Three-Tier Hierarchy (integration)
5. [ ] Section 5: Constraint Matching (business logic)
6. [ ] Section 6: Monthly Limit Tracking (advanced logic)
7. [ ] Section 8: UI/UX Testing (frontend)
8. [ ] Section 7: Complete AP2 Flow (end-to-end)
9. [ ] Section 9: Security Features
10. [ ] Section 10: Billing & Usage
11. [ ] Section 11: GDPR Compliance
12. [ ] Section 12: Error Handling
13. [ ] Section 13: Edge Cases

---

## Known Issues & Limitations

From codebase review:

1. **Logger Error**: Non-blocking logger issue in end-to-end testing
   - Status: Under investigation
   - Impact: Doesn't affect production functionality

2. **UI Navigation**: AI Assistant page not in main navigation
   - Workaround: Direct URL access
   - Status: To be fixed

3. **Monthly Limit Reset**: Requires month rollover
   - Testing: May need manual date adjustment in database

---

## Test Environment Configuration

### Required Environment Variables

```bash
# Backend (.env)
GOOGLE_CLOUD_KMS_KEY_NAME=projects/.../keyRings/.../cryptoKeys/...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
DATABASE_URL=sqlite:///./test.db
```

### Test Data Setup Script

```python
# create_ap2_test_data.py
import requests

BASE_URL = "http://localhost:8000"

# Login as user1
response = requests.post(f"{BASE_URL}/api/v1/auth/login",
    data={"username": "user1", "password": "Passowrd123!"})
token = response.json()["access_token"]

headers = {"Authorization": f"Bearer {token}"}

# Create test Intent Mandate
requests.post(f"{BASE_URL}/api/ap2/intent-mandate",
    headers=headers,
    json={
        "constraints": {
            "max_amount": 200.00,
            "monthly_limit": 1000.00,
            "category": "OFFICE_SUPPLIES",
            "merchant": "Amazon"
        }
    })

print("Test data created successfully")
```

---

## Reporting Issues

When reporting test failures, include:

1. **Test ID** (e.g., Test 3.1)
2. **Expected vs Actual** behavior
3. **Steps to reproduce**
4. **Screenshots** (for UI tests)
5. **Logs** (check backend console for `[AP2]` prefix)
6. **Environment details** (OS, browser, versions)

**Example**:
```
Test ID: 3.1
Issue: Expense not auto-approved despite matching Intent Mandate
Expected: auto_approved = true, status = APPROVED
Actual: auto_approved = false, status = PENDING
Logs: [AP2] No active Intent Mandates found for user xyz-789
```

---

## Success Criteria

AP2 automation is considered fully functional when:

- [ ] 100% of Section 1-7 tests pass (core functionality)
- [ ] 90%+ of Section 8 tests pass (UI/UX)
- [ ] 100% of Section 9 tests pass (security)
- [ ] 100% of Section 10 tests pass (billing)
- [ ] 100% of Section 11 tests pass (compliance)
- [ ] 80%+ of Section 12-13 tests pass (error handling, edge cases)
- [ ] Auto-approval rate reaches 60-70% in real-world usage
- [ ] No critical security vulnerabilities
- [ ] All audit trails complete and accurate

---

## Appendix: Quick Reference

### API Endpoints Quick List

```
POST   /api/ap2/intent-mandate
GET    /api/ap2/user/mandates
GET    /api/ap2/intent-mandate/{id}/status
POST   /api/ap2/intent-mandate/{id}/revoke

POST   /api/ap2/cart-mandate
POST   /api/ap2/cart-mandate/{id}/revoke

POST   /api/ap2/payment-mandate
POST   /api/ap2/payment-mandate/{id}/revoke
POST   /api/ap2/execute-payment

POST   /api/ap2/complete-flow
GET    /api/ap2/stats
```

### Common Test Commands

```bash
# Login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user1&password=Passowrd123!"

# Create Intent Mandate
curl -X POST "http://localhost:8000/api/ap2/intent-mandate" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"constraints": {...}}'

# Submit Expense
curl -X POST "http://localhost:8000/api/v1/expenses" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"amount": 50, "vendor": "Amazon", "category": "OFFICE_SUPPLIES"}'

# Check Stats
curl -X GET "http://localhost:8000/api/ap2/stats" \
  -H "Authorization: Bearer {token}"
```

### Category Values

```
OFFICE_SUPPLIES
SOFTWARE
TRAVEL
MEALS
ENTERTAINMENT
UTILITIES
MARKETING
HARDWARE
PROFESSIONAL_SERVICES
OTHER
```

---

**Document Version**: 1.0
**Last Updated**: 2026-01-22
**Total Test Cases**: 74
**Estimated Testing Time**: 6-8 hours (full suite)
