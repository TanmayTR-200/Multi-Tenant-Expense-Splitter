@echo off
title Expense Splitter — one-command launcher

echo Starting Django API...
start "Django API (8000)" cmd /k "cd /d %~dp0backend && python manage.py runserver 127.0.0.1:8000"

echo Starting Settlement Service...
start "Settlement (8001)" cmd /k "cd /d %~dp0settlement_service && python -m uvicorn main:app --host 127.0.0.1 --port 8001"

echo Starting React Frontend...
start "React Frontend (5173)" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo All windows launched. Close each window to stop that service.