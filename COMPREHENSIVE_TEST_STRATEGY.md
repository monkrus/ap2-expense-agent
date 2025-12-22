# AP2 Expense Management Agent - Comprehensive Test Strategy

**Generated**: 2025-12-21
**Purpose**: Deep, exhaustive test coverage for all roles, tiers, flows, and interactions

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Test Dimensions Matrix](#test-dimensions-matrix)
3. [Role-Based Test Scenarios](#role-based-test-scenarios)
4. [Tier-Based Test Scenarios](#tier-based-test-scenarios)
5. [Critical Flow Tests](#critical-flow-tests)
6. [Multi-Tenancy & Security Tests](#multi-tenancy--security-tests)
7. [State Machine Tests](#state-machine-tests)
8. [Integration Tests](#integration-tests)
9. [Edge Cases & Boundary Tests](#edge-cases--boundary-tests)
10. [Performance & Load Tests](#performance--load-tests)
11. [Priority Test Execution Plan](#priority-test-execution-plan)

---

## System Overview

### User Roles (Global System Level)

| Role | Permissions | Approval Limit | Key Capabilities |
|------|-------------|----------------|------------------|
| **ADMIN** | All permissions | Unlimited | System configuration, all expenses, user management |
| **MANAGER** | Department-scoped | ≤ $5,000 | View/approve dept expenses, bulk operations, reporting |
| **ACCOUNTANT** | Read-only, all visibility | None | View all expenses/reports, export, audit trails |
| **EMPLOYEE** | Own resources only | None | Submit expenses, view own data, upload receipts |

### Organization Roles (Multi-Tenant Level)

| Role | Hierarchy | Key Powers |
|------|-----------|------------|
| **OWNER** | Highest | Delete org, grant OWNER role, remove ADMINs, all org operations |
| **ADMIN** | High | Manage members (except OWNER), update settings, approve expenses |
| **MANAGER** | Medium | View org data, manage team expenses |
| **MEMBER** | Low | Standard employee access within org |

### Subscription Tiers

| Tier | Price | Users | Orgs | Expenses/Mo | AI | AP2 | OCR | Special Features |
|------|-------|-------|------|-------------|----|----|-----|------------------|
| **FREE** | $0 | 1 | 1 | 20 | 0 | 0 | 5 | Hard limits, daily rate limits |
| **STARTER** | $29 | 5 | 3 | 50 | 100 | 10 | 50 | Email support |
| **PROFESSIONAL** | $99 | 25 | 10 | ∞ | 2,000 | 50 | 500 | Priority support, chat |
| **ENTERPRISE** | $399 | 100 | 25 | ∞ | ∞ | ∞ | 5,000 | SSO, API, analytics, SLA 99.9% |

### Critical State Machines

#### Expense Status Flow
```
PENDING → APPROVED ✓
PENDING → REJECTED ✓
PENDING → PROCESSING ✓
PENDING → WITHDRAWN ✓
APPROVED → PROCESSING ✓
PROCESSING → [Payment completion states]
```

#### Organization Status
```
ACTIVE → INACTIVE (soft delete) ✓
INACTIVE → [Cannot be reactivated] (slug reuse allowed)
```

#### Subscription Status
```
active → trialing → past_due → canceled
```

#### Invitation Status
```
pending → accepted ✓
pending → expired ✓
pending → revoked ✓
```

---

## Test Dimensions Matrix

### Dimension 1: Roles × Permissions

**Matrix Size**: 4 user roles × 50+ permissions × 2 organization roles = **400+ test cases**

| User Role | Org Role | Test Scenarios |
|-----------|----------|----------------|
| EMPLOYEE | MEMBER | Can submit expense, view own, cannot approve, cannot view others |
| EMPLOYEE | ADMIN | Can submit + approve (org context), view all org expenses |
| EMPLOYEE | OWNER | Can submit + approve + delete org, manage all members |
| MANAGER | MEMBER | Can view dept expenses, approve ≤ $5K, bulk approve |
| MANAGER | ADMIN | Can view all org + approve ≤ $5K + manage members |
| MANAGER | OWNER | Full org control + $5K approval limit |
| ACCOUNTANT | MEMBER | Read-only all expenses, cannot approve, can export |
| ACCOUNTANT | ADMIN | Read-only + manage members (org admin powers) |
| ACCOUNTANT | OWNER | Read-only + org owner powers (unusual edge case) |
| ADMIN | MEMBER | Full permissions regardless of org role |
| ADMIN | ADMIN | Full permissions |
| ADMIN | OWNER | Full permissions + org ownership |

**Priority**: 🔴 CRITICAL - Core authorization model

---

### Dimension 2: Tiers × Limits

**Matrix Size**: 4 tiers × 8 limit types × 3 enforcement modes = **96+ test cases**

| Tier | Limit Type | Current | At Limit | Over Limit | Expected Behavior |
|------|------------|---------|----------|------------|-------------------|
| FREE | Expenses/mo | 10 | 20 | 21 | ❌ HARD BLOCK (402 Payment Required) |
| FREE | Users | 1 | 1 | 2 | ❌ HARD BLOCK (402) |
| FREE | Organizations | 1 | 1 | 2 | ❌ HARD BLOCK (402) |
| FREE | AI categorizations | 0 | 0 | 1 | ❌ HARD BLOCK (402) |
| FREE | AP2 transactions | 0 | 0 | 1 | ❌ HARD BLOCK (402) |
| FREE | OCR scans | 3 | 5 | 6 | ❌ HARD BLOCK (402) |
| STARTER | Expenses/mo | 25 | 50 | 51 | ⚠️ SOFT LIMIT (overage fee $0.01) |
| STARTER | Users | 3 | 5 | 6 | ⚠️ SOFT LIMIT (overage fee) |
| PROFESSIONAL | Expenses/mo | 1000 | - | ∞ | ✅ UNLIMITED |
| ENTERPRISE | All limits | - | - | ∞ | ✅ UNLIMITED (except users: 100) |

**Daily Rate Limits (FREE tier only)**:
- Expenses: 10/day
- OCR scans: 3/day
- AI categorizations: 0/day (blocked)
- AP2 transactions: 0/day (blocked)

**Priority**: 🔴 CRITICAL - Revenue protection, free tier abuse prevention

---

### Dimension 3: Flows × States

**Matrix Size**: 12 major flows × avg 5 states each = **60+ test cases**

#### Flow 1: User Registration → Onboarding
```
1. Register (rate-limited: 3/hour) → User created (is_verified=False)
2. Email verification → User verified (is_verified=True)
3. Auto-create Free subscription → Subscription created (status=active)
4. Auto-create personal organization → Organization created (max_members=1)
5. User becomes OWNER of personal org → OrganizationMember created
```

**Edge Cases**:
- ✅ Duplicate email/username during registration
- ✅ Expired verification token
- ✅ Rate limit exceeded (429 response)
- ✅ Subscription creation failure doesn't break registration

**Priority**: 🟠 HIGH

---

#### Flow 2: Organization Creation → Member Invitation
```
1. User creates organization → Check tier limits (owned_orgs < max_organizations)
2. Slug/name validation → Check for duplicates (only ACTIVE orgs)
3. Organization created → User becomes OWNER
4. Invite member → Check user limits (members < max_users)
5. Member accepts invite → OrganizationMember created
```

**Edge Cases**:
- ✅ Recreate organization with same slug after soft delete
- ✅ Case-insensitive name collision
- ✅ Race condition on slug creation (IntegrityError handling)
- ✅ Invitation expiration (7 days)
- ✅ Invite already-member user
- ✅ Accept invite with wrong email
- ✅ User limit exceeded during invitation

**Priority**: 🔴 CRITICAL - Multi-tenancy foundation

---

#### Flow 3: Expense Submission → Auto-Approval → Payment
```
1. Employee submits expense → Validate amount, category, vendor
2. Check tier limits → expenses_this_month < max_expenses_per_month
3. Evaluate approval policies → Match by priority (highest first)
4. Policy conditions match → Auto-approve (status=APPROVED, auto_approved=True)
5. If no match → Manual approval required (status=PENDING)
6. Manual approval → Manager/Admin approves (approved_by, approved_at)
7. Payment mandate creation → AP2 protocol integration
8. Payment execution → Update expense (transaction_id)
```

**Edge Cases**:
- ✅ Multiple policies match (priority resolution)
- ✅ Policy daily/monthly limits exhausted for user
- ✅ Manager approves >$5K expense (should fail)
- ✅ Manager approves expense from different department (should fail)
- ✅ Accountant tries to approve (should fail - read-only)
- ✅ User tries to approve own expense (should fail)
- ✅ Auto-approval with require_receipt=True but no receipt uploaded
- ✅ Concurrent expense submissions hitting monthly limit

**Priority**: 🔴 CRITICAL - Core business flow

---

#### Flow 4: Member Role Changes → Permission Cascade
```
1. OWNER updates member role → Check permissions (only OWNER can grant OWNER)
2. Role updated → OrganizationMember.role changed
3. User accesses resources → Permissions re-evaluated
```

**Edge Cases**:
- ✅ ADMIN tries to grant OWNER role to someone (should fail)
- ✅ ADMIN tries to remove another ADMIN (should fail, only OWNER can)
- ✅ User tries to modify own role (should fail - CRITICAL-2 security fix)
- ✅ OWNER cannot be removed from organization
- ✅ OWNER role cannot be changed (even by OWNER)
- ✅ Changing role from ADMIN to MEMBER removes admin permissions immediately

**Priority**: 🔴 CRITICAL - Security boundary

---

#### Flow 5: Organization Deletion → Cascade Effects
```
1. OWNER deletes organization → Only OWNER can delete
2. Organization soft-deleted → is_active=False
3. All members soft-deleted → member.is_active=False
4. User caches invalidated → invalidate_user_cache(all members)
5. Slug becomes available → Can be reused for new org
6. Expenses/data retained → Audit trail preservation
```

**Edge Cases**:
- ✅ Non-OWNER tries to delete (should fail)
- ✅ Recreate org with same slug immediately after deletion
- ✅ Members cannot access org after deletion (403 Forbidden)
- ✅ Deleted org not counted toward tier limits
- ✅ Soft-deleted org expenses remain in database (audit)

**Priority**: 🟠 HIGH

---

#### Flow 6: Billing Tier Upgrade → Limit Changes
```
1. User upgrades subscription (Stripe checkout) → Payment successful
2. Stripe webhook received → Subscription.tier updated
3. Organization limits updated → max_members, max_expenses_per_month increased
4. Previously blocked features enabled → AI, AP2 access granted
5. Usage overage fees stop → Hard limits → Soft limits
```

**Edge Cases**:
- ✅ Upgrade during mid-month (prorated billing)
- ✅ Downgrade with current usage > new tier limit
- ✅ Subscription canceled but still in grace period
- ✅ Payment failure during renewal (subscription becomes past_due)
- ✅ GCP Marketplace entitlement vs. Stripe subscription conflict

**Priority**: 🟠 HIGH - Revenue critical

---

#### Flow 7: Receipt Upload → OCR → Expense Pre-fill
```
1. User uploads receipt → Validate file size (≤10MB), type (image/pdf)
2. Check OCR limit → ocr_scans_this_month < tier_limit
3. OCR extraction → extracted_amount, extracted_vendor, extracted_date
4. Pre-fill expense form → User reviews and submits
5. Receipt attached to expense → Receipt.expense_id set
```

**Edge Cases**:
- ✅ OCR limit exceeded (FREE: 5/month, STARTER: 50/month)
- ✅ Invalid file type (accept only images, PDFs)
- ✅ File size >10MB (security mitigation)
- ✅ OCR extraction fails (return empty fields, don't block upload)
- ✅ Multiple receipts for one expense
- ✅ Receipt uploaded without expense (orphaned)

**Priority**: 🟡 MEDIUM

---

#### Flow 8: Recurring Expense Scheduling → Auto-Submission
```
1. User creates recurring template → frequency, start_date, end_date
2. Scheduler runs (cron job) → Check next_run_date
3. Create ScheduledExpense → status=pending
4. Submit expense → Create Expense linked to template
5. Update template stats → total_submitted++, last_submitted_at
6. Notify user → ExpenseNotification created
```

**Edge Cases**:
- ✅ Template created but auto_submit=False (notification only)
- ✅ Expense limit reached during auto-submission (skip or fail?)
- ✅ Template paused (is_paused=True) - should not submit
- ✅ Template end_date reached - should deactivate
- ✅ Scheduler runs late (next_run_date in past) - catch up or skip?
- ✅ Concurrent scheduler runs (idempotency)

**Priority**: 🟡 MEDIUM

---

#### Flow 9: Budget Tracking → Alerts → Enforcement
```
1. Budget created → amount, period (monthly/quarterly/yearly), warning_threshold (75%)
2. Expenses tracked → Calculate sum(expenses.amount) for period
3. Threshold reached (75%) → BudgetAlert created (alert_type=warning)
4. Critical threshold (90%) → BudgetAlert created (alert_type=critical)
5. Budget exceeded (100%) → BudgetAlert created (alert_type=exceeded)
6. Optional enforcement → Block new expenses if budget exceeded
```

**Edge Cases**:
- ✅ Multiple budgets for same org (category-specific vs. org-wide)
- ✅ User-specific budget vs. org-wide budget (which takes precedence?)
- ✅ Budget period rollover (reset at start of new period)
- ✅ Alert fatigue (duplicate alerts not sent within threshold)
- ✅ Budget updated mid-period (recalculate thresholds)

**Priority**: 🟡 MEDIUM

---

#### Flow 10: GCP Marketplace Procurement → Entitlement → Billing
```
1. Customer initiates purchase → GCP Marketplace UI
2. Procurement webhook received → Decode Pub/Sub message
3. Verify signature → Google-signed OIDC token + HMAC (dev only)
4. Link account → Create MarketplaceAccount (account_id, consumer_id, organization_id)
5. Create entitlement → MarketplaceEntitlement (plan, state=ACTIVE)
6. Update organization subscription → Map plan to tier (FREE/STARTER/PRO/ENTERPRISE)
7. Usage reporting (hourly) → Send usage metrics to GCP API
8. Entitlement changed → Webhook received, update tier
9. Entitlement canceled → Webhook received, downgrade to FREE or suspend
```

**Edge Cases**:
- ✅ Duplicate webhook delivery (idempotency via MarketplaceWebhookEvent)
- ✅ Webhook signature verification failure (reject with 403)
- ✅ Account already linked to different org (conflict resolution)
- ✅ Entitlement state PENDING → ACTIVE → CANCELLED transitions
- ✅ Grace period handling (ACTIVE → GRACE → CANCELLED)
- ✅ Trial period handling (trial_start, trial_end)
- ✅ Usage reporting failure (retry logic, DLQ)
- ✅ Plan name mismatch (unknown plan ID)
- ✅ Concurrent entitlement updates

**Priority**: 🔴 CRITICAL - GCP Marketplace integration (production requirement)

---

#### Flow 11: AP2 Payment Protocol → Intent → Cart → Payment
```
1. User creates Intent Mandate → Define constraints (amount limits, merchant whitelist)
2. Intent approved → status=active, signature captured
3. Create Cart Mandate → Items, total, merchant (within intent constraints)
4. Validate cart → total ≤ intent.max_amount, merchant in whitelist
5. User signs cart → user_signature
6. Create Payment Mandate → payment_method, audit_trail
7. Process payment → payment_processor_response
8. Link to expense → Expense.payment_mandate_id
```

**Edge Cases**:
- ✅ Cart violates intent constraints (amount, merchant)
- ✅ Intent expired (expiration date passed)
- ✅ Intent revoked mid-transaction
- ✅ Payment processor failure (status=failed, retry?)
- ✅ Concurrent cart creation from same intent
- ✅ AP2 limit exceeded (FREE: 0, STARTER: 10/month)

**Priority**: 🟡 MEDIUM (Feature flag)

---

#### Flow 12: Audit Trail → Tamper Detection → Compliance
```
1. User action occurs → AuditLog entry created
2. Calculate previous_hash → SHA-256 of last entry
3. Calculate entry_hash → SHA-256(id + action + details + previous_hash)
4. Chain validation → Verify hash chain integrity
5. Export audit log → GDPR compliance, legal hold
```

**Edge Cases**:
- ✅ Audit log tampering detection (broken hash chain)
- ✅ First audit entry (previous_hash=None)
- ✅ Concurrent audit log writes (sequence_number conflicts)
- ✅ Audit log retention period enforcement
- ✅ Export filtering (date range, user, action type)

**Priority**: 🟠 HIGH - Compliance requirement

---

## Role-Based Test Scenarios

### Scenario Set A: EMPLOYEE Role Tests

| Test ID | Description | Steps | Expected Result | Priority |
|---------|-------------|-------|-----------------|----------|
| ROLE-EMP-001 | Employee submits expense in own org | 1. Login as EMPLOYEE<br>2. Submit expense | ✅ Expense created (status=PENDING) | 🔴 |
| ROLE-EMP-002 | Employee views own expense | 1. Login as EMPLOYEE<br>2. GET /expenses/{own_expense_id} | ✅ 200 OK, expense returned | 🔴 |
| ROLE-EMP-003 | Employee views other's expense | 1. Login as EMPLOYEE<br>2. GET /expenses/{other_user_expense_id} | ❌ 403 Forbidden | 🔴 |
| ROLE-EMP-004 | Employee tries to approve expense | 1. Login as EMPLOYEE<br>2. POST /expenses/{id}/approve | ❌ 403 Forbidden (no permission) | 🔴 |
| ROLE-EMP-005 | Employee edits own PENDING expense | 1. Login as EMPLOYEE<br>2. PATCH /expenses/{own_pending_id} | ✅ 200 OK, expense updated | 🟠 |
| ROLE-EMP-006 | Employee edits own APPROVED expense | 1. Login as EMPLOYEE<br>2. PATCH /expenses/{own_approved_id} | ❌ 403 Forbidden (cannot edit approved) | 🟠 |
| ROLE-EMP-007 | Employee uploads receipt | 1. Login as EMPLOYEE<br>2. POST /receipts with image | ✅ 201 Created, Receipt created | 🟠 |
| ROLE-EMP-008 | Employee views org members | 1. Login as EMPLOYEE<br>2. GET /organizations/{org_id}/members | ✅ 200 OK, list returned (read-only) | 🟡 |
| ROLE-EMP-009 | Employee tries to invite member | 1. Login as EMPLOYEE<br>2. POST /organizations/{org_id}/invitations | ❌ 403 Forbidden (OWNER/ADMIN only) | 🟠 |
| ROLE-EMP-010 | Employee creates approval policy | 1. Login as EMPLOYEE<br>2. POST /approval-policies | ❌ 403 Forbidden (OWNER/ADMIN only) | 🟠 |

**Total EMPLOYEE Tests**: 25+ scenarios

---

### Scenario Set B: MANAGER Role Tests

| Test ID | Description | Steps | Expected Result | Priority |
|---------|-------------|-------|-----------------|----------|
| ROLE-MGR-001 | Manager approves dept expense ≤$5K | 1. Login as MANAGER<br>2. POST /expenses/{dept_expense_id}/approve (amount=$3000) | ✅ 200 OK, expense approved | 🔴 |
| ROLE-MGR-002 | Manager approves expense >$5K | 1. Login as MANAGER<br>2. POST /expenses/{id}/approve (amount=$10000) | ❌ 403 Forbidden "Requires admin approval" | 🔴 |
| ROLE-MGR-003 | Manager approves different dept expense | 1. Login as MANAGER (dept=Sales)<br>2. Approve expense (user.dept=Engineering) | ❌ 403 Forbidden "Different department" | 🔴 |
| ROLE-MGR-004 | Manager views all dept expenses | 1. Login as MANAGER<br>2. GET /expenses?department={manager_dept} | ✅ 200 OK, all dept expenses returned | 🟠 |
| ROLE-MGR-005 | Manager bulk approves dept expenses | 1. Login as MANAGER<br>2. POST /expenses/bulk-approve with dept expense IDs | ✅ 200 OK, all approved (if ≤$5K each) | 🟠 |
| ROLE-MGR-006 | Manager tries to approve own expense | 1. Login as MANAGER<br>2. Submit expense<br>3. Approve own expense | ❌ 403 Forbidden (cannot self-approve) | 🔴 |
| ROLE-MGR-007 | Manager exports dept report | 1. Login as MANAGER<br>2. GET /reports/export?department={dept} | ✅ 200 OK, CSV/Excel downloaded | 🟡 |
| ROLE-MGR-008 | Manager views audit log (dept only) | 1. Login as MANAGER<br>2. GET /audit-logs?department={dept} | ✅ 200 OK, dept audit logs | 🟡 |

**Total MANAGER Tests**: 20+ scenarios

---

### Scenario Set C: ACCOUNTANT Role Tests

| Test ID | Description | Steps | Expected Result | Priority |
|---------|-------------|-------|-----------------|----------|
| ROLE-ACC-001 | Accountant views all expenses | 1. Login as ACCOUNTANT<br>2. GET /expenses | ✅ 200 OK, all expenses (across all orgs if system ACCOUNTANT) | 🟠 |
| ROLE-ACC-002 | Accountant tries to approve expense | 1. Login as ACCOUNTANT<br>2. POST /expenses/{id}/approve | ❌ 403 Forbidden (read-only role) | 🔴 |
| ROLE-ACC-003 | Accountant exports financial report | 1. Login as ACCOUNTANT<br>2. GET /reports/financial | ✅ 200 OK, full financial data | 🟠 |
| ROLE-ACC-004 | Accountant views audit trail | 1. Login as ACCOUNTANT<br>2. GET /audit-logs | ✅ 200 OK, complete audit log | 🟠 |
| ROLE-ACC-005 | Accountant tries to edit expense | 1. Login as ACCOUNTANT<br>2. PATCH /expenses/{id} | ❌ 403 Forbidden (read-only) | 🟠 |
| ROLE-ACC-006 | Accountant tries to delete expense | 1. Login as ACCOUNTANT<br>2. DELETE /expenses/{id} | ❌ 403 Forbidden (read-only) | 🟠 |

**Total ACCOUNTANT Tests**: 15+ scenarios

---

### Scenario Set D: ADMIN Role Tests

| Test ID | Description | Steps | Expected Result | Priority |
|---------|-------------|-------|-----------------|----------|
| ROLE-ADM-001 | Admin approves any expense (no limit) | 1. Login as ADMIN<br>2. POST /expenses/{id}/approve (amount=$50000) | ✅ 200 OK, expense approved | 🔴 |
| ROLE-ADM-002 | Admin creates user | 1. Login as ADMIN<br>2. POST /users | ✅ 201 Created, user created | 🟠 |
| ROLE-ADM-003 | Admin suspends user | 1. Login as ADMIN<br>2. POST /users/{id}/suspend | ✅ 200 OK, user.is_active=False | 🟠 |
| ROLE-ADM-004 | Admin changes user role | 1. Login as ADMIN<br>2. PATCH /users/{id} (role=MANAGER) | ✅ 200 OK, role updated | 🟠 |
| ROLE-ADM-005 | Admin configures system settings | 1. Login as ADMIN<br>2. PATCH /settings | ✅ 200 OK, settings updated | 🟡 |
| ROLE-ADM-006 | Admin views system health | 1. Login as ADMIN<br>2. GET /system/health | ✅ 200 OK, health metrics | 🟡 |

**Total ADMIN Tests**: 30+ scenarios

---

## Tier-Based Test Scenarios

### Scenario Set E: FREE Tier Limits

| Test ID | Description | Steps | Expected Result | Priority |
|---------|-------------|-------|-----------------|----------|
| TIER-FREE-001 | Create 1st expense (under limit) | 1. FREE user, 10 expenses this month<br>2. Submit expense | ✅ 201 Created | 🔴 |
| TIER-FREE-002 | Create 20th expense (at limit) | 1. FREE user, 19 expenses this month<br>2. Submit expense | ✅ 201 Created (last one allowed) | 🔴 |
| TIER-FREE-003 | Create 21st expense (over limit) | 1. FREE user, 20 expenses this month<br>2. Submit expense | ❌ 402 Payment Required "Upgrade to Starter" | 🔴 |
| TIER-FREE-004 | Invite 2nd user (over limit) | 1. FREE user (1 user max)<br>2. Invite another user | ❌ 402 Payment Required "User limit reached" | 🔴 |
| TIER-FREE-005 | Create 2nd organization (over limit) | 1. FREE user (1 org max)<br>2. Create 2nd org | ❌ 402 Payment Required "Org limit reached" | 🔴 |
| TIER-FREE-006 | Use AI categorization (not allowed) | 1. FREE user<br>2. Request AI categorization | ❌ 402 Payment Required "Upgrade to Starter for AI" | 🔴 |
| TIER-FREE-007 | Use AP2 transaction (not allowed) | 1. FREE user<br>2. Create intent mandate | ❌ 402 Payment Required "Upgrade to Starter for AP2" | 🔴 |
| TIER-FREE-008 | Upload 6th OCR receipt (over limit) | 1. FREE user (5 OCR max)<br>2. Upload 6th receipt with OCR | ❌ 402 Payment Required "OCR limit reached" | 🔴 |
| TIER-FREE-009 | Daily expense limit (11th today) | 1. FREE user, 10 expenses today<br>2. Submit 11th expense | ❌ 402 Payment Required "Daily limit reached, try tomorrow" | 🟠 |
| TIER-FREE-010 | Recreate deleted org (slug reuse) | 1. FREE user deletes org<br>2. Create new org with same slug | ✅ 201 Created (slug now available) | 🟠 |

**Total FREE Tier Tests**: 20+ scenarios

---

### Scenario Set F: STARTER Tier Limits (Soft Limits)

| Test ID | Description | Steps | Expected Result | Priority |
|---------|-------------|-------|-----------------|----------|
| TIER-STR-001 | Create 50th expense (at limit) | 1. STARTER user, 49 expenses this month<br>2. Submit expense | ✅ 201 Created (at limit, no overage yet) | 🟠 |
| TIER-STR-002 | Create 51st expense (overage) | 1. STARTER user, 50 expenses this month<br>2. Submit expense | ✅ 201 Created + UsageMetric recorded (Marketplace handles overage billing) | 🟠 |
| TIER-STR-003 | Invite 6th user (soft limit overage) | 1. STARTER user (5 users max)<br>2. Invite 6th user | ✅ 201 Created + Overage fee charged | 🟠 |
| TIER-STR-004 | Create 4th organization (over 3 limit) | 1. STARTER user (3 orgs max)<br>2. Create 4th org | ⚠️ Depends: Block or allow with fee? | 🟡 |
| TIER-STR-005 | Use 101st AI categorization (overage) | 1. STARTER user (100 AI max)<br>2. Use 101st AI call | ✅ Success + Overage fee ($0.05) | 🟡 |

**Total STARTER Tier Tests**: 15+ scenarios

---

### Scenario Set G: PROFESSIONAL & ENTERPRISE (Unlimited)

| Test ID | Description | Steps | Expected Result | Priority |
|---------|-------------|-------|-----------------|----------|
| TIER-PRO-001 | Submit 1000th expense this month | 1. PRO user, 999 expenses this month<br>2. Submit expense | ✅ 201 Created (unlimited) | 🟡 |
| TIER-PRO-002 | Use 5000th AI categorization | 1. PRO user (2000 included)<br>2. Use AI call | ✅ Success + Overage fee (if >2000) | 🟡 |
| TIER-ENT-001 | Submit unlimited expenses | 1. ENTERPRISE user<br>2. Submit 10,000 expenses | ✅ All created (unlimited) | 🟡 |
| TIER-ENT-002 | Access API (feature-gated) | 1. ENTERPRISE user<br>2. GET /api/v1/expenses (API access) | ✅ 200 OK (API enabled) | 🟡 |
| TIER-ENT-003 | Enable SSO (feature-gated) | 1. ENTERPRISE user<br>2. Configure SSO settings | ✅ 200 OK (SSO enabled) | 🟡 |
| TIER-PRO-004 | FREE user tries to access API | 1. FREE user<br>2. GET /api/v1/* with API key | ❌ 402 Payment Required "API requires PRO" | 🟠 |

**Total PRO/ENTERPRISE Tests**: 12+ scenarios

---

## Multi-Tenancy & Security Tests

### Scenario Set H: Tenant Isolation

| Test ID | Description | Steps | Expected Result | Priority |
|---------|-------------|-------|-----------------|----------|
| SEC-ISO-001 | User A views User B's expense (different org) | 1. User A (Org 1)<br>2. GET /expenses/{user_b_expense_id} (Org 2) | ❌ 403 Forbidden (tenant isolation) | 🔴 |
| SEC-ISO-002 | User A uses X-Organization-Id header for Org B | 1. User A (member of Org 1 only)<br>2. Submit expense with X-Organization-Id: Org B | ❌ 403 Forbidden (not member of Org B) | 🔴 |
| SEC-ISO-003 | Manager A approves expense from Org B | 1. Manager A (Org 1)<br>2. POST /expenses/{org_b_expense_id}/approve | ❌ 403 Forbidden (cross-org access denied) | 🔴 |
| SEC-ISO-004 | SQL injection via organization_id filter | 1. Attacker submits: `org_id="1' OR '1'='1"`<br>2. Query expenses | ❌ No data leak (parameterized queries) | 🔴 |
| SEC-ISO-005 | Soft-deleted org data invisible | 1. User deletes Org A<br>2. Query org data via API | ❌ 404 Not Found (is_active=False filtered) | 🟠 |
| SEC-ISO-006 | Soft-deleted member cannot access org | 1. OWNER removes member<br>2. Ex-member tries to access org | ❌ 403 Forbidden (member.is_active=False) | 🟠 |

**Total Isolation Tests**: 20+ scenarios

---

### Scenario Set I: Permission Boundary Tests

| Test ID | Description | Steps | Expected Result | Priority |
|---------|-------------|-------|-----------------|----------|
| SEC-PERM-001 | User tries to modify own role (CRITICAL-2) | 1. Login as ADMIN (org role)<br>2. PATCH /members/{self}/role (to OWNER) | ❌ 403 Forbidden "Cannot modify own role" | 🔴 |
| SEC-PERM-002 | ADMIN tries to grant OWNER role (CRITICAL-1) | 1. Login as ORG ADMIN<br>2. PATCH /members/{user}/role (to OWNER) | ❌ 403 Forbidden "Only OWNER can grant OWNER" | 🔴 |
| SEC-PERM-003 | ADMIN tries to remove OWNER (HIGH-2) | 1. Login as ORG ADMIN<br>2. DELETE /members/{owner_id} | ❌ 403 Forbidden "Only OWNER can remove ADMINs" | 🟠 |
| SEC-PERM-004 | Manager approves >$5K (amount check) | 1. Login as MANAGER<br>2. Approve expense ($10000) | ❌ 403 Forbidden "Requires admin approval" | 🔴 |
| SEC-PERM-005 | Accountant tries to delete expense | 1. Login as ACCOUNTANT<br>2. DELETE /expenses/{id} | ❌ 403 Forbidden (read-only) | 🟠 |

**Total Permission Tests**: 25+ scenarios

---

### Scenario Set J: Authentication & Session Security

| Test ID | Description | Steps | Expected Result | Priority |
|---------|-------------|-------|-----------------|----------|
| SEC-AUTH-001 | Login with invalid password | 1. POST /login (wrong password) | ❌ 401 Unauthorized | 🔴 |
| SEC-AUTH-002 | Account lockout after 5 failed logins | 1. Fail login 5 times<br>2. Try to login with correct password | ❌ 423 Locked "Account locked for X minutes" | 🔴 |
| SEC-AUTH-003 | 2FA required when enabled | 1. Enable 2FA<br>2. Login without TOTP code | ❌ 401 "TOTP code required" | 🟠 |
| SEC-AUTH-004 | JWT token expiration | 1. Login (get token)<br>2. Wait for expiration<br>3. Use expired token | ❌ 401 "Token expired" | 🟠 |
| SEC-AUTH-005 | Refresh token reuse detection | 1. Use refresh token<br>2. Use same refresh token again | ❌ 401 "Token already used" | 🟠 |
| SEC-AUTH-006 | Rate limit: Registration (3/hour) | 1. Register 3 users in 1 hour<br>2. Try 4th registration | ❌ 429 Too Many Requests | 🟠 |
| SEC-AUTH-007 | Rate limit: Login attempts | 1. Fail login 10 times rapidly | ❌ 429 Too Many Requests | 🟠 |

**Total Auth Tests**: 20+ scenarios

---

## State Machine Tests

### Scenario Set K: Expense State Transitions

| Test ID | Description | Valid Transition | Steps | Expected Result | Priority |
|---------|-------------|------------------|-------|-----------------|----------|
| STATE-EXP-001 | PENDING → APPROVED | ✅ Valid | Submit expense → Manager approves | status=APPROVED, approved_by set | 🔴 |
| STATE-EXP-002 | PENDING → REJECTED | ✅ Valid | Submit expense → Manager rejects | status=REJECTED, rejection_reason set | 🔴 |
| STATE-EXP-003 | APPROVED → PENDING | ❌ Invalid | Approve expense → Try to set PENDING | ❌ Should reject (one-way transition) | 🟠 |
| STATE-EXP-004 | REJECTED → APPROVED | ❌ Invalid | Reject expense → Try to approve | ❌ Should reject (cannot reverse) | 🟠 |
| STATE-EXP-005 | PENDING → WITHDRAWN | ✅ Valid | User withdraws own expense | status=WITHDRAWN | 🟡 |
| STATE-EXP-006 | APPROVED → PROCESSING | ✅ Valid | Approved expense enters payment flow | status=PROCESSING | 🟡 |

---

### Scenario Set L: Subscription State Transitions

| Test ID | Description | Valid Transition | Steps | Expected Result | Priority |
|---------|-------------|------------------|-------|-----------------|----------|
| STATE-SUB-001 | active → trialing | ❌ Invalid | N/A (trialing comes first) | Should not occur | 🟡 |
| STATE-SUB-002 | trialing → active | ✅ Valid | Trial ends, payment succeeds | status=active | 🟠 |
| STATE-SUB-003 | active → past_due | ✅ Valid | Payment fails | status=past_due | 🟠 |
| STATE-SUB-004 | past_due → active | ✅ Valid | Payment retry succeeds | status=active | 🟠 |
| STATE-SUB-005 | active → canceled | ✅ Valid | User cancels subscription | status=canceled, canceled_at set | 🟠 |
| STATE-SUB-006 | canceled → active | ✅ Valid | User resubscribes | status=active, canceled_at=NULL | 🟡 |

---

## Integration Tests

### Scenario Set M: Stripe Integration

| Test ID | Description | Steps | Expected Result | Priority |
|---------|-------------|-------|-----------------|----------|
| INT-STRIPE-001 | Create checkout session | 1. User upgrades to STARTER<br>2. POST /payment/checkout | ✅ Stripe checkout URL returned | 🟠 |
| INT-STRIPE-002 | Webhook: payment_succeeded | 1. Stripe sends payment_succeeded webhook<br>2. Verify signature | ✅ Subscription updated, tier upgraded | 🔴 |
| INT-STRIPE-003 | Webhook: payment_failed | 1. Stripe sends payment_failed webhook | ✅ Subscription status=past_due | 🟠 |
| INT-STRIPE-004 | Webhook: customer.subscription.deleted | 1. Stripe sends subscription deleted | ✅ Subscription canceled, tier downgraded | 🟠 |
| INT-STRIPE-005 | Idempotent webhook processing | 1. Send same webhook twice (same event ID) | ✅ Processed once only (no duplicate charges) | 🔴 |

**Total Stripe Tests**: 15+ scenarios

---

### Scenario Set N: GCP Marketplace Integration

| Test ID | Description | Steps | Expected Result | Priority |
|---------|-------------|-------|-----------------|----------|
| INT-GCP-001 | Procurement webhook (account approval) | 1. Customer purchases on GCP Marketplace<br>2. Procurement webhook received | ✅ MarketplaceAccount created, organization linked | 🔴 |
| INT-GCP-002 | Entitlement created (PENDING → ACTIVE) | 1. Entitlement webhook (state=ACTIVE) | ✅ MarketplaceEntitlement created, subscription upgraded | 🔴 |
| INT-GCP-003 | Entitlement canceled | 1. Customer cancels on GCP<br>2. Entitlement webhook (state=CANCELLED) | ✅ Subscription downgraded or suspended | 🔴 |
| INT-GCP-004 | Usage reporting (hourly cron) | 1. Cron job runs<br>2. Calculate usage (expenses, users, etc.)<br>3. POST to GCP API | ✅ UsageMetric created, reported_to_gcp=True | 🔴 |
| INT-GCP-005 | Webhook signature verification | 1. Send webhook with invalid OIDC token | ❌ 403 Forbidden "Unauthorized webhook" | 🔴 |
| INT-GCP-006 | Idempotent webhook (duplicate event) | 1. Send same webhook twice (same dedupe_key) | ✅ Processed once (MarketplaceWebhookEvent prevents duplicate) | 🔴 |
| INT-GCP-007 | Account re-linking (org switch) | 1. Customer links account to Org A<br>2. Customer re-links to Org B | ✅ Account unlinked from A, linked to B | 🟠 |
| INT-GCP-008 | Grace period handling | 1. Entitlement enters grace period (payment issue) | ✅ Access continues during grace, suspended after | 🟠 |

**Total GCP Tests**: 20+ scenarios

---

### Scenario Set O: Email Integration

| Test ID | Description | Steps | Expected Result | Priority |
|---------|-------------|-------|-----------------|----------|
| INT-EMAIL-001 | Verification email sent on registration | 1. Register new user | ✅ Email sent to user.email with token | 🟠 |
| INT-EMAIL-002 | Organization invitation email | 1. OWNER invites user | ✅ Email sent with invitation link | 🟠 |
| INT-EMAIL-003 | Password reset email | 1. POST /auth/password-reset (email) | ✅ Email sent with reset token | 🟠 |
| INT-EMAIL-004 | Expense approved notification | 1. Manager approves expense | ✅ Email sent to expense owner | 🟡 |
| INT-EMAIL-005 | Budget alert email | 1. Budget reaches 90% threshold | ✅ Email sent to org owner/admin | 🟡 |

**Total Email Tests**: 10+ scenarios

---

## Edge Cases & Boundary Tests

### Scenario Set P: Concurrent Operations

| Test ID | Description | Steps | Expected Result | Priority |
|---------|-------------|-------|-----------------|----------|
| EDGE-CONC-001 | Concurrent expense submissions at limit | 1. FREE user at 19 expenses<br>2. Submit 2 expenses concurrently | ✅ 1st succeeds, 2nd fails (402) OR both succeed with race (acceptable) | 🟠 |
| EDGE-CONC-002 | Concurrent org creation (same slug) | 1. User A creates org "acme-corp"<br>2. User B creates org "acme-corp" (same time) | ❌ 1 succeeds, 1 fails with UNIQUE constraint error (400) | 🟠 |
| EDGE-CONC-003 | Concurrent member role updates | 1. OWNER A updates member role to ADMIN<br>2. OWNER B updates same member to MANAGER | ✅ Last write wins (or error if concurrent update detection) | 🟡 |
| EDGE-CONC-004 | Concurrent approval policy evaluations | 1. Expense submitted<br>2. 2 policies match (same priority)<br>3. Evaluated concurrently | ✅ First match wins (priority tie-breaker: created_at) | 🟡 |

---

### Scenario Set Q: Data Validation Boundaries

| Test ID | Description | Input | Expected Result | Priority |
|---------|-------------|-------|-----------------|----------|
| EDGE-VAL-001 | Expense amount = $0 | amount: 0 | ❌ 400 "Amount must be positive" | 🟠 |
| EDGE-VAL-002 | Expense amount = $0.01 | amount: 0.01 | ✅ 201 Created | 🟠 |
| EDGE-VAL-003 | Expense amount = $1,000,000 | amount: 1000000 | ✅ 201 Created (at limit) | 🟠 |
| EDGE-VAL-004 | Expense amount = $1,000,001 | amount: 1000001 | ❌ 400 "Amount cannot exceed $1M" | 🟠 |
| EDGE-VAL-005 | Expense description = 1000 chars | description: "a" * 1000 | ✅ 201 Created (at limit) | 🟡 |
| EDGE-VAL-006 | Expense description = 1001 chars | description: "a" * 1001 | ❌ 400 "Description max 1000 chars" | 🟡 |
| EDGE-VAL-007 | Vendor name with XSS attempt | vendor: `<script>alert('XSS')</script>` | ✅ Sanitized (HTML escaped) | 🔴 |
| EDGE-VAL-008 | Organization slug with uppercase | slug: "Acme-Corp" | ❌ 400 "Slug must be lowercase" | 🟠 |
| EDGE-VAL-009 | Receipt upload = 10MB | file_size: 10485760 bytes (10MB) | ✅ 201 Created (at limit) | 🟠 |
| EDGE-VAL-010 | Receipt upload = 10.1MB | file_size: 10590617 bytes (10.1MB) | ❌ 400 "File too large (max 10MB)" | 🟠 |
| EDGE-VAL-011 | Username = 3 chars | username: "bob" | ✅ 201 Created (min length) | 🟠 |
| EDGE-VAL-012 | Username = 2 chars | username: "ab" | ❌ 400 "Username min 3 chars" | 🟠 |
| EDGE-VAL-013 | Password missing uppercase | password: "password123" | ❌ 400 "Password must have uppercase" | 🔴 |
| EDGE-VAL-014 | Email = invalid format | email: "not-an-email" | ❌ 400 "Invalid email format" | 🟠 |

**Total Validation Tests**: 30+ scenarios

---

### Scenario Set R: Race Conditions & Idempotency

| Test ID | Description | Steps | Expected Result | Priority |
|---------|-------------|-------|-----------------|----------|
| EDGE-RACE-001 | Double webhook delivery (Stripe) | 1. Send webhook event ID "evt_123" twice | ✅ Processed once (idempotency key) | 🔴 |
| EDGE-RACE-002 | Double webhook delivery (GCP) | 1. Send GCP webhook with same dedupe_key twice | ✅ Processed once (MarketplaceWebhookEvent) | 🔴 |
| EDGE-RACE-003 | Soft-delete org + recreate race | 1. Delete org "acme"<br>2. Recreate "acme" before commit | ⚠️ UNIQUE error → aggressive cleanup → retry | 🟠 |
| EDGE-RACE-004 | Audit log hash chain concurrent writes | 1. Two audit events written simultaneously | ✅ Sequence numbers prevent collision | 🟡 |

---

## Performance & Load Tests

### Scenario Set S: Scalability Tests

| Test ID | Description | Load | Expected Result | Priority |
|---------|-------------|------|-----------------|----------|
| PERF-LOAD-001 | 100 concurrent expense submissions | 100 users submit at same time | ✅ All succeed (or fail gracefully with 429/5xx) | 🟡 |
| PERF-LOAD-002 | 1000 concurrent API requests | 1000 GET /expenses requests | ✅ Avg response time <500ms | 🟡 |
| PERF-LOAD-003 | Large org with 1000 members | Org with 1000 members, list all | ✅ Response <2s (with pagination) | 🟡 |
| PERF-LOAD-004 | 10,000 expenses in database | Query expenses for org with 10K records | ✅ Response <1s (with pagination, indexing) | 🟡 |
| PERF-LOAD-005 | Webhook flood (100 webhooks/sec) | Send 100 webhooks/second for 1 min | ✅ All processed or queued (no data loss) | 🟠 |

**Total Performance Tests**: 10+ scenarios

---

### Scenario Set T: Database Performance (N+1 Queries)

| Test ID | Description | Issue | Fix | Priority |
|---------|-------------|-------|-----|----------|
| PERF-N1-001 | List org members (25 members) | 1 query (members) + 25 queries (users) = 26 queries | ✅ Use joinedload() → 2 queries (FIXED) | 🟠 |
| PERF-N1-002 | List expenses with approver names | N+1 query for each approver user | ✅ Use selectinload(Expense.approver) | 🟡 |
| PERF-N1-003 | List receipts with expense details | N+1 query for each expense | ✅ Use eager loading | 🟡 |

---

## Priority Test Execution Plan

### Phase 1: CRITICAL (Pre-Production) - 🔴

**Timeline**: Week 1-2
**Focus**: Security, authorization, multi-tenancy, billing

| Priority | Test Set | Test Count | Estimated Hours |
|----------|----------|------------|-----------------|
| 🔴 | ROLE-* (all role tests) | ~90 | 20h |
| 🔴 | TIER-FREE-* (hard limits) | ~20 | 8h |
| 🔴 | SEC-ISO-* (tenant isolation) | ~20 | 10h |
| 🔴 | SEC-PERM-* (permission boundaries) | ~25 | 12h |
| 🔴 | SEC-AUTH-* (authentication) | ~20 | 8h |
| 🔴 | STATE-EXP-* (expense states) | ~10 | 5h |
| 🔴 | INT-STRIPE-* (payment critical paths) | ~10 | 8h |
| 🔴 | INT-GCP-* (marketplace critical) | ~15 | 12h |
| 🔴 | EDGE-VAL-* (XSS, injection, sanitization) | ~15 | 8h |
| 🔴 | EDGE-RACE-* (idempotency) | ~5 | 4h |

**Total Phase 1**: ~230 tests, ~95 hours

---

### Phase 2: HIGH (Production Hardening) - 🟠

**Timeline**: Week 3-4
**Focus**: Business logic, workflows, edge cases

| Priority | Test Set | Test Count | Estimated Hours |
|----------|----------|------------|-----------------|
| 🟠 | Flow tests (org creation, invitations, approvals) | ~40 | 16h |
| 🟠 | TIER-STR-* (soft limits, overages) | ~15 | 6h |
| 🟠 | State transition tests (subscriptions, invitations) | ~12 | 5h |
| 🟠 | Integration tests (email, webhooks) | ~15 | 6h |
| 🟠 | Concurrent operations | ~8 | 6h |
| 🟠 | Data validation boundaries | ~20 | 8h |
| 🟠 | Performance (N+1 queries) | ~5 | 4h |

**Total Phase 2**: ~115 tests, ~51 hours

---

### Phase 3: MEDIUM (Feature Completeness) - 🟡

**Timeline**: Week 5
**Focus**: Advanced features, reporting, analytics

| Priority | Test Set | Test Count | Estimated Hours |
|----------|----------|------------|-----------------|
| 🟡 | TIER-PRO/ENT-* (unlimited tiers) | ~12 | 5h |
| 🟡 | Recurring expenses flow | ~10 | 5h |
| 🟡 | Budget tracking & alerts | ~8 | 4h |
| 🟡 | AP2 protocol flow | ~10 | 6h |
| 🟡 | Audit trail & compliance | ~8 | 4h |
| 🟡 | Performance & load tests | ~10 | 8h |

**Total Phase 3**: ~58 tests, ~32 hours

---

## Grand Total

**Total Test Scenarios**: ~400+ tests
**Total Estimated Effort**: ~178 hours (~4.5 weeks for 1 QA engineer)

---

## Test Data Setup Requirements

### Organizations
- Org A (FREE tier, 1 user)
- Org B (STARTER tier, 5 users)
- Org C (PROFESSIONAL tier, 25 users)
- Org D (ENTERPRISE tier, 100 users)

### Users (Per Organization)
- 1 OWNER
- 2 ADMINs
- 3 MANAGERs (different departments: Sales, Engineering, Marketing)
- 5 ACCOUNTANTs
- 20 EMPLOYEEs (spread across departments)

### Expenses (Per Organization)
- 10 PENDING expenses (various amounts: $10, $100, $1000, $10000)
- 10 APPROVED expenses
- 5 REJECTED expenses
- 2 WITHDRAWN expenses

### Approval Policies (Per Organization)
- Policy 1: Auto-approve meals ≤$50 (priority 10)
- Policy 2: Auto-approve office supplies ≤$200 (priority 5)
- Policy 3: Require receipt for all >$100 (priority 1)

### Subscriptions
- User on FREE (19 expenses this month - near limit)
- User on STARTER (48 expenses this month - near limit)
- User on PRO (unlimited)
- User on ENTERPRISE (unlimited + features)

---

## Automation Recommendations

### Test Framework Stack

**Backend**:
- **pytest** (main framework)
- **pytest-asyncio** (async test support)
- **pytest-xdist** (parallel test execution)
- **Faker** (test data generation)
- **factory_boy** (model factories)

**Frontend** (E2E):
- **Playwright** or **Cypress**
- **jest** (component tests)

**API Testing**:
- **requests** or **httpx** (Python)
- **Postman/Newman** (collection runner)

**Load Testing**:
- **Locust** (Python-based)
- **k6** (Go-based)

---

### CI/CD Integration

**GitHub Actions Workflow**:
```yaml
test-critical:
  runs-on: ubuntu-latest
  steps:
    - pytest -m critical --cov=src --cov-report=html
    - Upload coverage to Codecov
    - Fail if coverage <80%

test-high:
  runs-on: ubuntu-latest
  needs: test-critical
  steps:
    - pytest -m high

test-medium:
  runs-on: ubuntu-latest
  needs: test-high
  steps:
    - pytest -m medium
```

**Test Markers**:
- `@pytest.mark.critical` - Phase 1 tests (🔴)
- `@pytest.mark.high` - Phase 2 tests (🟠)
- `@pytest.mark.medium` - Phase 3 tests (🟡)
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.security` - Security tests
- `@pytest.mark.slow` - Long-running tests

---

## Coverage Goals

| Category | Target Coverage | Current | Gap |
|----------|----------------|---------|-----|
| **Overall** | 85% | ~70% | 15% |
| **Auth & Security** | 95% | ~80% | 15% |
| **Billing & Limits** | 90% | ~60% | 30% |
| **Multi-Tenancy** | 95% | ~75% | 20% |
| **API Routes** | 85% | ~70% | 15% |
| **Business Logic** | 90% | ~65% | 25% |

---

## Risk Assessment

### Highest Risk Areas (Require Extra Testing)

1. **🔴 CRITICAL**: Multi-tenant data isolation
   - **Risk**: Data leakage between organizations
   - **Mitigation**: Extensive fuzzing, SQL injection tests, parameter tampering

2. **🔴 CRITICAL**: Billing & tier limit enforcement
   - **Risk**: Revenue loss (soft limits not charged), free tier abuse
   - **Mitigation**: Stress test all limits, verify overage billing

3. **🔴 CRITICAL**: GCP Marketplace integration
   - **Risk**: Account linking failures, duplicate billing, webhook replay attacks
   - **Mitigation**: Idempotency tests, signature verification, end-to-end procurement flow

4. **🔴 CRITICAL**: Permission escalation vulnerabilities
   - **Risk**: Users gain unauthorized roles (EMPLOYEE → OWNER)
   - **Mitigation**: Test all role transition edge cases, especially self-modification

5. **🟠 HIGH**: Stripe webhook processing
   - **Risk**: Duplicate charges, subscription status desync
   - **Mitigation**: Idempotency keys, webhook retry logic, signature verification

6. **🟠 HIGH**: Approval policy logic
   - **Risk**: Incorrect auto-approvals (bypassing limits)
   - **Mitigation**: Test all condition combinations, priority resolution, limit enforcement

---

## Maintenance Plan

### Regression Test Suite
- **Frequency**: Every PR merge
- **Duration**: ~30 minutes (parallelized)
- **Scope**: All 🔴 CRITICAL tests

### Full Test Suite
- **Frequency**: Daily (nightly builds)
- **Duration**: ~3 hours
- **Scope**: All tests (🔴 + 🟠 + 🟡)

### Performance Benchmarks
- **Frequency**: Weekly
- **Baseline**: Current production metrics
- **Alerts**: >20% degradation triggers investigation

### Security Audits
- **Frequency**: Quarterly
- **Tools**: Bandit (Python), npm audit, OWASP ZAP
- **Manual**: Penetration testing (yearly)

---

## Appendix: Test Case Template

```python
import pytest
from fastapi.testclient import TestClient

@pytest.mark.critical
@pytest.mark.security
def test_ROLE_EMP_003_employee_cannot_view_others_expense(
    client: TestClient,
    employee_user: User,
    other_user_expense: Expense,
    employee_auth_headers: dict
):
    """
    Test ID: ROLE-EMP-003
    Priority: 🔴 CRITICAL
    Category: Authorization

    Verify that an EMPLOYEE cannot view another user's expense
    (multi-tenant isolation + role-based access control)

    Expected: 403 Forbidden
    """
    response = client.get(
        f"/api/v1/expenses/{other_user_expense.id}",
        headers=employee_auth_headers
    )

    assert response.status_code == 403
    assert "You can only access your own expenses" in response.json()["detail"]
```

---

**End of Comprehensive Test Strategy**

---

## Next Steps

1. ✅ **Review this strategy** with the team
2. ⏭️ **Implement test infrastructure** (factories, fixtures, utilities)
3. ⏭️ **Execute Phase 1** (CRITICAL tests) - ~2 weeks
4. ⏭️ **Execute Phase 2** (HIGH tests) - ~2 weeks
5. ⏭️ **Execute Phase 3** (MEDIUM tests) - ~1 week
6. ⏭️ **Automate CI/CD integration**
7. ⏭️ **Establish monitoring & alerting** for production
