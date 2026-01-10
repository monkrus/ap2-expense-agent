# AP2 Expense Management Agent - Claude Code Guide

This file provides context and best practices for Claude Code and subagents working on this project.

## Project Overview

**Stack**: Python FastAPI (backend) + React (frontend) + SQLite/PostgreSQL
**Architecture**: Multi-tenant SaaS with Google Cloud Marketplace integration

### 🎯 **CORE VALUE PROPOSITION: AP2 Autonomous Agent**

**This is NOT just another expense management app.** Our competitive advantage is:

**✨ AI Agent Auto-Approves 60-70% of Expenses Instantly Using AP2 Protocol**

**How it works:**
1. **User sets Intent Mandates once** - "Auto-approve Amazon office supplies up to $200/month"
2. **Employee submits expense** - Agent checks Intent Mandates in real-time
3. **Instant approval** - No manager bottleneck for routine expenses
4. **Cryptographic audit trail** - Full AP2 compliance (GDPR, SOC 2 ready)

**Key Differentiators:**
- ✅ **True autonomous agent** - Not just OCR or categorization
- ✅ **AP2 protocol** - Open standard with cryptographic guarantees
- ✅ **Manager time saved** - Focus on exceptions, not routine approvals
- ✅ **Faster reimbursements** - Seconds instead of days

**Competitors:**
- Expensify: Manual approval or OCR only
- Concur: Rules-based but no AI agent
- Ramp: ML categorization but still manual approval
- **Us**: Autonomous agent with cryptographic AP2 guarantees

**Key Features** (Priority Order):
1. **AP2 Autonomous Approval** - Intent Mandates → Auto-approval (CORE SELLING POINT)
2. Expense management - Submit, track, export
3. Approval workflows - Manual approval for exceptions
4. Organization management - Multi-tenant with RBAC
5. Marketplace billing - Google Cloud integration

---

## Common Commands

### Backend Development

```bash
# Start backend server (from project root)
cd backend && .venv/Scripts/python.exe -m uvicorn src.api:app --host 127.0.0.1 --port 8000 --reload

# Alternative (if virtual env activated)
cd backend && uvicorn src.api:app --reload

# Run backend tests
cd backend && pytest

# Run specific test file
cd backend && pytest tests/test_auth.py -v

# Database migrations (Alembic)
cd backend && alembic upgrade head
cd backend && alembic revision --autogenerate -m "description"
```

### Frontend Development

```bash
# Start frontend dev server (from project root)
cd frontend && npm run dev

# Build frontend
cd frontend && npm run build

# Run frontend tests
cd frontend && npm test
```

### Database Operations

```bash
# Quick database inspection (from backend dir)
python -c "from src.database import SessionLocal; from src.models import Organization; db = SessionLocal(); print(db.query(Organization).all())"

# Clean up soft-deleted organizations
python backend/cleanup_soft_deleted_orgs.py

# Seed test data
cd backend && python seed_tiers_quick.py
```

### Testing Organization Features

```bash
# Comprehensive organization tests (from project root)
python test_org_final.py

# Full test suite with new user registration
python test_organization_scenarios.py

# Comprehensive security audit (Google Cloud Marketplace readiness)
python security_audit_comprehensive.py
```

### Production Deployment & Operations

```bash
# Validate environment before deployment
./scripts/validate-environment.sh production

# Create database backup
./scripts/backup-database.sh

# Deploy to production (automated)
./scripts/deploy-production.sh v1.0.0 production

# Run smoke tests after deployment
./scripts/smoke-test.sh production

# Rollback if needed
./scripts/rollback-deployment.sh v0.9.0

# Seed demo data for screenshots
python backend/seed_screenshot_data.py

# Capture screenshots with guided helper
./scripts/capture-screenshots.sh
```

---

## Code Architecture

### Backend Structure (`backend/src/`)

```
api.py                      # Main FastAPI application
routes/
  ├── organizations.py      # Organization CRUD, invitations, members
  ├── auth.py              # Authentication endpoints
  ├── billing_org.py       # Organization-level billing (Marketplace)
  └── webhooks.py          # Marketplace/Stripe webhooks
models.py                  # SQLAlchemy ORM models
models_billing.py          # Billing-specific models
billing/
  ├── usage_tracker.py     # Org usage tracking
  └── limit_enforcer.py    # Org usage/limit enforcement
tenant_context.py          # Multi-tenancy utilities
```

