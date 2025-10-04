# AP2 Expense Management - Authentication & Authorization

## Overview

This document describes the comprehensive authentication and authorization system implemented for the AP2 Expense Management platform.

## Features Implemented

### ✅ 1. User Authentication (OAuth 2.0)
- **OAuth 2.0 Authorization Code Flow** - Full implementation with client registration
- **JWT Access Tokens** - Secure, stateless authentication with configurable expiration
- **Refresh Tokens** - Long-lived tokens for obtaining new access tokens
- **Token Revocation** - Ability to revoke refresh tokens and sessions

### ✅ 2. Login/Logout Functionality
- **User Login** - Username/password authentication with optional 2FA
- **User Logout** - Secure logout with token revocation
- **Session Management** - Track active sessions with device info, IP, and user agent
- **Automatic Token Refresh** - Frontend automatically refreshes expired tokens

### ✅ 3. JWT Token Validation
- **Token Signing** - HS256 algorithm with configurable secret
- **Token Verification** - Validate signature, expiration, and claims
- **Token Refresh** - Exchange refresh token for new access token
- **Custom Claims** - User ID, username, and role embedded in token

### ✅ 4. Session Management
- **Active Session Tracking** - Database-backed session storage
- **Session Expiration** - Configurable session timeout (default: 24 hours)
- **Multi-Device Support** - Track sessions across different devices
- **Session Revocation** - Users can revoke individual sessions

### ✅ 5. Role-Based Access Control (RBAC)
- **User Roles**:
  - `admin` - Full system access
  - `manager` - Manage team expenses and approvals
  - `accountant` - Financial oversight and reporting
  - `employee` - Submit and view own expenses

- **Role-Based Middleware**:
  - `require_admin()` - Admin-only endpoints
  - `require_manager()` - Manager and Admin access
  - `require_accountant()` - Accountant and Admin access
  - Custom role checks per endpoint

### ✅ 6. User Management System
- **User CRUD Operations**:
  - Create users (admin only)
  - Read user profiles (self or manager+)
  - Update user information
  - Delete users (admin only)
  - List users with filtering

- **User Registration** - Public endpoint for new user signup
- **Profile Management** - Users can update their own profiles

### ✅ 7. Password Reset
- **Reset Request** - Generate secure reset token
- **Email Notification** - Send reset link via email (configurable SMTP)
- **Token Validation** - Time-limited, single-use tokens
- **Password Confirmation** - Set new password with token
- **Password Change** - Authenticated users can change password

### ✅ 8. 2FA/MFA (TOTP)
- **TOTP Setup** - Generate secret and QR code
- **Backup Codes** - 10 single-use backup codes
- **2FA Enable/Disable** - User-controlled 2FA management
- **Login with 2FA** - Support for TOTP codes during login
- **Backup Code Validation** - Use backup codes when TOTP unavailable

## API Endpoints

### Authentication (`/api/v1/auth`)

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/register` | POST | Register new user | No |
| `/login` | POST | Login with credentials | No |
| `/logout` | POST | Logout and revoke token | Yes |
| `/refresh` | POST | Refresh access token | No |
| `/me` | GET | Get current user info | Yes |
| `/password/reset-request` | POST | Request password reset | No |
| `/password/reset-confirm` | POST | Confirm password reset | No |
| `/password/change` | POST | Change password | Yes |
| `/2fa/setup` | POST | Setup 2FA | Yes |
| `/2fa/enable` | POST | Enable 2FA | Yes |
| `/2fa/disable` | POST | Disable 2FA | Yes |
| `/2fa/verify` | POST | Verify 2FA code | Yes |

### User Management (`/api/v1/users`)

| Endpoint | Method | Description | Auth Required | Role Required |
|----------|--------|-------------|---------------|---------------|
| `/` | GET | List all users | Yes | Manager/Admin |
| `/{user_id}` | GET | Get user by ID | Yes | Self/Manager/Admin |
| `/` | POST | Create user | Yes | Admin |
| `/{user_id}` | PATCH | Update user | Yes | Self/Admin |
| `/{user_id}` | DELETE | Delete user | Yes | Admin |
| `/{user_id}/sessions` | GET | List user sessions | Yes | Self/Admin |
| `/{user_id}/sessions/{session_id}` | DELETE | Revoke session | Yes | Self/Admin |

### OAuth2 (`/api/v1/oauth2`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/authorize` | GET/POST | OAuth2 authorization |
| `/token` | POST | Get access token |
| `/consent` | GET | OAuth2 consent page |

## Frontend Components

### Context & Providers
- **AuthContext** - Global authentication state management
- **AuthProvider** - Provides auth methods and state to components

