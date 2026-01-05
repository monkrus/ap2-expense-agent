# Billing Tier Limits - Protection & Enforcement

## CRITICAL: Tier Limits Are Protected

The billing tier limits are **legally binding** and affect customer billing, SLAs, and revenue. **Unauthorized changes are prohibited** and will be automatically detected.

---

## Official Tier Limits

### Free Tier ($0/month)
| Feature | Limit |
|---------|-------|
| Organizations | 1 |
| Users | 2 |
| Expenses/month | 30 |
| OCR Scans/month | 20 |
| OCR Scans/day | 3 |
| AI Categorizations | 0 |
| AP2 Transactions | 20 |
| Data Retention | 90 days |
| Approval Workflows | ❌ No |
| Advanced Analytics | ❌ No |
| API Access | ❌ No |

### Starter Tier ($29/month)
| Feature | Limit |
|---------|-------|
| Organizations | 3 |
| Users | 10 |
| Expenses/month | 100 |
| OCR Scans/month | 100 |
| OCR Scans/day | 20 |
| AI Categorizations | 50 |
| AP2 Transactions | 100 |
| Data Retention | 1 year |
| Approval Workflows | ✅ Yes |
| Advanced Analytics | ✅ Yes |
| API Access | ❌ No |

### Professional Tier ($99/month)
| Feature | Limit |
|---------|-------|
| Organizations | 10 |
| Users | 50 |
| Expenses/month | 500 |
| OCR Scans/month | ♾️ Unlimited |
| OCR Scans/day | ♾️ Unlimited |
| AI Categorizations | 200 |
| AP2 Transactions | ♾️ Unlimited |
| Data Retention | 3 years |
| Approval Workflows | ✅ Yes |
| Advanced Analytics | ✅ Yes |
| API Access | ✅ Yes |

---

## Protection Mechanisms

### 1. Source of Truth Files

These files define the official tier limits and **must remain synchronized**:

- **Backend:** `backend/seed_billing_tiers.py` - `OFFICIAL_TIERS` dictionary
- **Frontend:** `frontend/src/config/constants.js` - `TIER_LIMITS` object

**⚠️ WARNING:** Any changes to these files trigger automated validation.

### 2. Automated Validation

**Pre-Commit Hook:**
The `.git/hooks/pre-commit` script automatically runs before each commit to verify:
- Tier limits match official specification
- Frontend and backend are synchronized
- All validation tests pass

**To bypass (EMERGENCY ONLY):**
```bash
git commit --no-verify -m "Emergency commit (requires approval)"
```

### 3. Database Seeding & Verification

**Seed Database:**
```bash
cd backend
python seed_billing_tiers.py --force
```

**Verify Limits:**
```bash
cd backend
python seed_billing_tiers.py --verify
```

**Show Comparison Table:**
```bash
cd backend
python seed_billing_tiers.py --show
```

### 4. Automated Testing

**Run Tier Limit Tests:**
```bash
cd backend
python test_tier_limits_enforcement.py
```

This test suite verifies:
- ✅ All tier limits in database match official specification
- ✅ Tier hierarchy is correct (Starter > Free, Professional > Starter)
- ✅ Pricing is correct ($0, $29, $99)
- ✅ Features are correctly assigned to each tier
- ✅ Limit enforcer correctly blocks over-limit usage

**Expected Result:** 18/18 tests passed (100%)

---

## How to Change Tier Limits (Authorized Process)

### Step 1: Get Approval
- **Required Approvals:**
  - Product Manager
  - Finance Team
  - Legal Team (for contract implications)
  - Engineering Lead

### Step 2: Update Official Specification
Update both files:

1. **Backend:** `backend/seed_billing_tiers.py`
   ```python
   OFFICIAL_TIERS = {
       "free": {
           "limits": {
               "max_users": 2,  # ← Change here
               # ...
           }
       }
   }
   ```

2. **Frontend:** `frontend/src/config/constants.js`
   ```javascript
   export const TIER_LIMITS = {
     FREE: {
       MAX_USERS: 2,  // ← Change here
       // ...
     }
   }
   ```

### Step 3: Verify Changes
```bash
# Show what will change
cd backend
python seed_billing_tiers.py --show

# Verify tier limits
python seed_billing_tiers.py --verify
```

### Step 4: Update Database
```bash
cd backend
python seed_billing_tiers.py --force
```

### Step 5: Run Tests
```bash
# Backend tier tests
python test_tier_limits_enforcement.py

# Full test suite
pytest tests/
```

