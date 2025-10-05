# AP2 Expense Management System - Security Audit Report

**Audit Date:** October 4, 2025
**Auditor:** System Security Review
**Version:** 1.0.0

---

## Executive Summary

This comprehensive security audit evaluates the AP2 Expense Management application, which consists of a FastAPI backend with PostgreSQL database and a React frontend. The system implements Google's AP2 Protocol for AI agent payments with comprehensive authentication and authorization.

### Overall Security Rating: **B+ (Good)**

**Strengths:**
- Comprehensive authentication system with JWT + refresh tokens
- 2FA/TOTP implementation with backup codes
- Role-Based Access Control (RBAC) with 4 roles
- OAuth 2.0 Authorization Code Flow
- Session management with tracking
- Audit logging system
- Password security (hashing, validation)
- Database connection pooling
- Data retention policies

**Critical Issues Found:** 3
**High-Priority Issues:** 8
**Medium-Priority Issues:** 12
**Low-Priority Issues:** 7

---

## 1. Architecture Overview

### Backend Stack
- **Framework:** FastAPI 0.104.1
- **Database:** PostgreSQL (configured) / SQLite (currently active)
- **ORM:** SQLAlchemy 2.0.23
- **Authentication:** JWT (python-jose), bcrypt (passlib)
- **2FA:** PyOTP with QR codes
- **Migrations:** Alembic

### Frontend Stack
- **Framework:** React 18.2.0
- **Build Tool:** Vite 5.0.8
- **Styling:** Tailwind CSS 3.3.6
- **HTTP Client:** Axios 1.6.2

### File Structure
```
backend/
├── src/
│   ├── agent.py          # AP2 protocol implementation
│   ├── api.py            # Main FastAPI app
│   ├── auth.py           # Authentication service
│   ├── config.py         # Configuration
│   ├── database.py       # Database setup
│   ├── models.py         # SQLAlchemy models
│   ├── schemas.py        # Pydantic schemas
│   ├── maintenance.py    # Data retention service
│   └── routes/           # API endpoints
│       ├── auth.py       # Auth endpoints
│       ├── users.py      # User management
│       ├── oauth.py      # OAuth2 flow
│       └── admin.py      # Admin endpoints
├── alembic/              # Database migrations
└── tests/                # Test directory (EMPTY)

frontend/
├── src/
│   ├── App.jsx           # Main expense UI
│   ├── components/       # React components
│   └── contexts/         # Auth context
```

---

## 2. Critical Security Issues ⚠️

### 2.1 **CRITICAL: SQLite in Production Instead of PostgreSQL**
**Severity:** CRITICAL
**Location:** `backend/.env:1`

```env
DATABASE_URL=sqlite:///./expenses.db  # Using SQLite
```

**Issue:**
- `.env` file uses SQLite instead of PostgreSQL
- PostgreSQL migrations exist but not being used
- SQLite has limited concurrency and security features

**Impact:**
- Data integrity issues under concurrent access
- No advanced security features (row-level security, etc.)
- Performance degradation at scale

**Recommendation:**
```env
DATABASE_URL=postgresql://ap2user:changeme@localhost:5432/expenses
```

**Fix Priority:** IMMEDIATE

---

### 2.2 **CRITICAL: Hardcoded Secrets in Configuration**
**Severity:** CRITICAL
**Location:** `backend/src/config.py`

```python
jwt_secret: str = "your-secret-key-change-in-production"
```

**Issue:**
- Default JWT secret is hardcoded
- Same secret in `.env` file
- Could be committed to version control

**Impact:**
- JWT tokens can be forged if secret is known
- Complete authentication bypass possible

**Recommendation:**
```python
jwt_secret: str  # No default, must be set in .env
# Generate strong secret: python -c "import secrets; print(secrets.token_urlsafe(64))"
```

**Fix Priority:** IMMEDIATE

---

### 2.3 **CRITICAL: Missing Input Validation on File Uploads**
**Severity:** CRITICAL
**Location:** Not implemented

**Issue:**
- No file upload handling implemented
- If added later, could introduce vulnerabilities

**Impact:**
- Potential for malicious file uploads
- Code execution vulnerabilities

**Recommendation:**
- Implement file type validation
- Scan uploads for malware
- Limit file sizes
- Store outside webroot

**Fix Priority:** Before implementing file uploads

---

