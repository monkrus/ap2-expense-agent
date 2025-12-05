# PowerShell script to run GCP Marketplace tests
# Usage: .\run_tests.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "GCP Marketplace Integration - Test Runner" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Set environment variable for test mode
$env:GCP_JWT_TEST_MODE = "true"

Write-Host "Starting backend server in test mode..." -ForegroundColor Yellow
Write-Host ""

# Start backend server in background
$serverJob = Start-Job -ScriptBlock {
    param($path)
    Set-Location $path
    $env:GCP_JWT_TEST_MODE = "true"
    & .venv\Scripts\python.exe -m uvicorn src.api:app --host 127.0.0.1 --port 8000
} -ArgumentList $PSScriptRoot

Write-Host "Waiting for server to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Run tests
Write-Host "Running tests..." -ForegroundColor Yellow
Write-Host ""
.venv\Scripts\python.exe test_gcp_webhook_quick.py

# Cleanup
Write-Host ""
Write-Host "Stopping server..." -ForegroundColor Yellow
Stop-Job -Job $serverJob
Remove-Job -Job $serverJob

Write-Host ""
Write-Host "Done!" -ForegroundColor Green
