$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $root 'frontend'

Write-Host '构建前端（生产模式）...' -ForegroundColor Green
Push-Location $frontend
npm run build
Pop-Location

Write-Host ''
Write-Host '构建完成：frontend\dist' -ForegroundColor Green
Write-Host '启动后端后将自动托管前端，访问 http://127.0.0.1:8000'
Write-Host '启动命令：cd backend; .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000'
