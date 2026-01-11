# AP2 (Agent Payments Protocol) Features Overview

## What is AP2?

AP2 (Agent Payments Protocol) is a **premium AI agent feature** that enables automatic expense approval based on pre-authorized constraints. It's Google's protocol for cryptographic payment verification with AI agents.

Think of it as: **"Pre-authorize your AI to auto-approve specific expenses"**

---

## How It Works

### The 3-Tier Flow

```
User → Intent Mandate → Expense Submitted → Auto-Approved!
```

1. **Intent Mandate** (User sets rules)
   - "Auto-approve Amazon purchases under $200/month for office supplies"
   - User pre-authorizes AI agent with constraints

2. **Expense Submission** (Employee submits expense)
   - Employee submits $45 Amazon expense for "Wireless keyboard"

3. **Automatic Approval** (AI agent checks)
   - ✅ Vendor: Amazon (matches)
   - ✅ Category: Office Supplies (matches)
   - ✅ Amount: $45 < $200 (matches)
   - ✅ Monthly usage: $45 < $200 limit (matches)
   - **Result: AUTO-APPROVED** with ✨ AI Agent badge

---

## Key Components

### 1. **Intent Mandate** (Authorization)

**What it is:**
- User's pre-authorization for AI agent to approve expenses
- Contains constraints/rules the expense must match

**Example:**
```json
{
  "merchant": "Amazon",
  "category": "OFFICE_SUPPLIES",
  "max_amount": 200.00,
  "monthly_limit": 1000.00
}
```

**Features:**
- Expiration date (default: 24 hours, configurable)
- Cryptographic signature using Google Cloud KMS
- Status tracking: `active`, `expired`, `used`
- Monthly spending limits

---

### 2. **Cart Mandate** (Shopping Cart)

**What it is:**
- Specific items for approval
- Created when expense matches Intent Mandate

**Example:**
```json
{
  "items": [
    {
      "description": "Wireless keyboard",
      "amount": 45.99,
      "vendor": "Amazon",
      "category": "office_supplies"
    }
  ],
  "total": 45.99,
  "merchant": "Amazon"
}
```

---

### 3. **Payment Mandate** (Execution)

**What it is:**
- Final payment execution record
- Contains cryptographic audit trail
- Integrates with Stripe for actual payment

**Audit Trail Includes:**
- Timestamp
- User signature
- Intent Mandate reference
- Cart details
- Payment processor response

---

## Auto-Approval Logic

### Constraint Matching

When an expense is submitted, AP2 checks:

1. **Active Intent Mandate exists** for this user
2. **Not expired** (expiration > current time)
3. **Merchant matches** (case-insensitive)
   - "amazon" matches "Amazon"
4. **Category matches** (case-insensitive)
   - "office_supplies" matches "OFFICE_SUPPLIES"
5. **Amount under limit** (per-expense max)
   - $45 < $200 max ✅
6. **Monthly limit not exceeded**
   - Current month usage + new amount < monthly limit
   - $150 existing + $45 new = $195 < $1000 ✅

### Priority System

1. **Tier 1: AP2 Intent Mandate** (checked FIRST - Premium)
2. **Tier 2: Approval Policy** (checked SECOND - Free)
3. **Tier 3: Manual Approval** (fallback)

---

## Frontend UI

### Components

1. **IntentMandateManager.jsx**
   - View/create/delete Intent Mandates
   - Filter by status (all, active, expired, used)
   - Visual constraint display
   - Monthly usage tracking

2. **ConstraintBuilder.jsx**
   - Drag-and-drop constraint builder
   - Vendor selection
   - Category selection
   - Amount limits
   - Time restrictions

3. **AgentActivityMonitor.jsx**
   - Real-time AP2 transaction monitoring
   - Auto-approval history
   - Spending analytics

---

## Backend API

### Endpoints

**Intent Mandate Management:**
```
POST   /api/ap2/intent-mandate      - Create Intent Mandate
GET    /api/ap2/intent-mandate/:id  - Get Intent Mandate details
DELETE /api/ap2/intent-mandate/:id  - Delete Intent Mandate
GET    /api/ap2/intent-mandates     - List user's mandates
```

**Cart Mandate:**
```
POST   /api/ap2/cart-mandate         - Create Cart Mandate
GET    /api/ap2/cart-mandate/:id     - Get Cart details
```

**Payment Mandate:**
```
POST   /api/ap2/payment-mandate      - Create Payment Mandate
POST   /api/ap2/payment/:id/execute  - Execute payment
GET    /api/ap2/payment-mandate/:id  - Get payment status
```

**Complete Flow:**
```
POST   /api/ap2/complete-flow        - Execute full AP2 flow in one call
```

---

## Database Models

### IntentMandate
```python
- id: UUID
- user_id: User who created it
- constraints: JSON (merchant, category, limits)
- timestamp: Creation time
- expiration: When it expires
- status: active/expired/used
- signature: Cryptographic signature (Cloud KMS)
```

