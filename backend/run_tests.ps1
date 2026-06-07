# PowerShell script to run AP2 Expense Agent tests
# Usage: .\run_tests.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "AP2 Expense Agent - Test Runner" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Set environment variable for test mode
$env:TESTING = "true"

Write-Host "Running tests..." -ForegroundColor Yellow
Write-Host ""

# Run pytest with common ignores
.venv\Scripts\python.exe -m pytest tests/ `
    --ignore=tests/test_rate_limit_alerting.py `
    -v

Write-Host ""
Write-Host "Done!" -ForegroundColor Green