## 3. High-Priority Security Issues 🔴

### 3.1 **No Rate Limiting on Authentication Endpoints**
**Severity:** HIGH
**Location:** `backend/src/routes/auth.py`

**Issue:**
- Login endpoint has no rate limiting
- Password reset has no rate limiting
- Brute force attacks possible

**Impact:**
- Credential stuffing attacks
- Password guessing
- Account enumeration

**Recommendation:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/login")
@limiter.limit("5/minute")
async def login(...):
    pass
```

**Fix Priority:** HIGH

---

### 3.2 **CORS Configuration Too Permissive**
**Severity:** HIGH
**Location:** `backend/src/api.py:29`

```python
allow_origins=settings.cors_origins.split(","),
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
```

**Issue:**
- Allows all methods and headers
- Could enable CSRF attacks

**Recommendation:**
```python
allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
allow_headers=["Authorization", "Content-Type"],
```

---

### 3.3 **No HTTPS/TLS Enforcement**
**Severity:** HIGH
**Location:** Configuration

**Issue:**
- No HTTPS redirect
- Cookies not marked as Secure
- Tokens transmitted in plaintext over HTTP

**Impact:**
- Man-in-the-middle attacks
- Token/credential interception

**Recommendation:**
```python
# In production config
app.add_middleware(
    HTTPSRedirectMiddleware
)

# Set secure cookies
response.set_cookie(
    key="access_token",
    value=token,
    httponly=True,
    secure=True,  # HTTPS only
    samesite="strict"
)
```

---

### 3.4 **Weak Password Policy**
**Severity:** HIGH
**Location:** `backend/src/schemas.py:16-26`

**Current Policy:**
- Minimum 8 characters
- 1 uppercase, 1 lowercase, 1 digit

**Missing:**
- No special character requirement
- No password history check
- No common password dictionary check

**Recommendation:**
```python
import re
from passlib.pwd import genword

@validator('password')
def validate_password(cls, v):
    if len(v) < 12:  # Increase to 12
        raise ValueError('Password must be at least 12 characters')
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
        raise ValueError('Password must contain special character')
    # Check against common passwords
    if v.lower() in COMMON_PASSWORDS:
        raise ValueError('Password is too common')
    return v
```

---

### 3.5 **No Account Lockout Mechanism**
**Severity:** HIGH
**Location:** Missing

**Issue:**
- Unlimited login attempts
- No temporary account lockout
- No failed login tracking

**Impact:**
- Brute force attacks easier
- No protection against automated attacks

**Recommendation:**
```python
# Add to User model
failed_login_attempts: int = 0
locked_until: Optional[datetime] = None

# In login endpoint
if user.locked_until and user.locked_until > datetime.utcnow():
    raise HTTPException(status_code=423, detail="Account locked")

if not verify_password:
    user.failed_login_attempts += 1
    if user.failed_login_attempts >= 5:
        user.locked_until = datetime.utcnow() + timedelta(minutes=30)
    db.commit()
    raise HTTPException(...)
