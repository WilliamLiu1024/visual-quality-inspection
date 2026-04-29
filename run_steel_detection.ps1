$ProjectDir = $PSScriptRoot
Set-Location $ProjectDir

if (-not (Test-Path '.\.venv\Scripts\python.exe')) {
    Write-Host '正在创建虚拟环境...'
    $pythonCmd = $null
    foreach ($cmd in @('py -3', 'python3', 'python')) {
        $parts = $cmd -split ' '
        try {
            & $parts[0] ($parts[1..99] + @('-m', 'venv', '.venv')) 2>$null
            if ($LASTEXITCODE -eq 0) { $pythonCmd = $cmd; break }
        } catch {}
    }
    if (-not $pythonCmd) {
        Write-Host '错误：未找到 Python，请先安装 Python 3。'
        Read-Host '按回车退出'
        exit 1
    }
}

$uvicornCheck = & .\.venv\Scripts\python.exe -c 'import uvicorn' 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host '正在安装依赖（需要网络）...'
    & .\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host '错误：依赖安装失败，请检查网络或手动安装。'
        Read-Host '按回车退出'
        exit 1
    }
}

$env:DETECTOR_NAME = 'yolo26'
Start-Job -ScriptBlock {
    Start-Sleep -Seconds 5
    Start-Process 'http://127.0.0.1:8000/'
} | Out-Null

Write-Host '后端启动中，稍后浏览器将自动打开...'
& .\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
