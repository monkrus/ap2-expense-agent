@echo off
echo ============================================
echo Stripe Webhook Setup for Local Testing
echo ============================================
echo.

echo Step 1: Logging into Stripe...
echo This will open your browser. Please click "Allow access"
echo.
C:\Users\robot\stripe-cli\stripe.exe login
echo.

echo Step 2: Starting webhook listener...
echo This will forward Stripe webhooks to your local backend
echo Keep this window open while testing!
echo.
echo Press Ctrl+C to stop the listener when done testing.
echo.
C:\Users\robot\stripe-cli\stripe.exe listen --forward-to localhost:8000/api/payment/webhooks/stripe

pause