### Frontend Structure (`frontend/src/`)

```
pages/
  ├── PricingPlans.jsx     # Subscription tier selection
  ├── BillingDashboard.jsx # User billing management
  └── Organizations.jsx    # Organization management
components/               # Reusable React components
api/                     # API client functions
```

---

## 🤖 AP2 Autonomous Agent Architecture

### **Current State vs. Goal**

**❌ CURRENT (BROKEN):** AP2 triggers AFTER manual approval
```python
# expenses.py:965 - WRONG: Retroactive AP2 creation
expense.status = APPROVED  # Manager approved manually
ap2_service.complete_ap2_flow()  # Creates mandates after decision
```

**✅ GOAL (CORRECT):** Intent Mandates enable auto-approval
```python
# expenses.py:240 - RIGHT: Intent Mandate drives decision
matching_mandate = ap2_service.find_matching_intent_mandate(expense)
if matching_mandate:
    # Auto-approve via AP2 (no human needed!)
    expense.status = APPROVED
    expense.auto_approved = True
else:
    # Manual approval needed
    expense.status = PENDING
```

### **AP2 Protocol Components**

Located in `backend/src/payments/ap2_service.py`:

1. **Intent Mandate** - User's authorization constraints
   - Created BEFORE expenses are submitted
   - Example: "Auto-approve Amazon up to $200/month for office_supplies"
   - Stored in `intent_mandates` table

2. **Cart Mandate** - Specific expense items for approval
   - Created when expense matches Intent Mandate
   - Contains: items, total, merchant, user_signature
   - Validates against Intent Mandate constraints

3. **Payment Mandate** - Payment execution record
   - Created after Cart Mandate approval
   - Includes: payment_method, audit_trail, timestamp
   - Triggers Stripe payment

### **Implementation Checklist**

**Phase 1: Core Autonomy (PRIORITY)** ⭐

- [ ] `backend/src/payments/ap2_service.py`:
  - [ ] Add `find_matching_intent_mandate()` method
  - [ ] Add `_expense_matches_constraints()` helper
  - [ ] Add `_get_mandate_monthly_usage()` for spending limits

- [ ] `backend/src/routes/expenses.py`:
  - [ ] Check Intent Mandates BEFORE creating expense (line ~240)
  - [ ] Auto-approve if mandate matches
  - [ ] REMOVE AP2 from manual approval endpoint (lines 965-1003)

- [ ] Database:
  - [ ] Add `auto_approved` boolean to expenses table
  - [ ] Add `intent_mandate_id` to expenses table (already exists)

**Phase 2: User Experience**

- [ ] `frontend/src/components/ExpenseForm.jsx`:
  - [ ] Show "Will auto-approve" indicator
  - [ ] Suggest Intent Mandate creation for common expenses

- [ ] `frontend/src/pages/AIAssistant.jsx`:
  - [ ] Intent Mandate creation wizard
  - [ ] Dashboard showing auto-approval stats
  - [ ] Manager time saved metrics

- [ ] `frontend/src/components/IntentMandateManager.jsx`:
  - [ ] Intuitive constraint builder
  - [ ] Monthly spending limits
  - [ ] Activity preview

**Phase 3: Advanced Features**

- [ ] Learning: "Create mandate based on last 10 expenses?"
- [ ] Analytics: Auto-approval rate, time saved
- [ ] Manager override: Revoke mandate if abuse detected

### **AP2 Files Reference**

**Backend:**
- `backend/src/payments/ap2_service.py` - AP2 protocol implementation
- `backend/src/routes/ap2.py` - API endpoints (Intent/Cart/Payment Mandates)
- `backend/src/models.py:766-833` - AP2 database models
- `backend/src/security/kms_service.py` - Cryptographic signing

**Frontend:**
- `frontend/src/pages/AIAssistant.jsx` - Main AP2 interface
- `frontend/src/components/IntentMandateManager.jsx` - Mandate CRUD
- `frontend/src/components/AgentActivityMonitor.jsx` - Transaction history
- `frontend/src/components/ConstraintBuilder.jsx` - Constraint UI

**Tests:**
- `backend/tests/test_ap2_protocol.py` - AP2 compliance tests
- `backend/tests/test_ap2_payment_service.py` - Service tests

### **AP2 Usage Limits (Billing)**

