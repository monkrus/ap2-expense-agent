@echo off
echo Starting AP2 Backend Server...
cd /d C:\Users\robot\Desktop\ap2-expense-agent\backend
call .venv\Scripts\activate.bat
python -m uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
pause
