# AP2 Expense Management - Comprehensive Testing Strategy

**Version**: 1.0
**Date**: 2025-11-12
**Status**: In Implementation

---

## Executive Summary

This document outlines the complete testing strategy for the AP2 Expense Management System, covering all components from backend APIs to Kubernetes deployments, security testing, performance validation, and compliance verification.

### Current Test Status
- **Total Tests**: 170 (120 passing, 28 failing, 22 skipped)
- **Coverage**: 38% (Target: >80%)
- **Test Types**: Unit, Integration, AP2 Protocol, Compliance
- **CI/CD**: To be implemented

---

## 1. Scope & Components

### Included Components
✅ **backend** - FastAPI, AP2 protocol handlers, auth, DB models
✅ **frontend** - React/TypeScript UI
✅ **helm/ap2-expense** - Kubernetes manifests
✅ **infrastructure/terraform** - Infrastructure as Code
✅ **monitoring** - Observability and security docs/scripts
✅ **CI config** - cloudbuild.yaml, Dockerfiles, GitHub Actions

### Excluded
- External third-party closed-source integrations (we mock them)
- Manual exploratory testing (documented separately)

---

## 2. Test Categories & Approach

### 2.1 Unit Tests
**Purpose**: Fast, isolated, deterministic tests
**Tools**: `pytest` (backend), `Jest/RTL` (frontend)
**Coverage Target**: >80% (goal: 90% for critical modules)

**Backend Unit Tests**:
- API handlers and validators
- AP2 protocol modules
- Input sanitization
- Business logic services
- Repository patterns
- Authentication/authorization logic

**Frontend Unit Tests**:
- Component rendering
- State management
- Form validation
- API client functions
- Utility functions

### 2.2 Integration Tests
**Purpose**: Multi-component flow validation
**Tools**: `pytest` with test DB, Docker containers
**Coverage**: All major workflows

**Test Scenarios**:
- Expense workflow: submit → OCR → parse → DB → approval message
- AP2 gateway interactions (mocked)
- OAuth providers (mocked)
- Email/SMS notifications (mocked)
- Database transactions and migrations

### 2.3 End-to-End (E2E) Tests
**Purpose**: Reproduce full user journeys
**Tools**: `Playwright` (primary), `Cypress` (alternative)
**Coverage**: Critical paths

**User Journeys**:
1. **Employee Flow**: Login → Submit expense with receipt → View status
2. **Manager Flow**: Login → View pending expenses → Approve/reject → View audit
3. **Admin Flow**: Dashboard → User management → Billing → Reports
4. **AP2 Flow**: Submit → AP2 signature → Verify audit trail
5. **Mobile Responsive**: Test on mobile viewports

### 2.4 Security Testing
**Purpose**: Identify vulnerabilities and ensure compliance
**Tools**: Multiple (see below)

#### SAST (Static Application Security Testing)
- **Bandit** - Python security linting
- **ESLint security rules** - JavaScript/TypeScript
- **SonarQube** - Code quality and security
- **Semgrep** - Pattern-based security analysis

#### Dependency Scanning
- **pip-audit** / **safety** - Python dependencies
- **npm audit** / **Snyk** - JavaScript dependencies
- **Trivy** - Container image CVE scanning
- **Dependabot** - Automated dependency updates

#### DAST (Dynamic Application Security Testing)
- **OWASP ZAP** - Full-scan against staging
- **Burp Suite Community** - Manual testing
- **OWASP Dependency-Check** - Known vulnerabilities

#### Additional Security Tests
- **git-secrets** / **gitleaks** - Secret detection in commits
- **Cloud IAM audits** - GCP permission validation
- **KMS integration** - Key management and rotation
- **Penetration testing** - External vendor engagement

### 2.5 Performance & Load Testing
**Purpose**: Validate scalability and SLA compliance
**Tools**: `k6` (primary), `Locust` (alternative)

**Test Types**:
- **Load Tests**: Baseline 100 req/s, normal throughput
- **Spike Tests**: 10× expected peak load
- **Soak Tests**: Sustained load for 6-24 hours (memory leak detection)
- **Stress Tests**: Find breaking point
- **Concurrent Users**: 100+ simultaneous users

**SLA Targets**:
- 95th percentile latency < 500ms for simple APIs
- 99th percentile latency < 2s for complex operations
- Failure rate < 1% under nominal load
- Zero data loss under load

### 2.6 AP2 Protocol & Compliance Tests
**Purpose**: Verify protocol conformance and legal compliance

#### AP2 Protocol Tests
- **Structure**: Validate request/response against AP2 schema
- **Signing**: Test signing/verification end-to-end
- **Edge cases**: Revoked keys, expired tokens, replay attempts
- **Mandate chain**: Verify intent → cart → payment linkage
- **Audit trail**: Verify tamper-evident logs and signature verification

