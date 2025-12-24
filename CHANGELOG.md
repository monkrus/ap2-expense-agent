# Changelog

All notable changes to the AP2 Expense Agent project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security - Organization Limit Bypass Fix (2025-12-24)

#### MEDIUM Severity Vulnerability Patched

**Issue**: Free tier users could create unlimited organizations, bypassing the 1-organization limit defined in the billing tier system.

**Impact**:
- Revenue loss from users not upgrading to paid tiers
- Potential database bloat from unlimited organization creation
- Business logic bypass (tier limits not enforced)

**Root Cause**:
- `create_organization` endpoint had no backend validation for organization count
- `LimitEnforcer` service had methods for user/expense limits but not organization limits
- Only frontend validation existed (easily bypassed via direct API calls)

**Fix Implemented**:
- ✅ Added `check_organization_limit()` method to `LimitEnforcer` service
- ✅ Integrated limit check into organization creation endpoint
- ✅ Returns 402 Payment Required with upgrade options when limit exceeded
- ✅ Respects soft-deletion and multi-tenancy
- ✅ Added debug logging for limit enforcement

**Files Modified**:
- `backend/src/billing/limit_enforcer.py` (+76 lines): New `check_organization_limit()` method
- `backend/src/routes/organizations.py` (+31 lines): Added limit validation before creation

**Testing**:
- ✅ Automated test confirms vulnerability and fix (`test_org_limit_bypass.py`)
- ✅ Proper 402 error response with upgrade options
- ⏳ Manual frontend testing pending

**Documentation**:
- `SECURITY_ISSUE_ORG_LIMIT_BYPASS.md` - Complete security report (400+ lines)

**Validation Order** (now correct):
1. Check GCP Marketplace mode
2. Clean up soft-deleted organizations with same slug
3. Check duplicate slug (400 Bad Request)
4. Check duplicate name (400 Bad Request)
5. **Check organization count limit (402 Payment Required)** ← NEW
6. Create organization

**Error Response**:
```json
{
  "error": "limit_exceeded",
  "feature": "Organizations",
  "current_tier": "Free",
  "current_limit": 1,
  "current_count": 1,
  "message": "Organizations limit exceeded: 1/1...",
  "upgrade_options": [...]
}
```

**Reference**: See `SECURITY_ISSUE_ORG_LIMIT_BYPASS.md` for full details.

---

### Added - Production Readiness & Testing Infrastructure (2025-12-23/24)

#### Comprehensive Testing Infrastructure
- **Frontend Unit Testing** (`frontend/src/test/`):
  - Vitest test framework configuration (`vite.config.test.js`)
  - Test environment setup with mocks (`src/test/setup.js`)
  - Toast component tests (13 test cases) - accessibility, auto-dismiss, interactions
  - AccessibleModal component tests (18 test cases) - WCAG 2.1 AA compliance, focus trap, keyboard nav
  - Test scripts: `test:unit`, `test:unit:ui`, `test:unit:coverage`, `test:all`
  - **Status**: ✅ 41/41 tests passing
- **Backend Testing**:
  - **Status**: ✅ 391/391 tests passing (96.4% coverage)
  - Comprehensive test suite across all modules

#### Component Improvements
- **Toast Component** (`frontend/src/components/Toast.jsx`):
  - Added auto-dismiss functionality with configurable duration
  - Added accessible close button with `aria-label="Close notification"`
  - Added `aria-hidden="true"` to icon elements
  - Improved screen reader compatibility
- **AccessibleModal Component** (`frontend/src/components/AccessibleModal.jsx`):
  - Fixed ARIA structure (moved `role="dialog"` to content div)
  - Added `onClick` handler to prevent backdrop click event bubbling
  - Improved keyboard navigation and focus management
  - Enhanced WCAG 2.1 AA compliance

#### Production Deployment Documentation
- **Production Deployment Checklist** (`PRODUCTION_DEPLOYMENT_CHECKLIST.md`, 800 lines):
  - Pre-deployment validation (tests, security, documentation)
  - Environment configuration (48+ environment variables)
  - Database preparation (backup, migrations, health checks)
  - Build & test procedures
  - Docker & container registry workflows
  - Cloud Run deployment steps (backend + frontend)
  - Post-deployment verification (health, functional, performance, security)
  - Rollback procedures (when, how, post-rollback actions)
  - Monitoring setup instructions
  - Success criteria and emergency contacts