Per tier AP2 transaction limits:
- **Free**: 20 transactions/month (hook users on core feature)
- **Starter**: 100 transactions/month
- **Professional**: 500 transactions/month
- **Enterprise**: Unlimited

**Enforcement:** `backend/src/routes/ap2.py:307, 367`

### **Common AP2 Patterns**

**Creating Intent Mandate (User Setup):**
```python
# backend/src/payments/ap2_service.py
mandate = await ap2_service.create_intent_mandate(
    user_id=user.id,
    constraints={
        "max_amount": 200.00,
        "category": "office_supplies",
        "merchant": "Amazon",
        "monthly_limit": 500.00
    },
    expiration_hours=720  # 30 days
)
```

**Auto-Approving Expense (On Submission):**
```python
# backend/src/routes/expenses.py
matching_mandate = ap2_service.find_matching_intent_mandate(
    user_id=user.id,
    amount=expense.amount,
    category=expense.category,
    merchant=expense.vendor,
    organization_id=org_id
)

if matching_mandate:
    ap2_result = await ap2_service.complete_ap2_flow(
        user_id=user.id,
        items=[expense_as_cart_item],
        merchant=expense.vendor,
        intent_mandate_id=matching_mandate.id
    )
    expense.auto_approved = True
```

**Revoking Intent Mandate (GDPR):**
```python
# backend/src/routes/ap2.py:580
# POST /api/ap2/intent-mandate/{id}/revoke
# Cascade revokes all dependent Cart/Payment Mandates
```

---

## Important Conventions

### Database

- **Soft Deletes**: Use `is_active=False` instead of hard deletes for organizations, members
- **UUIDs**: All primary keys use string UUIDs (e.g., `str(uuid.uuid4())`)
- **Timestamps**: Use `datetime.utcnow()` for all datetime fields
- **Session Management**: Always use `db: Session = Depends(get_db)` in route handlers

### API Design

- **Prefix**: All routes use `/api/v1/` prefix (except auth: `/api/v1/auth/`)
- **Status Codes**:
  - `201` - Resource created
  - `204` - Successful deletion (no content)
  - `400` - Bad request (validation errors)
  - `402` - Payment required (tier limits)
  - `403` - Forbidden (permission denied)
  - `404` - Not found
- **Error Format**: Return `{"detail": "error message"}` for consistency

### Multi-Tenancy

- **Organization Filtering**: Always filter by `organization_id` and `is_active=True`
- **Access Control**: Use `TenantAwareQuery.ensure_organization_access()` before operations
- **Role Checks**: Verify roles with `get_user_organization_role()`

### Validation Order

When creating resources, validate in this order:
1. **Input validation** (duplicate slugs/names) → 400
2. **Permission checks** (roles, access) → 403
3. **Tier limits** (subscription constraints) → 402

Example (organizations.py:67-121):
```python
# 1. Check slug/name duplicates (400)
# 2. Check tier limits (402)
# 3. Create resource
```

---

## Billing Tiers (Marketplace)

**Current Pricing** (Finalized 2025-12-30):
- **Free**: $0/month - 2 users, 30 expenses, 20 AP2 payments, 30 OCR scans
- **Starter**: $29/month - 5 users, 50 expenses, 100 AP2 payments, 50 OCR scans
- **Professional**: $79/month - 25 users, 500 expenses, 1,000 AP2 payments, 200 OCR scans
- **Enterprise**: Disabled (may be enabled later)

**Important**: AP2 payment processing fees (2.9% + $0.30/transaction) are passed through to users.
This is critical for sustainable economics - see `documents/PRICING_STRUCTURE.md` for full analysis.

**Implementation**:
- Tier definitions: `backend/src/models_billing.py` (BillingTier model)
- Seeding: `backend/scripts/seed_billing_tiers.py`
- Limit enforcement: `backend/src/billing/limit_enforcer.py`
- Usage tracking: `backend/src/billing/usage_tracker.py`

**Export & Approvals**: Available in ALL tiers (CSV/Excel/PDF export, basic approval workflows)

---

## Testing Guidelines

### Writing Tests

- **Location**: Place tests in `backend/tests/` or create root-level test scripts
- **Naming**: Use `test_*.py` for pytest discovery
- **Rate Limits**: Registration limited to 3/hour - reuse test users when possible
- **Cleanup**: Always clean up created resources (orgs, users) after tests
- **Test User Pattern**:
  ```python
  username = f"testuser_{int(time.time())}"  # Unique username
  ```

