$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$venvPython = Join-Path $backend '.venv\Scripts\python.exe'

Write-Host '=== 问数 AskData 环境初始化 ===' -ForegroundColor Green

if (-not (Test-Path $venvPython)) {
  Write-Host '[1/5] 创建 Python 虚拟环境 ...'
  python -m venv (Join-Path $backend '.venv')
} else {
  Write-Host '[1/5] Python 虚拟环境已存在，跳过创建'
}

Write-Host '[2/5] 安装后端依赖 ...'
& $venvPython -m pip install --disable-pip-version-check -i https://pypi.tuna.tsinghua.edu.cn/simple -r (Join-Path $backend 'requirements.txt')

Write-Host '[3/5] 安装前端依赖 ...'
Push-Location $frontend
npm install
Pop-Location

Write-Host '[4/5] 生成演示数据 ...'
& $venvPython (Join-Path $root 'scripts\gen_demo_data.py')

Write-Host '[5/5] 初始化环境变量 ...'
$envFile = Join-Path $backend '.env'
if (-not (Test-Path $envFile)) {
  Copy-Item (Join-Path $backend '.env.example') $envFile
  Write-Host '  已创建 backend\.env，可填入 LLM_API_KEY（不填则使用演示模式）'
} else {
  Write-Host '  backend\.env 已存在，跳过'
}

Write-Host ''
Write-Host '初始化完成 ✅' -ForegroundColor Green
Write-Host '下一步：修改 backend\.env 填入模型 Key（可选），然后运行 scripts\dev.ps1'