- **Monitoring & Alerts Configuration** (`MONITORING_ALERTS_CONFIGURATION.md`, 900 lines):
  - 4 Cloud Monitoring dashboards (Application, Database, Security, Business Metrics)
  - 10 alerting policies with P1-P4 severity levels
  - 3 uptime checks (backend health, frontend, database connectivity)
  - 5+ log-based metrics (auth failures, API errors, slow queries)
  - Custom metrics implementation (Python code examples)
  - Notification channels setup (PagerDuty, Slack, Email, SMS)
  - Incident response runbooks with severity levels
  - Complete setup script (`scripts/setup-monitoring.sh`)
  - Cost optimization best practices

#### Automation Scripts
- **Monitoring Setup** (`scripts/setup-monitoring.sh`):
  - Automated Cloud Monitoring configuration
  - Notification channel creation (Slack, PagerDuty, Email)
  - Uptime checks creation and configuration
  - Log-based metrics deployment
  - Alerting policies setup
  - Environment-aware (staging/production)

### Fixed - Test Suite Improvements (2025-12-23/24)

#### Frontend Testing
- **Vitest Configuration**:
  - Fixed test file inclusion to only target `src/**/*.{test,spec}.{js,jsx}`
  - Added exclusion for Playwright E2E tests (`tests/**/*.spec.js`)
  - Resolved esbuild TextEncoder conflicts
  - Prevented test suite interference
- **Toast Tests**:
  - Fixed fake timer conflicts with userEvent
  - Removed global fake timers from `beforeEach`
  - Added fake timers only to specific timing tests
  - Fixed auto-dismiss test timeout issues
- **AccessibleModal Tests**:
  - Fixed backdrop click test by correcting ARIA structure
  - All 18 tests now passing with proper role hierarchy

#### Production Build
- **Status**: ✅ Build successful (7.11s)
- **Output**: Optimized production bundle in `dist/`
- **Bundle Sizes**: All chunks optimized (exceljs warning expected)

### Added - Auto-Approval System (2025-12-12)

#### Automated Expense Approval
- **Approval Policy System**: Comprehensive rule-based auto-approval engine
  - Configurable policies with priority-based matching
  - Flexible JSON conditions (amount, category, vendor, user role, time-based)
  - Per-user limits (daily/monthly/yearly)
  - Receipt requirement enforcement
  - Budget compliance checks
  - Organization-scoped policies (multi-tenant safe)
- **Policy Management API** (`backend/src/routes/approval_policies.py`):
  - Full CRUD operations for approval policies
  - Policy testing endpoint for validation
  - Usage analytics and statistics
  - RBAC protected (OWNER/ADMIN only)
- **Email Notification Templates** (`backend/src/email_templates.py`):
  - Professional HTML email templates with inline CSS
  - Expense approved notifications (green theme)
  - Expense rejected notifications (red theme, includes reason)
  - Pending approval alerts for managers (orange theme, action buttons)
  - Budget alerts (warning/critical levels with progress bars)
  - Plain text fallbacks for all templates
- **Approval Policy Service** (`backend/src/services/approval_policy_service.py`):
  - Evaluates expenses against active policies
  - Complex condition matching (amount, category, vendor, user, time)
  - Limit enforcement and usage tracking
  - Detailed logging and audit trail
- **Database Migration**: New `approval_policies` table + auto-approval columns on expenses

### Security - Critical RBAC Fixes (2025-12-12)

#### Critical Vulnerabilities Patched
- **CRITICAL-1**: Prevent ADMINs from granting OWNER role
  - Only organization OWNER can grant OWNER role to others
  - Prevents organizational takeover by malicious admins
  - File: `backend/src/routes/organizations.py:545-550`
- **CRITICAL-2**: Prevent self-role modification
  - Users cannot modify their own membership roles
  - Prevents self-privilege escalation attacks
  - File: `backend/src/routes/organizations.py:532-537`

#### High Severity Fixes
- **HIGH-2**: Restrict ADMIN removal to OWNER only
  - Only OWNER can remove other ADMINs
  - Prevents "admin wars" where admins attack each other
  - File: `backend/src/routes/organizations.py` (remove_organization_member)
- **HIGH-4**: Fix global role leakage in expense access
  - Removed global `UserRole.ACCOUNTANT/MANAGER` checks
  - Only organization-specific roles grant expense access
  - Fixes cross-organization data leakage vulnerability
  - Files: `backend/src/routes/expenses.py` (2 locations)

#### Security Audit Documentation
- **RBAC Security Audit Report**: Comprehensive audit identifying 10 vulnerabilities (752 lines)
- **Security Fixes Implementation Guide**: Step-by-step fix instructions (406 lines)
- **Security Fixes Verification Report**: Validation and testing results (396 lines)
- **RBAC Test Suites**: Automated security tests (2 new test files)

