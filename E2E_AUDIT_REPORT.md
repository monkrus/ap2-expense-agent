# AP2 Expense Agent — End-to-End Audit Report

**Date:** 2026-04-28
**Scope:** Full-stack E2E testing for Google Cloud Marketplace readiness
**Method:** Live API testing (backend on localhost:8000), code review, frontend build validation

---

## EXECUTIVE SUMMARY

**Overall Readiness: NOT YET READY FOR MARKETPLACE**

The application has a solid foundation — good multi-tenant architecture, comprehensive API surface, and working AP2 protocol flow. However, there are **4 CRITICAL bugs**, **12 HIGH-severity issues**, and numerous medium/low findings that must be addressed before a GCP Marketplace listing.

| Severity | Count | Summary |
|----------|-------|---------|
| CRITICAL | 4 | 500 errors on core endpoints, missing dependency, broken export, GDPR not registered |
| HIGH | 12 | Security bypasses, logic bugs, inconsistent APIs, self-approval allowed |
| MEDIUM | 15 | UX issues, missing validation, env var mismatches, stale data risks |
| LOW | 8 | Code quality, cosmetic, optimization |

---

## CRITICAL ISSUES (Must fix before any release)

### CRIT-1: `GET /api/v1/expenses` returns 500 when no org header — parameter shadowing bug

**File:** `backend/src/routes/expenses.py:412`
**Repro:** `GET /api/v1/expenses` with valid token but no `X-Organization-Id` header
**Response:** `{"error":{"message":"AttributeError: 'NoneType' object has no attribute 'HTTP_400_BAD_REQUEST'","code":"INTERNAL_ERROR","status":500}}`

**Root cause:** The query parameter `status: Optional[str] = None` on line 412 **shadows** the imported `from fastapi import status` module. When `status` is `None` (its default), line 430 calls `status.HTTP_400_BAD_REQUEST` which becomes `None.HTTP_400_BAD_REQUEST` → AttributeError → 500.

**Fix:** Rename the parameter to `expense_status` or alias the import: `from fastapi import status as http_status`.

**Impact:** Every customer who hits the expense list without an org header sees a raw 500 error instead of a clear "Organization required" message. This is the most-trafficked endpoint in the app.

---

### CRIT-2: `GET /api/v1/expenses/export?format=csv` returns 500 — missing `reportlab` dependency

**Repro:** `GET /api/v1/expenses/export?format=csv` with valid auth + org
**Response:** `{"error":{"message":"ModuleNotFoundError: No module named 'reportlab'","code":"INTERNAL_ERROR","status":500}}`

**Root cause:** The export endpoint imports `reportlab` at runtime but it's not in `requirements.txt`.

**Fix:** Add `reportlab` to requirements.txt, or handle the ImportError gracefully.

**Impact:** The entire export feature (CSV, PDF) is broken. This is a core customer workflow.

---

### CRIT-3: GDPR compliance endpoints not registered in the app

**File:** `backend/src/api.py` — no `gdpr_router` import or `include_router` call
**Repro:** `GET /api/gdpr/export/my-data` → 404

**Root cause:** The GDPR route file exists (`backend/src/routes/gdpr.py`) but is never imported or registered in `api.py`.

**Fix:** Add `from .routes.gdpr import router as gdpr_router` and `app.include_router(gdpr_router)` to `api.py`.

**Impact:** GDPR data export and deletion rights are completely non-functional. This is a compliance blocker for EU customers and may be flagged in GCP Marketplace review.

---

### CRIT-4: Frontend unit test suite entirely broken — missing `@testing-library/dom`

**Repro:** `cd frontend && npm run test:unit -- --run` → all 5 suites crash at import time
**Root cause:** `@testing-library/react@16` requires `@testing-library/dom` as a peer dependency, but it's not in `package.json`.

**Fix:** `npm install --save-dev @testing-library/dom`

**Impact:** Zero unit test coverage can be verified. CI will always fail on tests.

---

## HIGH SEVERITY ISSUES

### HIGH-1: `GET /api/v1/expenses/categories` returns "Expense not found" (route ordering bug)

**Repro:** `GET /api/v1/expenses/categories` with valid auth + org header
**Response:** `{"detail":"Expense not found"}`