#### Legally-Binding Logs
- Persistence of signed logs
- Verifiable evidence (hash chain)
- Ability to re-verify signatures
- Long-term storage compliance

### 2.7 Helm / Kubernetes Tests
**Purpose**: Validate deployment configurations

**Test Steps**:
1. **Lint**: `helm lint`, `kubeval` against K8s API versions
2. **Dry-run**: `helm template` + `kubectl apply --dry-run=server`
3. **Smoke deploy**: Install to test cluster (kind/minikube/GKE)
4. **RBAC**: Check ServiceAccount scopes, Role/ClusterRole, least privilege
5. **Resource limits**: Verify CPU/memory requests and limits
6. **Health checks**: Readiness and liveness probes
7. **Secrets**: Proper secret management

### 2.8 Infrastructure / Terraform Tests
**Purpose**: Ensure infrastructure code quality

**Test Steps**:
1. **Static checks**: `terraform validate`, `tflint`
2. **Plan-only**: Run `terraform plan` with sample vars
3. **Drift detection**: Simulate changes and verify alerts
4. **IAM tests**: Ensure service accounts have minimal scopes
5. **Cost estimation**: `terraform cost` for budget awareness

### 2.9 CI/CD & Container Tests
**Purpose**: Build quality and security

**Checks**:
- **Build reproducibility**: Deterministic Docker builds
- **Multi-stage optimization**: Layer caching, size optimization
- **Image scanning**: Trivy, Clair, GCR/Artifact Registry scanning
- **Non-root user**: Container runtime security
- **SBOM generation**: Software Bill of Materials

### 2.10 Monitoring & Observability Tests
**Purpose**: Validate logging, alerting, and tracing

**Tests**:
- **Alerting**: Trigger synthetic alerts, validate PagerDuty/email delivery
- **Tracing**: Validate OpenTelemetry traces for long-running flows
- **Log masking**: Ensure PII is not logged
- **Metrics collection**: Verify Prometheus scraping
- **Dashboard validation**: Grafana dashboards display correctly

### 2.11 Compatibility & Cross-Platform Tests
**Purpose**: Ensure broad compatibility

**Coverage**:
- **Browsers**: Chrome, Firefox, Safari (latest LTS)
- **Operating Systems**: Linux, macOS, Windows
- **Kubernetes versions**: Latest 3 minor versions
- **GCP services**: Cloud SQL, Cloud Storage, GKE, Secret Manager
- **Mobile devices**: iOS Safari, Android Chrome

### 2.12 Accessibility & Visual QA
**Purpose**: Ensure inclusive design and visual consistency

**Tools**:
- **axe-core**: Automated a11y checks
- **Lighthouse CI**: Performance and accessibility scoring
- **Percy / Playwright snapshots**: Visual regression testing
- **Manual testing**: Keyboard navigation, screen readers

### 2.13 Compliance & Legal Tests
**Purpose**: Ensure regulatory compliance

**Areas**:
- **Data lifecycle**: Retention, delete/forget flows (GDPR/CCPA)
- **Audit trail**: Export tamper-evident records
- **SLA validation**: Uptime tracking
- **EULA**: Billing/usage meter integration
- **Privacy**: PII handling and masking
- **E-signature**: AP2 signature verification

---

## 3. Test Data & Environment Strategy

### 3.1 Test Environments
1. **Local dev**: docker-compose / kind
2. **Staging**: GCP GKE sandbox (mirrors production)
3. **Production**: Final smoke tests only

### 3.2 Test Data
- **Synthetic receipts**: Varied quality (low-light, rotated, multi-currency)
- **Role-based accounts**: Admin, manager, approver, auditor, tenant-user
- **PII-laden records**: For redaction tests
- **Edge cases**: Large amounts, negative values, special characters

### 3.3 Mocks & Emulators
- **AP2 signing service**: Mock with test keys
- **OCR provider**: Sandbox/test API
- **Cloud SQL**: Use emulator for local tests
- **Email/SMS**: Mock SMTP server

### 3.4 Secrets Management
- CI uses GCP Secret Manager or GitHub Secrets
- Tests must not write secrets to logs
- Rotate test credentials regularly

---

## 4. CI Gating & Release Policy

### 4.1 Pre-Merge Checks (Pull Request)
**Required for merge**:
- ✅ Linting (code style)
- ✅ Unit tests pass (backend & frontend)
- ✅ Minimum coverage check (fail if < 75%)
- ✅ SAST quick scan (no high/critical findings)
- ✅ Dependency check (no critical CVEs)
- ✅ Conventional commits validation

### 4.2 Merge to Main
**Automatic triggers**:
- Build container images → push to test registry
- Run integration tests → ephemeral test env
- DAST fast scan (fail on high severity)
- E2E smoke tests (critical paths)
- Tag Docker images with commit SHA