### Running Tests

- **Backend**: `cd backend && pytest` (requires virtual env)
- **Specific test**: `pytest tests/test_file.py::test_function -v`
- **Coverage**: `pytest --cov=src --cov-report=html`
- **Organization tests**: `python test_org_final.py` (from project root)

---

## Security Notes

- **Never commit**: `.env` files, credentials, API keys
- **Secrets**: Use environment variables for sensitive data
- **SQL Injection**: All queries use SQLAlchemy ORM (parameterized)
- **XSS**: Frontend uses React (auto-escapes)
- **CSRF**: Disabled for API (stateless JWT auth)
- **Rate Limiting**: Enabled on auth endpoints (see `backend/src/rate_limit.py`)

---

## Common Issues & Solutions

### "Organization slug already taken" after deletion

**Cause**: Backend server hasn't reloaded with `is_active` filter changes
**Fix**: Restart backend server or run `python backend/cleanup_soft_deleted_orgs.py`

### Rate limit exceeded (429)

**Cause**: Too many registration/login attempts
**Fix**: Wait 60 seconds or use existing test users

### Database locked

**Cause**: SQLite doesn't handle concurrent writes well
**Fix**: Close other DB connections or use PostgreSQL for production

### Import errors in tests

**Cause**: Python path not set correctly
**Fix**: Run from project root or use `PYTHONPATH=. python script.py`

### Backend won't start

**Check**:
1. Virtual environment activated: `.venv/Scripts/activate`
2. Dependencies installed: `pip install -r requirements.txt`
3. Port 8000 not in use: `netstat -ano | findstr :8000`
4. Correct working directory: Should be in `backend/` folder

---

## Workflow Best Practices (Per Claude Code Guide)

### Before Starting Work

1. **Read relevant files** - Don't jump straight to coding
2. **Ask to plan** - Use "think" or request a plan for complex tasks
3. **Be specific** - Detail requirements, edge cases, desired approach
4. **Reference files** - Use tab-completion to mention specific files

### During Development

1. **Test-driven** - Write tests first when possible
2. **Iterate** - Provide feedback loops (tests, visual mockups)
3. **Course correct** - Use Escape to interrupt and redirect
4. **Clear context** - Use `/clear` between unrelated tasks

### After Completion

1. **Run tests** - Verify changes work
2. **Update docs** - Keep CLAUDE.md current with `#` key
3. **Commit properly** - Descriptive messages following project style
4. **Clean up** - Remove test files, temporary data

---

## Project-Specific Warnings

⚠️ **AP2 IS THE SELLING POINT**: Intent Mandates must enable auto-approval, not document it retroactively
⚠️ **Multi-tenant Data**: Always filter by `organization_id` and `is_active=True`
⚠️ **Soft Deletes**: Never hard delete organizations/users - use `is_active=False`
⚠️ **Tier Limits**: Free tier has hard enforcement - test carefully
⚠️ **Windows Paths**: Use forward slashes in code, backslashes in shell commands
⚠️ **Server Restart**: Code changes require backend restart (no hot reload for imports)

### ⚠️ Critical AP2 Pattern

**NEVER** create Intent Mandates after approval decisions:
```python
# ❌ WRONG - Retroactive documentation
expense.status = APPROVED  # Human decided
ap2_service.complete_ap2_flow()  # Creates mandates after

# ✅ RIGHT - Intent Mandate drives decision
matching_mandate = find_matching_intent_mandate(expense)
if matching_mandate:
    expense.status = APPROVED  # AI decided
    expense.auto_approved = True
```

**Why this matters**: AP2's value is autonomous decision-making, not audit trails for manual decisions.

---

## 🔒 CRITICAL: Preventing Regressions

**ALWAYS** follow these rules when modifying code to prevent breaking existing functionality:

### 1. Read Before Modifying ✅

```
❌ BAD:  Modify backend/src/routes/organizations.py without reading it first
✅ GOOD: Read the entire file, understand context, then make surgical changes
```

**Rule**: Never propose changes to code you haven't read. If modifying a file, read it completely first.

### 2. Run Tests After Changes ✅

