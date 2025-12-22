@echo off
echo ========================================
echo Deploy AP2 Expense App to Google Cloud Run
echo Domain: itestapp.com
echo ========================================
echo.

REM Check if gcloud is installed
where gcloud >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: gcloud CLI is not installed or not in PATH
    echo Please install from: https://cloud.google.com/sdk/docs/install-sdk#windows
    pause
    exit /b 1
)

echo Step 1: Checking GCP configuration...
echo.

REM Get current project
for /f "tokens=2 delims==" %%a in ('gcloud config get-value project 2^>nul') do set PROJECT_ID=%%a
if "%PROJECT_ID%"=="" (
    echo ERROR: No GCP project configured
    echo Please run: gcloud init
    pause
    exit /b 1
)

echo Current GCP Project: %PROJECT_ID%
echo.

REM Ask for confirmation
set /p CONFIRM="Continue with deployment to project '%PROJECT_ID%'? (Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo Deployment cancelled.
    pause
    exit /b 0
)

echo.
echo Step 2: Enabling required APIs...
echo.

gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable sqladmin.googleapis.com

echo.
echo Step 3: Building and deploying BACKEND...
echo.

REM Build and deploy backend
gcloud builds submit --tag gcr.io/%PROJECT_ID%/ap2-expense-backend -f Dockerfile.backend .

if %errorlevel% neq 0 (
    echo ERROR: Backend build failed
    pause
    exit /b 1
)

echo.
echo Deploying backend to Cloud Run...
echo.

gcloud run deploy ap2-expense-backend ^
    --image gcr.io/%PROJECT_ID%/ap2-expense-backend ^
    --region us-central1 ^
    --platform managed ^
    --allow-unauthenticated ^
    --min-instances 1 ^
    --max-instances 10 ^
    --memory 2Gi ^
    --cpu 2 ^
    --port 8080 ^
    --set-env-vars ENVIRONMENT=production

if %errorlevel% neq 0 (
    echo ERROR: Backend deployment failed
    pause
    exit /b 1
)

REM Get backend URL
for /f "tokens=*" %%a in ('gcloud run services describe ap2-expense-backend --region us-central1 --format="value(status.url)"') do set BACKEND_URL=%%a

echo.
echo Backend deployed successfully!
echo Backend URL: %BACKEND_URL%
echo.

echo Step 4: Building and deploying FRONTEND...
echo.

REM Create temporary .env for frontend build with backend URL
echo VITE_API_URL=%BACKEND_URL%/api/v1 > frontend\.env.production

REM Build and deploy frontend
gcloud builds submit --tag gcr.io/%PROJECT_ID%/ap2-expense-frontend -f Dockerfile.frontend .

if %errorlevel% neq 0 (
    echo ERROR: Frontend build failed
    pause
    exit /b 1
)

echo.
echo Deploying frontend to Cloud Run...
echo.

gcloud run deploy ap2-expense-frontend ^
    --image gcr.io/%PROJECT_ID%/ap2-expense-frontend ^
    --region us-central1 ^
    --platform managed ^
    --allow-unauthenticated ^
    --min-instances 1 ^
    --max-instances 5 ^
    --memory 512Mi ^
    --cpu 1 ^
    --port 80

if %errorlevel% neq 0 (
    echo ERROR: Frontend deployment failed
    pause
    exit /b 1
)

REM Get frontend URL
for /f "tokens=*" %%a in ('gcloud run services describe ap2-expense-frontend --region us-central1 --format="value(status.url)"') do set FRONTEND_URL=%%a

echo.
echo Frontend deployed successfully!
echo Frontend URL: %FRONTEND_URL%
echo.

echo ========================================
echo Deployment Complete!
echo ========================================
echo.
echo Your services are now running:
echo Backend:  %BACKEND_URL%
echo Frontend: %FRONTEND_URL%
echo.
echo ========================================
echo Step 5: Set up custom domain
echo ========================================
echo.
echo To use your custom domain (itestapp.com), follow these steps:
echo.
echo 1. Map custom domains to Cloud Run services:
echo.
echo    For BACKEND (api.itestapp.com):
echo    gcloud run domain-mappings create --service ap2-expense-backend --domain api.itestapp.com --region us-central1
echo.
echo    For FRONTEND (itestapp.com):
echo    gcloud run domain-mappings create --service ap2-expense-frontend --domain itestapp.com --region us-central1
echo.
echo 2. Cloud Run will provide DNS records. Configure them in Squarespace:
echo.
echo    Login to: https://account.squarespace.com/domains/managed/itestapp.com/dns/dns-settings
echo.
echo    Add the DNS records that Cloud Run provides (usually CNAME records)
echo.
echo 3. Wait for DNS propagation (can take up to 48 hours, usually faster)
echo.
echo 4. SSL certificates will be provisioned automatically by Google
echo.
echo ========================================
echo.
pause
