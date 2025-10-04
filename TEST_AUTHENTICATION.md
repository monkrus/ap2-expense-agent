# Testing the Authentication System

## Prerequisites Check

Before testing, ensure you have:
- [ ] Python 3.10+ installed
- [ ] Node.js 18+ installed
- [ ] PostgreSQL running
- [ ] Git repository cloned

## Step-by-Step Testing Guide

### Step 1: Database Setup

```bash
# Option A: Using psql (if PostgreSQL is installed)
psql -U postgres
CREATE DATABASE expenses;
CREATE USER ap2user WITH PASSWORD 'changeme';
GRANT ALL PRIVILEGES ON DATABASE expenses TO ap2user;
\q

# Option B: Using createdb command
createdb expenses

# Verify database exists
psql -U postgres -l | grep expenses
```

### Step 2: Backend Setup & Start

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Initialize authentication (creates admin user)
python setup_auth.py

# Start the backend server
uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

Keep this terminal running and open a new terminal for frontend.

### Step 3: Frontend Setup & Start

```bash
# Open a NEW terminal
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

**Expected output:**
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

### Step 4: Test the UI

1. **Open your browser**: Navigate to `http://localhost:5173`

2. **You should see the Login page** with:
   - Username field
   - Password field
   - "Sign In" button
   - "Sign up" link

3. **Test Login with default admin**:
   - Username: `admin`
   - Password: `Admin123!`
   - Click "Sign In"

4. **If successful, you should see**:
   - Top navigation bar with user info
   - "Admin" role badge
   - Logout button
   - Expense management interface

5. **Test Logout**:
   - Click the "Logout" button in top right
   - You should be redirected to login page

6. **Test Registration**:
   - Click "Sign up" link on login page
   - Fill in the form:
     - Email: `test@example.com`
     - Username: `testuser`
     - Full Name: `Test User`
     - Password: `SecurePass123!`
     - Confirm Password: `SecurePass123!`
   - Watch password requirements turn green as you type
   - Click "Create Account"
   - Should show success message and redirect to login

7. **Test Login with New User**:
   - Username: `testuser`
   - Password: `SecurePass123!`
   - Should login successfully with "Employee" role

### Step 5: Test API Endpoints (Using Swagger UI)

1. **Open Swagger UI**: Navigate to `http://localhost:8000/docs`

2. **Test Registration** (POST /api/v1/auth/register):
   - Click on the endpoint to expand
   - Click "Try it out"
   - Use this JSON:
   ```json
   {
     "email": "john@example.com",
     "username": "john",
     "password": "MyPassword123!",
     "full_name": "John Doe",
     "role": "employee"
   }
   ```
   - Click "Execute"
   - Should return 201 with user details

3. **Test Login** (POST /api/v1/auth/login):
   - Expand the endpoint
   - Click "Try it out"
   - Use this JSON:
   ```json
   {
     "username": "admin",
     "password": "Admin123!"
   }
   ```
   - Click "Execute"
   - Should return access_token and refresh_token
   - **Copy the access_token** (you'll need it)

4. **Authorize Swagger UI**:
   - Click the green "Authorize" button at top
   - Paste your access_token in the "Value" field
   - Click "Authorize"
   - Click "Close"

5. **Test Protected Endpoint** (GET /api/v1/auth/me):
   - Expand the endpoint
   - Click "Try it out"
   - Click "Execute"
   - Should return your user information

6. **Test User Listing** (GET /api/v1/users/):
   - Should return list of users (requires manager/admin role)

7. **Test 2FA Setup** (POST /api/v1/auth/2fa/setup):
   - Should return QR code URL and backup codes
   - You can scan QR code with Google Authenticator app

### Step 6: Test with cURL (Command Line)

```bash
# Test Registration
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@example.com",
    "username": "alice",
    "password": "AlicePass123!",
    "full_name": "Alice Smith"
  }'

# Test Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "Admin123!"
  }' | python -m json.tool

# Save the access_token from response, then test protected endpoint
TOKEN="your_access_token_here"

curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# Test User Management (requires admin)
curl -X GET http://localhost:8000/api/v1/users/ \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

### Step 7: Test 2FA (Two-Factor Authentication)

1. **Setup 2FA**:
   - Login to UI as admin
   - Open browser console (F12)
   - Run:
   ```javascript
   const token = localStorage.getItem('access_token');
   fetch('http://localhost:8000/api/v1/auth/2fa/setup', {
     headers: { 'Authorization': `Bearer ${token}` }
   }).then(r => r.json()).then(console.log);
   ```
   - Copy the `qr_code_url` and paste in browser address bar
   - Scan QR code with Google Authenticator app
   - Save the backup codes

2. **Enable 2FA**:
   - Get TOTP code from Google Authenticator
   - Run:
   ```javascript
   const token = localStorage.getItem('access_token');
   fetch('http://localhost:8000/api/v1/auth/2fa/enable', {
     method: 'POST',
     headers: {
       'Authorization': `Bearer ${token}`,
       'Content-Type': 'application/json'
     },
     body: JSON.stringify({ totp_code: '123456' }) // Use actual code
   }).then(r => r.json()).then(console.log);
   ```

3. **Test Login with 2FA**:
   - Logout
   - Try to login with username/password
   - Should show 2FA code input
   - Enter code from Google Authenticator
   - Should login successfully

### Step 8: Test Password Reset

```bash
# Request password reset
curl -X POST http://localhost:8000/api/v1/auth/password/reset-request \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@ap2expense.com"
  }' | python -m json.tool

