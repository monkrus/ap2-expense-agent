@echo off
echo ===================================
echo Stripe CLI Authentication
echo ===================================
echo.

REM Try to find stripe.exe in common locations
set STRIPE_EXE=

if exist "C:\Users\robot\stripe-cli\stripe.exe" (
    set STRIPE_EXE=C:\Users\robot\stripe-cli\stripe.exe
    echo Found Stripe CLI in: C:\Users\robot\stripe-cli\
)

if exist "%LOCALAPPDATA%\Temp\chocolatey\ChocolateyScratch\stripe-cli\1.33.0\tools\stripe.exe" (
    set STRIPE_EXE=%LOCALAPPDATA%\Temp\chocolatey\ChocolateyScratch\stripe-cli\1.33.0\tools\stripe.exe
    echo Found Stripe CLI in: Chocolatey temp directory
)

if exist "%USERPROFILE%\Desktop\ap2-expense-agent\stripe-cli\stripe.exe" (
    set STRIPE_EXE=%USERPROFILE%\Desktop\ap2-expense-agent\stripe-cli\stripe.exe
    echo Found Stripe CLI in: Desktop project directory
)

REM Try to find it using 'where' command
where stripe.exe >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=*" %%i in ('where stripe.exe') do set STRIPE_EXE=%%i
    echo Found Stripe CLI in PATH: %STRIPE_EXE%
)

if "%STRIPE_EXE%"=="" (
    echo.
    echo ERROR: Could not find stripe.exe
    echo.
    echo Please download Stripe CLI from:
    echo https://github.com/stripe/stripe-cli/releases/latest
    echo.
    echo Or install via Chocolatey:
    echo choco install stripe-cli
    echo.
    pause
    exit /b 1
)

echo.
echo Using: %STRIPE_EXE%
echo.
echo This will:
echo 1. Generate a pairing code
echo 2. Open your browser to Stripe
echo 3. Ask you to authorize the CLI
echo.
echo Press any key to start...
pause >nul

"%STRIPE_EXE%" login

echo.
echo If authentication succeeded, you can now use the Stripe CLI!
echo.
pause
