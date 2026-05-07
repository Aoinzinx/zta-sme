@echo off
title ZT-SME Framework Launcher
echo ============================================
echo  ZT-SME Zero Trust Framework - Local Start
echo ============================================
echo.
echo Starting Policy Engine  (port 8001) ...
start "Policy Engine" cmd /k "%~dp0run_policy_engine.bat"

echo Waiting 5 seconds...
timeout /t 5 /nobreak >nul

echo Starting Auth Service   (port 8002) ...
start "Auth Service" cmd /k "%~dp0run_auth_service.bat"

echo Waiting 4 seconds...
timeout /t 4 /nobreak >nul

echo Starting Gateway        (port 8445) ...
start "Gateway" cmd /k "%~dp0run_gateway.bat"

echo.
echo All three services launched in separate windows.
echo.
echo To start the Dashboard, open a new terminal and run:
echo   cd "%~dp0dashboard"
echo   npm run dev
echo.
echo Then open: http://localhost:3000
echo Login:     admin / Admin@1234
echo.
pause