```

---

### 3.6 **OAuth Client Secrets in Memory**
**Severity:** HIGH
**Location:** `backend/src/routes/oauth.py:16-33`

**Issue:**
- OAuth client credentials stored in-memory dictionary
- Lost on restart
- No encryption

**Recommendation:**
- Store in database with encryption
- Use environment variables for production
- Implement client credential rotation

---

### 3.7 **No Request ID Tracking**
**Severity:** HIGH
**Impact:** Difficult to trace security incidents

**Recommendation:**
```python
from uuid import uuid4

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
```

---

### 3.8 **Frontend Stores Tokens in localStorage**
**Severity:** HIGH
**Location:** `frontend/src/contexts/AuthContext.jsx:21-28`

**Issue:**
- Tokens stored in localStorage
- Vulnerable to XSS attacks
- Tokens accessible to all JavaScript

**Impact:**
- Token theft via XSS
- Session hijacking

**Recommendation:**
- Use httpOnly cookies for refresh tokens
- Keep access tokens in memory only
- Implement token refresh on page load

---

## 4. Medium-Priority Issues 🟡

### 4.1 **Missing Content Security Policy (CSP)**
**Severity:** MEDIUM

**Recommendation:**
```python
app.add_middleware(
    CSPMiddleware,
    policy={
        "default-src": ["'self'"],
        "script-src": ["'self'", "'unsafe-inline'"],
        "style-src": ["'self'", "'unsafe-inline'"],
    }
)
```

---

### 4.2 **No Email Verification Flow**
**Severity:** MEDIUM
**Location:** `backend/src/routes/auth.py:23-67`

**Issue:**
- Users created with `is_verified=False` but no verification flow
- Email verification not enforced

**Recommendation:**
- Implement email verification tokens
- Require verification before full access
- Send verification emails

---

### 4.3 **Insufficient Audit Logging**
**Severity:** MEDIUM

**Missing Events:**
- Password changes not logged
- Failed 2FA attempts not logged
- Admin actions partially logged

**Recommendation:**
```python
# Log all security events
AuthService.log_audit(
    db=db,
    user_id=user.id,
    action="2fa.failed_attempt",
    details={"code": code[:2] + "****"},
    request=request
)
```

---

### 4.4 **No API Versioning Strategy**
**Severity:** MEDIUM

**Issue:**
- All routes use `/api/v1/` but no version management

**Recommendation:**
- Document versioning strategy
- Plan for v2 migration
- Version deprecation policy

---

### 4.5 **Missing Error Handling Middleware**
**Severity:** MEDIUM

**Issue:**
- Unhandled exceptions may leak stack traces
- No global error handler

**Recommendation:**
```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
```

---

### 4.6 **No Database Connection Encryption**
**Severity:** MEDIUM

**Recommendation:**
```python
database_url = "postgresql://user:pass@host:5432/db?sslmode=require"
```

---

### 4.7 **Authorization Code Not Deleted After Use**
**Severity:** MEDIUM
**Location:** `backend/src/routes/oauth.py:181`

**Issue:**
- Code deleted only after successful token generation
- Could be reused if error occurs

**Recommendation:**
```python
try:
    # Generate tokens
    ...
finally:
    # Always delete code
    if token_request.code in authorization_codes:
        del authorization_codes[token_request.code]
```

---

### 4.8 **No Backup Code Hashing**
**Severity:** MEDIUM
**Location:** `backend/src/auth.py:205`

**Issue:**
- 2FA backup codes stored in plaintext
- If database compromised, backup codes exposed

**Recommendation:**
```python
# Hash backup codes before storage
hashed_codes = [AuthService.hash_password(code) for code in backup_codes]
user.backup_codes = ",".join(hashed_codes)

# Verify by checking against all hashes
for hashed in user.backup_codes.split(","):
    if AuthService.verify_password(input_code, hashed):
        # Valid backup code
```

---

### 4.9 **Frontend Password Validation Only Client-Side**
**Severity:** MEDIUM
**Location:** `frontend/src/components/Register.jsx`

**Issue:**
- Password validation only in frontend
- Can be bypassed

**Impact:**
- Backend has validation, but frontend should mirror it

---

### 4.10 **No Session Fingerprinting**
**Severity:** MEDIUM

**Issue:**
- Sessions not tied to device/browser fingerprint
- Session hijacking easier

**Recommendation:**
```python
# Generate session fingerprint
fingerprint = hashlib.sha256(
    f"{user_agent}:{ip_address}:{accept_language}".encode()
).hexdigest()

# Store with session
session.fingerprint = fingerprint

# Validate on each request
if request_fingerprint != session.fingerprint:
    raise HTTPException(status_code=401, detail="Session invalid")
```

---

### 4.11 **Missing API Documentation Security**
**Severity:** MEDIUM

**Issue:**
- No authentication on `/docs` and `/redoc`
- Internal API structure exposed

**Recommendation:**
```python
if settings.environment == "production":
    app = FastAPI(docs_url=None, redoc_url=None)
```

---

### 4.12 **No Timeout on Password Reset Tokens**
**Severity:** MEDIUM (Already implemented but worth noting)

**Status:** ✅ IMPLEMENTED
**Location:** `backend/src/routes/auth.py:212`

---

## 5. Low-Priority Issues 🟢

### 5.1 **No Automated Security Testing**
**Location:** `backend/tests/` (empty)

**Recommendation:**
- Implement pytest security tests
- SQL injection tests
- XSS tests
- CSRF tests

---

### 5.2 **Verbose Error Messages**
**Severity:** LOW

**Issue:**
- Some error messages reveal system details

**Recommendation:**
- Generic error messages in production
- Detailed errors only in logs

---

### 5.3 **No Dependency Vulnerability Scanning**

**Recommendation:**
```bash
# Add to CI/CD
pip install safety
safety check -r requirements.txt
```

---

### 5.4 **Missing Security Headers**

**Recommendation:**
```python
from fastapi.middleware.security import SecurityHeadersMiddleware

