@echo off
echo ========================================
echo AP2 Expense Management - Quick Start
echo ========================================
echo.

echo Checking prerequisites...

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)
echo [OK] Python found

:: Check Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found. Please install Node.js 18+
    pause
    exit /b 1
)
echo [OK] Node.js found

:: Check PostgreSQL
psql --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] PostgreSQL command not found
    echo Please make sure PostgreSQL is installed and running
    echo.
)

echo.
echo ========================================
echo Step 1: Database Setup
echo ========================================
echo.
echo Running database setup...
echo If prompted for password, use your PostgreSQL password
echo.

psql -U postgres -c "CREATE DATABASE expenses;" 2>nul
psql -U postgres -c "CREATE USER ap2user WITH PASSWORD 'changeme';" 2>nul
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE expenses TO ap2user;" 2>nul

echo Database setup attempted (ignore errors if database already exists)
echo.

echo ========================================
echo Step 2: Backend Setup
echo ========================================
echo.

cd backend

:: Create virtual environment if it doesn't exist
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

:: Install dependencies
echo Installing Python dependencies...
pip install -q -r requirements.txt

:: Create .env file if it doesn't exist
if not exist ".env" (
    echo Creating .env file...
    (
        echo DATABASE_URL=postgresql://ap2user:changeme@localhost:5432/expenses
        echo JWT_SECRET=development-secret-change-in-production-please
        echo ENVIRONMENT=development
        echo DEBUG=true
        echo CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost
    ) > .env
)

:: Run migrations
echo Running database migrations...
alembic upgrade head

:: Setup authentication
echo Setting up authentication system...
python setup_auth.py

echo.
echo ========================================
echo Backend setup complete!
echo ========================================
echo.
echo Default admin credentials:
echo   Username: admin
echo   Password: Admin123!
echo.
echo [IMPORTANT] Change this password after first login!
echo.

cd ..

echo ========================================
echo Step 3: Starting Servers
echo ========================================
echo.
echo Opening two terminals:
echo   1. Backend server (http://localhost:8000)
echo   2. Frontend server (http://localhost:5173)
echo.

:: Start backend in new window
start "AP2 Backend Server" cmd /k "cd backend && venv\Scripts\activate.bat && uvicorn src.api:app --reload --host 0.0.0.0 --port 8000"

:: Wait a bit for backend to start
timeout /t 3 /nobreak >nul

:: Start frontend in new window
start "AP2 Frontend Server" cmd /k "cd frontend && npm install && npm run dev"

echo.
echo ========================================
echo Servers are starting!
echo ========================================
echo.
echo Backend:  http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo Frontend: http://localhost:5173
echo.
echo Wait 10-15 seconds for servers to fully start, then:
echo   1. Open http://localhost:5173 in your browser
echo   2. Login with admin / Admin123!
echo.
echo Press any key to run API tests (optional)...
pause >nul

:: Run API tests
echo.
echo Running API tests...
python test_api.py

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo   1. Open browser: http://localhost:5173
echo   2. Login with: admin / Admin123!
echo   3. Change admin password
echo   4. See TEST_AUTHENTICATION.md for detailed testing
echo.
pause