### CartMandate
```python
- id: UUID
- intent_mandate_id: Parent Intent Mandate
- items: JSON array of cart items
- total: Total amount
- merchant: Vendor name
- timestamp: Creation time
- user_signature: User approval signature
- status: pending/completed/failed
```

### PaymentMandate
```python
- id: UUID
- cart_mandate_id: Parent Cart Mandate
- payment_method: stripe/crypto
- status: pending/completed/failed
- audit_trail: JSON (complete history)
- timestamp: Creation time
- payment_processor_response: Stripe response
```

---

## Security Features

### Cryptographic Signing

**Google Cloud KMS Integration:**
- RSA-2048 asymmetric signing
- Keys managed in HSM (Hardware Security Module)
- SHA-256 hashing
- PSS padding
- Keys never leave secure enclave

**What's Signed:**
- Intent Mandate creation
- Cart approval
- Payment execution

**Verification:**
- Public key verification
- Tamper detection
- Audit trail integrity

---

## Usage Tracking & Billing

### Tracked Metrics

1. **AP2 Transactions**
   - Each Intent Mandate auto-approval = 1 transaction
   - Tracked for billing purposes
   - Displayed in billing dashboard

2. **Monthly Usage**
   - Per Intent Mandate spending tracking
   - Organization-wide AP2 usage
   - Tier limit enforcement

### Billing Integration

- AP2 transactions are premium feature
- Counted toward usage-based billing
- Free tier: Limited AP2 transactions
- Paid tiers: Higher/unlimited AP2

---

## User Experience

### Employee View

**Submitting Expense:**
1. Fill out expense form ($45 Amazon keyboard)
2. Click "Submit"
3. **Instant auto-approval!** ✨
4. Badge shows "AI Agent" approved
5. No waiting for manager

**Benefits:**
- Faster reimbursement
- Less back-and-forth
- Clear visibility into auto-approval

### Admin View

**Setting Up Intent Mandates:**
1. Go to "AP2 Settings" or "Intent Mandates"
2. Click "Create Intent Mandate"
3. Set constraints:
   - Merchant: Amazon
   - Category: Office Supplies
   - Max Amount: $200
   - Monthly Limit: $1000
4. Set expiration (24h default)
5. Save → Mandate is active

**Monitoring:**
- View all Intent Mandates
- See monthly usage per mandate
- Track auto-approved expenses
- Audit trail for compliance

---

## Current Status in Your App

### ✅ Implemented (Backend)

1. **AP2PaymentService** (`backend/src/payments/ap2_service.py`)
   - Create Intent/Cart/Payment Mandates
   - Constraint matching logic
   - Monthly usage tracking
   - Cryptographic signing (KMS)
   - Full AP2 flow execution

2. **API Endpoints** (`backend/src/routes/ap2.py`)
   - All mandate CRUD operations
   - Complete flow endpoint
   - Status checking

3. **Database Models** (`backend/src/models.py`)
   - IntentMandate
   - CartMandate
   - PaymentMandate
   - Relationships & indexes

4. **Auto-Approval Integration** (`backend/src/routes/expenses.py`)
   - Lines 243-333: Intent Mandate auto-approval
   - Tier 1 priority (before Approval Policies)
   - Usage tracking
   - Audit logging

### ✅ Implemented (Frontend)

1. **IntentMandateManager** component
   - View/create/delete mandates
   - Status filtering
   - Constraint display

2. **ConstraintBuilder** component
   - Visual constraint builder

3. **AgentActivityMonitor** component
   - Real-time AP2 monitoring

4. **Dashboard Integration**
   - Auto-approval badges
   - "✨ AI Agent" labels
   - Expense auto-approval status

---

## Example Use Cases

### 1. Office Supplies Auto-Approval

**Intent Mandate:**
```json
{
  "merchant": "Amazon",
  "category": "OFFICE_SUPPLIES",
  "max_amount": 100.00,
  "monthly_limit": 500.00
}
```

**Result:**
- $35 keyboard → ✅ Auto-approved
- $250 desk → ❌ Manual approval (exceeds $100)
- $75 chair (6th purchase this month, $450 used) → ✅ Auto-approved
- $60 lamp (would exceed $500 monthly) → ❌ Manual approval

---

### 2. Software Subscriptions

**Intent Mandate:**
```json
{
  "merchant": ["Microsoft", "Adobe", "Atlassian"],
  "category": "SOFTWARE",
  "max_amount": 500.00,
  "monthly_limit": 2000.00
}
```

**Result:**
- $299 Adobe Creative Cloud → ✅ Auto-approved
- $149 Microsoft Office → ✅ Auto-approved
- $99 Atlassian Jira → ✅ Auto-approved
- $50 Random SaaS → ❌ Manual (vendor not in list)

---

### 3. Travel Expenses