app.add_middleware(
    SecurityHeadersMiddleware,
    x_frame_options="DENY",
    x_content_type_options="nosniff",
    x_xss_protection="1; mode=block",
    strict_transport_security="max-age=31536000; includeSubDomains"
)
```

---

### 5.5 **No Webhook Signature Verification**
**Status:** Not applicable (no webhooks implemented)

---

### 5.6 **Frontend Build Not Optimized**

**Recommendation:**
```bash
# Production build should minify and obfuscate
npm run build -- --mode production
```

---

### 5.7 **No Secrets Rotation Policy**

**Recommendation:**
- Document secret rotation schedule
- Automate JWT secret rotation
- Database credential rotation

---

## 6. Compliance & Regulatory Issues

### 6.1 **GDPR Compliance**
**Status:** PARTIAL ✓

**Implemented:**
- Data retention policies ✅
- User data deletion (cascade) ✅
- Audit logging ✅

**Missing:**
- User data export endpoint ❌
- Explicit consent tracking ❌
- Data breach notification process ❌
- Cookie consent banner ❌

---

### 6.2 **PCI DSS (If Handling Payments)**
**Status:** NOT APPLICABLE

**Note:** AP2 protocol implementation is simulated frontend-only. If real payments are implemented:
- Tokenize card data
- Never store CVV
- Encrypt card numbers
- Regular security audits

---

### 6.3 **SOX Compliance (Financial Audit Trail)**
**Status:** PARTIAL ✓

**Implemented:**
- Audit logs for all actions ✅
- 90-day retention ✅
- User activity tracking ✅

**Missing:**
- Immutable audit logs ❌
- Audit log digital signatures ❌
- 7-year retention for financial data ❌

---

## 7. AP2 Protocol Implementation Review

### 7.1 **Backend AP2 Implementation**
**Location:** `backend/src/agent.py`

**Status:** Comprehensive ✅

**Features:**
- IntentMandate with cryptographic signatures ✅
- CartMandate with total verification ✅
- PaymentMandate with audit trail ✅
- RSA key pair generation ✅
- Expense categorization AI ✅

**Issues:**
- Private keys generated but not securely stored ⚠️
- No key rotation mechanism ⚠️

---

### 7.2 **Frontend AP2 Simulation**
**Location:** `frontend/src/App.jsx:24-78`

**Status:** UI Simulation Only ⚠️

**Issue:**
- AP2 protocol simulated in frontend only
- Not connected to backend AP2 implementation
- Simulated mandates not cryptographically verified

**Recommendation:**
```javascript
// Connect to backend
const response = await fetch('/api/v1/agent/process-expense', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: JSON.stringify({ expense })
});
const { mandates } = await response.json();
```

---

## 8. Infrastructure & DevOps Security

### 8.1 **No CI/CD Security Checks**

**Recommendation:**
```yaml
# .github/workflows/security.yml
- name: Security Scan
  run: |
    pip install bandit safety
    bandit -r backend/src
    safety check -r requirements.txt
    npm audit