```bash
# After ANY backend changes:
cd backend && pytest

# After organization-related changes specifically:
python test_org_final.py

# Create regression tests for bugs you fix:
# Add/extend a pytest in backend/tests/ or extend test_org_final.py
```

**Rule**: Test your changes before considering them complete.

### 3. Verify Recent Fixes Are Intact 🛡️

**Recent Critical Fixes** (DO NOT BREAK):

#### Organization Name Validation (ADDED: 2025-11-27)
**File**: `backend/src/routes/organizations.py:80-91`
```python
# Check if name is already taken (case-insensitive, only ACTIVE organizations)
existing_name = (
    db.query(Organization)
    .filter(func.lower(Organization.name) == func.lower(org_data.name))
    .filter(Organization.is_active == True)  # ← CRITICAL: Filter inactive orgs
    .first()
)
```
**Test**: `python test_org_final.py` → "Duplicate name (exact)" test must pass

#### Organization Slug Soft-Delete Fix (ADDED: 2025-11-27)
**File**: `backend/src/routes/organizations.py:67-78`
```python
# Check if slug is already taken (only check ACTIVE organizations)
existing_slug = (
    db.query(Organization)
    .filter(Organization.slug == org_data.slug)
    .filter(Organization.is_active == True)  # ← CRITICAL: Allow slug reuse after deletion
    .first()
)
```
**Test**: `python test_org_final.py` → "Recreate after delete" test must pass

### 4. Validation Order Matters ⚠️

**File**: `backend/src/routes/organizations.py:67-121`

**CORRECT ORDER** (current implementation):
```python
1. Check duplicate slug (400 Bad Request)
2. Check duplicate name (400 Bad Request)
3. Check tier limits (402 Payment Required)
4. Create organization
```

**Why**: Users should get specific validation errors (400) before payment errors (402)

❌ **WRONG**: Checking tier limits before duplicate validation
✅ **RIGHT**: Validate input → Check permissions → Check limits

### 5. Multi-Tenancy Filters 🔐

**Every organization query MUST include**:
```python
.filter(Organization.is_active == True)  # Exclude soft-deleted
.filter(Organization.organization_id == org_id)  # Multi-tenant isolation
```

**Files to be extra careful with**:
- `backend/src/routes/organizations.py`
- `backend/src/routes/billing_org.py       # Organization-level billing (Marketplace)
- `backend/src/tenant_context.py`

### 6. Before Committing Checklist ✓

- [ ] Read all files you modified completely
- [ ] Tests pass: `cd backend && pytest`
- [ ] Organization tests pass: `python test_org_final.py`
- [ ] No removal of `is_active == True` filters
- [ ] No changes to validation order without explicit reason
- [ ] No hard deletes introduced (use `is_active = False`)
- [ ] Backend server restarted if testing manually

### 7. Regression Test Protection

**When you fix a bug, create a test** to prevent it from coming back:

```python
# Example: backend/tests/test_organizations.py
def test_duplicate_name_case_insensitive():
    """Prevent regression: org names must be unique (case-insensitive)"""
    # This test ensures the fix in organizations.py:80-91 stays in place
    pass
```

### 8. Code Review Red Flags 🚩

If you see these in code changes, STOP and reconsider:

- ❌ Removing `.filter(is_active == True)` from queries
- ❌ Hard deletes: `db.delete(organization)` instead of soft delete
- ❌ Changing validation order without reason
- ❌ Modifying files you haven't read
- ❌ Skipping tests after changes
- ❌ Adding logic without understanding existing flow

### 9. Safe Refactoring Pattern

```python
# Step 1: Read and understand
Read("backend/src/routes/organizations.py")

# Step 2: Write tests for current behavior
# (If tests don't exist, create them first!)

# Step 3: Make changes

# Step 4: Verify tests still pass
cd backend && pytest

# Step 5: Test manually if needed
python test_org_final.py

