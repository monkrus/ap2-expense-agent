@echo off
REM Stripe CLI Webhook Testing Script
REM This script starts the Stripe CLI to forward webhooks to your local backend

echo ===================================
echo Stripe CLI Webhook Listener
echo ===================================
echo.

REM Auto-detect Stripe CLI location
set STRIPE_EXE=
if exist "C:\Users\robot\stripe-cli\stripe.exe" set STRIPE_EXE=C:\Users\robot\stripe-cli\stripe.exe
if exist "%LOCALAPPDATA%\Temp\chocolatey\ChocolateyScratch\stripe-cli\1.33.0\tools\stripe.exe" set STRIPE_EXE=%LOCALAPPDATA%\Temp\chocolatey\ChocolateyScratch\stripe-cli\1.33.0\tools\stripe.exe
if exist "%USERPROFILE%\Desktop\ap2-expense-agent\stripe-cli\stripe.exe" set STRIPE_EXE=%USERPROFILE%\Desktop\ap2-expense-agent\stripe-cli\stripe.exe
where stripe.exe >nul 2>&1
if %ERRORLEVEL% EQU 0 for /f "tokens=*" %%i in ('where stripe.exe') do set STRIPE_EXE=%%i

if "%STRIPE_EXE%"=="" (
    echo ERROR: Could not find stripe.exe
    echo Please run stripe-login.bat first or install Stripe CLI
    pause
    exit /b 1
)

echo Using: %STRIPE_EXE%
echo.
echo This will:
echo 1. Listen for Stripe webhook events
echo 2. Forward them to http://localhost:8000/api/payment/webhooks/stripe
echo 3. Print the webhook signing secret (needed for .env)
echo.
echo IMPORTANT: Copy the webhook signing secret that appears!
echo Add it to backend/.env as: STRIPE_WEBHOOK_SECRET=whsec_...
echo.
pause

"%STRIPE_EXE%" listen --forward-to localhost:8000/api/payment/webhooks/stripe --print-secret

pause
