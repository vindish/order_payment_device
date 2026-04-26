@echo off
cd /d %~dp0backend
call venv\Scripts\activate

set ENV=dev

uvicorn app.main:app --reload