# Step 6: Commit with clear message
git commit -m "refactor: improve X without breaking Y"
```

---

## 📝 Recent Changes Log

Keep this updated when making significant changes (newest first):

### 2026-01-09: Strategic Pivot - AP2 Autonomous Agent as Core Value Proposition 🎯

**CRITICAL SHIFT**: AP2 is now the **primary selling point**, not just a technical feature.

**Problem Identified:**
- ❌ AP2 currently triggers AFTER manual approval (backwards!)
- ❌ Creates Intent Mandates retroactively (defeats purpose)
- ❌ Adds complexity without delivering autonomous agent value
- ❌ Just duplicates existing expense/approval workflow

**New Strategic Goal:**
- ✅ **Intent Mandates drive auto-approval** (not retroactive documentation)
- ✅ **AI Agent approves 60-70% of expenses instantly** (no manager needed)
- ✅ **True autonomous agent** as competitive differentiator
- ✅ **Measurable ROI**: Manager time saved, faster reimbursements

**Implementation Roadmap:**

**Phase 1: Core Autonomy (WEEK 1 PRIORITY)** ⭐
```python
# New flow in expenses.py line ~240:
matching_mandate = find_matching_intent_mandate(expense)
if matching_mandate:
    auto_approve_via_ap2()  # Instant approval!
else:
    manual_approval_flow()  # Exception handling