### 4.3 Release (Staging → Production)
**Manual approval required**:
- Full DAST (OWASP ZAP)
- Container full scan
- Performance baseline (k6)
- Helm chart validation
- Security & performance checklists signed-off

### 4.4 Rollback
- Automated rollback on failing health checks
- Readiness/liveness probe failures trigger rollback
- Canary deployment for gradual rollout

---

## 5. Test Coverage Targets

### Backend (Python)
| Module | Current | Target | Priority |
|--------|---------|--------|----------|
| **models.py** | 100% | 100% | ✅ Complete |
| **config.py** | 100% | 100% | ✅ Complete |
| **auth.py** | 73% | 90% | 🔴 High |
| **api.py** | 22% | 80% | 🔴 High |
| **routes/** | 20-50% | 80% | 🔴 High |
| **services/** | 15-30% | 70% | 🟡 Medium |
| **GCP integrations** | 10-25% | 60% | 🟡 Medium |
| **monitoring.py** | 0% | 60% | 🟡 Medium |

### Frontend (React)
| Component Type | Target | Status |
|----------------|--------|--------|
| **Pages** | 80% | 🔴 To implement |
| **Components** | 75% | 🔴 To implement |
| **Contexts** | 90% | 🔴 To implement |
| **Services** | 85% | 🔴 To implement |
| **Utils** | 95% | 🔴 To implement |

### E2E (Playwright)
| User Journey | Tests | Status |
|--------------|-------|--------|
| **Authentication** | 5 tests | 🔴 To implement |
| **Expense submission** | 8 tests | 🔴 To implement |
| **Approval workflow** | 6 tests | 🔴 To implement |
| **Admin functions** | 10 tests | 🔴 To implement |
| **Mobile responsive** | 4 tests | 🔴 To implement |

---

## 6. Example Test Cases

### 6.1 Happy-Path Expense Flow
```
GIVEN employee is logged in
WHEN they submit expense with receipt image
THEN OCR extracts fields
AND backend creates expense record
AND approver receives notification
WHEN approver approves
THEN AP2 signature is recorded
AND audit log entry is created
AND entry is verifiable via /api/v1/audit/{transaction_id}
```

### 6.2 Expired AP2 Mandate
```
GIVEN an intent mandate was created 48 hours ago
AND mandate expiration is 24 hours
WHEN approver attempts approval
THEN system rejects with error "Mandate expired"
AND audit log records rejection reason
```

### 6.3 Concurrent Approvals
```
GIVEN two approvers view same pending expense
WHEN both click approve simultaneously
THEN one approval succeeds
AND other receives conflict resolution status
AND audit trail shows both attempts with timestamps
```

### 6.4 Token Expiry
```
GIVEN user has valid access token
WHEN token expires after 60 minutes
THEN API returns 401 Unauthorized
AND refresh token flow succeeds
AND new access token is issued
WHEN refresh token is revoked
THEN user must re-authenticate
```

### 6.5 Malicious Input
```
GIVEN attacker sends large payload (>10MB)
THEN API rejects with 413 Payload Too Large
GIVEN SQL injection attempt in description field
THEN ORM sanitizes input
AND no database modification occurs
```

### 6.6 Network Degradation
```
GIVEN AP2 gateway latency increases to 5s
WHEN expense approval is attempted
THEN system retries with exponential backoff
AND timeout occurs after 30s
AND user receives meaningful error message
```

### 6.7 Data Privacy (PII)
```
GIVEN expense contains user email and SSN
WHEN logs are generated
THEN PII is masked (e.g., user@example.com → u***@e***.com)
WHEN export is requested
THEN sensitive fields are redacted
```

### 6.8 UI Accessibility
```
GIVEN user navigates with keyboard only
THEN all forms are accessible via Tab
AND all actions have keyboard shortcuts
AND focus indicators are visible
GIVEN color-blind user
THEN status indicators use patterns + colors
AND color contrast passes WCAG 2.1 AA
```

---

## 7. Test Matrix (Component → Test Types)

| Component | Unit | Integration | E2E | Security | Performance | Compliance |
|-----------|------|-------------|-----|----------|-------------|------------|
| **Backend API** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Frontend** | 🔴 | 🔴 | 🔴 | ✅ | 🔴 | N/A |
| **AP2 Protocol** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Database** | ✅ | ✅ | N/A | ✅ | ✅ | ✅ |
| **Auth** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Helm Charts** | N/A | 🔴 | 🔴 | 🔴 | N/A | N/A |
| **Terraform** | N/A | 🔴 | N/A | 🔴 | N/A | N/A |
| **CI/CD** | N/A | 🔴 | N/A | ✅ | N/A | N/A |

**Legend**: ✅ Implemented | 🔴 To implement | N/A Not applicable

---

## 8. Tools & Technologies

### Testing Frameworks
- **pytest** (v7.4.3) - Python testing
- **pytest-cov** - Coverage reporting
- **pytest-asyncio** - Async test support
- **Playwright** (v1.56.1) - E2E browser testing
- **Jest** / **React Testing Library** - Frontend unit tests

### Security Tools
- **Bandit** - Python SAST
- **ESLint** + **eslint-plugin-security** - JavaScript SAST
- **pip-audit** / **safety** - Dependency scanning
- **Snyk** - Multi-language vulnerability scanning
- **OWASP ZAP** - DAST
- **Trivy** - Container scanning
- **git-secrets** / **gitleaks** - Secret detection

### Performance Tools
- **k6** - Load testing
- **Locust** - Alternative load testing (already configured)
- **Artillery** - API load testing
- **Lighthouse CI** - Frontend performance

### Infrastructure Tools
- **helm** - Kubernetes package manager
- **kubeval** / **kubeconform** - K8s manifest validation
- **terraform** - Infrastructure as Code
- **tflint** - Terraform linting
- **conftest** - Policy-as-Code testing

### CI/CD Tools
- **GitHub Actions** - Primary CI/CD
- **Docker** - Container builds
- **Google Cloud Build** - GCP-specific builds

### Monitoring & Observability
- **Prometheus** - Metrics collection
- **Grafana** - Dashboards
- **OpenTelemetry** - Distributed tracing
- **Sentry** - Error tracking

---

## 9. Implementation Roadmap

### Phase 1: Foundation (Week 1)
- [x] Fix failing unit tests (28 failures → 0)
- [ ] Increase backend coverage to >60%
- [ ] Set up GitHub Actions CI pipeline
- [ ] Configure SAST (Bandit, ESLint)
- [ ] Set up dependency scanning

### Phase 2: Integration & E2E (Week 2)
- [ ] Create Playwright test suite (5 critical paths)
- [ ] Add missing integration tests
- [ ] Configure DAST (OWASP ZAP)
- [ ] Set up test environments (staging)

### Phase 3: Performance & Security (Week 3)
- [ ] Create k6 load tests
- [ ] Run baseline performance tests
- [ ] Security audit and penetration testing
- [ ] Container security scanning

### Phase 4: Infrastructure & Compliance (Week 4)
- [ ] Helm chart testing
- [ ] Terraform validation
- [ ] Compliance tests (GDPR/CCPA)
- [ ] AP2 audit trail verification

### Phase 5: Polish & Documentation (Week 5)
- [ ] Increase backend coverage to >80%
- [ ] Frontend unit tests (>75% coverage)
- [ ] Accessibility testing
- [ ] Complete test documentation

---

## 10. Success Metrics

### Coverage Targets
- ✅ Backend unit tests: >80% coverage
- ✅ Frontend unit tests: >75% coverage
- ✅ Critical paths: 100% E2E coverage
- ✅ API endpoints: 100% documented and tested

### Quality Gates
- ✅ Zero high/critical security vulnerabilities
- ✅ Zero P0/P1 bugs in production
- ✅ 95% test pass rate (allowing 5% flakiness)
- ✅ <1% error rate in production

### Performance Targets
- ✅ <200ms average API response time
- ✅ <500ms 95th percentile
- ✅ 99.9% uptime SLA
- ✅ Support 100+ concurrent users

### Compliance
- ✅ OWASP Top 10 compliance
- ✅ GDPR/CCPA compliance
- ✅ AP2 protocol conformance
- ✅ SOC 2 readiness

---

## 11. Continuous Improvement

### Weekly
- Review test failures and flakiness
- Update test data and scenarios
- Monitor coverage trends

### Monthly
- Security dependency updates
- Performance regression analysis
- Test suite optimization
- Update test documentation

### Quarterly
- External penetration testing
- Load testing at scale
- Architecture review
- Compliance audit

---

## 12. Contact & Resources

### Documentation
- Main README: `/README.md`
- Testing Guide: `/docs/TESTING_GUIDE.md`
- CI/CD Guide: `/.github/workflows/README.md`
- Security Policy: `/SECURITY.md`

### Tools & Access
- GitHub Actions: https://github.com/[org]/ap2-expense-agent/actions
- Test Coverage: https://codecov.io/gh/[org]/ap2-expense-agent
- Security Scans: https://snyk.io/org/[org]
- Performance Dashboard: [Internal Grafana]

---

**Version History**:
- v1.0 (2025-11-12): Initial comprehensive test strategy document

**Next Review**: 2025-11-19

**Owner**: Development Team
**Approvers**: Tech Lead, Security Team, QA Team