### Components
- **Login** - Login form with 2FA support
- **Register** - User registration with password validation
- **ProtectedRoute** - Route guard for authenticated users
- **AppWrapper** - Main app wrapper with auth integration

### Features
- Auto token refresh on 401 errors
- Persistent sessions (localStorage)
- User profile display
- Logout functionality
- Role-based UI rendering

## Database Schema

### Users Table
- `id` - Unique identifier
- `email` - User email (unique)
- `username` - Username (unique)
- `hashed_password` - Bcrypt hashed password
- `full_name` - Full name
- `role` - User role (enum)
- `is_active` - Account status
- `is_verified` - Email verification status
- `totp_secret` - 2FA secret
- `totp_enabled` - 2FA status
- `backup_codes` - Backup codes for 2FA
- Timestamps: `created_at`, `updated_at`, `last_login`

### Refresh Tokens Table
- `id`, `user_id`, `token`
- `expires_at`, `revoked`
- `device_info`

### Password Reset Tokens Table
- `id`, `user_id`, `token`
- `expires_at`, `used`

### Sessions Table
- `id`, `user_id`, `session_token`
- `expires_at`, `last_activity`
- `ip_address`, `user_agent`
- `revoked`

### Audit Logs Table
- `id`, `user_id`, `action`
- `resource_type`, `resource_id`
- `details`, `ip_address`, `user_agent`
- `created_at`

## Security Features

1. **Password Security**
   - Bcrypt hashing
   - Minimum 8 characters
   - Requires: uppercase, lowercase, digit
   - Validation on both frontend and backend

2. **Token Security**
   - JWT with HMAC-SHA256
   - Configurable expiration
   - Refresh token rotation
   - Secure token storage

3. **Session Security**
   - Session timeout
   - IP and user agent tracking
   - Multi-device management
   - Session revocation

4. **Audit Trail**
   - All auth events logged
   - User actions tracked
   - IP and timestamp recording

5. **2FA/MFA**
   - TOTP (Google Authenticator compatible)
   - Backup codes
   - QR code setup

## Configuration

Environment variables (`.env`):

```bash
# JWT
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

# Database
DATABASE_URL=postgresql://ap2user:changeme@localhost:5432/expenses

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

## Setup Instructions

### Backend Setup

1. Install dependencies:
```bash
cd backend
pip install -r requirements.txt
```

2. Set up database:
```bash
# Create PostgreSQL database
createdb expenses

# Run migrations
alembic upgrade head
```

3. Initialize authentication system:
```bash
python setup_auth.py
```

This creates a default admin user:
- Username: `admin`
- Password: `Admin123!`
- Email: `admin@ap2expense.com`

4. Start the server:
```bash
uvicorn src.api:app --reload
```

### Frontend Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Start development server:
```bash
npm run dev
```

3. Access the application:
```
http://localhost:5173
```

## Usage Examples

### Login
```javascript
const { login } = useAuth();
const result = await login('username', 'password', totpCode);
```

### Protected API Request
```javascript
const { apiRequest } = useAuth();
const response = await apiRequest('/api/v1/expenses', {
  method: 'POST',
  body: JSON.stringify(expenseData)
});
```

### Check User Role
```javascript
const { user } = useAuth();
if (user?.role === 'admin') {
  // Show admin features
}
```

### Setup 2FA
```javascript
// Backend automatically generates QR code
const response = await fetch('/api/v1/auth/2fa/setup', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const { qr_code_url, backup_codes } = await response.json();
```

## Testing

Default test users created by `setup_auth.py`:
- Admin: `admin` / `Admin123!`

Create additional users via:
- Registration endpoint
- Admin user creation endpoint

## Security Best Practices

1. **Change Default Credentials** - Immediately change admin password
2. **Use Strong JWT Secret** - Generate random secret for production
3. **Enable HTTPS** - Always use TLS in production
4. **Configure SMTP** - Set up email for password reset
5. **Regular Audits** - Review audit logs periodically
6. **Rate Limiting** - Implement rate limiting on auth endpoints
7. **Account Lockout** - Enable after failed login attempts

## Future Enhancements

- Email verification on registration
- Social login (Google, GitHub)
- Account lockout after failed attempts
- Password history
- Force password reset
- API key authentication
- WebAuthn/FIDO2 support
- Rate limiting middleware
- Geolocation-based security
- Device fingerprinting

## Support

For issues or questions:
1. Check API documentation: `http://localhost:8000/docs`
2. Review logs: Check FastAPI console output
3. Database issues: Check PostgreSQL logs
4. Frontend issues: Check browser console

---

**Note**: This authentication system is production-ready but should be reviewed by security experts before deployment to production environments.