**Root cause:** The `/{expense_id}` route catches `categories` as an expense ID before the `/categories` static route can match. Classic FastAPI route ordering issue — static paths must be defined BEFORE parameterized paths.

**Fix:** Move the `/categories` endpoint definition above `/{expense_id}` in `expenses.py`.

---

### HIGH-2: Admin can self-approve their own expenses

**Repro:** Admin creates expense, then approves it themselves → succeeds
**Code:** `backend/src/routes/expenses.py:1532` — `if expense.user_id == current_user.id and current_user.role != UserRole.ADMIN`

The self-approval check explicitly exempts system admins. This violates separation of duties — a fundamental accounting control. In a real organization, no single person should be able to both submit and approve expenses.

**Fix:** Remove the `UserRole.ADMIN` exemption. Require a different user to approve all expenses regardless of role.

---

### HIGH-3: `/my-organizations` endpoint returns 403 — tenant middleware conflict

**Repro:** `GET /api/v1/organizations/my-organizations` with valid admin token → 403 "You do not have access to this organization"

**Root cause:** The tenant middleware sets a context org from some header/default, and the route `/my-organizations` gets matched by the parameterized `/{organization_id}` route, treating "my-organizations" as an org ID. The org access check then fails.

**Fix:** Define `/my-organizations` (or just use `GET /api/v1/organizations` which works) and ensure static routes are before `/{organization_id}`. Or remove the dead endpoint reference.

**Impact:** Frontend code calling `/my-organizations` will fail. The working endpoint is `GET /api/v1/organizations`.

---

### HIGH-4: `/login/form` endpoint bypasses rate limiting

**File:** `backend/src/routes/auth.py:292-300`
**Root cause:** The `/login/form` endpoint delegates to `login()` but doesn't have its own `@limiter.limit(RateLimits.LOGIN)` decorator. Rate limits are per-decorated-function, so attackers can brute-force via `/login/form` without throttling.

**Fix:** Add `@limiter.limit(RateLimits.LOGIN)` directly to `login_form`.

---

### HIGH-5: Password-reset token leaked in API response on SQLite databases

**File:** `backend/src/routes/auth.py:396-398`
```python
if settings.database_url and "sqlite" in settings.database_url.lower():
    response_data["reset_token"] = token
```

**Root cause:** Uses database URL as a proxy for "dev mode". Any CI/CD pipeline or staging env using SQLite leaks real password reset tokens, enabling account takeover.

**Fix:** Gate on `settings.environment == "development"` only, or remove entirely.

---

### HIGH-6: `/metrics` Prometheus endpoint is unauthenticated

**File:** `backend/src/api.py:232-241`
**Impact:** Exposes full API surface, call rates, and error patterns to any unauthenticated caller. High-value reconnaissance for attackers.

**Fix:** Add `Depends(require_admin)` or restrict via infrastructure.

---

### HIGH-7: `create-from-extraction` accepts raw `dict` body — bypasses all validation

**File:** `backend/src/routes/receipts.py:495-500`
**Root cause:** The endpoint accepts `data: dict` instead of a Pydantic schema. User input bypasses HTML-escaping, length limits, and category allowlist validation.

**Fix:** Replace `data: dict` with a typed Pydantic model.

---

### HIGH-8: Inconsistent API base URL across frontend service layer

**Files:** `api.js` uses `VITE_API_URL`, `apiClient.js` uses `VITE_API_BASE_URL`, `adminAPI.js` uses `VITE_API_BASE_URL` from constants
**Impact:** In production where only one env var is set, roughly half of API calls go to the wrong host. Billing, admin, and org calls silently break.

**Fix:** Consolidate to a single env var across all service files.

---

### HIGH-9: Frontend `api.js` `authAPI.login` posts to wrong path

**File:** `frontend/src/services/api.js:501` — posts to `/api/auth/login` (missing `/v1`)
**Impact:** Any component using `authAPI.login` directly gets a 404. The `AuthContext` uses the correct path, masking the issue.

**Fix:** Change to `/api/v1/auth/login` or remove the duplicate `authAPI`.

---

### HIGH-10: Frontend `api.js` hard-redirects on 401 instead of token refresh

**File:** `frontend/src/services/api.js`
**Root cause:** On 401, clears localStorage and redirects to `/login` instead of using the refresh token. Users who leave a tab open get logged out mid-session.

