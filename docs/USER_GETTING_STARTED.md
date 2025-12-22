# User Getting Started Guide

Welcome to **AP2 Expense Agent**! This guide will help you get started with submitting and managing your expenses.

---

## Table of Contents

1. [First Time Login](#first-time-login)
2. [Submitting Your First Expense](#submitting-your-first-expense)
3. [Uploading Receipts](#uploading-receipts)
4. [Tracking Expense Status](#tracking-expense-status)
5. [Editing Pending Expenses](#editing-pending-expenses)
6. [Common Questions](#common-questions)

---

## First Time Login

### Step 1: Access the Application

Navigate to your organization's AP2 Expense Agent URL:
- If deployed via Google Cloud Marketplace: Check your welcome email
- Typical format: `https://your-company.ap2expense.com`

### Step 2: Sign In

You have three options:

**Option A: Username & Password**
1. Enter your username
2. Enter your password (from welcome email)
3. Click "Sign In"

**Option B: Google Single Sign-On (SSO)**
1. Click "Sign in with Google"
2. Select your Google account
3. Grant permissions

**Option C: GitHub OAuth** (if enabled)
1. Click "Sign in with GitHub"
2. Authorize the application

### Step 3: First-Time Setup

After your first login, you'll be prompted to:

1. **Change your password** (if using username/password)
   - Click on your profile icon → "Change Password"
   - Enter current password
   - Enter new password (min 8 characters)
   - Confirm new password

2. **Set up Two-Factor Authentication (2FA)** - Optional but Recommended
   - Go to Profile → Security
   - Click "Enable 2FA"
   - Scan QR code with authenticator app (Google Authenticator, Authy)
   - Enter verification code
   - Save backup codes in a safe place

3. **Complete your profile**
   - Add your full name
   - Set your timezone
   - Add phone number (optional)

---

## Submitting Your First Expense

### Step 1: Navigate to Submit Expense

From the dashboard:
- Click **"Submit Expense"** button (top right)
- Or: Click **"Expenses"** in sidebar → **"New Expense"**

### Step 2: Fill Out Expense Details

**Required Fields:**

| Field | Description | Example |
|-------|-------------|---------|
| **Amount** | Total expense amount | 45.99 |
| **Vendor** | Where you made the purchase | "Office Depot" |
| **Category** | Type of expense | "Office Supplies" |
| **Date** | When the expense occurred | 2025-11-13 |
| **Description** | Brief explanation | "Printer paper and toner" |

**Available Categories:**
- Office Supplies
- Travel
- Meals & Entertainment
- Software & Subscriptions
- Equipment
- Professional Services
- Marketing
- Training & Education
- Other

### Step 3: Upload Receipt (Optional but Recommended)

1. Click **"Upload Receipt"** or drag and drop
2. Supported formats: PDF, JPEG, PNG
3. Maximum size: 10MB per file
4. You can upload multiple receipts per expense

**AI Receipt Scanning** (Professional tier and above):
- The system will automatically extract:
  - Amount
  - Date
  - Vendor name
  - Tax amount (if visible)
- Review and confirm the extracted data

### Step 4: Submit for Approval

1. Review all details
2. Click **"Submit Expense"**
3. You'll see a confirmation message
4. An email notification is sent to your manager/approver

**What happens next?**
- Your expense is now in "Pending" status
- Managers/approvers receive an email notification
- You'll receive an email when your expense is approved or rejected
- Typical approval time: 1-2 business days

---

## Uploading Receipts

### Best Practices for Receipt Photos

**Do:**
✅ Take photos in good lighting
✅ Ensure all text is readable
✅ Capture the entire receipt
✅ Keep photos straight (not tilted)
✅ Include vendor name, date, amount, and items

**Don't:**
❌ Submit blurry photos
❌ Cut off important information
❌ Submit receipts with glare
❌ Submit screenshots of receipts (upload original)

### How to Upload

**Method 1: Drag and Drop**
1. Open the expense form
2. Drag receipt file from your computer
3. Drop onto the upload area
4. Wait for upload confirmation

**Method 2: Browse Files**
1. Click "Upload Receipt" button
2. Select file from your computer
3. Click "Open"
4. Wait for upload confirmation

**Method 3: Mobile Upload** (if mobile app installed)
1. Tap expense
2. Tap camera icon
3. Take photo or select from gallery
4. Confirm and upload

### Multiple Receipts

If your expense has multiple receipts (e.g., hotel + meals during travel):
1. Upload first receipt
2. Click "Add Another Receipt"
3. Upload additional receipts
4. All receipts are linked to the same expense

---

## Tracking Expense Status

### Expense Statuses

| Status | Meaning | What You Can Do |
|--------|---------|-----------------|
| **Pending** | Awaiting approval | Edit, withdraw, or wait |
| **Approved** | Manager approved | View only, receipt available |
| **Rejected** | Not approved | View reason, resubmit if corrected |
| **Withdrawn** | You cancelled it | View only (archived) |

### View Your Expenses

**Dashboard View:**
- Shows recent expenses
- Quick status overview
- Total pending amount

**All Expenses View:**
1. Click "Expenses" in sidebar
2. Filter by status:
   - All Expenses
   - Pending
   - Approved
   - Rejected
3. Search by vendor, amount, or description
4. Sort by date, amount, or status

### Email Notifications

You'll receive emails for:
- ✅ Expense submitted (confirmation)
- ✅ Expense approved
- ❌ Expense rejected (with reason)
- 💬 Comment added to your expense
- ⚠️ Expense needs additional information

**Email Settings:**
- Go to Profile → Notifications
- Enable/disable email notifications
- Set notification preferences

---

## Editing Pending Expenses

You can edit expenses while they're in "Pending" status.

### Steps to Edit

1. Go to "Expenses" → Find your pending expense
2. Click on the expense
3. Click **"Edit"** button
4. Make your changes:
   - Update amount
   - Change vendor
   - Modify description
   - Add/remove receipts
   - Change category
5. Click **"Save Changes"**

**Important Notes:**
- ⚠️ You cannot edit approved or rejected expenses
- ⚠️ Editing an expense does NOT reset the approval process
- ⚠️ Managers see edit history in audit logs

### Withdrawing an Expense

If you submitted an expense by mistake:

1. Open the expense
2. Click **"Withdraw"** button
3. Confirm withdrawal
4. Status changes to "Withdrawn"

**Notes:**
- You can only withdraw pending expenses
- Withdrawn expenses are archived (not deleted)
- You can view withdrawn expenses in the history

---

## Common Questions

### Q: How long does approval take?
**A:** Typically 1-2 business days. Check with your manager for specific timelines.

### Q: What if my expense is rejected?
**A:** You'll receive an email with the rejection reason. You can:
1. View the rejection reason in the expense details
2. Correct the issue
3. Submit a new expense with corrected information
4. Contact your manager for clarification

### Q: Can I submit expenses in bulk?
**A:** Yes! Managers and admins can use batch operations:
- Upload CSV with multiple expenses
- Use the API for programmatic submission
- Contact support for bulk import assistance

### Q: What if I don't have a receipt?
**A:**
- Small expenses (under $25): Often allowed without receipt (check policy)
- Lost receipts: Add note in description, manager may approve
- Digital receipts: Forward email receipt to your AP2 email address

### Q: How do I export my expense history?
**A:**
1. Go to "Expenses" → "Reports"
2. Select date range
3. Click "Export"
4. Choose format: CSV, Excel, or PDF
5. Download file

### Q: Can I submit expenses on behalf of someone else?
**A:** No, each user must submit their own expenses. Managers can approve but not submit for others.

### Q: What's the maximum expense amount I can submit?
**A:** This depends on your organization's approval policies:
- Ask your manager or HR
- Check the "Approval Policies" page in settings
- Typical limits:
  - Employee: Self-approve up to $50
  - Manager: Approve up to $1,000
  - Admin: Approve unlimited

### Q: How do I add comments to an expense?
**A:**
1. Open the expense
2. Scroll to "Comments" section
3. Type your comment
4. Click "Add Comment"
5. Relevant parties receive email notification

### Q: What if the AI categorizes my expense incorrectly?
**A:** Simply change the category manually:
1. Edit the expense
2. Select correct category from dropdown
3. Save changes
4. AI learns from corrections over time

### Q: Can I submit recurring expenses?
**A:** Yes! (Professional tier and above)
1. Go to "Expenses" → "Recurring"
2. Click "New Recurring Expense"
3. Set frequency (weekly, monthly, quarterly, yearly)
4. Expenses are auto-created on schedule

### Q: How secure is my receipt data?
**A:**
- All receipts encrypted at rest (AES-256)
- Transmitted over TLS 1.3
- Access logs tracked
- GDPR compliant
- See [Privacy Policy](../legal/PRIVACY_POLICY.md) for details

---

## Need More Help?

### Documentation Resources
- 📖 [API Integration Guide](API_INTEGRATION_GUIDE.md) - For developers
- 🔧 [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues
- 🔐 [Security & Compliance](../SECURITY.md) - Security information
- 📊 [Admin Guide](ADMIN_CUSTOMIZATION_GUIDE.md) - For administrators

### Contact Support
- **Email**: support@ap2expense.com
- **Response Time**:
  - Starter: 48 hours
  - Professional: 24 hours
  - Enterprise: 4 hours
- **Knowledge Base**: https://docs.ap2expense.com
- **Community Forum**: https://community.ap2expense.com

---

**Happy Expense Tracking!** 🎉

*Last Updated: November 2025*
*Version: 1.0*