### Step 6: Update Documentation
- Update this file (TIER_LIMITS_PROTECTION.md)
- Update README.md pricing table
- Update marketing materials
- Update Terms of Service (if contractual changes)

### Step 7: Communicate Changes
- Notify existing customers (if limits decrease)
- Update website pricing page
- Update Google Cloud Marketplace listing
- Send announcement to stakeholders

---

## Monitoring & Alerts

### Database Consistency Check (Automated)

A daily cron job runs:
```bash
python backend/seed_billing_tiers.py --verify
```

If tier limits in database don't match official specification:
- ❌ Alert sent to engineering team
- ❌ Slack notification
- ❌ Automated ticket created

### Usage Monitoring

The `LimitEnforcer` class logs when users hit limits:
```python
# Example log entry
{
  "event": "limit_exceeded",
  "organization_id": "...",
  "tier": "free",
  "limit_type": "ocr_scans_per_month",
  "current_usage": 20,
  "limit": 20,
  "timestamp": "2026-01-04T..."
}
```

---

## Emergency Procedures

### If Incorrect Limits Are Deployed

**Immediate Actions:**
1. ❌ Stop all new signups (if limits are too generous)
2. 🔄 Revert to previous tier limits immediately
3. 📧 Notify affected customers (if limits were too restrictive)
4. 💰 Issue credits for any overcharges

**Rollback Command:**
```bash
cd backend
git checkout HEAD~1 seed_billing_tiers.py
python seed_billing_tiers.py --force
python test_tier_limits_enforcement.py
```

### If Customers Are Overcharged

1. Identify affected organizations
2. Calculate overcharge amount
3. Issue credits via GCP Marketplace
4. Send apology email with explanation
5. Update limits to correct values
6. Add additional monitoring to prevent recurrence

---

## FAQ

**Q: Can I temporarily increase limits for a customer?**
A: No. Use custom tier or enterprise plan instead. Contact finance team.

**Q: What if a customer needs just one extra user?**
A: They must upgrade to the next tier. No exceptions (billing integrity).

**Q: Can we grandfather existing customers at old limits?**
A: Only with finance and legal approval. Requires custom subscription record.

**Q: How are "unlimited" limits enforced?**
A: Stored as `null` in database. `LimitEnforcer` treats `null` as unlimited.

**Q: What happens if I manually update limits in the database?**
A: Daily verification job will detect and alert. Limits will be reverted.

---

## Security & Audit Trail

### Database Audit Log

The `billing_events` table tracks all tier changes:
```sql
SELECT * FROM billing_events
WHERE event_type = 'tier_limit_change'
ORDER BY created_at DESC;
```

### Who Can Modify Tiers?

**Database Level:**
- Only database administrators with direct DB access

**Application Level:**
- No API endpoint exists to modify tier limits
- Tiers can only be modified via seed scripts
- All seed script runs are logged

**Production Environment:**
- Tier seed script requires elevated permissions
- All production changes require approved change request
- Deployment logs are audited monthly

---

## Compliance & Legal

### Contract Implications

Tier limits are part of:
- ✅ Terms of Service
- ✅ Service Level Agreements (SLAs)
- ✅ Google Cloud Marketplace listing
- ✅ Customer contracts

**Changing limits may require:**
- Legal review
- Customer notification (30-60 days)
- Terms of Service update
- Marketplace re-approval

### Data Retention Compliance

Different tiers have different retention periods:
- Free: 90 days
- Starter: 1 year
- Professional: 3 years

**Legal Requirements:**
- Some jurisdictions require 7 year retention (financial records)
- GDPR allows users to request deletion (conflicts with retention)
- Compliance team must approve retention changes

---

## Contact

**For Tier Limit Changes:**
- Product Manager: product@company.com
- Finance Team: finance@company.com
- Engineering Lead: engineering@company.com

**For Technical Issues:**
- DevOps Team: devops@company.com
- On-Call Engineer: See PagerDuty

**For Customer Requests:**
- Support Team: support@company.com
- Enterprise Sales: sales@company.com

---

## Changelog

### 2026-01-04 - Initial Official Limits
- Free: 1 org, 2 users, 30 expenses/month, 20 OCR/month, $0
- Starter: 3 orgs, 10 users, 100 expenses/month, 100 OCR/month, $29
- Professional: 10 orgs, 50 users, 500 expenses/month, Unlimited OCR, $99
- **Status:** ✅ Approved by Product, Finance, Engineering
- **Deployed:** Production (2026-01-04)

---

**Last Updated:** 2026-01-04
**Version:** 1.0
**Status:** 🔒 PROTECTED - Requires Approval for Changes
