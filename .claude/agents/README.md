# Subagents

These subagents specialize in distinct areas of the AP2 Expense Management
Agent. Use them to review, test, or validate changes in their domain.

## Coverage map

### Core workflows
- expense-flow-validator: end-to-end expense submission, approvals, exports.
- policy-budget-auditor: approval policies and budget enforcement.
- receipt-ocr-validator: receipt uploads and OCR extraction.
- reporting-export-auditor: CSV, Excel, and PDF reporting accuracy.

### Platform and security
- auth-security-checker: authentication, authorization, security review.
- rbac-tenant-guardian: tenant isolation and role boundaries.
- compliance-governance-auditor: GDPR, audit readiness, data retention.
- observability-monitoring-auditor: logging, metrics, alerting, tracing.

### Integrations and billing
- ap2-marketplace-reviewer: AP2 protocol and GCP Marketplace compliance.
- api-integration-tester: external APIs and webhooks.
- billing-usage-auditor: subscription tiers, usage metering, Stripe.
- notification-delivery-checker: email and in-app notifications.

### Engineering and delivery
- backend-tester: backend test suites and API validation.
- frontend-tester: frontend tests and build validation.
- database-migrator: schema changes and Alembic migrations.
- performance-profiler: latency, query, and bundle performance.
- deployment-validator: release readiness and environment configuration.
- infra-iac-reviewer: terraform, k8s, helm, and deployment scripts.

### Product and documentation
- ui-ux-accessibility-reviewer: usability and accessibility reviews.
- docs-marketplace-curator: docs, marketplace assets, changelog alignment.
