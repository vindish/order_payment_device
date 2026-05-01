@echo off
chcp 65001 >nul

echo ==============================
echo  🚀 启动项目（统一入口）
echo ==============================

cd /d %~dp0backend

if not exist venv (
echo [INFO] 创建虚拟环境...
python -m venv venv
)

call venv\Scripts\activate

if not exist .deps_installed (
echo [INFO] 安装依赖...
pip install -r requirements.txt
echo done > .deps_installed
)

echo [INFO] 启动服务...
uvicorn app.main:app --reload

pause
