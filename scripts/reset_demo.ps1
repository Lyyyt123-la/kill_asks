"""录制演示视频前重置环境：清空历史数据 → 重启后端 → 载入示例数据。

用法（在仓库根目录）：pwsh -ExecutionPolicy Bypass -File scripts\reset_demo.ps1
"""
$ErrorActionPreference = 'SilentlyContinue'
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root 'backend'
$python = Join-Path $backend '.venv\Scripts\python.exe'

Write-Host '[1/4] 停止后端 ...'
$conn = Get-NetTCPConnection -LocalPort 8000 -State Listen | Select-Object -First 1
if ($conn) { Stop-Process -Id $conn.OwningProcess -Force }
Start-Sleep -Milliseconds 800

Write-Host '[2/4] 清空数据集 / 文档 / 元数据 ...'
Remove-Item (Join-Path $backend 'data\meta.db') -ErrorAction SilentlyContinue
Remove-Item (Join-Path $backend 'data\datasets\*.duckdb') -ErrorAction SilentlyContinue
Remove-Item (Join-Path $backend 'data\documents\*') -Recurse -Force -ErrorAction SilentlyContinue

Write-Host '[3/4] 启动后端 ...'
Start-Process -FilePath $python -ArgumentList '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000' `
  -WorkingDirectory $backend -WindowStyle Hidden `
  -RedirectStandardOutput (Join-Path $env:TEMP 'askdata-api.log') `
  -RedirectStandardError (Join-Path $env:TEMP 'askdata-api-err.log')
Start-Sleep -Seconds 3

Write-Host '[4/4] 载入双11示例数据 ...'
try {
  $resp = Invoke-RestMethod -Method Post 'http://127.0.0.1:8000/api/datasets/demo' -TimeoutSec 60
  Write-Host "完成：$($resp.name)，$($resp.rows) 行"
} catch {
  Write-Warning '示例数据载入失败，请检查后端日志'
}

Write-Host ''
Write-Host '可以开始录制：http://127.0.0.1:8000' -ForegroundColor Green
Write-Host '演示素材：demo_data\documents\2025年Q3经营情况报告.pdf / 各渠道退款率截图.png / 双11大促复盘摘要.docx'