**Intent Mandate:**
```json
{
  "category": "TRAVEL",
  "max_amount": 300.00,
  "monthly_limit": 1500.00
}
```

**Result:**
- $125 Uber to airport → ✅ Auto-approved
- $250 Hotel night → ✅ Auto-approved
- $450 Flight → ❌ Manual (exceeds per-expense limit)

---

## Testing AP2

### Manual Test Steps

1. **Create Intent Mandate** (as admin/user)
   ```bash
   POST /api/ap2/intent-mandate
   {
     "constraints": {
       "merchant": "Amazon",
       "category": "OFFICE_SUPPLIES",
       "max_amount": 200,
       "monthly_limit": 1000
     },
     "expiration_hours": 720  # 30 days
   }
   ```

2. **Submit Matching Expense** (as employee)
   ```bash
   POST /api/v1/expenses
   {
     "amount": 75.50,
     "vendor": "Amazon",
     "category": "OFFICE_SUPPLIES",
     "description": "Wireless keyboard"
   }
   ```

3. **Verify Auto-Approval**
   - Check expense status = `APPROVED`
   - Check `auto_approved` = `true`
   - Check `auto_approved_via` = `intent_mandate`
   - Check badge shows "✨ AI Agent"

### Checking Intent Mandates

```bash
# List all Intent Mandates for current user
GET /api/ap2/intent-mandates

# Check monthly usage
GET /api/ap2/intent-mandate/:id/usage
```

---

## Configuration

### Environment Variables

```env
# Cloud KMS for cryptographic signing
GOOGLE_CLOUD_PROJECT=your-project-id
KMS_KEY_RING=ap2-mandates
KMS_KEY=mandate-signing-key

# Enable AP2 features
ENABLE_AP2=true

# Stripe integration (for payments)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
```

### Feature Flags

```python
# backend/src/config.py
enable_ap2 = True  # Enable AP2 features
ap2_transaction_fee = 0.10  # Fee per AP2 transaction
```

---

## Monitoring & Logs

### Log Examples

```
[AP2] Auto-approving expense abc-123 via Intent Mandate def-456
[AP2] Found 2 active Intent Mandates for user xyz-789
[AP2] Expense matches Intent Mandate def-456: $45 from Amazon (OFFICE_SUPPLIES)
[AP2] Monthly limit check: $195 < $1000 (current usage: $150, new: $45)
[AP2] All constraints satisfied for mandate def-456
[AP2] Tracked auto-approved expense via Intent Mandate: abc-123
```

### Audit Trail

Every AP2 transaction creates:
1. Intent Mandate record with signature
2. Cart Mandate record with items
3. Payment Mandate record with audit trail
4. Expense record with `intent_mandate_id`
5. Usage tracking record

**Full traceability for compliance!**

---

## Benefits

### For Employees
- ✅ Instant approval for routine expenses
- ✅ No waiting for manager
- ✅ Clear rules on what's auto-approved
- ✅ Faster reimbursement

### For Managers
- ✅ Less time approving routine expenses
- ✅ Focus on high-value/unusual expenses
- ✅ Set rules once, auto-approve forever
- ✅ Full audit trail for compliance

### For Organization
- ✅ Reduced processing time
- ✅ Better employee experience
- ✅ Cryptographic security (KMS)
- ✅ Compliance-ready audit trails
- ✅ Scalable automation

---

## Next Steps

### To Enable AP2 for Your Org

1. **Set up Intent Mandates** in the UI
2. **Configure constraints** for your use cases
3. **Test with sample expenses**
4. **Monitor auto-approvals** in dashboard
5. **Adjust constraints** as needed

### To Access AP2 UI

1. Login to app: http://localhost:5173
2. Navigate to "AP2 Settings" or "Intent Mandates"
3. Click "Create Intent Mandate"
4. Fill in constraints and save

---

## Documentation Files

- `backend/src/payments/ap2_service.py` - Core AP2 logic
- `backend/src/routes/ap2.py` - API endpoints
- `frontend/src/components/IntentMandateManager.jsx` - UI component
- `backend/src/models.py` (lines 767-833) - Database models

---

**Status**: ✅ Fully Implemented
**Premium Feature**: Yes
**Cryptographic Security**: Google Cloud KMS
**Ready to Use**: Yes!

---

## Quick Reference

| Feature | Status | File |
|---------|--------|------|
| Intent Mandate creation | ✅ | `ap2_service.py:33` |
| Constraint matching | ✅ | `ap2_service.py:565` |
| Monthly limit tracking | ✅ | `ap2_service.py:663` |
| Auto-approval flow | ✅ | `expenses.py:243` |
| Cryptographic signing | ✅ | `ap2_service.py:318` |
| UI for mandates | ✅ | `IntentMandateManager.jsx` |
| API endpoints | ✅ | `routes/ap2.py` |
| Usage tracking | ✅ | `ap2_service.py:429` |

