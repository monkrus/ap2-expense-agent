# AP2 Expense Management System

AI-powered expense management application implementing Google's AP2 Protocol for secure, cryptographically-verified agent payments.

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)
![React](https://img.shields.io/badge/React-18.2-blue.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)

## ✨ Features

### Authentication & Authorization
- ✅ JWT Authentication with refresh tokens
- ✅ OAuth 2.0 Authorization Code Flow
- ✅ 2FA/TOTP with QR codes & backup codes
- ✅ Role-Based Access Control (Admin, Manager, Accountant, Employee)
- ✅ Session management with device tracking
- ✅ Password security with bcrypt
- ✅ Rate limiting protection

### AP2 Protocol
- ✅ Intent Mandates - Cryptographic authorization
- ✅ Cart Mandates - Transaction verification
- ✅ Payment Mandates - Audit trail
- ✅ AI Expense Categorization
- ✅ Receipt OCR

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 15+

### Installation

**Backend:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your DATABASE_URL and JWT_SECRET

# Run migrations
alembic upgrade head

# Start server
uvicorn src.api:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Access:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## 📚 Documentation

- [Implementation Plan](IMPLEMENTATION_PLAN.md)
- [Security Audit](SECURITY_AUDIT_REPORT.md)
- [System Audit](COMPREHENSIVE_AUDIT_REPORT.md)
- [Backup Strategy](backend/DATABASE_BACKUP_STRATEGY.md)
- [Data Retention](backend/DATA_RETENTION_POLICY.md)

## 🔒 Security

- Rate limiting on auth endpoints
- JWT with secure secrets
- 2FA/TOTP authentication
- Audit logging
- Session tracking
- Password complexity requirements

## 🧪 Testing

\`\`\`bash
# Backend
pytest tests/ --cov=src

# Frontend
npm test
\`\`\`

## 📄 License

MIT License

---

**Built with FastAPI, React, and Google's AP2 Protocol**
