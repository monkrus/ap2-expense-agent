@echo off
REM Trigger test Stripe events using Stripe CLI
REM Run this AFTER starting the webhook listener

echo ===================================
echo Trigger Test Stripe Events
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

:menu
echo Choose a test event to trigger:
echo.
echo 1. Checkout Session Completed (subscription activated)
echo 2. Subscription Created
echo 3. Subscription Updated
echo 4. Subscription Deleted
echo 5. Invoice Paid
echo 6. Invoice Payment Failed
echo 7. Run ALL test events
echo 8. Exit
echo.
set /p choice="Enter your choice (1-8): "

if "%choice%"=="1" goto checkout_completed
if "%choice%"=="2" goto subscription_created
if "%choice%"=="3" goto subscription_updated
if "%choice%"=="4" goto subscription_deleted
if "%choice%"=="5" goto invoice_paid
if "%choice%"=="6" goto invoice_failed
if "%choice%"=="7" goto all_events
if "%choice%"=="8" goto end
echo Invalid choice. Please try again.
echo.
goto menu

:checkout_completed
echo.
echo Triggering: checkout.session.completed
"%STRIPE_EXE%" trigger checkout.session.completed
echo.
goto menu

:subscription_created
echo.
echo Triggering: customer.subscription.created
"%STRIPE_EXE%" trigger customer.subscription.created
echo.
goto menu

:subscription_updated
echo.
echo Triggering: customer.subscription.updated
"%STRIPE_EXE%" trigger customer.subscription.updated
echo.
goto menu

:subscription_deleted
echo.
echo Triggering: customer.subscription.deleted
"%STRIPE_EXE%" trigger customer.subscription.deleted
echo.
goto menu

:invoice_paid
echo.
echo Triggering: invoice.paid
"%STRIPE_EXE%" trigger invoice.paid
echo.
goto menu

:invoice_failed
echo.
echo Triggering: invoice.payment_failed
"%STRIPE_EXE%" trigger invoice.payment_failed
echo.
goto menu

:all_events
echo.
echo Running ALL test events...
echo.
echo [1/6] checkout.session.completed
"%STRIPE_EXE%" trigger checkout.session.completed
timeout /t 2 /nobreak >nul

echo.
echo [2/6] customer.subscription.created
"%STRIPE_EXE%" trigger customer.subscription.created
timeout /t 2 /nobreak >nul

echo.
echo [3/6] customer.subscription.updated
"%STRIPE_EXE%" trigger customer.subscription.updated
timeout /t 2 /nobreak >nul

echo.
echo [4/6] customer.subscription.deleted
"%STRIPE_EXE%" trigger customer.subscription.deleted
timeout /t 2 /nobreak >nul

echo.
echo [5/6] invoice.paid
"%STRIPE_EXE%" trigger invoice.paid
timeout /t 2 /nobreak >nul

echo.
echo [6/6] invoice.payment_failed
"%STRIPE_EXE%" trigger invoice.payment_failed
echo.
echo All events triggered!
echo.
goto menu

:end
echo.
echo Exiting...
