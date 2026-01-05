# Tier Limits Protection - Quick Start Guide

## Installation (One-Time Setup)

### 1. Install Git Pre-Commit Hook

```bash
bash scripts/install-tier-protection-hook.sh
```

This installs a pre-commit hook that validates tier limits before allowing commits.

### 2. Verify Current Tier Limits

```bash
cd backend
python seed_billing_tiers.py --verify
```

Expected output:
```
[PASS] Tier 'free' limits are correct
[PASS] Tier 'starter' limits are correct
[PASS] Tier 'professional' limits are correct
[SUCCESS] All tier limits verified successfully
```

### 3. Run Test Suite

```bash
python test_tier_limits_enforcement.py
```

Expected output:
```
TEST SUMMARY: 18/18 tests passed (100%)
[SUCCESS] All tier limit tests passed!
```

### 4. Verify Application Startup Protection

```bash
# Start the backend (it will verify tier limits automatically)
cd backend
./venv/Scripts/python.exe -m uvicorn src.api:app --reload
```

Look for:
```
[STARTUP] Verifying tier limits on application startup...
✓ Tier limits verification passed - application startup allowed
```

---

## Protection Layers Active

✅ **Layer 1:** Read-only code constants
✅ **Layer 2:** Application startup validation (SHA256 checksums)
✅ **Layer 3:** Database audit trail
✅ **Layer 4:** Git pre-commit hook
✅ **Layer 5:** CI/CD pipeline validation
✅ **Layer 6:** Database checksum validation
✅ **Layer 7:** Automated test suite (18 tests)
✅ **Layer 8:** Daily monitoring (cron jobs in production)

---

## Daily Operations

### Check Tier Limits Status

```bash
cd backend
python seed_billing_tiers.py --show
```

### View Tier Limits Comparison

```
Feature                        | Free         | Starter      | Professional
--------------------------------------------------------------------------------
Organizations                  | 1            | 3            | 10
Users                          | 2            | 10           | 50
Expenses/month                 | 30           | 100          | 500
OCR Scans/month                | 20           | 100          | Unlimited
AI Categorizations             | 0            | 50           | 200
AP2 Transactions               | 20           | 100          | Unlimited
Data Retention                 | 90 days      | 365 days     | 1095 days
Price/month                    | $0           | $29          | $99
```

### Force Update (After Authorized Changes)

```bash
cd backend
python seed_billing_tiers.py --force
python test_tier_limits_enforcement.py
```

---

## Verification Commands

| Command | Purpose |
|---------|---------|
| `python seed_billing_tiers.py --verify` | Verify database matches official spec |
| `python seed_billing_tiers.py --show` | Display tier comparison table |
| `python seed_billing_tiers.py --force` | Update database with official limits |
| `python test_tier_limits_enforcement.py` | Run full test suite (18 tests) |

---

## What to Do If...

### Verification Fails

```
[ERROR] Tier 'free' limit mismatch:
  Field: ocr_scans_included
  Expected: 20
  Actual: 30
```

**Solution:**
```bash
cd backend
python seed_billing_tiers.py --force  # Restore correct limits
python test_tier_limits_enforcement.py  # Verify fix
```

### Application Won't Start

```
[CRITICAL] Tier limit verification failed
[CRITICAL] Application startup BLOCKED for security
```

**Solution:**
```bash
cd backend
python seed_billing_tiers.py --verify  # Check what's wrong
python seed_billing_tiers.py --force   # Fix it
```

### Pre-Commit Hook Blocks Commit

```
❌ TIER LIMIT VERIFICATION FAILED
```

**Options:**
1. **Revert your changes** (recommended):
   ```bash
   git checkout backend/seed_billing_tiers.py
   ```

2. **Get approvals and proceed** (if authorized):
   - Obtain approvals from Product, Finance, Legal, Engineering
   - Update documentation
   - Confirm when prompted

3. **Emergency bypass** (logged and caught by CI/CD):
   ```bash
   git commit --no-verify
   ```

### CI/CD Pipeline Fails

Check GitHub Actions for details. Common fixes:
- Ensure frontend and backend are synchronized
- Update `TIER_LIMITS_PROTECTION.md` changelog
- Get required approvals documented in PR description

---

## Files to Know

### Source of Truth (3 files must match)
1. `backend/seed_billing_tiers.py` → `OFFICIAL_TIERS`
2. `frontend/src/config/constants.js` → `TIER_LIMITS`
3. `backend/src/billing/tier_limit_guardian.py` → `OFFICIAL_TIER_LIMITS`

### Protection Infrastructure
- `.github/workflows/tier-limits-validation.yml` - CI/CD validation
- `scripts/install-tier-protection-hook.sh` - Git hook installer
- `backend/test_tier_limits_enforcement.py` - Test suite

### Documentation
- `TIER_LIMITS_PROTECTION.md` - Detailed protection guide
- `TIER_LIMITS_COMPLETE_PROTECTION.md` - Full security analysis
- `TIER_LIMITS_UPDATE_SUMMARY.md` - Recent changes log

---

## Approval Requirements

**To modify tier limits, you MUST have approval from:**
- ☐ Product Manager
- ☐ Finance Team
- ☐ Legal Team
- ☐ Engineering Lead

**Document approvals in:**
- Git commit message
- Pull request description
- `TIER_LIMITS_PROTECTION.md` changelog

---

## Support

**Questions:** See `TIER_LIMITS_COMPLETE_PROTECTION.md`
**Security Issues:** security@company.com
**General Help:** engineering@company.com

---

**Status:** 🔒 **PROTECTED** - All safeguards active
