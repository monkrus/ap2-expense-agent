# Complete Approval Options Guide

## Overview

Your expense management system has **3 approval mechanisms** that work together in a priority cascade:

```
When an expense is submitted:
  ↓
1. Check AP2 Intent Mandates (Premium) → Auto-approve if match
  ↓ (no match)
2. Check Approval Policies (Free) → Auto-approve if match
  ↓ (no match)
3. Require Manual Approval (Human) → Manager reviews
```

---

## Option 1: AP2 Intent Mandates (Premium, Autonomous)

### What It Is
Pre-authorized constraints that allow an AI agent to automatically approve expenses without any human intervention.

### How It Works
1. User creates an **Intent Mandate** with constraints
2. Employee submits an expense
3. System checks if expense matches Intent Mandate
4. If match → **Instantly auto-approved** by `ai_agent`
5. Creates full AP2 audit trail (cart + payment mandates)
6. Processes payment through Stripe
7. Counts as 1 "used" mandate

### Constraints You Can Set
```json
{
  "max_amount": 100.00,           // Per-expense limit
  "monthly_limit": 1000.00,       // Monthly spending cap
  "categories": ["OFFICE_SUPPLIES", "SOFTWARE"],
  "merchants": ["Amazon", "Microsoft"],
  "merchant": "Amazon",            // Single merchant
  "category": "OFFICE_SUPPLIES",   // Single category
  "recurring": "monthly",          // Recurring purchases
  "expiration_hours": 720          // When mandate expires
}
```

### Valid Categories
- `OFFICE_SUPPLIES`
- `SOFTWARE`
- `TRAVEL`
- `MEALS`
- `ENTERTAINMENT`
- `UTILITIES`
- `MARKETING`
- `HARDWARE`
- `PROFESSIONAL_SERVICES`
- `OTHER`

### Example Use Cases
✅ "Auto-approve Amazon office supplies under $100/month"
✅ "Auto-approve Microsoft software purchases under $500"
✅ "Auto-approve recurring monthly subscriptions"
✅ "Auto-approve travel expenses from approved vendors"

### How to Create

**Via API:**
```bash
POST /api/ap2/intent-mandate
Authorization: Bearer {token}

{
  "constraints": {
    "max_amount": 100.00,
    "categories": ["OFFICE_SUPPLIES"],
    "merchants": ["Amazon"]
  },
  "expiration_hours": 720  // 30 days
}
```

**Via Frontend:**
- Navigate to AP2 section
- Click "Create Intent Mandate"
- Use ConstraintBuilder component
- Set constraints
- Set expiration date
- Submit

### Features
- ✅ Fully autonomous (no human needed)
- ✅ Cryptographic signatures (Cloud KMS)
- ✅ Immediate approval
- ✅ Complete audit trail
- ✅ Payment processing included
- ⚠️ Premium feature (uses AP2 transaction quota)

### Tier Limits
- **Free Tier**: 5 AP2 transactions/month
- **Pro Tier**: 50 AP2 transactions/month
- **Enterprise**: Unlimited

### When Expense is Approved
- Status: `approved`
- Approved by: `ai_agent`
- Auto-approved via: `intent_mandate`
- Intent Mandate ID: Linked
- Cart Mandate ID: Created
- Payment Mandate ID: Created

---

## Option 2: Approval Policies (Free, Automatic)

### What It Is
Organizational rules that automatically approve expenses based on category and amount limits.

### How It Works
1. Admin creates an **Approval Policy** with conditions
2. Employee submits an expense
3. System checks if expense matches policy
4. If match → **Instantly auto-approved** by `policy`
5. No AP2 mandates created
6. No payment processing
7. Free feature (no quota used)

### Conditions You Can Set
```json
{
  "name": "Meal Policy",
  "description": "Auto-approve meals under $50",
  "conditions": {
    "category": "MEALS",
    "max_amount": 50.00
  },
  "auto_approve": true
}
```

### Example Use Cases
✅ "Auto-approve meals under $50"
✅ "Auto-approve office supplies under $200"
✅ "Auto-approve travel expenses under $1000"
✅ "Auto-approve any expense under $25"

### How to Create

**Via API:**
```bash
POST /api/v1/approval-policies
Authorization: Bearer {token}
X-Organization-Id: {org_id}

{
  "name": "Meal Policy",
  "description": "Auto-approve meals under $50",
  "conditions": {
    "category": "MEALS",
    "max_amount": 50.00
  },
  "auto_approve": true
}
```

**Via Frontend:**
- Navigate to Admin Settings
- Go to "Approval Policies"
- Click "Create Policy"
- Set conditions
- Enable/disable auto-approve
- Submit

### Features
- ✅ Automatic approval
- ✅ Organizational efficiency
- ✅ No human needed
- ✅ Free feature (no quota)
- ✅ Simple to configure
- ⚠️ No payment processing
- ⚠️ No cryptographic audit trail

### When Expense is Approved
- Status: `approved`
- Approved by: `policy`
- Auto-approved via: `approval_policy`
- No AP2 mandates created

---

## Option 3: Manual Approval (Free, Human)

### What It Is
Traditional approval workflow where a manager or admin manually reviews and approves/rejects expenses.

### How It Works
1. Employee submits an expense
2. System checks AP2 → No match
3. System checks Policies → No match
4. Status set to: `PENDING`
5. Notification sent to approver
6. Manager reviews expense
7. Manager clicks "Approve" or "Reject"
8. Status updated accordingly

### When It's Triggered
- ❌ No Intent Mandate matches
- ❌ No Approval Policy matches
- ✅ Expense requires human oversight

