# AP2 Expense Management Agent

[![Production Ready](https://img.shields.io/badge/production-ready-brightgreen)](https://github.com/monkrus/ap2-expense-agent)
[![Test Coverage](https://img.shields.io/badge/coverage-96%25-brightgreen)](backend/tests)
[![Security](https://img.shields.io/badge/security-hardened-green)](backend/SECURITY_REMEDIATION_REPORT.md)
[![QuickBooks](https://img.shields.io/badge/QuickBooks-App%20Store-2CA01C)](https://developer.intuit.com/)
[![Stripe](https://img.shields.io/badge/Stripe-billing-635BFF)](https://stripe.com)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

AI-powered expense management with autonomous AP2 protocol approvals, QuickBooks Online sync, and Stripe subscription billing. Built for the Intuit App Store.

## What Makes AP2 Different

Most expense tools still require manual manager approval for every receipt. AP2 uses **Intent Mandates** to auto-approve 60-70% of routine expenses instantly:

1. Manager creates a rule: *"Auto-approve Amazon office supplies up to $200/month"*
2. Employee submits a $45 Amazon receipt
3. AP2 agent matches the mandate and approves in seconds - no human needed
4. Exceptions route to manual review as usual

Result: faster reimbursements, less manager overhead, full cryptographic audit trail.

## Features

### Core
- **AP2 Autonomous Approvals** - Intent Mandate matching auto-approves routine expenses
- **Expense Management** - Submit, approve, track, and export with receipt attachments
- **QuickBooks Online Sync** - OAuth2 connect, expense sync, account/vendor mapping
- **Budget Management** - Track budgets, set alerts, monitor spending
- **Receipt OCR** - AI-powered receipt scanning and data extraction
- **Export & Reporting** - CSV, Excel, and PDF exports with custom filtering

### Billing & Integration
- **Stripe Subscription Billing** - Checkout, Customer Portal, webhook lifecycle
- **Subscription Tiers** - Free, Starter ($29/mo), Professional ($79/mo)
- **QuickBooks App Store** - Listed on the Intuit App Store for discovery
- **2FA Authentication** - TOTP-based two-factor authentication
- **Audit Logging** - Hash-chain verified audit trail (GDPR/SOC 2 ready)
- **Multi-Tenant Architecture** - Organization isolation with RBAC

### Technical
- **150+ API Endpoints** - REST API with OpenAPI/Swagger docs
- **PostgreSQL + SQLite** - Postgres in production, SQLite for dev
- **Cloud Run Deployment** - Containerized with auto-scaling
- **CI/CD Pipeline** - GitHub Actions for testing and deployment
- **Security Hardened** - Input validation, rate limiting, JWT auth

---

## Quick Start

### Local Development

```bash
# Clone
git clone https://github.com/monkrus/ap2-expense-agent.git
cd ap2-expense-agent

# Backend
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env     # Edit with your values
uvicorn src.api:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev

# Access
# Frontend: http://localhost:5173
# Backend:  http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Docker Compose

```bash
cp .env.example .env  # Edit with your values
docker-compose up -d
```

### Production Deployment (Cloud Run)

```bash
# Requires gcloud CLI configured
./deploy-complete.sh --project YOUR_GCP_PROJECT_ID
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Google Cloud Run                       │
│  ┌────────────────┐  ┌────────────────┐  ┌───────────┐  │
│  │  Backend API   │  │  Frontend SPA  │  │ Cloud SQL │  │
│  │  (FastAPI)     │  │  (React/Vite)  │  │ Postgres  │  │
│  └───────┬────────┘  └────────────────┘  └─────┬─────┘  │
│          │                                      │        │
│          ├──── Secret Manager ──────────────────┘        │
│          │                                               │
└──────────┼───────────────────────────────────────────────┘
           │
    ┌──────┴──────────────────────────────────┐
    │           External Services              │
    │  ┌─────────┐ ┌────────────┐ ┌────────┐  │
    │  │ Stripe  │ │ QuickBooks │ │ SMTP   │  │
    │  │ Billing │ │ Online API │ │ Email  │  │
    │  └─────────┘ └────────────┘ └────────┘  │
    └─────────────────────────────────────────┘
```

### Tech Stack

**Backend:** FastAPI, SQLAlchemy 2.0, Pydantic 2, Alembic, Python 3.11
**Frontend:** React 18, Vite, TailwindCSS, Axios, Lucide Icons
**Infrastructure:** Cloud Run, Cloud SQL (Postgres 15), Secret Manager
**Integrations:** Stripe (billing), QuickBooks Online (accounting sync), SendGrid (email)

---

## Deployment Scripts

| Script | Purpose |
|--------|---------|
| `deploy-complete.sh` | End-to-end Cloud Run deployment |
| `scripts/deploy-production.sh` | Production deploy with gradual rollout |
| `scripts/validate-environment.sh` | Pre-deploy environment validation |
| `scripts/backup-database.sh` | Cloud SQL backup |
| `scripts/rollback-deployment.sh` | Safe rollback |
| `scripts/smoke-test.sh` | Post-deploy health checks |

---

## Testing

```bash
# Backend tests
cd backend && pytest --cov=src --cov-report=html

# Frontend build
cd frontend && npm run build
```

---

## Pricing

| Feature | Free | Starter ($29/mo) | Professional ($79/mo) |
|---------|------|-------------------|----------------------|
| Users | 2 | 5 | 25 |
| Expenses/month | 30 | 50 | 500 |
| AP2 Auto-Approvals | 20 | 100 | 1,000 |
| OCR Scans | 30 | 50 | 200 |
| QuickBooks Sync | - | Basic | Full |
| Data Retention | 90 days | 1 year | 3 years |

AP2 payment processing: 2.9% + $0.30 per transaction (standard Stripe fees).
See [PRICING_STRUCTURE.md](documents/PRICING_STRUCTURE.md) for full details.

---

## API Overview

Interactive docs at `http://localhost:8000/docs` (Swagger UI).

**Key endpoint groups:**

| Group | Prefix | Purpose |
|-------|--------|---------|
| Auth | `/api/v1/auth/*` | Register, login, 2FA, refresh |
| Expenses | `/api/v1/expenses/*` | CRUD, approve, export |
| AP2 | `/api/ap2/*` | Intent/Cart/Payment mandates |
| Organizations | `/api/v1/organizations/*` | Org CRUD, invitations, members |
| Stripe Billing | `/api/v1/stripe/*` | Checkout, Portal, webhooks |
| QuickBooks | `/api/v1/quickbooks/*` | OAuth, sync, accounts, vendors |
| Analytics | `/api/v1/analytics/*` | Variance, spending, forecasts |
| Budgets | `/api/budgets/*` | Budget CRUD, health, evaluate |

**Total:** 150+ endpoints

---

## Environment Variables

Copy `.env.example` to `.env` and configure. Key variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes (prod) | PostgreSQL connection string |
| `JWT_SECRET` | Yes | Secret key for JWT tokens |
| `STRIPE_SECRET_KEY` | Yes (billing) | Stripe API secret key |
| `STRIPE_WEBHOOK_SECRET` | Yes (billing) | Stripe webhook signing secret |
| `QUICKBOOKS_CLIENT_ID` | Yes (QB) | Intuit OAuth2 client ID |
| `QUICKBOOKS_CLIENT_SECRET` | Yes (QB) | Intuit OAuth2 client secret |
| `SMTP_SERVER` | Yes (email) | SMTP host (e.g., smtp.sendgrid.net) |
| `SMTP_USERNAME` | Yes (email) | SMTP username |
| `SMTP_PASSWORD` | Yes (email) | SMTP password / API key |

See [.env.example](.env.example) for the complete list.

---

## Intuit App Store Listing

This app is designed for listing on the [Intuit App Store](https://apps.intuit.com/). Requirements met:

- OAuth2 connect/disconnect flow for QuickBooks Online
- Intuit disconnect webhook handler (`POST /api/v1/quickbooks/webhook/disconnect`)
- Expense sync to QuickBooks as Bills/Purchases
- Account and vendor mapping
- Privacy policy and terms of service at `/legal/`
- HTTPS enforced in production

See [INTUIT_APP_STORE.md](INTUIT_APP_STORE.md) for submission checklist and configuration.

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Run tests: `cd backend && pytest`
4. Open a Pull Request

---

## License

MIT - see [LICENSE](LICENSE).

---

Built with FastAPI, React, Stripe, and QuickBooks Online API.
