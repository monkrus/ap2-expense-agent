# AP2 Expense Management Agent - Claude Code Guide

This file provides context and best practices for Claude Code and subagents working on this project.

## Project Overview

**Stack**: Python FastAPI (backend) + React (frontend) + SQLite/PostgreSQL
**Architecture**: Multi-tenant SaaS with Google Cloud Marketplace integration
**Key Features**: Expense management, AP2 protocol, Stripe billing, organization management

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
cd backend && pytest tests/test_organizations.py -v

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
python cleanup_soft_deleted_orgs.py

# Seed test data
cd backend && python seed_tiers_quick.py
```

### Testing Organization Features

```bash
# Comprehensive organization tests (from project root)
python test_org_final.py

# Full test suite with new user registration
python test_organization_scenarios.py
```

---

## Code Architecture

### Backend Structure (`backend/src/`)

```
api.py                      # Main FastAPI application
routes/
  ├── organizations.py      # Organization CRUD, invitations, members
  ├── auth.py              # Authentication endpoints
  ├── billing.py           # Subscription & billing
  ├── billing_org.py       # Organization-level billing
  ├── payment.py           # Stripe checkout sessions
  └── webhooks.py          # Stripe webhook handlers
models.py                  # SQLAlchemy ORM models
models_billing.py          # Billing-specific models
billing/
  ├── tier_limits.py       # Subscription tier definitions
  ├── subscription_service.py
  └── limit_enforcer.py    # Usage limit enforcement
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

## Subscription Tiers

Defined in `backend/src/billing/tier_limits.py`:

| Tier | Monthly Price | Max Orgs | Max Users | Max Expenses/Mo |
|------|--------------|----------|-----------|-----------------|
| FREE | $0 | 1 | 1 | 20 |
| STARTER | $29 | 3 | 5 | 50 |
| PROFESSIONAL | $99 | 10 | 25 | Unlimited |
| ENTERPRISE | $399 | 25 | 100 | Unlimited |

**Critical**: Free tier has hard limits enforced. Other tiers may have usage-based billing.

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
**Fix**: Restart backend server or run `python cleanup_soft_deleted_orgs.py`

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

⚠️ **Multi-tenant Data**: Always filter by `organization_id` and `is_active=True`
⚠️ **Soft Deletes**: Never hard delete organizations/users - use `is_active=False`
⚠️ **Tier Limits**: Free tier has hard enforcement - test carefully
⚠️ **Windows Paths**: Use forward slashes in code, backslashes in shell commands
⚠️ **Server Restart**: Code changes require backend restart (no hot reload for imports)

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
cd backend && pytest tests/test_organizations.py::test_duplicate_name_validation -v
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
- `backend/src/routes/billing_org.py`
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

Keep this updated when making significant changes:

**2025-11-27**:
- ✅ Added case-insensitive organization name validation
- ✅ Fixed soft-delete slug filtering (allow reuse after deletion)
- ✅ Created comprehensive test suite (test_org_final.py)
- ✅ Cleaned up 22 orphaned soft-deleted organizations

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
- **Architecture**: Read `README.md` and code in `backend/src/`
- **Billing**: See `MONETIZATION_STRATEGY.md` and `backend/src/billing/`
- **Testing**: Check `backend/tests/` for examples
- **Security**: Review `SECURITY_REMEDIATION_REPORT.md`

**Use `/clear` before starting a new, unrelated task to maintain focus.**
