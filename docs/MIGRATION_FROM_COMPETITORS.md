# Migration Guide - Switching to AP2 Expense Agent

Complete guide for migrating from Expensify, Concur, or other expense management systems.

---

## Table of Contents

1. [Overview](#overview)
2. [Migration from Expensify](#migration-from-expensify)
3. [Migration from Concur SAP](#migration-from-concur-sap)
4. [Migration from Zoho Expense](#migration-from-zoho-expense)
5. [Generic CSV Import](#generic-csv-import)
6. [User Account Migration](#user-account-migration)
7. [Receipt Transfer](#receipt-transfer)
8. [Testing Your Migration](#testing-your-migration)
9. [Go-Live Checklist](#go-live-checklist)

---

## Overview

### Migration Timeline

**Typical migration takes 1-2 weeks:**
- Week 1: Data export, cleanup, and import
- Week 2: User onboarding and parallel testing

### What Gets Migrated

✅ **Migrated:**
- Historical expense data
- User accounts (email-based matching)
- Receipt attachments
- Approval workflows (recreated)
- Categories (mapped to AP2 categories)

⚠️ **Not Migrated:**
- Payment history (stays in old system for audit)
- Custom integrations (rebuilt in AP2)
- Old system users/permissions (recreated)

### Prerequisites

Before starting:
- [ ] Admin access to current expense system
- [ ] List of all active users (emails)
- [ ] Approval workflow documentation
- [ ] Budget/policy configurations
- [ ] Export window selected (recommend last 12 months)

---

## Migration from Expensify

### Step 1: Export Data from Expensify

**Export Expenses:**
1. Login to Expensify as admin
2. Go to **Reports** → **All Reports**
3. Select date range (e.g., last 12 months)
4. Click **Export** → **CSV (Detailed)**
5. Save as `expensify_export.csv`

**Export Users:**
1. Go to **Settings** → **Policies** → [Your Policy]
2. Click **People**
3. Export user list → `expensify_users.csv`

**Download Receipts:**
1. Go to **Reports** → **All Reports**
2. For each report with receipts:
   - Click report → **Receipts**
   - Download all → Save to folder `receipts/`

### Step 2: Transform Expensify Data

**CSV Format Mapping:**

| Expensify Column | AP2 Column | Notes |
|------------------|------------|-------|
| `Created` | `date` | Convert to YYYY-MM-DD |
| `Amount` | `amount` | Remove currency symbol |
| `Merchant` | `vendor` | Direct mapping |
| `Category` | `category` | See category mapping below |
| `Description` | `description` | Direct mapping |
| `Submitter Email` | `user_email` | For user matching |

**Category Mapping:**

| Expensify Category | AP2 Category |
|--------------------|--------------|
| Office Supplies | `office_supplies` |
| Airfare | `travel` |
| Hotel | `travel` |
| Meals | `meals` |
| Software | `software` |
| Equipment | `equipment` |
| Consulting | `professional_services` |
| Advertising | `marketing` |
| Training | `training` |
| *Other* | `other` |

**Python Transformation Script:**

```python
import pandas as pd
from datetime import datetime

# Load Expensify export
df = pd.read_csv('expensify_export.csv')

# Category mapping
category_map = {
    'Office Supplies': 'office_supplies',
    'Airfare': 'travel',
    'Hotel': 'travel',
    'Meals': 'meals',
    'Software': 'software',
    'Equipment': 'equipment',
    'Consulting': 'professional_services',
    'Advertising': 'marketing',
    'Training': 'training'
}

# Transform data
df['date'] = pd.to_datetime(df['Created']).dt.strftime('%Y-%m-%d')
df['amount'] = df['Amount'].replace('[\$,]', '', regex=True).astype(float)
df['vendor'] = df['Merchant']
df['category'] = df['Category'].map(category_map).fillna('other')
df['description'] = df['Description']
df['user_email'] = df['Submitter Email']
df['status'] = 'approved'  # Historical expenses marked as approved

# Select columns for AP2
ap2_export = df[['date', 'amount', 'vendor', 'category', 'description', 'user_email', 'status']]

# Save transformed CSV
ap2_export.to_csv('ap2_import.csv', index=False)
print(f"Transformed {len(ap2_export)} expenses for import")
```

### Step 3: Import into AP2 Expense Agent

**Option A: Bulk Import via API**

```python
import requests
import pandas as pd

API_BASE = "https://your-backend-url/api/v1"
ADMIN_TOKEN = "your_admin_token"

headers = {
    "Authorization": f"Bearer {ADMIN_TOKEN}",
    "Content-Type": "application/json"
}

# Load transformed data
df = pd.read_csv('ap2_import.csv')

# Import expenses
for _, row in df.iterrows():
    # Find or create user
    user_response = requests.get(
        f"{API_BASE}/users?email={row['user_email']}",
        headers=headers
    )

    if user_response.status_code == 404:
        # Create user
        user_data = {
            "email": row['user_email'],
            "username": row['user_email'].split('@')[0],
            "role": "employee",
            "is_active": True
        }
        user_response = requests.post(
            f"{API_BASE}/admin/users",
            headers=headers,
            json=user_data
        )

    user_id = user_response.json()['id']

    # Create expense
    expense_data = {
        "amount": row['amount'],
        "vendor": row['vendor'],
        "category": row['category'],
        "description": row['description'],
        "date": row['date'],
        "user_id": user_id,
        "status": row['status']  # Pre-approved
    }

    response = requests.post(
        f"{API_BASE}/expenses",
        headers=headers,
        json=expense_data
    )

    if response.status_code == 201:
        print(f"✓ Imported: {row['vendor']} - ${row['amount']}")
    else:
        print(f"✗ Failed: {row['vendor']} - {response.text}")
```

**Option B: Bulk Import via Admin Dashboard**

1. Login as admin
2. Go to **Admin** → **Data Import**
3. Click **Upload CSV**
4. Select `ap2_import.csv`
5. Map columns (auto-detected)
6. Click **Import**
7. Review import summary

### Step 4: Transfer Receipts

**Match Receipts to Expenses:**

```python
import os
import requests

API_BASE = "https://your-backend-url/api/v1"
ADMIN_TOKEN = "your_admin_token"
RECEIPTS_DIR = "receipts/"

headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}

# Get all imported expenses
expenses_response = requests.get(f"{API_BASE}/expenses", headers=headers)
expenses = expenses_response.json()

# Upload receipts
for expense in expenses:
    # Match receipt file by vendor and amount
    receipt_filename = f"{expense['vendor']}_{expense['amount']}.pdf"
    receipt_path = os.path.join(RECEIPTS_DIR, receipt_filename)

    if os.path.exists(receipt_path):
        with open(receipt_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(
                f"{API_BASE}/expenses/{expense['id']}/receipts",
                headers=headers,
                files=files
            )
            if response.status_code == 201:
                print(f"✓ Receipt uploaded: {receipt_filename}")
```

---

## Migration from Concur SAP

### Step 1: Export from Concur

**Export Expenses:**
1. Login to Concur
2. Navigate to **Administration** → **Reports**
3. Select **Standard Accounting Extract**
4. Choose date range
5. Export format: CSV
6. Download → `concur_export.csv`

**Export Users:**
1. **Administration** → **Company** → **Users**
2. Export user list
3. Save → `concur_users.csv`

### Step 2: Transform Concur Data

**CSV Format Mapping:**

| Concur Column | AP2 Column | Transformation |
|---------------|------------|----------------|
| `Transaction Date` | `date` | Convert to YYYY-MM-DD |
| `Posted Amount` | `amount` | Remove currency, convert to float |
| `Vendor Name` | `vendor` | Direct mapping |
| `Expense Type` | `category` | Map using table below |
| `Business Purpose` | `description` | Direct mapping |
| `Employee Email` | `user_email` | User matching |

**Concur Category Mapping:**

| Concur Expense Type | AP2 Category |
|---------------------|--------------|
| Airfare | `travel` |
| Car Rental | `travel` |
| Hotel | `travel` |
| Meals | `meals` |
| Office Supplies | `office_supplies` |
| Computer Hardware | `equipment` |
| Software License | `software` |
| Professional Fees | `professional_services` |

**Transformation Script:**

```python
import pandas as pd

# Load Concur export
df = pd.read_csv('concur_export.csv', encoding='utf-8-sig')

# Transform
df['date'] = pd.to_datetime(df['Transaction Date']).dt.strftime('%Y-%m-%d')
df['amount'] = df['Posted Amount'].str.replace(',', '').astype(float).abs()
df['vendor'] = df['Vendor Name']
df['description'] = df['Business Purpose']
df['user_email'] = df['Employee Email']
df['status'] = 'approved'

# Category mapping
concur_categories = {
    'Airfare': 'travel',
    'Car Rental': 'travel',
    'Hotel': 'travel',
    'Meals': 'meals',
    'Office Supplies': 'office_supplies',
    'Computer Hardware': 'equipment',
    'Software License': 'software',
    'Professional Fees': 'professional_services'
}

df['category'] = df['Expense Type'].map(concur_categories).fillna('other')

# Export
ap2_df = df[['date', 'amount', 'vendor', 'category', 'description', 'user_email', 'status']]
ap2_df.to_csv('ap2_import_concur.csv', index=False)
print(f"Concur data transformed: {len(ap2_df)} expenses")
```

---

## Migration from Zoho Expense

### Step 1: Export from Zoho

1. **Settings** → **Data Administration** → **Export Data**
2. Select **Expenses** and **Users**
3. Choose **All Time** or specific date range
4. Format: CSV
5. Download exports

### Step 2: Transform Data

**Zoho has similar structure to Expensify:**

```python
import pandas as pd

df = pd.read_csv('zoho_expenses.csv')

# Zoho uses standard names, minimal transformation needed
df['date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
df['amount'] = df['Amount']
df['vendor'] = df['Merchant']
df['description'] = df['Notes']
df['user_email'] = df['User Email']
df['category'] = df['Category'].str.lower().str.replace(' ', '_')
df['status'] = 'approved'

ap2_df = df[['date', 'amount', 'vendor', 'category', 'description', 'user_email', 'status']]
ap2_df.to_csv('ap2_import_zoho.csv', index=False)
```

---

## Generic CSV Import

If exporting from another system, create CSV with these columns:

### Required Columns

```csv
date,amount,vendor,category,description,user_email,status
2025-11-13,45.99,Office Depot,office_supplies,Printer supplies,employee@company.com,approved
2025-11-12,125.00,Amazon,software,Adobe subscription,manager@company.com,approved
```

### Column Specifications

| Column | Format | Required | Example |
|--------|--------|----------|---------|
| `date` | YYYY-MM-DD | Yes | `2025-11-13` |
| `amount` | Float, no $ | Yes | `45.99` |
| `vendor` | String | Yes | `Office Depot` |
| `category` | Enum value | Yes | `office_supplies` |
| `description` | String | Yes | `Printer supplies` |
| `user_email` | Email | Yes | `user@company.com` |
| `status` | `approved` or `pending` | No | `approved` |

### Valid Categories

```
office_supplies, travel, meals, software, equipment,
professional_services, marketing, training, other
```

---

## User Account Migration

### Step 1: Export User List

Create CSV with user information:

```csv
email,full_name,role,is_active
john.doe@company.com,John Doe,employee,true
jane.manager@company.com,Jane Manager,manager,true
admin@company.com,Admin User,admin,true
```

### Step 2: Bulk Create Users

**Python Script:**

```python
import requests
import pandas as pd
import secrets
import string

API_BASE = "https://your-backend-url/api/v1"
ADMIN_TOKEN = "your_admin_token"

def generate_temp_password():
    """Generate secure temporary password"""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(16))

headers = {
    "Authorization": f"Bearer {ADMIN_TOKEN}",
    "Content-Type": "application/json"
}

# Load users
df = pd.read_csv('users_import.csv')

created_users = []

for _, user in df.iterrows():
    temp_password = generate_temp_password()

    user_data = {
        "email": user['email'],
        "username": user['email'].split('@')[0],
        "full_name": user['full_name'],
        "role": user['role'],
        "password": temp_password,
        "is_active": user['is_active']
    }

    response = requests.post(
        f"{API_BASE}/admin/users",
        headers=headers,
        json=user_data
    )

    if response.status_code == 201:
        created_users.append({
            'email': user['email'],
            'temp_password': temp_password
        })
        print(f"✓ Created: {user['email']}")
    else:
        print(f"✗ Failed: {user['email']} - {response.text}")

# Save credentials for welcome emails
pd.DataFrame(created_users).to_csv('user_credentials.csv', index=False)
print(f"\n✓ Created {len(created_users)} users")
print("✓ Credentials saved to user_credentials.csv")
print("⚠️  IMPORTANT: Send welcome emails and ask users to change passwords!")
```

### Step 3: Send Welcome Emails

**Email Template:**

```
Subject: Welcome to AP2 Expense Agent

Hi [Name],

Your account has been created for AP2 Expense Agent, our new expense management system.

Login URL: https://your-org.ap2expense.com
Email: [email]
Temporary Password: [temp_password]

IMPORTANT: Change your password immediately after first login.

Steps to get started:
1. Login with credentials above
2. Click your profile → Change Password
3. Set up 2FA (recommended)
4. Submit your first expense

Questions? Email support@company.com

Best regards,
IT Team
```

---

## Receipt Transfer

### Organized Receipt Migration

**Step 1: Organize Receipts**

```bash
# Create folder structure
mkdir -p receipts/
cd receipts/

# Organize by date or expense ID
# receipts/2025-11/exp001_receipt.pdf
# receipts/2025-11/exp002_receipt.pdf
```

**Step 2: Bulk Upload Script**

```python
import os
import requests
import pandas as pd
from pathlib import Path

API_BASE = "https://your-backend-url/api/v1"
ADMIN_TOKEN = "your_admin_token"
RECEIPTS_DIR = "receipts/"

headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}

# Load expense mapping (expense_id -> receipt_filename)
mapping = pd.read_csv('receipt_mapping.csv')

for _, row in mapping.iterrows():
    expense_id = row['expense_id']
    receipt_file = row['receipt_filename']
    receipt_path = os.path.join(RECEIPTS_DIR, receipt_file)

    if not os.path.exists(receipt_path):
        print(f"⚠ Missing: {receipt_file}")
        continue

    with open(receipt_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(
            f"{API_BASE}/expenses/{expense_id}/receipts",
            headers=headers,
            files=files
        )

        if response.status_code == 201:
            print(f"✓ Uploaded: {receipt_file} → {expense_id}")
        else:
            print(f"✗ Failed: {receipt_file} - {response.text}")
```

---

## Testing Your Migration

### Validation Checklist

- [ ] **Total expense count matches**
  - Old system: ___ expenses
  - AP2 import: ___ expenses
  - Difference: ___ (should be 0 or explained)

- [ ] **Total amount matches**
  - Old system: $___
  - AP2 import: $___
  - Difference: $___ (should be <0.01%)

- [ ] **All users created**
  - Old system: ___ users
  - AP2 import: ___ users
  - Missing: ___ users

- [ ] **Receipt coverage**
  - Total expenses with receipts: ___
  - Receipts migrated: ___
  - Missing receipts: ___

### Test Scenarios

**Test 1: Spot Check**
- Pick 10 random expenses from old system
- Verify they exist in AP2 with same data
- Check receipt is attached

**Test 2: User Login**
- Have 3-5 users test login
- Verify they see their historical expenses
- Confirm they can submit new expenses

**Test 3: Approval Flow**
- Submit test expense
- Approve as manager
- Verify email notifications
- Check audit trail

---

## Go-Live Checklist

### Pre-Launch (1 week before)

- [ ] Complete data import
- [ ] Verify all receipts transferred
- [ ] Test all user accounts
- [ ] Configure approval workflows
- [ ] Set up budgets (if applicable)
- [ ] Schedule training sessions
- [ ] Prepare user documentation
- [ ] Set up support email forwarding

### Launch Day

- [ ] Send announcement email to all users
- [ ] Share login instructions
- [ ] Monitor support tickets
- [ ] Be available for questions
- [ ] Track adoption metrics

### Post-Launch (1 week after)

- [ ] Disable old system (read-only mode first)
- [ ] Export final archive from old system
- [ ] Cancel old system subscription
- [ ] Collect user feedback
- [ ] Address any issues
- [ ] Celebrate successful migration! 🎉

### Announcement Email Template

```
Subject: 🚀 Switching to AP2 Expense Agent - Action Required

Hi Team,

We're upgrading to a new expense management system: AP2 Expense Agent!

IMPORTANT DATES:
- November 18: New system goes live
- November 18-25: Parallel period (both systems active)
- November 25: Old system disabled

WHAT YOU NEED TO DO:
1. Check your email for login credentials
2. Login at: https://your-org.ap2expense.com
3. Change your temporary password
4. Review migrated expenses (last 12 months imported)
5. Submit new expenses in AP2 only (starting Nov 18)

TRAINING:
- Live demo: November 17, 2pm (Teams link)
- Video tutorial: [link]
- User guide: [link]
- Support: support@company.com

WHY WE'RE SWITCHING:
✓ Faster approvals (automated workflows)
✓ AI receipt scanning
✓ Better mobile experience
✓ Real-time expense tracking
✓ Lower cost ($X,XXX annual savings)

Questions? We're here to help!
IT Team
```

---

## Migration Support

Need help with your migration?

**Professional Services:**
- Migration planning consultation
- Custom data transformation scripts
- Bulk import assistance
- User training sessions
- Post-launch support

**Contact:**
- Email: migrations@ap2expense.com
- Enterprise customers: Dedicated migration specialist included
- Professional tier: Discounted migration services available

---

*Last Updated: November 2025*
*Version: 1.0*
