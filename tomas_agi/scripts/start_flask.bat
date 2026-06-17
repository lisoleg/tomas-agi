@echo off
REM Flask 服务器启动脚本 (Windows)
REM 使用方法: start_flask.bat

echo Starting TOMAS Flask Server...

cd /d "%~dp0\.."
cd tomas_agi\sim

REM 检查 Python 是否可用
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found in PATH
    pause
    exit /b 1
)

REM 检查 .env 文件是否存在
if not exist ".env" (
    echo Warning: .env file not found, using default config
)

REM 启动 Flask 服务器 (后台运行)
start /min "TOMAS Flask" python server.py

echo Flask server started!
echo Server running at http://localhost:5000
echo.
echo To stop the server, close the "TOMAS Flask" window or use Task Manager
pause
