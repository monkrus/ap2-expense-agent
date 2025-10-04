# AP2 Expense Management - Quick Setup Guide

## Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- Git

## Quick Start

### 1. Clone and Setup Database

```bash
# Create PostgreSQL database
createdb expenses

# Or using psql
psql -U postgres
CREATE DATABASE expenses;
CREATE USER ap2user WITH PASSWORD 'changeme';
GRANT ALL PRIVILEGES ON DATABASE expenses TO ap2user;
\q
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
DATABASE_URL=postgresql://ap2user:changeme@localhost:5432/expenses
JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
ENVIRONMENT=development
DEBUG=true
EOF

# Run database migrations
alembic upgrade head

# Initialize authentication system (creates default admin user)
python setup_auth.py

# Start backend server
uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: `http://localhost:8000`
API Documentation: `http://localhost:8000/docs`

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at: `http://localhost:5173`

### 4. Default Login Credentials

After running `setup_auth.py`, you can login with:

- **Username**: `admin`
- **Password**: `Admin123!`
- **Email**: `admin@ap2expense.com`

⚠️ **Important**: Change the admin password immediately after first login!

## Environment Variables

### Backend (.env)

```bash
# Database
DATABASE_URL=postgresql://ap2user:changeme@localhost:5432/expenses
REDIS_URL=redis://localhost:6379/0

# JWT & Authentication
JWT_SECRET=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60
REFRESH_TOKEN_EXPIRATION_DAYS=30

# Security
PASSWORD_RESET_EXPIRATION_HOURS=1
SESSION_EXPIRATION_HOURS=24
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION_MINUTES=30

# Email (for password reset)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=noreply@ap2expense.com

# Google AI (optional)
GOOGLE_API_KEY=your-google-api-key
GOOGLE_CLOUD_PROJECT=your-project-id

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost

# Environment
ENVIRONMENT=development
DEBUG=true
```

## Testing the Authentication System

### 1. Register a New User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "testuser",
    "password": "SecurePass123!",
    "full_name": "Test User"
  }'
```

### 2. Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "Admin123!"
  }'
```

Response includes `access_token` and `refresh_token`.

### 3. Access Protected Endpoint

```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 4. Setup 2FA

```bash
curl -X POST http://localhost:8000/api/v1/auth/2fa/setup \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Returns QR code URL and backup codes.

## File Structure

```
ap2-expense-agent/
├── backend/
│   ├── alembic/
│   │   ├── versions/
│   │   │   └── 001_initial_auth_tables.py
│   │   ├── env.py
│   │   └── script.py.mako
│   ├── src/
│   │   ├── routes/
│   │   │   ├── auth.py          # Authentication endpoints
│   │   │   ├── users.py         # User management
│   │   │   └── oauth.py         # OAuth2 endpoints
│   │   ├── models.py            # Database models
│   │   ├── schemas.py           # Pydantic schemas
│   │   ├── auth.py              # Auth utilities & middleware
│   │   ├── database.py          # Database connection
│   │   ├── config.py            # Configuration
│   │   ├── api.py               # Main API app
│   │   └── agent.py             # Expense agent
│   ├── alembic.ini
│   ├── requirements.txt
│   └── setup_auth.py            # Auth setup script
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Login.jsx
│   │   │   ├── Register.jsx
│   │   │   └── ProtectedRoute.jsx
│   │   ├── contexts/
│   │   │   └── AuthContext.jsx
│   │   ├── App.jsx
│   │   ├── AppWrapper.jsx
│   │   └── main.jsx
│   └── package.json
├── AUTHENTICATION.md            # Detailed auth documentation
└── SETUP_GUIDE.md              # This file
```

## Features Implemented

### ✅ Authentication & Authorization
- [x] User authentication (OAuth 2.0)
- [x] Login/logout functionality
- [x] JWT token validation
- [x] Session management
- [x] Role-based access control (RBAC)
- [x] User management system
- [x] Password reset
- [x] 2FA/MFA (TOTP)

### User Roles
- **Admin**: Full system access
- **Manager**: Manage team expenses and approvals
- **Accountant**: Financial oversight and reporting
- **Employee**: Submit and view own expenses

### Security Features
- Bcrypt password hashing
- JWT access tokens with refresh tokens
- Session tracking with device info
- Audit logging
- 2FA with TOTP (Google Authenticator)
- Password requirements validation
- Protected API endpoints
- CORS configuration

## Common Issues & Solutions

### Database Connection Error
```bash
# Check PostgreSQL is running
sudo service postgresql status

# Check database exists
psql -U postgres -c "\l" | grep expenses
```

### Import Errors
```bash
# Make sure you're in the virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Frontend Not Loading
```bash
# Clear node modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

### CORS Errors
Update `CORS_ORIGINS` in backend `.env` to include your frontend URL.

## Next Steps

1. **Change Admin Password**: Login and change the default password
2. **Create Users**: Register additional users or create via admin panel
3. **Configure Email**: Set up SMTP for password reset emails
4. **Enable 2FA**: Setup two-factor authentication for admin account
5. **Review Security**: Check AUTHENTICATION.md for security best practices
6. **Customize**: Adjust settings in config.py and .env

## API Documentation

Once the backend is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Support

For detailed information, see:
- `AUTHENTICATION.md` - Complete authentication documentation
- `backend/src/routes/` - API endpoint implementations
- `frontend/src/contexts/AuthContext.jsx` - Frontend auth logic

---

Happy coding! 🚀