**Fix:** Route calls through `apiClient.apiFetch` which already handles refresh, or add refresh logic to `api.js`.

---

### HIGH-11: OAuth2 hardcoded client secret and in-memory auth code store

**File:** `backend/src/routes/oauth.py:31-48`
**Root cause:** Client secret `"dev-secret-change-in-production"` is hardcoded, never loaded from env. Auth codes are stored in a process-level dict, breaking in multi-replica deployments.

**Fix:** Load secret from env var. Move auth code store to Redis.

---

### HIGH-12: Google OAuth callback doesn't validate `state` parameter (CSRF)

**File:** `backend/src/routes/oauth.py:345-428`
**Root cause:** The `state` parameter is received but never compared to the original nonce. Open to CSRF and open-redirect attacks.

**Fix:** Use the existing `NonceService` to validate state.

---

## MEDIUM SEVERITY ISSUES

### MED-1: Approve/reject use PUT instead of POST — unconventional REST design

Approve (`PUT /{id}/approve`) and reject (`PUT /{id}/reject`) are state-change operations, not idempotent resource updates. The frontend or any REST client would naturally try POST first (as the test agents did), getting 405 Method Not Allowed.

### MED-2: Login error reveals remaining attempt count and account existence

`backend/src/routes/auth.py:229-233` — Returns distinct messages for "wrong password" (with attempt count) vs "account suspended" (403), enabling username enumeration.

### MED-3: Budget creation returns empty response

`POST /api/budgets/` returns empty body on success. Customer gets no confirmation, no budget ID back.

### MED-4: Recurring expenses endpoint returns 404 despite router being registered

The router is registered but `GET /api/recurring-expenses/` returns empty. May have route ordering or path mismatch issues.

### MED-5: CSP allows `'unsafe-inline'` and `'unsafe-eval'` — defeats XSS protection

**File:** `backend/src/security_middleware.py:35`

### MED-6: HSTS and error masking use `os.getenv("ENVIRONMENT")` instead of `settings.environment`

**Files:** `security_middleware.py:27`, `error_handlers.py:326` — Silently skips HSTS and leaks stack traces when env is set via `.env` file.

### MED-7: Frontend uses native `alert()` and `window.confirm()` in 7+ places

Breaks visual design, untestable in jsdom, blocked in some embedded webviews (including GCP Console).

### MED-8: `GoogleCallback.jsx:44` logs full user object to browser console

Security issue: user data visible in console on OAuth login.

### MED-9: Expense report counts don't match reality

After approving and withdrawing expenses, the report shows `approved_count: 0` for an expense that has status `withdrawn` (was approved, then withdrawn). The count logic only checks for exact status match, not for the approval history.

### MED-10: `approved_at` field is set even on rejected expenses

In the test, the rejected expense has `approved_at: "2026-04-28T04:36:18.659334"`. This is confusing — a rejected expense should not have an `approved_at` timestamp.

### MED-11: API prefix inconsistency across route modules

| Module | Prefix |
|--------|--------|
| Expenses | `/api/v1/expenses` |
| Auth | `/api/v1/auth` |
| Organizations | `/api/v1/organizations` |
| Budgets | `/api/budgets` (missing `/v1`) |
| AP2 | `/api/ap2` (missing `/v1`) |
| Notifications | `/api/notifications` (missing `/v1`) |
| Recurring | `/api/recurring-expenses` (missing `/v1`) |

Inconsistent versioning makes the API harder to document and consume. Frontend services assume `/api/v1` for some calls but not others.

### MED-12: 23 React hooks `exhaustive-deps` violations — stale data risk

Most impactful: `AdminDashboard.jsx`, `OrganizationManagement.jsx`, `UserManagementDashboard.jsx` — fetch functions omitted from `useEffect` deps cause stale UI.

### MED-13: No 404 page in frontend — unrecognized paths fall through silently

Custom path-based routing in `AppWrapper.jsx` has no fallback for unknown routes.

### MED-14: Feature flags `VITE_ENABLE_AI`, `VITE_ENABLE_OCR`, `VITE_ENABLE_AP2` not documented

Default to `false` — operators won't know to enable them, so paid tier features appear disabled.

### MED-15: TOTP backup codes stored as plaintext comma-separated string

