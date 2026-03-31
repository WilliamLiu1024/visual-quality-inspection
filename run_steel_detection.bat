@echo off
setlocal
set PROJECT_DIR=D:\06Code\20260330visual-quality-inspection
cd /d "%PROJECT_DIR%"

if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
)

call .venv\Scripts\python.exe -m pip install fastapi uvicorn sqlalchemy pydantic python-multipart opencv-python pillow
set DETECTOR_NAME=yolo26
start "Steel Detection Browser" powershell -WindowStyle Hidden -Command "Start-Sleep -Seconds 4; Start-Process 'http://127.0.0.1:8000/'"
call .venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
