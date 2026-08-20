# Auto-Approval System Guide

**Last Updated:** 2026-01-04

## Overview

The AP2 Expense Agent includes a powerful **policy-based auto-approval system** that automatically approves expenses matching pre-configured rules. This reduces admin workload and speeds up expense processing.

---

## Features

### ✅ What Can Be Automated

- **Amount-based approval** (e.g., auto-approve under $50)
- **Category restrictions** (e.g., only Meals and Travel)
- **Vendor whitelists** (e.g., pre-approved vendors)
- **User/role-based rules** (e.g., trust certain employees)
- **Time restrictions** (e.g., only business hours)
- **Spending limits** (daily/monthly/yearly caps per user)
- **Budget compliance** (won't exceed budgets)
- **Multiple policies with priorities**

### ❌ What Stays Manual

- Expenses exceeding policy limits
- Expenses from excluded vendors
- Expenses outside allowed categories
- Expenses submitted outside allowed times
- Expenses that would exceed budgets

---

## Example Policies

### Example 1: Small Expenses Auto-Approval
**Use Case:** Automatically approve small expenses under $50

```json
{
  "name": "Small Expenses",
  "priority": 100,
  "auto_approve": true,
  "max_amount_per_expense": 50.00,
  "daily_limit_per_user": 200.00,
  "monthly_limit_per_user": 1000.00,
  "conditions": {
    "categories": ["MEALS", "OFFICE_SUPPLIES", "PARKING"]
  }
}
```

**Result:**
- ✅ Auto-approves: $45 lunch, $30 office supplies, $15 parking
- ❌ Requires manual: $75 dinner (exceeds $50)
- ❌ Blocks: 5th expense today totaling $205 (exceeds daily limit)

---

### Example 2: Pre-Approved Vendors
**Use Case:** Auto-approve specific trusted vendors

```json
{
  "name": "Trusted Vendors",
  "priority": 200,
  "auto_approve": true,
  "max_amount_per_expense": 500.00,
  "conditions": {
    "vendors": ["Amazon", "Staples", "FedEx", "Delta Airlines"],
    "categories": ["OFFICE_SUPPLIES", "SHIPPING", "TRAVEL"]
  }
}
```

**Result:**
- ✅ Auto-approves: $300 Amazon office supplies
- ✅ Auto-approves: $450 Delta flight
- ❌ Requires manual: $600 Amazon purchase (exceeds $500)
- ❌ Requires manual: $50 from unknown vendor

---

### Example 3: Executive Fast-Track
**Use Case:** Auto-approve most expenses for trusted executives

```json
{
  "name": "Executive Auto-Approval",
  "priority": 300,
  "auto_approve": true,
  "max_amount_per_expense": 2000.00,
  "monthly_limit_per_user": 10000.00,
  "conditions": {
    "user_roles": ["admin"],
    "exclude_vendors": ["Cash Advance", "Personal Reimbursement"]
  }
}
```

**Result:**
- ✅ Auto-approves: $1,500 executive travel
- ✅ Auto-approves: $800 client dinner
- ❌ Requires manual: $2,500 conference (exceeds $2,000)
- ❌ Blocks: Cash advance (excluded vendor)

---

### Example 4: Business Hours Only
**Use Case:** Only auto-approve during work hours to prevent fraud

```json
{
  "name": "Business Hours Approval",
  "priority": 50,
  "auto_approve": true,
  "max_amount_per_expense": 100.00,
  "conditions": {
    "time_range": {
      "start": "09:00",
      "end": "17:00"
    },
    "days_of_week": [0, 1, 2, 3, 4],  // Monday-Friday
    "categories": ["MEALS", "PARKING", "FUEL"]
  }
}
```

**Result:**
- ✅ Auto-approves: $45 lunch at 12:30 PM Tuesday
- ❌ Requires manual: $45 lunch at 8:00 PM (outside hours)
- ❌ Requires manual: $30 parking on Saturday

---

### Example 5: Budget-Aware Approval
**Use Case:** Auto-approve only if within budget

```json
{
  "name": "Budget Compliant",
  "priority": 150,
  "auto_approve": true,
  "max_amount_per_expense": 300.00,
  "conditions": {
    "require_budget_compliance": true,
    "categories": ["MARKETING", "ADVERTISING"]
  }
}
```

**Result:**
- ✅ Auto-approves: $200 Facebook ads (budget has $500 left)
- ❌ Requires manual: $250 Google ads (would exceed $300 budget)

---

## How to Create Policies

### Via API

```bash
POST /api/v1/approval-policies
Authorization: Bearer {admin_token}

{
  "name": "Small Expenses Auto-Approval",
  "description": "Auto-approve small daily expenses",
  "priority": 100,
  "auto_approve": true,
  "max_amount_per_expense": 50.00,
  "daily_limit_per_user": 200.00,
  "monthly_limit_per_user": 1000.00,
  "conditions": {
    "categories": ["MEALS", "PARKING", "OFFICE_SUPPLIES"]
  }
}
```

### Via Frontend (Admin Dashboard)

1. Login as Admin
2. Go to Settings → Approval Policies
3. Click "Create Policy"
4. Configure:
   - Policy name and description
   - Priority (higher = checked first)
   - Amount limits
   - Category restrictions
   - User/vendor filters
   - Time restrictions
   - Spending limits
5. Click "Save"

---

## Policy Priority System

Policies are evaluated in **descending priority order** (highest first):

```
Priority 300: Executive Fast-Track (admins only)
  ↓ (if doesn't match, try next)
Priority 200: Trusted Vendors
  ↓ (if doesn't match, try next)
Priority 150: Budget Compliant
  ↓ (if doesn't match, try next)
Priority 100: Small Expenses
  ↓ (if doesn't match, try next)
Priority 50: Business Hours Only
  ↓ (if no matches)
MANUAL APPROVAL REQUIRED
```

**Best Practice:** Higher priority for more specific/restrictive policies.

---

## Testing Policies

### Test API Endpoint

Before creating a policy, test if it would work:

```bash
POST /api/v1/approval-policies/test

{
  "amount": 75.00,
  "category": "MEALS",
  "vendor": "Chipotle",
  "has_receipt": true
}
```

**Response:**
```json
{
  "would_auto_approve": true,
  "matching_policy": {
    "id": "policy_123",
    "name": "Small Expenses",
    "priority": 100
  },
  "reason": "Matched policy: Small Expenses",
  "remaining_limits": {
    "daily_remaining": 125.00,
    "monthly_remaining": 925.00
  }
}
```

---

## Monitoring Auto-Approvals

### View Auto-Approved Expenses

```bash
GET /api/v1/expenses?auto_approved=true
```

### Check Policy Usage

```bash
GET /api/v1/approval-policies/{policy_id}/stats
```

Returns:
- Total expenses auto-approved
- Total amount auto-approved
- Average approval time
- Top categories/vendors

---

## Security & Audit Trail

### Every Auto-Approval Records:
- ✅ Which policy approved it
- ✅ Timestamp of approval
- ✅ User who submitted
- ✅ Approval criteria matched
- ✅ Limits checked

### Audit Query:
```sql
SELECT
  e.id,
  e.amount,
  e.category,
  e.vendor,
  e.approved_at,
  ap.name as policy_name,
  u.full_name as submitter
FROM expenses e
JOIN approval_policies ap ON e.approval_policy_id = ap.id
JOIN users u ON e.user_id = u.id
WHERE e.auto_approved = true
ORDER BY e.approved_at DESC;
```

---

## Best Practices

### 1. Start Conservative
Begin with:
- Low amount limits ($50)
- Specific categories only
- Daily/monthly caps
- Business hours restrictions

### 2. Review Regularly
- Check auto-approved expenses weekly
- Adjust limits based on patterns
- Remove unused policies

### 3. Layer Policies
Create multiple policies for different scenarios:
- Small expenses (low priority, broad)
- Trusted vendors (medium priority, specific)
- Executive approvals (high priority, selective)

### 4. Use Exclusions
Rather than listing allowed vendors, sometimes it's easier to exclude problematic ones:
```json
{
  "conditions": {
    "exclude_vendors": ["Cash", "Personal Reimbursement", "Petty Cash"]
  }
}
```

### 5. Monitor Limits
Set up alerts when users approach their limits:
- 80% of daily limit
- 90% of monthly limit
- Approaching yearly cap

---

## Advanced Features

### Conditional Approval (Future Enhancement)
Coming in v1.2:
- Auto-approve pending receipt upload
- Re-evaluate policies after receipt attached
- Conditional approval workflows

### AI-Powered Policies (Roadmap)
- Learn from manual approvals
- Suggest policy improvements
- Detect anomalies automatically

---

## Troubleshooting

### Policy Not Working?

**Check:**
1. ✅ Policy is **active** (`is_active: true`)
2. ✅ Policy has **auto_approve** enabled
3. ✅ Priority is high enough (conflicts with other policies?)
4. ✅ User hasn't exceeded limits
5. ✅ Category/vendor matches exactly (case-sensitive)
6. ✅ Time restrictions met (if configured)

### Debugging Auto-Approval

View logs:
```bash
grep "auto-approved" backend/logs/app.log | tail -20
```

Look for:
```
INFO: Expense exp_123 auto-approved by policy policy_456 (Small Expenses)
INFO: Expense exp_124 matched policy policy_456 but exceeded limits: Would exceed daily limit of $200
```

---

## Configuration Examples

### Startup Company (Lean & Fast)
```json
[
  {
    "name": "Most Expenses Auto",
    "priority": 100,
    "max_amount_per_expense": 500,
    "monthly_limit_per_user": 2000,
    "auto_approve": true
  }
]
```

### Corporate (Strict Controls)
```json
[
  {
    "name": "Small Only",
    "priority": 100,
    "max_amount_per_expense": 50,
    "daily_limit_per_user": 100,
    "conditions": {
      "categories": ["MEALS", "PARKING"],
      "time_range": {"start": "09:00", "end": "17:00"},
      "days_of_week": [0, 1, 2, 3, 4]
    }
  },
  {
    "name": "Pre-Approved Vendors",
    "priority": 200,
    "max_amount_per_expense": 200,
    "conditions": {
      "vendors": ["Amazon", "Staples"]
    }
  }
]
```

---

## API Reference

### Create Policy
```http
POST /api/v1/approval-policies
Content-Type: application/json
Authorization: Bearer {admin_token}

{
  "name": "string",
  "description": "string",
  "priority": 0-1000,
  "auto_approve": true,
  "require_receipt": true,
  "notify_on_auto_approve": true,
  "max_amount_per_expense": number,
  "daily_limit_per_user": number,
  "monthly_limit_per_user": number,
  "yearly_limit_per_user": number,
  "conditions": {
    "categories": ["CATEGORY1", "CATEGORY2"],
    "vendors": ["Vendor1", "Vendor2"],
    "exclude_vendors": ["BadVendor"],
    "user_ids": ["user_123"],
    "user_roles": ["admin"],
    "time_range": {"start": "HH:MM", "end": "HH:MM"},
    "days_of_week": [0-6],
    "require_budget_compliance": true
  }
}
```

### List Policies
```http
GET /api/v1/approval-policies
Authorization: Bearer {token}
```

### Update Policy
```http
PUT /api/v1/approval-policies/{id}
Content-Type: application/json
Authorization: Bearer {admin_token}

{
  "is_active": false,  // Disable policy
  "max_amount_per_expense": 75.00  // Update limit
}
```

### Delete Policy
```http
DELETE /api/v1/approval-policies/{id}
Authorization: Bearer {admin_token}
```

### Test Policy
```http
POST /api/v1/approval-policies/test
Content-Type: application/json
Authorization: Bearer {token}

{
  "amount": 50.00,
  "category": "MEALS",
  "vendor": "Chipotle",
  "has_receipt": true
}
```

---

## Summary

Your auto-approval system provides:

✅ **Flexibility** - Multiple policies with priorities
✅ **Control** - Granular limits and conditions
✅ **Security** - Full audit trail and limits
✅ **Efficiency** - Instant approvals for qualifying expenses
✅ **Compliance** - Budget and policy enforcement

**Result:** Admins spend less time on trivial approvals, users get faster reimbursements, and the company maintains control and compliance.
