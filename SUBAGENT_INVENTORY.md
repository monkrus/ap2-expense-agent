# Subagent Inventory for AP2 Expense Agent

This document captures the responsibilities and primary commands/validation areas for each of the 20 configured subagents.

## Core Workflows

### expense-flow-validator
- Focus: End-to-end expense submission, receipt uploads, approvals, PDF exports, data integrity, AP2 mandates.
- Commands/tests: `pytest tests/test_expenses.py -v`, `pytest tests/test_admin.py -v`, targeted frontend/test coverage (e.g., `npm test -- expense`), manual integration flow verification.

### policy-budget-auditor
- Focus: Budget enforcement, approval policy precedence, auto-approvals, alerts, and rounding/currency correctness.
- Commands: Review backend routes/services (`budgets.py`, `approval_policies.py`, etc.); no fixed CLI commands.

### receipt-ocr-validator
- Focus: Receipt uploads, OCR extraction, file validation, PII handling, and accurate data mapping.
- Commands: Code review of receipt endpoints/services (no explicit commands provided).

### reporting-export-auditor
- Focus: Export accuracy for CSV/Excel/PDF, filtering, totals, permissions, and performance on large exports.
- Commands: Code review of expense/export endpoints and UI export components.

## Platform and Security

### auth-security-checker
- Focus: Authentication/authorization, JWT, password security, OAuth, OWASP, CORS, token policies.
- Commands: `pytest tests/test_auth.py -v`, `pytest tests/test_security.py -v`, grep for hardcoded secrets, review `.env`.

### rbac-tenant-guardian
- Focus: Tenant isolation, RBAC checks, organization scoping, admin protections, multi-tenancy safeguards.
- Commands: Code review of permission/context modules; no CLI commands specified.

### compliance-governance-auditor
- Focus: GDPR export/deletion, data retention, audit logs, privacy policy, legal documents.
- Commands: Review GDPR and audit files; no explicit commands.

### observability-monitoring-auditor
- Focus: Logging, metrics, alerting, health checks, PII redaction.
- Commands: Inspect `monitoring.py`/`logging_config.py`, monitoring scripts; no CLI commands specified.

## Integrations and Billing

### ap2-marketplace-reviewer
- Focus: AP2 protocol, Google Cloud Marketplace compliance, payment metadata, agent communication.
- Commands: Guidance based on code review; no direct CLI commands but targeted testing when adjusting payment flows.

### api-integration-tester
- Focus: External APIs (Marketplace, AP2, Gemini, Stripe, email/webhooks), error handling, retries, webhook validation.
- Commands: `pytest tests/test_integrations.py -v`, `pytest tests/test_webhooks.py -v`, `pytest backend/tests/test_stripe_processor.py -v`, `pytest tests/test_payments.py -v`, `pytest tests/test_gemini_ai.py -v`, `pytest tests/test_notifications.py -v`, plus manual log inspections and env var checks.

### billing-usage-auditor
- Focus: Subscription tiers, usage metering (AP2/AI), Stripe, Google Marketplace metering, revenue reconciliation.
- Commands: Activate backend venv, run `pytest backend/tests/test_gcp_* -v`, run audit scripts (e.g., `scripts/audit_usage.py`), reconcile scripts, SQL checks, and Marketplace verification commands.

### notification-delivery-checker
- Focus: Email/in-app triggers, templates, retry behavior, branding, SMTP config, templates.
- Commands: Review notification services/templates (no CLI commands specified).

## Engineering and Delivery

### backend-tester
- Focus: Comprehensive backend pytest suite, migration status, API coverage, AP2 mandates, billing, cache, multi-tenancy.
- Commands: Activate `.venv`, `pytest -v`, `pytest --cov=src --cov-report=term-missing`, targeted tests (`tests/test_api.py`, `tests/test_ap2_mandates.py`, etc.), `alembic current`, `alembic history`.

### frontend-tester
- Focus: React/Vite frontend tests, builds, linting, dev server checks.
- Commands: `npm install`, `npm test`, `npm run build`, `npm run dev`, `npm run lint`.

### database-migrator
- Focus: Alembic migration creation/validation, schema drift detection, safety checks, optimization.
- Commands: `alembic current`, `alembic history`, `alembic revision --autogenerate`, `alembic upgrade head`, `alembic downgrade -1`.

### performance-profiler
- Focus: Backend/DB/frontend performance, profiling (cProfile/memory), caching, load testing, Lighthouse.
- Commands: `python -m cProfile`, `snakeviz`, PG `EXPLAIN ANALYZE`, `locust`, `npm run build -- --analyze`, `npx lighthouse`, etc.

### deployment-validator
- Focus: Deployment readiness (Cloud Run, env vars, builds, migrations, marketplace manifest, security compliance).
- Commands: Backend tests, `alembic` checks, Docker builds/runs, health checks, frontend builds, env var checks, `gcloud run deploy` (dry run), Cloud SQL connect.

### infra-iac-reviewer
- Focus: Terraform/Helm/K8s review, resource sizing, secrets, rollback, reliability.
- Commands: Review IaC directories (no CLI commands mandated).

### ui-ux-accessibility-reviewer
- Focus: UI/UX, accessibility, responsive, keyboard navigation, contrast, forms.
- Commands: `npm run dev`, `npm run lint` (optional).

### docs-marketplace-curator
- Focus: Documentation, changelog, marketplace assets, README accuracy, screenshots.
- Commands: Review docs (`README.md`, `CHANGELOG.md`, etc.).