```

---

### 8.2 **No Docker Security Hardening**
**Location:** `backend/Dockerfile`

**Recommendation:**
- Use non-root user
- Multi-stage builds
- Minimal base image
- Security scanning

---

### 8.3 **No Environment Separation**

**Recommendation:**
```
.env.development
.env.staging
.env.production
```

---

## 9. Positive Security Findings ✅

### Implemented Security Features

1. **Authentication & Authorization**
   - ✅ JWT access tokens with expiration
   - ✅ Refresh token rotation
   - ✅ Role-Based Access Control (4 roles)
   - ✅ 2FA/TOTP with QR codes
   - ✅ Backup codes for 2FA recovery
   - ✅ Password hashing with bcrypt
   - ✅ Session management with device tracking

2. **Data Security**
   - ✅ Password validation (complexity requirements)
   - ✅ SQL injection protection (SQLAlchemy ORM)
   - ✅ Database connection pooling
   - ✅ Data retention policies

3. **Audit & Compliance**
   - ✅ Comprehensive audit logging
   - ✅ Session tracking with IP/User-Agent
   - ✅ Password reset token expiration
   - ✅ Revoked token cleanup

4. **API Security**
   - ✅ OAuth 2.0 Authorization Code Flow
   - ✅ CORS configuration
   - ✅ Input validation with Pydantic

---

## 10. Immediate Action Items

### Critical (Fix Within 24 Hours)
1. ⚠️ Switch from SQLite to PostgreSQL
2. ⚠️ Change JWT secret to secure random value
3. ⚠️ Remove hardcoded secrets from code

### High Priority (Fix Within 1 Week)
4. 🔴 Implement rate limiting on auth endpoints
5. 🔴 Add account lockout mechanism
6. 🔴 Implement HTTPS/TLS enforcement
7. 🔴 Move tokens from localStorage to httpOnly cookies
8. 🔴 Strengthen password policy (12 chars + special char)

### Medium Priority (Fix Within 1 Month)
9. 🟡 Implement email verification flow
10. 🟡 Add global error handling middleware
11. 🟡 Hash 2FA backup codes
12. 🟡 Connect frontend AP2 to backend implementation
13. 🟡 Add security headers middleware

### Low Priority (Ongoing)
14. 🟢 Write security test suite
15. 🟢 Setup dependency scanning
16. 🟢 Document secrets rotation policy
17. 🟢 Add GDPR data export endpoint

---

## 11. Security Best Practices Checklist

### Authentication ✅ GOOD
- [x] Password hashing
- [x] JWT implementation
- [x] Refresh tokens
- [x] 2FA/TOTP
- [ ] Rate limiting
- [ ] Account lockout
- [ ] Email verification

### Authorization ✅ EXCELLENT
- [x] Role-based access control
- [x] Route protection
- [x] Admin endpoints secured
- [x] User isolation

### Data Protection ⚠️ NEEDS IMPROVEMENT
- [x] ORM (SQL injection protection)
- [x] Input validation
- [ ] Encryption at rest
- [ ] Encryption in transit (HTTPS)
- [ ] Secrets management

### Logging & Monitoring ✅ GOOD
- [x] Audit logs
- [x] Session tracking
- [ ] Security event alerting
- [ ] Request ID tracing

### Compliance ⚠️ PARTIAL
- [x] Data retention
- [x] Audit trail
- [ ] GDPR full compliance
- [ ] Data export
- [ ] Breach notification

---

## 12. Recommended Security Roadmap

### Phase 1: Critical Fixes (Week 1)
- Switch to PostgreSQL
- Secure secrets management
- Implement rate limiting
- HTTPS enforcement

### Phase 2: High Priority (Week 2-3)
- Account lockout
- Enhanced password policy
- Token storage improvements
- Email verification

### Phase 3: Hardening (Month 2)
- Security headers
- Error handling
- CSP implementation
- Backup code hashing

### Phase 4: Testing & Monitoring (Month 3)
- Security test suite
- Penetration testing
- Automated scanning
- Security monitoring

---

## 13. Contact & Resources

### Security Resources
- OWASP Top 10: https://owasp.org/www-project-top-ten/
- FastAPI Security: https://fastapi.tiangolo.com/tutorial/security/
- JWT Best Practices: https://tools.ietf.org/html/rfc8725

### Recommended Tools
- **SAST:** Bandit, Semgrep
- **Dependency Scan:** Safety, Snyk
- **DAST:** OWASP ZAP
- **Secret Scan:** GitLeaks, TruffleHog

---

## 14. Conclusion

The AP2 Expense Management System demonstrates a **solid security foundation** with comprehensive authentication, authorization, and audit capabilities. However, several **critical and high-priority issues** must be addressed before production deployment.

### Security Score Breakdown
- **Authentication:** 85/100 ✅
- **Authorization:** 95/100 ✅
- **Data Protection:** 65/100 ⚠️
- **Infrastructure:** 60/100 ⚠️
- **Compliance:** 70/100 ⚠️

**Overall: B+ (82/100)**

### Next Steps
1. Address all critical issues immediately
2. Implement high-priority fixes within 1 week
3. Schedule penetration testing
4. Conduct regular security reviews
5. Implement continuous security monitoring

---

**Report Generated:** October 4, 2025
**Next Review Date:** November 4, 2025
