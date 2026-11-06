# AskData Judge Launcher
# Double-click 启动演示.bat (or run: powershell -ExecutionPolicy Bypass -File scripts\judge_start.ps1)
# It installs dependencies if needed, loads the local model key, starts the server, and opens the browser.
param([int]$Port = 8000)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Venv = Join-Path $Backend ".venv"
$VenvPython = Join-Path $Venv "Scripts\python.exe"

Write-Host ""
Write-Host "=============================================="
Write-Host "  AskData - One-click Launcher (Judge Edition)"
Write-Host "=============================================="

# ---------- 1. Python ----------
$pythonCmd = $null
foreach ($candidate in @("python", "py")) {
    try {
        $null = & $candidate --version 2>&1
        if ($LASTEXITCODE -eq 0) { $pythonCmd = $candidate; break }
    } catch { }
}
if (-not $pythonCmd) {
    Write-Host "[ERROR] Python not found. Please install Python 3.11+ and try again."
    exit 1
}
Write-Host "[1/5] Python OK: $(& $pythonCmd --version 2>&1)"

# ---------- 2. Virtual environment + dependencies ----------
if (-not (Test-Path $VenvPython)) {
    Write-Host "[2/5] Creating virtual environment ..."
    if ($pythonCmd -eq "py") { & py -3 -m venv $Venv } else { & python -m venv $Venv }
}
Write-Host "[2/5] Installing backend dependencies via Tsinghua mirror (first run may take 2-5 minutes) ..."
& $VenvPython -m pip install --disable-pip-version-check -q --timeout 120 -i https://pypi.tuna.tsinghua.edu.cn/simple -r (Join-Path $Backend "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARN] Tsinghua mirror failed, retrying with default PyPI ..."
    & $VenvPython -m pip install --disable-pip-version-check -q --timeout 120 -r (Join-Path $Backend "requirements.txt")
}

# ---------- 3. Model key ----------
$EnvFile = Join-Path $Backend ".env"
if (-not (Test-Path $EnvFile)) {
    $judgeEnv = Join-Path $Root "judge\backend.env"
    $exampleEnv = Join-Path $Backend ".env.example"
    if (Test-Path $judgeEnv) {
        Copy-Item $judgeEnv $EnvFile
        Write-Host "[3/5] Model key loaded from judge\backend.env"
    } elseif (Test-Path $exampleEnv) {
        Copy-Item $exampleEnv $EnvFile
        Write-Host "[3/5] No key found - running in DEMO mode (fully usable UI)."
    }
    if (Test-Path $EnvFile) { Write-Host "[3/5] Created backend\.env" }
}

# ---------- 4. Frontend build ----------
$DistIndex = Join-Path $Frontend "dist\index.html"
if (-not (Test-Path $DistIndex)) {
    $npm = Get-Command npm -ErrorAction SilentlyContinue
    if ($npm) {
        Write-Host "[4/5] Building frontend (first run only) ..."
        Push-Location $Frontend
        & npm install --no-audit --no-fund
        & npm run build
        Pop-Location
    } else {
        Write-Host "[4/5] WARN: frontend build missing and npm not found. API only."
    }
} else {
    Write-Host "[4/5] Frontend build found - skip."
}

# ---------- 5. Start server ----------
$existing = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "[5/5] Port $Port is busy. Trying $($Port + 1) ..."
    $Port = $Port + 1
}
Write-Host "[5/5] Starting server on http://127.0.0.1:$Port ..."
$log = Join-Path $env:TEMP "askdata_judge.log"
$process = Start-Process -FilePath $VenvPython `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "$Port" `
    -WorkingDirectory $Backend -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $log -RedirectStandardError ($log + ".err")

$ready = $false
for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Seconds 2
    try {
        $health = Invoke-RestMethod "http://127.0.0.1:$Port/api/health" -TimeoutSec 3
        $ready = $true
        break
    } catch { }
}
if (-not $ready) {
    Write-Host "[ERROR] Server did not start. See log: $log"
    exit 1
}

$mode = if ($health.mock_mode) { "DEMO (no key)" } else { $health.model }
Write-Host ""
Write-Host "=============================================="
Write-Host "  Server ready:  http://127.0.0.1:$Port"
Write-Host "  Model:         $mode"
Write-Host "  Vision:        $($health.vision_model)"
Write-Host "  Press Ctrl+C in this window to stop."
Write-Host "=============================================="
Write-Host ""
Start-Process "http://127.0.0.1:$Port"
try {
    Wait-Process -Id $process.Id
} finally {
    Write-Host "Server stopped."
}
