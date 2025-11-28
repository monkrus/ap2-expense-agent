# Dependabot Alert Management

## Alerts to Dismiss (Mitigated)

When reviewing Dependabot alerts at https://github.com/monkrus/ap2-expense-agent/security/dependabot,
use these dismissal reasons:

### Frontend (NPM)

#### xlsx - Prototype Pollution + ReDoS
- **CVE**: GHSA-4r6h-8v6p-xvw6, GHSA-5pgg-2g8v-p4x9
- **Severity**: High
- **Status**: MITIGATED
- **Dismissal Reason**: "Risk is tolerable for this project"
- **Justification**:
  ```
  Mitigated with comprehensive security controls:
  - 5-second timeout protection prevents ReDoS
  - Error boundary prevents app crashes
  - Client-side processing only (no server exposure)
  - File size validation (10MB max)
  - Workbook structure validation
  - Security event logging

  See MITIGATIONS_IMPLEMENTED.md for full details.
  ```

### Backend (Python)

#### ecdsa - Timing Attacks
- **CVE**: CVE-2024-23342, PVE-2024-64396
- **Severity**: Medium
- **Status**: LATEST VERSION (no fix available)
- **Dismissal Reason**: "No bandwidth to fix this"
- **Justification**:
  ```
  Running latest version (0.19.1).
  No security patch available from upstream.
  Used for JWT signing in AP2 protocol.
  Monitoring repository for updates.

  See DEPENDENCY_AUDIT_REPORT.md for full risk assessment.
  ```

## Alerts to Accept (Dependabot PRs)

For any alerts where Dependabot creates automatic update PRs:
- ✅ Review the PR
- ✅ Check if tests pass
- ✅ Merge immediately if critical/high severity

## Weekly Review Process

Every Monday (when Dependabot runs):
1. Check new alerts at security tab
2. Accept auto-generated PRs for updateable packages
3. Dismiss known mitigated alerts (use justifications above)
4. Update DEPENDENCY_AUDIT_REPORT.md if new issues found

## Critical Alert Response

For **CRITICAL** severity alerts:
1. Investigate immediately
2. Update dependency ASAP
3. Run full test suite
4. Deploy fix within 24 hours
5. Document in incident log

## Contact

Security concerns: Report via GitHub Security Advisory
