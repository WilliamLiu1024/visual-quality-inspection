$ProjectDir = 'D:\06Code\20260330visual-quality-inspection'
Set-Location $ProjectDir

if (-not (Test-Path '.\.venv\Scripts\python.exe')) {
    py -3 -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install fastapi uvicorn sqlalchemy pydantic python-multipart opencv-python pillow
$env:DETECTOR_NAME = 'yolo26'
Start-Job -ScriptBlock {
    Start-Sleep -Seconds 4
    Start-Process 'http://127.0.0.1:8000/'
} | Out-Null
& .\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
