@echo off
REM Quick Setup Script for GCP Marketplace Integration
REM Run this to install dependencies and verify setup

echo ========================================
echo GCP Marketplace Integration - Quick Setup
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

echo Step 2: Installing new dependencies...
pip install PyJWT[crypto]==2.8.0 --quiet
pip install cryptography==41.0.7 --quiet
pip install requests==2.31.0 --quiet
pip install tenacity==8.2.3 --quiet
echo ✓ Dependencies installed
echo.

echo Step 3: Updating requirements.txt...
pip freeze > requirements.txt
echo ✓ Requirements updated
echo.

echo Step 4: Verifying installation...
python -c "import jwt; print('✓ PyJWT installed')" 2>nul
if errorlevel 1 (
    echo ERROR: PyJWT not installed correctly
    exit /b 1
)

python -c "from cryptography.hazmat.primitives import serialization; print('✓ Cryptography installed')" 2>nul
if errorlevel 1 (
    echo ERROR: Cryptography not installed correctly
    exit /b 1
)

python -c "import requests; print('✓ Requests installed')" 2>nul
if errorlevel 1 (
    echo ERROR: Requests not installed correctly
    exit /b 1
)
echo.

echo Step 5: Checking new files...
if exist "src\gcp\jwt_verification.py" (
    echo ✓ JWT verification module created
) else (
    echo ✗ Missing: src\gcp\jwt_verification.py
)

if exist "test_gcp_webhook_quick.py" (
    echo ✓ Test script created
) else (
    echo ✗ Missing: test_gcp_webhook_quick.py
)
echo.

echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Start the backend server:
echo    uvicorn src.api:app --reload
echo.
echo 2. In another terminal, run the test:
echo    python test_gcp_webhook_quick.py
echo.
echo 3. Check the results!
echo.
pause