Should be hashed like passwords to protect against DB breach.

---

## LOW SEVERITY ISSUES

1. **Refresh tokens not rotated on use** — stolen tokens remain valid indefinitely
2. **Admin user list allows `per_page=1000`** — enables bulk data exfiltration
3. **Deprecated `onKeyPress` used in 3 components** — should be `onKeyDown`
4. **205 ESLint warnings** (130 unused vars, 23 hooks violations)
5. **Empty `vendor-react` Vite chunk** in production build
6. **`validate_secrets()` checks wrong env var** (`JWT_SECRET_KEY` vs `JWT_SECRET`)
7. **Debug `console.log` in production** — 17 instances across frontend
8. **PDF upload validation logs but doesn't reject** malicious PDFs with `/JavaScript`

---

## LIVE API TEST RESULTS SUMMARY

| Test | Result | Notes |
|------|--------|-------|
| Setup status | PASS | Returns `{"needs_setup":false}` |
| Login (JSON) | PASS | Returns token + user object |
| Login (form-urlencoded) | FAIL (422) | Expects JSON body, not form data — inconsistent with OAuth2 spec |
| Get current user | PASS | Returns user profile |
| Registration | PASS | Creates user with auto-org |
| List organizations | PASS | `GET /api/v1/organizations` works |
| `/my-organizations` | FAIL (403) | Route ordering conflict |
| Create expense | PASS | Returns expense with pending status |
| List expenses (with org) | PASS | Returns array of expenses |
| List expenses (no org) | **FAIL (500)** | Parameter shadowing bug |
| Categories | FAIL (404) | Route ordering — caught by `/{expense_id}` |
| Export CSV | **FAIL (500)** | Missing `reportlab` module |
| Approve expense (PUT) | PASS | Works correctly |
| Reject expense (PUT) | PASS | Works, creates notification |
| Self-approve (admin) | PASS (but wrong) | Admin can self-approve — logic flaw |
| Delete/withdraw expense | PASS | Returns "withdrawn" status |
| Cross-org isolation | PASS | Returns 403 for fake org ID |
| AP2 intent mandate | PASS | Creates with signature |
| Budget create | PASS (empty body) | No response body — confusing |
| Budget health | PASS | Returns health summary |
| Analytics variance | PASS | Returns variance report |
| Notifications | PASS | Works at `/api/notifications` |
| GDPR export | FAIL (404) | Router not registered |
| Admin list users | PASS | Returns paginated users |
| Recurring expenses | FAIL (empty) | Returns nothing |

---

## RECOMMENDATIONS BY PRIORITY

### Before Marketplace Submission (Blockers)

1. Fix CRIT-1: Rename `status` parameter in `list_expenses` to avoid shadowing
2. Fix CRIT-2: Add `reportlab` to requirements.txt
3. Fix CRIT-3: Register GDPR router in `api.py`
4. Fix HIGH-1: Reorder routes — static paths before `/{expense_id}`
5. Fix HIGH-2: Remove admin self-approval exemption
6. Fix HIGH-3: Fix `/my-organizations` route conflict
7. Fix HIGH-4: Add rate limit to `/login/form`
8. Fix HIGH-5: Change dev-mode detection from DB URL to `settings.environment`
9. Fix HIGH-6: Protect `/metrics` endpoint
10. Fix HIGH-7: Add Pydantic schema to `create-from-extraction`
11. Fix MED-5: Remove `unsafe-inline`/`unsafe-eval` from CSP
12. Fix MED-6: Use `settings.environment` consistently

### Before Customer Launch

13. Fix HIGH-8 through HIGH-12 (frontend API consistency, OAuth security)
14. Fix MED-1: Change approve/reject to POST
15. Fix MED-3: Return budget object on creation
16. Fix MED-10: Don't set `approved_at` on rejected expenses
17. Fix MED-11: Standardize API prefixes to `/api/v1/`
18. Fix CRIT-4: Install missing test dependency
19. Fix MED-7: Replace native browser dialogs with React modals

### Short-Term Improvements

20. Fix remaining MEDIUM and LOW issues
21. Add comprehensive E2E test suite that runs against live API
22. Run `pip-audit` on requirements.txt — GCP reviews check for known CVEs
23. Document all env vars needed for production deployment