```

Changes needed:
1. `ap2_service.py`: Add `find_matching_intent_mandate()` method
2. `expenses.py:240`: Check mandates BEFORE submitting
3. `expenses.py:965-1003`: REMOVE retroactive AP2 (broken pattern)
4. Database: `auto_approved` boolean field

**Phase 2: User Experience (WEEK 2)**
1. Expense submission shows "Will auto-approve" indicator
2. Intent Mandate creation wizard
3. Dashboard: Auto-approval rate, time saved
4. Email: "Your expense was auto-approved by AI"

**Phase 3: Advanced Features (WEEK 3)**
1. AI suggests Intent Mandates from patterns
2. Monthly spending limits per mandate
3. Manager override/revoke capabilities
4. Usage analytics

**Marketing Value:**
- **Before**: Generic expense app (same as competitors)
- **After**: "AI auto-approves 70% of expenses instantly"

**Competitive Position:**
- Expensify: Manual approval only
- Concur: Rules but no AI agent
- Ramp: ML categorization but still manual
- **Us**: True autonomous AP2 agent ✨

**Success Metrics:**
- Auto-approval rate: 60-70%
- Time to approval: <1 minute (vs 2-3 days)
- Manager time saved: Hours/month
- User satisfaction: Instant reimbursement

**Files to Update:**
- ✅ `documents/CLAUDE.md` - Updated with new strategy
- [ ] `backend/src/payments/ap2_service.py` - Add matching logic
- [ ] `backend/src/routes/expenses.py` - Reorder AP2 flow
- [ ] `frontend/src/components/ExpenseForm.jsx` - Add indicators
- [ ] `frontend/src/pages/AIAssistant.jsx` - Enhanced dashboard

**Status**: Documentation updated, implementation pending

---

### 2025-12-30: Pricing Structure Finalized ✅

- ✅ **Finalized 3-tier pricing model**: Free ($0), Starter ($29), Professional ($79)
- ✅ **Disabled Enterprise tier**: Commented out in seed script, marked inactive in database
- ✅ **Strategic Free tier updates**:
  - Increased users: 1 → 2 (enable approval workflow testing)
  - Increased expenses: 20 → 30/month
  - Added AP2 transactions: 0 → 20/month (hook users on core feature)
  - Increased OCR scans: 5 → 30/month
  - Added organizations limit: 1
  - Added data retention: 90 days
- ✅ **Export strategy**: CSV/Excel/PDF in ALL tiers (user-first, builds trust)
- ✅ **Approval workflows**: Available in ALL tiers (basic in Free/Starter, multi-level in Pro)
- ✅ **AP2 payment processing fees**: Passed through to users (2.9% + $0.30/transaction)
  - Critical for sustainability - without this, losses scale with growth
  - Standard industry practice (Stripe Connect, PayPal, Square)
- ✅ **Unit economics validated**:
  - Free: -$0.12/user/month (acceptable CAC)
  - Starter: +$27.78/user/month (95.8% margin)
  - Professional: +$73.39/user/month (92.9% margin)
  - Target mix (1,000 Free + 100 Starter + 20 Pro): $2,971/month profit at 66% margin
- ✅ **Documentation created**: `documents/PRICING_STRUCTURE.md` (comprehensive pricing guide)
- ✅ **Database updated**: `update_all_tiers_final.py` applied to production database
- ✅ **Seed script updated**: `backend/scripts/seed_billing_tiers.py` reflects final pricing

**Files Modified**:
- `backend/scripts/seed_billing_tiers.py` - Updated tier definitions with fee disclosures
- `backend/update_all_tiers_final.py` - Created database update script
- `documents/PRICING_STRUCTURE.md` - Created comprehensive pricing documentation

**Status**: Production-ready pricing structure, sustainable economics validated

---

### 2025-12-30: Error Prevention Safeguards ✅ **FULLY INTEGRATED**
- ✅ **CI/CD Pipeline** (`.github/workflows/ci.yml`): Automated testing on push/PR
  - Backend tests (Python 3.10 & 3.11), frontend linting, integration tests
  - Security scanning (Bandit, npm audit)
  - ⚠️ Linters currently non-blocking (use `|| echo` fallback) - can be made blocking if desired
- ✅ **PR Template** (`.github/pull_request_template.md`): Comprehensive review checklist
  - Response structure validation, header validation, shared constants checks
  - Security, testing, documentation requirements
- ✅ **API Doc Generator** (`backend/generate_api_docs.py`): Auto-generates docs from code
  - OpenAPI schema, Markdown docs, TypeScript types
  - Run manually: `python backend/generate_api_docs.py`
  - Can be added to CI/CD if needed
- ✅ **Production Logging** (`backend/src/logging_config.py`): Structured JSON logging
  - Request/response logging, audit logging, error tracking
  - **INTEGRATED** in `src/api.py:14,73`
- ✅ **Enhanced Startup Validation** (`backend/src/startup_checks.py`): Production config + comprehensive checks
  - Production: Validates JWT secrets, database config, CORS settings
  - Development: Optional env vars, DB connection, secrets strength validation
  - **INTEGRATED** in `src/api.py:64` (production checks run automatically)
  - Run comprehensive checks: `from src.startup_checks import run_comprehensive_checks; run_comprehensive_checks()`
- ✅ **Error Pattern Detection** (`backend/src/utils/error_tracking.py`): Recurring error detection
  - Middleware tracks error patterns automatically (alerts after 10 occurrences)
  - Structured error logging with full context
  - **INTEGRATED** in `src/api.py:39,91` (middleware active)
  - View error report: `python -c "from src.utils.error_tracking import ErrorPatternDetector; print(ErrorPatternDetector.get_error_report())"`

**Status**: 6/6 safeguards fully integrated and active
**Documentation**: See `ADDITIONAL_SAFEGUARDS.md` for detailed documentation
**Files Removed**: `backend/src/utils/startup_checks.py` (functionality merged into `src/startup_checks.py`)

---

### 2025-12-04: Production Automation Suite

- ✅ Created comprehensive automation scripts for production deployment
- ✅ **Deployment Automation** (`scripts/deploy-production.sh`): End-to-end production deployment with gradual rollout
- ✅ **Environment Validation** (`scripts/validate-environment.sh`): Validates all required environment variables
- ✅ **Database Backup** (`scripts/backup-database.sh`): Automated Cloud SQL backup creation
- ✅ **Rollback Procedure** (`scripts/rollback-deployment.sh`): Safe deployment rollback with health checks
- ✅ **Smoke Tests** (`scripts/smoke-test.sh`): Post-deployment verification (13 tests)
- ✅ **Screenshot Helper** (`scripts/capture-screenshots.sh`): Interactive guide for GCP Marketplace screenshots
- ✅ **Demo Data Seeder** (`backend/seed_screenshot_data.py`): Generates realistic demo data
- ✅ Updated **README.md**: Added automation scripts section and documentation links
- ✅ Enhanced **CI/CD Pipeline**: Made linters blocking, enabled E2E tests
- ✅ Security hardening: Environment-aware HSTS headers in production
- ✅ Updated **.gitignore**: Added backup cache, screenshots, test data exclusions

---

### 2025-11-27: Security & Testing
- ✅ Added case-insensitive organization name validation
- ✅ Fixed soft-delete slug filtering (allow reuse after deletion)
- ✅ Created comprehensive test suite (test_org_final.py)
- ✅ Cleaned up 22 orphaned soft-deleted organizations
- ✅ Conducted comprehensive security audit (30/30 tests passed)
- ✅ Added input length validation (username, password limits)
- ✅ Confirmed production-ready for Google Cloud Marketplace

---

## 🔐 Security Testing

### Running Security Audits

```bash
# Comprehensive security audit (30+ tests)
python security_audit_comprehensive.py

