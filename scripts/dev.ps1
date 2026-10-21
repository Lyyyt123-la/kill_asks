$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$venvPython = Join-Path $backend '.venv\Scripts\python.exe'

if (-not (Test-Path $venvPython)) {
  Write-Warning '未找到 backend\.venv，请先运行 scripts\setup.ps1'
  exit 1
}

function Test-Port($port) {
  $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
  return [bool]$conn
}

if (Test-Port 8000) {
  Write-Host '[后端] 8000 端口已在运行，跳过启动'
} else {
  Write-Host '[后端] 启动 http://127.0.0.1:8000 ...'
  Start-Process -FilePath $venvPython `
    -ArgumentList '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000', '--reload' `
    -WorkingDirectory $backend -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $env:TEMP 'askdata-backend.log') `
    -RedirectStandardError (Join-Path $env:TEMP 'askdata-backend-err.log')
}

if (Test-Port 5173) {
  Write-Host '[前端] 5173 端口已在运行，跳过启动'
} else {
  Write-Host '[前端] 启动 http://127.0.0.1:5173 ...'
  Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', 'npm run dev' `
    -WorkingDirectory $frontend -WindowStyle Hidden
}

Start-Sleep -Seconds 4
Write-Host ''
Write-Host '问数 AskData 已启动：' -ForegroundColor Green
Write-Host '  前端界面   http://127.0.0.1:5173'
Write-Host '  接口文档   http://127.0.0.1:8000/docs'
Write-Host '  健康检查   http://127.0.0.1:8000/api/health'
