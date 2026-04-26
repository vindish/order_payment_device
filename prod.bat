@echo off
cd /d %~dp0backend
call venv\Scripts\activate

set ENV=prod

uvicorn app.main:app --host 0.0.0.0 --port 8000
