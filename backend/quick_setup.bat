@echo off
REM Quick Setup Script for AP2 Expense Agent
REM Run this to install dependencies and verify setup

echo ========================================
echo AP2 Expense Agent - Quick Setup
echo ========================================
echo.

REM Check if in backend directory
if not exist "src\api.py" (
    echo ERROR: Please run this from the backend directory
    echo cd backend
    echo quick_setup.bat
    exit /b 1
)

echo Step 1: Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Could not activate virtual environment
    echo Please create one first: python -m venv .venv
    exit /b 1
)
echo ✓ Virtual environment activated
echo.

echo Step 2: Installing dependencies...
pip install -r requirements.txt --quiet
echo ✓ Dependencies installed
echo.

echo Step 3: Verifying installation...
python -c "import fastapi; print('✓ FastAPI installed')" 2>nul
python -c "import stripe; print('✓ Stripe installed')" 2>nul
python -c "import httpx; print('✓ httpx installed')" 2>nul
python -c "from cryptography.fernet import Fernet; print('✓ Cryptography installed')" 2>nul
echo.

echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Copy .env.example to .env and configure
echo 2. Start the backend server:
echo    uvicorn src.api:app --reload
echo 3. Run tests:
echo    pytest
echo.
pause
