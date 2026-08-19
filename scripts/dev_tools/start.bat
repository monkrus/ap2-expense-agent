@echo off
echo ========================================
echo AP2 Expense Management - Clean Start
echo ========================================
echo.

echo Killing processes on ports 5173 and 8000...
echo.

:: Kill process on port 5173 (frontend)
for /f "tokens=5" %%P in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING') do (
    echo Killing process on port 5173 (PID: %%P)
    taskkill /F /PID %%P >nul 2>&1
)

:: Kill process on port 8000 (backend)
for /f "tokens=5" %%P in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo Killing process on port 8000 (PID: %%P)
    taskkill /F /PID %%P >nul 2>&1
)

echo Ports cleared!
echo.

:: Wait a moment for ports to be released
timeout /t 2 /nobreak >nul

echo ========================================
echo Starting Backend Server
echo ========================================
echo.

:: Start backend in new window
start "AP2 Backend Server" cmd /k "cd /d "%~dp0\backend" && (if exist venv\Scripts\activate.bat (venv\Scripts\activate.bat) else (python -m venv venv && venv\Scripts\activate.bat && pip install -r requirements.txt)) && uvicorn src.api:app --reload --host 0.0.0.0 --port 8000"

echo Backend starting on http://localhost:8000
echo.

:: Wait for backend to initialize
echo Waiting 5 seconds for backend to initialize...
timeout /t 5 /nobreak >nul

echo ========================================
echo Starting Frontend Server
echo ========================================
echo.

:: Start frontend in new window
start "AP2 Frontend Server" cmd /k "cd /d "%~dp0\frontend" && npm run dev"

echo Frontend starting on http://localhost:5173
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
echo   2. Login with your credentials
echo.
echo Press any key to exit this window...
pause >nul