# Tests include:
# - SQL injection prevention
# - XSS/Command injection blocking
# - JWT token security
# - Rate limiting enforcement
# - Multi-tenancy isolation
# - Input validation
# - Error handling
```

### Security Test Results (Latest)

**Date**: 2025-11-27
**Status**: ✅ PRODUCTION READY FOR GCP MARKETPLACE
**Score**: 97% (30/31 tests passed)

**Security Audit**:
- ✅ 0 Critical Issues
- ✅ 0 High Severity
- ⚠️ 1 Medium (rate limiting - expected behavior)

**Dependency Audit**:
- ✅ 2 vulnerabilities FIXED (glob, anyio)
- ⚠️ 3 vulnerabilities DOCUMENTED with mitigations (xlsx, ecdsa x2)
- ✅ All remaining issues have documented risk assessments

**Testing**:
- Run security audit: `python security_audit_comprehensive.py`
- Review security policy: `documents/SECURITY.md`

---

### Input Validation Limits

**All user inputs are validated** (`backend/src/schemas.py`):

```python
# User fields
username: 3-50 chars, alphanumeric + underscore/dash only
password: 8-128 chars, must have upper, lower, digit
full_name: max 100 chars
email: valid email format (EmailStr)

# Organization fields
name: 1-255 chars
slug: 3-255 chars, lowercase alphanumeric + dash only
description: unlimited (but sanitized)
```

---

---

## Subagent Guidelines

When spawning subagents:

- **Explore agent**: For "how does X work?" or "find files related to Y"
- **Plan agent**: For complex features requiring architectural decisions
- **Testing agents**: For running test suites after changes
- **Database agent**: For migration issues or schema changes

**Important**: Subagents inherit this CLAUDE.md context automatically.

---

## Quick Reference URLs

- **Frontend**: http://localhost:5173
- **Backend**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Test Coverage**: backend/htmlcov/index.html (after running with --cov)

### Quick AP2 Reference

**What AP2 Does:**
1. User creates Intent Mandate: "Auto-approve office supplies from Amazon up to $200/month"
2. Employee submits $45 Amazon office supplies expense
3. AI Agent checks Intent Mandate → Matches! → Auto-approves instantly
4. Manager only sees exceptions that don't match any mandates

**Key Endpoints:**
- `POST /api/ap2/intent-mandate` - Create authorization rules
- `GET /api/ap2/user/mandates` - List user's mandates
- `GET /api/ap2/stats` - Usage statistics
- `POST /api/ap2/intent-mandate/{id}/revoke` - GDPR revocation

**Database Tables:**
- `intent_mandates` - User authorization constraints
- `cart_mandates` - Approved expense items
- `payment_mandates` - Payment execution records
- `expenses.auto_approved` - Boolean flag for AI decisions

**Success Criteria:**
- 60-70% of expenses auto-approved
- <1 minute approval time (vs 2-3 days manual)
- Clear ROI: "AI saved 8 hours this month"

---

## Git Workflow

```bash
# Standard commit message format
git commit -m "feat: add organization name validation

- Add case-insensitive duplicate name check
- Filter only active organizations
- Update tests

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"

# Create PR
gh pr create --title "Feature: Organization name validation" --body "..."
```

---

## Questions or Clarifications Needed?

If you need clarification on:
- **🎯 AP2 Strategy & Implementation**: See AP2 section above (lines 163-318)
- **Architecture**: Read `README.md` and code in `backend/src/`
- **Billing & Pricing**: See `documents/PRICING_STRUCTURE.md`, `backend/src/billing/`, and `backend/src/models_billing.py`
- **Testing**: Check `backend/tests/` for examples (30 test files)
- **Security**: Review `documents/SECURITY.md` and run `python security_audit_comprehensive.py`
- **Error Prevention**: See `documents/ADDITIONAL_SAFEGUARDS.md`
- **Deployment**: Check `backend/GCP_MARKETPLACE_TESTING.md` and `backend/CLOUD_RUN_DEPLOYMENT.md`
- **Legal/Compliance**: See `legal/PRIVACY_POLICY.md` and `legal/TERMS_OF_SERVICE.md`

**Key Principle**: AP2 autonomous agents are our competitive advantage. Intent Mandates enable instant auto-approval, not retroactive documentation.

**Use `/clear` before starting a new, unrelated task to maintain focus.**