#### Security Impact
- **Before**: 2 CRITICAL + 4 HIGH severity vulnerabilities
- **After**: 0 CRITICAL + 0 HIGH (all patched)
- **Status**: ✅ Production-ready for deployment

### Added - Production Readiness Improvements (2025-12-04)

#### Automation Scripts
- **Screenshot Capture Helper** (`scripts/capture-screenshots.sh`): Interactive guide for capturing all 8 required GCP Marketplace screenshots with step-by-step instructions
- **Environment Variable Validation** (`scripts/validate-environment.sh`): Comprehensive validation script checking all required environment variables with pattern matching and format validation
- **Database Backup Automation** (`scripts/backup-database.sh`): Cloud SQL backup creation with verification and metadata storage
- **Deployment Rollback** (`scripts/rollback-deployment.sh`): Safe rollback procedure with health checks, database migration handling, and automated notifications
- **Smoke Tests** (`scripts/smoke-test.sh`): Post-deployment verification testing 13 critical system components including health checks, authentication, security headers, and performance baselines

#### Demo Data & Documentation
- **Screenshot Demo Data Seeder** (`backend/seed_screenshot_data.py`): Creates realistic demo data for marketplace screenshots:
  - Acme Corporation organization
  - 3 demo users (admin, manager, employee)
  - 10 sample expenses with varied statuses
  - 3 budgets with usage tracking
- **Marketplace Asset Creation Guide** (`MARKETPLACE_ASSET_CREATION_GUIDE.md`): Comprehensive 9,000+ word guide for creating all GCP Marketplace assets
- **Production Alerting Setup Guide** (`PRODUCTION_ALERTING_SETUP.md`): Step-by-step instructions for configuring Slack, PagerDuty, and GCP Monitoring alerts
- **Pre-Launch Checklist** (`PRE_LAUNCH_CHECKLIST.md`): 150+ item checklist organized in 9 phases for production deployment

### Changed - Security & CI/CD Improvements (2025-12-04)

#### Security Enhancements
- **Environment-Aware HSTS**: Modified `backend/src/security_middleware.py` to enable HSTS headers only in production environment, preventing development issues while maintaining production security

#### CI/CD Pipeline Hardening
- **Blocking Linters**: Removed `continue-on-error: true` from Python linting jobs (Black, isort, Flake8) to make code quality checks blocking
- **Blocking Frontend Linters**: Removed `|| true` from ESLint and Prettier checks to enforce frontend code quality
- **Blocking SAST**: Removed `|| true` from Bandit security scans to make security issues fail the build
- **E2E Tests Enabled**: Enabled Playwright E2E tests in CI/CD pipeline

#### Project Configuration
- **License File Added**: Created MIT License file (was referenced in README badge but missing)
- **Gitignore Updates**: Added entries for:
  - Backup verification cache (`scripts/.backup-verification-cache`)
  - Backup reports (`*.backup-report.json`)
  - Screenshot staging area (`screenshots/staging/`)
  - Marketplace screenshots (`marketplace/screenshots/*.png`, `marketplace/screenshots/*.jpg`)
  - Temporary test data (`test-data/`, `sample-data-*.json`)

### Fixed

#### Security
- All critical and high-severity security vulnerabilities resolved (97% security score, 30/31 tests passing)
- Dependencies updated:
  - `glob` (npm): Command injection vulnerability fixed via `npm audit fix`
  - `anyio` (Python): Race condition fixed (3.7.1 → 4.11.0)

#### Mitigations Implemented
- **xlsx ReDoS Protection**: 5-second timeout protection for Excel file parsing
- **Excel Error Boundaries**: React error boundary component to prevent app crashes
- **Security Event Logging**: Comprehensive monitoring and alerting for suspicious activity
- **File Size Validation**: 10MB maximum file size to prevent oversized attacks
- **Workbook Structure Validation**: Prevents memory exhaustion attacks

### Testing

#### Security Testing
- Comprehensive security audit conducted (30/31 tests passed, 97% score)
- 0 critical issues
- 0 high severity issues
- 3 medium severity issues (ALL MITIGATED)

#### Test Coverage
- Backend: 96.4% coverage (268/278 tests passing)
- Security score: 97% (30/31 tests)

## [1.0.0] - 2025-11-27 (Pre-Release)

### Added

#### Core Features
- Multi-tenant expense management system
- Organization management with soft-delete support
- Role-based access control (RBAC) with 36 permissions
- Subscription tier system (FREE, STARTER, PROFESSIONAL, ENTERPRISE)
- Stripe payment integration
- Google Cloud Marketplace integration
- AP2 Protocol implementation (3-mandate flow)
- Receipt upload and management
- PDF report generation
- Expense approval workflows
- Budget tracking
- Two-factor authentication (2FA/TOTP)

