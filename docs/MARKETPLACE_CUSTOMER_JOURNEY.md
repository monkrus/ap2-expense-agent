# Google Cloud Marketplace Customer Journey
## How Companies Purchase and Use AP2 Expense Agent

This document explains the complete customer journey from discovery to daily usage of the AP2 Expense Agent on Google Cloud Marketplace.

---

## 📋 Table of Contents

1. [Discovery & Purchase](#1-discovery--purchase)
2. [Deployment & Setup](#2-deployment--setup)
3. [Organization Onboarding](#3-organization-onboarding)
4. [Daily Operations](#4-daily-operations)
5. [Billing & Usage](#5-billing--usage)
6. [Support & Upgrades](#6-support--upgrades)

---

## 1. Discovery & Purchase

### Step 1.1: Company Discovers the App

**Where:** Google Cloud Marketplace (console.cloud.google.com/marketplace)

**Search Methods:**
- Browse "AI Agents" category
- Search: "expense management", "AP2 protocol", "AI expense tracking"
- Recommended by Google (if AI/finance tools)

**What They See:**
- Product listing page with screenshots
- Pricing tiers ($29, $99, $399, Custom)
- Feature comparison
- Customer reviews
- "14-Day Free Trial" button

### Step 1.2: Evaluate the Product

**Free Trial (No Credit Card Required):**
```
Click "Start Free Trial" →
Select Google Cloud Project →
Choose Tier (defaults to Professional) →
Agree to Terms of Service →
Click "Subscribe"
```

**What Happens:**
1. Google creates a **Procurement Account** (entitlement)
2. Your app receives a webhook: `POST /api/webhooks/gcp/procurement`
3. Backend creates:
   - Organization record
   - Admin user (from GCP IAM)
   - 14-day trial subscription
4. User receives email: "Welcome to AP2 Expense Agent"

### Step 1.3: Purchase Decision

**After Trial or During Trial:**

**Option A: Continue with Free Trial → Paid**
- Trial ends after 14 days
- Auto-converts to paid subscription
- Google charges customer's Cloud Billing account
- No interruption in service

**Option B: Upgrade Tier During Trial**
- User clicks "Upgrade" in app or marketplace
- Selects higher tier (e.g., Professional → Enterprise)
- Google updates entitlement
- App receives webhook, updates subscription
- New features unlock immediately

**Option C: Cancel**
- User cancels in GCP Marketplace
- Grace period: 7 days
- Data exported (if requested)
- Account deactivated

---

## 2. Deployment & Setup

### Step 2.1: Google Provisions Infrastructure

**Automatic Deployment (User doesn't see this):**

```
Google Cloud Marketplace → Cloud Run Deployment
├── Backend Service (gcr.io/ap2-expense/backend:latest)
│   ├── Min Instances: 1
│   ├── Max Instances: 100
│   ├── Memory: 2Gi
│   └── CPU: 2
│
├── Frontend Service (gcr.io/ap2-expense/frontend:latest)
│   ├── Min Instances: 1
│   ├── Max Instances: 50
│   ├── Memory: 512Mi
│   └── CPU: 1
│
├── Cloud SQL (PostgreSQL 15)
│   ├── Tier: db-custom-2-8192
│   ├── Storage: 100GB
│   ├── Backups: Daily
│   └── High Availability: Enabled
│
├── Secret Manager
│   ├── JWT_SECRET
│   ├── DATABASE_URL
│   └── STRIPE_API_KEY
│
└── Cloud Storage
    └── Bucket: {org-id}-receipts
```

**Time to Deploy:** 3-5 minutes

**Result:**
- Frontend URL: `https://ap2-expense-{random}.run.app`
- Backend API: `https://ap2-expense-backend-{random}.run.app`
- Database: Fully configured and migrated

### Step 2.2: Customer Receives Access

**Email Notification:**
```
Subject: Your AP2 Expense Agent is Ready!

Hi [Customer],

Your AP2 Expense Agent has been deployed successfully!

🔗 Access your app: https://ap2-expense-abc123.run.app
📧 Login with: your-gcp-account@company.com
🔑 Password: Check your email for temporary password

Next Steps:
1. Log in and change your password
2. Invite your team members
3. Configure approval workflows
4. Start submitting expenses!

Need help? Visit: docs.ap2expense.com/quickstart
```

---

## 3. Organization Onboarding

### Step 3.1: Admin First Login

**What Admin Sees:**

```
Login Screen
└── Option 1: Google Workspace SSO (if Enterprise tier)
└── Option 2: Email + Password + 2FA

After Login:
└── Welcome Screen
    ├── "Complete Setup" (5 steps)
    ├── Organization Profile
    ├── Team Invites
    ├── Approval Workflows
    └── Payment Methods
```

### Step 3.2: Organization Configuration

**Step 1: Organization Profile**
```
Company Name: Acme Corp
Industry: Technology
Size: 100-250 employees
Fiscal Year: Calendar Year
Currency: USD
Timezone: America/New_York
```

**Step 2: Invite Team Members**
```
Bulk Upload CSV:
email,role,department
john@acme.com,employee,Engineering
sarah@acme.com,manager,Engineering
mike@acme.com,accountant,Finance
jane@acme.com,admin,HR
```

**What Happens:**
- System sends invitation emails
- Users click link → Set password → Access app
- Usage metrics start tracking (seats/users)

**Step 3: Configure Approval Workflows**
```
Rule 1: Expenses < $50 → Auto-approve
Rule 2: Expenses $50-$500 → Manager approval
Rule 3: Expenses > $500 → Manager + Accountant approval
Rule 4: Travel expenses → Always require receipt
```

**Step 4: Connect Payment Methods**
```
Option 1: Stripe (for AP2 automated payments)
Option 2: Corporate Card (for manual processing)
Option 3: Crypto Wallet (via AP2 protocol)
```

**Step 5: Customize Settings**
```
- Expense categories (Travel, Meals, Software, etc.)
- Receipt requirements
- Notification preferences
- Data retention policies
```

---

## 4. Daily Operations

### How Employees Use the App

#### Scenario 1: Employee Submits Expense

**Method A: Manual Entry**
```
1. Employee logs in
2. Clicks "New Expense"
3. Fills form:
   - Amount: $45.00
   - Vendor: Starbucks
   - Category: Meals & Entertainment
   - Description: Client meeting
   - Date: 2025-10-30
4. Uploads receipt photo (JPG/PNG/PDF)
5. Clicks "Submit"
```

**What Happens (Backend):**
```python
# 1. AI analyzes receipt (OCR)
receipt_data = ai_vision.extract_receipt(image)
# → Amount: $45.00, Vendor: Starbucks, Date: 2025-10-30

# 2. AI categorizes expense
category = ai_agent.categorize(receipt_data)
# → Category: "Meals & Entertainment" (95% confidence)

# 3. Check for duplicates
if duplicate_detector.check(receipt_data):
    flag_as_duplicate()

# 4. Apply workflow rules
if amount < 50:
    auto_approve()
else:
    send_to_manager()

# 5. Track usage (for billing)
billing.track_usage(org_id, "ai_categorization", 1)
billing.track_usage(org_id, "ocr_scan", 1)
```

**Method B: Receipt Upload (AI Does Everything)**
```
1. Employee drags receipt image to upload area
2. AI extracts ALL data automatically:
   ✓ Amount
   ✓ Vendor
   ✓ Date
   ✓ Category
   ✓ Tax amount
3. Employee reviews and clicks "Confirm"
```

**Method C: Email Forward**
```
Employee forwards receipt email to:
expenses@ap2-expense-abc123.run.app

AI parses email, extracts receipt, creates expense
Employee gets notification: "Expense created, review here"
```

#### Scenario 2: Manager Approves Expense

**Manager's Workflow:**
```
1. Manager receives notification (email/Slack/in-app)
2. Logs in → "Pending Approvals" (5 items)
3. Reviews expense:
   - Employee: John Smith
   - Amount: $450.00
   - Vendor: Delta Airlines
   - Receipt: ✓ Attached
   - AI Analysis: ✓ Valid business expense
   - Policy Compliance: ✓ Passed
4. Clicks "Approve"
```

**What Happens (AP2 Protocol):**
```
Step 1: Create Intent Mandate
└── User: john@acme.com authorized by manager@acme.com
└── Constraints: max $450, vendor "Delta", category "Travel"
└── Signature: [cryptographic signature]

Step 2: Create Cart Mandate
└── Items: [Flight to NYC - $450.00]
└── Total: $450.00
└── User Signature: [manager approval signature]

Step 3: Create Payment Mandate
└── Payment Method: Stripe/Corporate Card
└── Status: Pending execution
└── Audit Trail: {intent_id, cart_id, approver_id}

Step 4: Execute Payment (if automated)
└── Stripe charges corporate card
└── Payment Mandate: Completed
└── Notification sent to employee & accountant
```

**Result:**
- Expense status → "Approved"
- Payment processed (if AP2 automated)
- Audit trail created (tamper-proof)
- Usage tracked: 1 AP2 transaction

#### Scenario 3: Accountant Reviews & Exports

**Monthly Close Process:**
```
1. Accountant logs in
2. Goes to "Reports" → "Monthly Expenses"
3. Filters:
   - Date Range: Oct 1-31, 2025
   - Status: Approved
   - Department: All
4. Reviews totals:
   - Total Expenses: $45,231.00
   - By Category:
     - Travel: $12,450
     - Meals: $8,200
     - Software: $15,000
     - Office Supplies: $3,500
     - Other: $6,081
5. Clicks "Export to QuickBooks"
```

**Export Options:**
- CSV (all accounting systems)
- QuickBooks Online (direct integration)
- PDF Report (for auditors)
- Excel with pivot tables

---

## 5. Billing & Usage

### How Google Cloud Marketplace Charges Customers

#### Monthly Billing Cycle

**Example: Professional Tier ($99/month) for Acme Corp**

```
Billing Period: Oct 1-31, 2025

Base Subscription: $99.00
├── Up to 100 users ✓ (currently 45 users)
├── Unlimited expenses ✓ (submitted 342 expenses)
├── AI categorizations: 5,000 included
└── AP2 transactions: 100 included

Usage This Month:
├── AI Categorizations: 6,234 (1,234 over limit)
│   └── Overage: 1,234 × $0.05 = $61.70
├── AP2 Transactions: 127 (27 over limit)
│   └── Overage: 27 × $0.10 = $2.70
└── OCR Scans: 423 (all included)

Total Invoice: $99.00 + $61.70 + $2.70 = $163.40

Charged to: Google Cloud Billing Account
Payment Date: Nov 1, 2025
```

**Where Customer Sees This:**
1. GCP Console → Billing → Transactions
2. AP2 Expense App → Settings → Billing
3. Monthly email: "Your October Invoice"

### Usage Tracking & Reporting (Real-Time)

**Backend Tracks Every Action:**

```python
# When expense is categorized by AI
billing_service.track_usage(
    organization_id="org_acme",
    metric_type="ai_categorization",
    quantity=1
)

# When AP2 transaction is completed
billing_service.track_usage(
    organization_id="org_acme",
    metric_type="ap2_transaction",
    quantity=1
)

# Every hour: Report to Google
billing_service.report_to_gcp_marketplace(
    organization_id="org_acme",
    metrics={
        "ai_categorization": 6234,
        "ap2_transaction": 127,
        "active_users": 45
    }
)
```

**Google's Backend:**
```
Receives usage reports via API
├── Validates against entitlement
├── Calculates overage charges
├── Updates invoice
└── Sends to customer's billing account
```

### Customer Can Monitor Usage

**In the App:**
```
Settings → Billing Dashboard

Current Period: Oct 1-31
Tier: Professional ($99/month)

Usage Summary:
├── Users: 45/100 (45% capacity)
├── Expenses: 342 (unlimited ✓)
├── AI Categorizations: 6,234/5,000 (overage: 1,234)
│   └── Estimated overage charge: $61.70
├── AP2 Transactions: 127/100 (overage: 27)
│   └── Estimated overage charge: $2.70
└── OCR Scans: 423/1,000 (42% used)

Projected Month-End Total: ~$165.00

💡 Tip: Upgrade to Enterprise tier to eliminate overage charges!
   Enterprise: Unlimited AI categorizations for $399/month
   Current Pace: Would save $42.70/month
```

---

## 6. Support & Upgrades

### Customer Support Channels

**By Tier:**

**Starter ($29/month):**
- Email support: support@ap2expense.com
- Response time: 48 hours
- Documentation: docs.ap2expense.com
- Community forum

**Professional ($99/month):**
- Email support (24-hour response)
- Live chat (business hours)
- Video tutorials
- Priority bug fixes

**Enterprise ($399/month):**
- Email + Phone + Chat (4-hour response)
- Dedicated Slack channel
- Quarterly business reviews
- Custom integrations support

**Enterprise Plus (Custom):**
- 24/7 phone support (1-hour response)
- Dedicated account manager
- On-site training available
- Custom feature development

### Upgrading/Downgrading Tiers

**Customer Initiates:**

```
In App: Settings → Subscription → Upgrade to Enterprise

Or

GCP Marketplace:
└── My Products → AP2 Expense Agent → Manage → Change Plan
```

**What Happens:**
1. User selects new tier
2. Google updates entitlement
3. Webhook sent to your app: `POST /api/webhooks/gcp/entitlement-updated`
4. App updates subscription immediately
5. New features unlock in real-time
6. Prorated billing automatically calculated by Google

**Example Proration:**
```
Oct 15: Upgrade from Professional ($99) to Enterprise ($399)

Remaining days in October: 16 days
Daily rate difference: ($399 - $99) / 30 = $10/day
Prorated charge: $10 × 16 = $160

Oct 31 Invoice:
├── Professional (Oct 1-14): $99 × 14/30 = $46.20
├── Enterprise (Oct 15-31): $399 × 16/30 = $212.80
├── Overage charges: $64.40
└── Total: $323.40
```

---

## 7. Technical Integration Flow

### Behind the Scenes: Google ↔ Your App

#### Initial Purchase Flow

```mermaid
Customer → Google Marketplace: Subscribe
Google → Your App: POST /api/webhooks/gcp/procurement
                   {
                     "entitlement_id": "ent_abc123",
                     "account_id": "acct_456",
                     "plan": "professional",
                     "state": "ACTIVE"
                   }
Your App → Database: Create organization + admin user
Your App → Email Service: Send welcome email
Your App → Google: 200 OK {organization_id: "org_789"}
Google → Customer: Deployment complete, access link
```

#### Daily Usage Reporting

```mermaid
Every Hour:
Your App → Aggregates usage metrics
Your App → Google API: POST /v1/usage
                       {
                         "entitlement_id": "ent_abc123",
                         "metrics": {
                           "ai_categorization": 125,
                           "ap2_transaction": 8,
                           "active_users": 45
                         }
                       }
Google → Billing Engine: Calculate charges
Google → Customer Invoice: Update amount
```

#### Customer Cancellation

```mermaid
Customer → GCP Marketplace: Cancel subscription
Google → Your App: POST /api/webhooks/gcp/entitlement-cancelled
Your App → Database: Mark subscription as "cancelled"
Your App → Email: Send cancellation confirmation
Your App → Data Export: Generate data export (7-day retention)
Your App → Google: 200 OK
(After 7 days)
Your App → Database: Soft-delete organization data
```

---

## Summary: Customer Journey Timeline

### Day 0: Purchase
- 9:00 AM: Customer finds app in marketplace
- 9:15 AM: Starts free trial
- 9:20 AM: App deployed, welcome email sent

### Days 1-3: Onboarding
- Admin configures organization
- Invites team members (45 users)
- Sets up approval workflows
- Connects Stripe payment method

### Days 4-14: Trial Usage
- Team submits 50 expenses
- AI categorizes automatically (50 categorizations tracked)
- Managers approve 45 expenses
- 3 AP2 automated payments processed
- Usage visible in real-time dashboard

### Day 15: Trial Ends → Paid
- Auto-converts to Professional tier ($99/month)
- First invoice: $99.00 (no overage yet)
- Charged to GCP billing account
- Email: "Your subscription is now active"

### Days 15-30: Full Operations
- Team fully adopted the system
- 342 expenses submitted (usage tracked)
- 127 AP2 transactions (27 overage × $0.10)
- 6,234 AI categorizations (1,234 overage × $0.05)

### Day 31: Month-End Billing
- Invoice: $99 + $2.70 + $61.70 = $163.40
- Usage report emailed to admin
- Suggestion: "Upgrade to Enterprise to save on overages"

### Day 60: Upgrade to Enterprise
- Admin clicks "Upgrade"
- Instant unlock: Unlimited AI & AP2
- Prorated billing applied
- New features: SSO, custom integrations

### Ongoing:
- Monthly billing continues automatically
- Usage tracked and reported hourly
- Support tickets resolved per SLA
- Quarterly business review (Enterprise tier)

---

## Key Takeaways for You as the Developer

1. **Google Handles:**
   - Customer billing & payment collection
   - Infrastructure provisioning (Cloud Run, Cloud SQL)
   - SSL certificates & domain management
   - DDoS protection & global CDN
   - Legal contracts & compliance

2. **Your App Handles:**
   - User authentication & authorization
   - Expense workflow logic
   - AI processing (OCR, categorization, fraud detection)
   - AP2 protocol implementation
   - Usage tracking & reporting to Google
   - Customer support (via your team)

3. **Integration Points:**
   - Webhook: `/api/webhooks/gcp/procurement` (new customer)
   - Webhook: `/api/webhooks/gcp/entitlement-updated` (tier change)
   - Webhook: `/api/webhooks/gcp/entitlement-cancelled` (cancellation)
   - API: Report usage to Google hourly
   - API: Validate entitlements before allowing features

4. **Revenue Flow:**
   ```
   Customer pays Google → Google takes 20% fee → You receive 80%
   Example: $99/month tier
   ├── Customer pays: $99.00
   ├── Google fee (20%): $19.80
   └── You receive: $79.20

   Plus usage overages (you get 80% of those too)
   ```

5. **Critical Success Factors:**
   - Fast onboarding (<10 minutes from purchase to first use)
   - Accurate usage tracking (no disputes)
   - Responsive support (SLA compliance)
   - Regular feature updates (keep customers engaged)
   - Clear upgrade path (trial → paid → enterprise)

---

**This is exactly how your AP2 Expense Agent will work on Google Cloud Marketplace!**