### Features
- ✅ Human oversight and judgment
- ✅ Full review of expense details
- ✅ Free feature (no quota)
- ✅ Audit trail of approver
- ⚠️ Slower (depends on manager availability)
- ⚠️ Requires human action

### Approval Process

**For Managers/Admins:**

**Via API:**
```bash
# Approve
POST /api/v1/expenses/{expense_id}/approve
Authorization: Bearer {token}
X-Organization-Id: {org_id}

{
  "comments": "Approved - valid business expense"
}

# Reject
POST /api/v1/expenses/{expense_id}/reject
Authorization: Bearer {token}
X-Organization-Id: {org_id}

{
  "reason": "Missing receipt",
  "comments": "Please resubmit with proper documentation"
}
```

**Via Frontend:**
- Navigate to "Pending Expenses"
- Click on expense to review
- View details, receipt, description
- Click "Approve" or "Reject"
- Add comments (optional)
- Submit

### Who Can Approve
Based on role-based access control (RBAC):
- ✅ Organization Admin
- ✅ Manager role
- ✅ Users with `can_approve_expense` permission
- ❌ Regular employees cannot approve

### When Expense is Approved
- Status: `approved`
- Approved by: `{manager_name}`
- Approved at: `{timestamp}`
- Approval comments: Recorded

### When Expense is Rejected
- Status: `rejected`
- Rejected by: `{manager_name}`
- Rejected at: `{timestamp}`
- Rejection reason: Recorded
- Employee can resubmit after fixing issues

---

## Comparison Table

| Feature | AP2 Intent Mandate | Approval Policy | Manual Approval |
|---------|-------------------|-----------------|-----------------|
| **Speed** | Instant | Instant | Minutes to days |
| **Cost** | Premium (quota) | Free | Free |
| **Human Needed** | No | No | Yes |
| **Payment Processing** | Yes (Stripe) | No | No |
| **Audit Trail** | Cryptographic | Standard | Standard |
| **Flexibility** | Very high | Medium | Unlimited |
| **Use Case** | AI agent autonomy | Org efficiency | Complex/high-value |
| **Approved By** | `ai_agent` | `policy` | `manager_name` |
| **AP2 Transaction** | Yes (counts) | No | No |

---

## Current Configuration

### Active Intent Mandates
Run to check:
```bash
GET /api/ap2/user/mandates
Authorization: Bearer {token}
```

### Active Approval Policies
Run to check:
```bash
GET /api/v1/approval-policies
Authorization: Bearer {token}
X-Organization-Id: {org_id}
```

---

## How to Choose Which Option

### Use AP2 Intent Mandates When:
- ✅ You want fully autonomous AI agent approval
- ✅ You have predictable spending patterns
- ✅ You want instant approval with audit trail
- ✅ You want payment processing included
- ✅ You're okay with premium feature (uses quota)

**Example:** "My AI agent should auto-approve Amazon office supplies under $100 without asking me."

### Use Approval Policies When:
- ✅ You want organizational efficiency
- ✅ You have simple approval rules
- ✅ You want free auto-approval
- ✅ Amount limits are straightforward
- ✅ No payment processing needed

**Example:** "Always auto-approve meals under $50 for anyone in the org."

### Use Manual Approval When:
- ✅ Expense is high-value
- ✅ Expense is unusual or one-time
- ✅ Human judgment is required
- ✅ Expense doesn't match any policy
- ✅ Detailed review is needed

**Example:** "$5000 conference ticket - manager should review and decide."

---

## Configuration Examples

### Scenario 1: Small Team, Simple Rules

**Setup:**
- Approval Policy: Auto-approve < $50 any category
- Approval Policy: Auto-approve meals < $100
- Manual approval: Everything else

**Result:**
- 90% of expenses auto-approved (free)
- High-value expenses require review
- No AP2 quota needed

---

### Scenario 2: AI-First, Autonomous

**Setup:**
- Intent Mandate: Amazon office supplies < $200/month
- Intent Mandate: Microsoft software < $500/month
- Intent Mandate: Recurring subscriptions
- Approval Policy: Meals < $50
- Manual approval: Everything else

**Result:**
- Predictable expenses fully autonomous (AP2)
- Small expenses auto-approved (policy)
- Unusual expenses require review
- Uses AP2 quota for autonomous purchases

---

### Scenario 3: Strict Control

**Setup:**
- Approval Policy: None (disabled)
- Intent Mandate: None
- Manual approval: Everything

**Result:**
- All expenses require manager review
- Full human oversight
- Free (no quota)
- Slower approval process

---

## Best Practices

### 1. Start with Policies (Free)
- Create basic approval policies first
- Auto-approve common, low-value expenses
- See what patterns emerge

### 2. Add AP2 for Predictability
- Identify predictable spending patterns
- Create Intent Mandates for those patterns
- Enable autonomous approval for AI agents

### 3. Keep Manual as Fallback
- Always have manual approval as safety net
- High-value expenses go to human review
- Unusual expenses get human judgment

### 4. Monitor and Adjust
- Review auto-approval rates
- Adjust limits based on experience
- Refine constraints over time

---

## Testing Your Setup

```bash
# Test script
python test_complete_approval_flow.py

# This will test:
# 1. AP2 Intent Mandate approval
# 2. Approval Policy approval
# 3. Manual approval requirement
```

---

## Summary

You have **3 powerful approval options** working together:

1. **AP2 Intent Mandates** = Premium, autonomous, full audit trail
2. **Approval Policies** = Free, automatic, organizational efficiency
3. **Manual Approval** = Free, human oversight, unlimited flexibility

All three work in a **priority cascade**, checking from most autonomous to most manual, ensuring expenses are approved efficiently while maintaining appropriate oversight.