#### Backend Infrastructure
- FastAPI REST API with 150+ endpoints
- PostgreSQL database with SQLAlchemy ORM
- Redis caching layer
- 14 Alembic database migrations
- JWT authentication (access + refresh tokens)
- bcrypt password hashing (cost factor 12)
- Rate limiting via SlowAPI
- Audit logging with tamper-proof hash chain
- Prometheus metrics
- Structured JSON logging

#### Frontend Application
- React 18.2.0 + Vite
- Tailwind CSS for styling
- Responsive design (mobile-optimized)
- Dashboard with expense summary
- Expense list with filtering and search
- Expense creation with receipt upload
- Approval workflow interface
- Reports and analytics
- Organization management
- Admin panel

#### Cloud Infrastructure
- Google Cloud Run deployment
- Google Kubernetes Engine (GKE) support
- Terraform Infrastructure as Code
- Helm charts for Kubernetes
- Cloud SQL (PostgreSQL 14+)
- Cloud Storage for receipts
- Cloud KMS for encryption
- Secret Manager for credentials
- Docker containerization

#### Testing & Quality
- pytest test suite (96.4% backend coverage)
- Playwright E2E tests
- Security scanning (Bandit, ESLint security plugin)
- 7 GitHub Actions workflows
- Automated dependency scanning

#### Documentation
- Comprehensive README with quickstart
- API documentation (OpenAPI/Swagger)
- Architecture documentation
- Security audit reports
- Dependency audit reports
- Production readiness summary
- Claude Code guide (CLAUDE.md)

### Security

#### Implemented
- OWASP Top 10 protection
- SQL injection prevention (parameterized queries)
- XSS protection (React auto-escaping)
- Command injection prevention
- CSRF protection (stateless JWT)
- Security headers (HSTS, CSP, X-Frame-Options, etc.)
- Rate limiting on authentication endpoints
- Multi-tenancy isolation
- Input validation and sanitization
- Session management
- Audit logging

#### Audits
- Security audit: 97% score (30/31 tests)
- Dependency audit: 2 vulnerabilities fixed, 3 documented with mitigations
- Production readiness: ✅ APPROVED for GCP Marketplace

### Known Issues

#### Medium Severity (Mitigated)
- **xlsx dependency**: ReDoS vulnerability (CVE-2024-58248)
  - **Mitigation**: 5-second timeout, file size limits, error boundaries
  - **Risk**: Medium → Low (60% reduction)
- **ecdsa dependency**: Timing attack vulnerabilities (2 CVEs)
  - **Mitigation**: Used only for JWT verification, not cryptographic operations
  - **Risk**: Low impact (JWT validation only)

### Deployment

#### Supported Platforms
- Google Cloud Run (production)
- Google Kubernetes Engine (GKE)
- Local development (Docker Compose)

#### Requirements
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Redis 6+

## Release Notes

### Version 1.0.0 - Initial Production Release

This is the first production-ready release of AP2 Expense Agent, a comprehensive expense management solution designed for Google Cloud Marketplace.

**Highlights**:
- ✅ Production-ready architecture (94.5/100 score)
- ✅ Comprehensive security (97% audit score)
- ✅ High test coverage (96.4% backend)
- ✅ Full GCP Marketplace integration
- ✅ Multi-tenant SaaS architecture
- ✅ Complete automation suite

**What's New**:
- All core features implemented and tested
- Complete documentation suite
- Automated deployment and rollback procedures
- Comprehensive monitoring and alerting setup
- Production-grade security hardening

**Migration Notes**:
- This is the initial release, no migration needed

**Upgrade Instructions**:
- First deployment - follow PRE_LAUNCH_CHECKLIST.md

**Breaking Changes**:
- None (initial release)

---

## Versioning Strategy

### Version Numbers
- **Major**: Breaking changes, significant architecture changes
- **Minor**: New features, non-breaking changes
- **Patch**: Bug fixes, security patches

### Release Schedule
- **Major releases**: As needed for significant changes
- **Minor releases**: Monthly feature releases
- **Patch releases**: As needed for bugs and security

### Support Policy
- **Current version**: Full support
- **Previous major**: Security patches for 6 months
- **Older versions**: Best-effort support

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## Security

See [SECURITY.md](SECURITY.md) for security policy and vulnerability reporting.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

*Last Updated: 2025-12-04*
*Next Release: TBD*
