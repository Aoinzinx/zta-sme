@echo off
title Auth Service - Port 8002
SET DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ztdb
SET JWT_SECRET=your-local-dev-secret-key-change-in-production
SET ACCESS_TOKEN_EXPIRE_MINUTES=15
SET REFRESH_TOKEN_EXPIRE_HOURS=8
SET POLICY_ENGINE_URL=http://127.0.0.1:8001
SET UPSTREAM_AWS_URL=http://127.0.0.1:9001
SET UPSTREAM_AZURE_URL=http://127.0.0.1:9002
SET ENVIRONMENT=development
SET PYTHONPATH=%~dp0auth-service;%~dp0
cd /d "%~dp0auth-service"
python -m uvicorn main:app --host 127.0.0.1 --port 8002
pause