# In development, the response includes the reset_token
# Use it to reset password:
curl -X POST http://localhost:8000/api/v1/auth/password/reset-confirm \
  -H "Content-Type: application/json" \
  -d '{
    "token": "RESET_TOKEN_FROM_ABOVE",
    "new_password": "NewPassword123!"
  }' | python -m json.tool
```

### Step 9: Test Session Management

```bash
# Get current user sessions
curl -X GET "http://localhost:8000/api/v1/users/USER_ID/sessions" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# Revoke a session
curl -X DELETE "http://localhost:8000/api/v1/users/USER_ID/sessions/SESSION_ID" \
  -H "Authorization: Bearer $TOKEN"
```

### Step 10: Test Role-Based Access Control

1. **Login as employee (testuser)**:
   - Try to access GET /api/v1/users/
   - Should return 403 Forbidden (employees can't list users)

2. **Login as admin**:
   - Try to access GET /api/v1/users/
   - Should return 200 with user list (admins can list users)

3. **Create a manager user via admin**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/users/ \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "manager@example.com",
       "username": "manager",
       "password": "ManagerPass123!",
       "full_name": "Manager User",
       "role": "manager"
     }'
   ```

4. **Login as manager and test permissions**

## ✅ Success Criteria

After completing all tests, you should have verified:

- ✅ User registration works
- ✅ User login works
- ✅ JWT tokens are generated
- ✅ Protected routes require authentication
- ✅ Role-based access control works
- ✅ User management (CRUD) works
- ✅ Password reset flow works
- ✅ 2FA setup and login works
- ✅ Session management works
- ✅ Logout and token revocation works
- ✅ Frontend UI displays correctly
- ✅ Auto token refresh works

## 🐛 Common Issues & Solutions

### Issue: "Connection refused" to PostgreSQL

**Solution:**
```bash
# Check if PostgreSQL is running
sudo service postgresql status
# or
pg_ctl status

# Start PostgreSQL
sudo service postgresql start
```

### Issue: "ModuleNotFoundError"

**Solution:**
```bash
# Make sure virtual environment is activated
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: Frontend not connecting to backend

**Solution:**
- Check backend is running on http://localhost:8000
- Check CORS_ORIGINS in backend/.env includes http://localhost:5173
- Check browser console for errors

### Issue: "Alembic command not found"

**Solution:**
```bash
# Install alembic explicitly
pip install alembic

# Or use python -m
python -m alembic upgrade head
```

### Issue: 401 Unauthorized on protected endpoints

**Solution:**
- Make sure you copied the full access_token
- Check token hasn't expired (default 60 minutes)
- Use format: `Bearer YOUR_TOKEN_HERE`

## 📊 Testing Checklist

Print this checklist and check off as you test:

```
Frontend UI Tests:
□ Login page displays
□ Register page displays
□ Password validation shows
□ Login with admin works
□ User profile shows in nav
□ Logout works
□ Register new user works
□ Login with new user works

API Tests (Swagger):
□ /auth/register works
□ /auth/login returns tokens
□ /auth/me returns user info
□ /users/ returns user list (admin)
□ /auth/2fa/setup works
□ Protected endpoints require auth
□ Invalid token returns 401

Advanced Tests:
□ 2FA setup and enable
□ 2FA login works
□ Password reset request
□ Password reset confirm
□ Session listing
□ Session revocation
□ RBAC blocks unauthorized access
□ Token refresh works
□ Audit logs created
```

## 🎯 Next Steps After Testing

Once everything works:
1. Change admin password
2. Configure SMTP for email
3. Set secure JWT_SECRET
4. Review security settings
5. Set up production database
6. Enable HTTPS
7. Configure rate limiting

---

**Need Help?** Check the logs:
- Backend logs: Terminal running uvicorn
- Frontend logs: Browser console (F12)
- Database logs: PostgreSQL logs
