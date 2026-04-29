@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo 正在创建虚拟环境...
    py -3 -m venv .venv 2>nul
    if errorlevel 1 (
        python3 -m venv .venv 2>nul
        if errorlevel 1 (
            python -m venv .venv 2>nul
            if errorlevel 1 (
                echo 错误：未找到 Python，请先安装 Python 3。
                pause
                exit /b 1
            )
        )
    )
)

.venv\Scripts\python.exe -c "import uvicorn" 2>nul
if errorlevel 1 (
    echo 正在安装依赖（需要网络）...
    .venv\Scripts\python.exe -m pip install -r backend\requirements.txt
    if errorlevel 1 (
        echo 错误：依赖安装失败，请检查网络或手动安装。
        pause
        exit /b 1
    )
)

set DETECTOR_NAME=yolo26
start "" powershell -WindowStyle Hidden -Command "Start-Sleep -Seconds 5; Start-Process 'http://127.0.0.1:8000/'"
echo 后端启动中，稍后浏览器将自动打开...
.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
