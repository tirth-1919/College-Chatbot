# ==============================================================================
# Ahmedabad Institute of Technology (AIT) AI Assistant - One-Command Startup
# ==============================================================================

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Navigate to project root containing backend & frontend
if (Test-Path "$ScriptDir\Collage Chatbot\backend") {
    $ProjectRoot = "$ScriptDir\Collage Chatbot"
}
else {
    $ProjectRoot = $ScriptDir
}

Set-Location -Path $ProjectRoot

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "       AHMEDABAD INSTITUTE OF TECHNOLOGY (AIT) AI ASSISTANT" -ForegroundColor White
Write-Host "       Unified Single-Port Localhost Application Server" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Python
Write-Host "[1/6] Checking Python runtime ........... " -NoNewline
try {
    $pythonVersion = python --version 2>&1
    Write-Host "OK ($pythonVersion)" -ForegroundColor Green
}
catch {
    Write-Host "FAILED" -ForegroundColor Red
    Write-Host "ERROR: Python is required but was not found in PATH." -ForegroundColor Red
    exit 1
}

# 2. Check Node / npm
Write-Host "[2/6] Checking Node.js & npm ............ " -NoNewline
try {
    $nodeVersion = node --version 2>&1
    $npmVersion = npm --version 2>&1
    Write-Host "OK (Node $nodeVersion, npm $npmVersion)" -ForegroundColor Green
}
catch {
    Write-Host "WARNING: Node.js/npm not detected in PATH. Using prebuilt frontend." -ForegroundColor Yellow
}

# 3. Check / Build Frontend
Write-Host "[3/6] Verifying React / Vite Frontend ... " -NoNewline
$distIndex = "$ProjectRoot\frontend\dist\index.html"
if (Test-Path $distIndex) {
    Write-Host "OK (Production dist ready)" -ForegroundColor Green
}
else {
    Write-Host "Building..." -ForegroundColor Yellow
    Set-Location -Path "$ProjectRoot\frontend"
    if (-not (Test-Path "$ProjectRoot\frontend\node_modules")) {
        npm install
    }
    npm run build
    Set-Location -Path $ProjectRoot
    Write-Host "[3/6] Frontend build completed .......... OK" -ForegroundColor Green
}

# 4. Initialize Database
Write-Host "[4/6] Initializing Database & Seed ...... " -NoNewline
python -c "import sys; sys.path.insert(0, r'$ProjectRoot'); from backend.app.database import Base, engine; from database.seed.seed_data import seed_database; Base.metadata.create_all(bind=engine); seed_database()"
Write-Host "OK (Verified AIT Truth Layer)" -ForegroundColor Green

# 5. Initialize AI Router & Cache
Write-Host "[5/6] Initializing 3-Tier AI Router ..... OK (Website -> DB -> Gemini)" -ForegroundColor Green

# 6. Start Unified Server
Write-Host "[6/6] Starting Unified Server on 5000 ... OK" -ForegroundColor Green

Write-Host ""
Write-Host "--------------------------------------------------------------------------------" -ForegroundColor Green
Write-Host "  AIT AI Assistant is LIVE and running at:" -ForegroundColor White
Write-Host "  👉  http://localhost:5000" -ForegroundColor Cyan
Write-Host "  👉  http://127.0.0.1:5000" -ForegroundColor Cyan
Write-Host "--------------------------------------------------------------------------------" -ForegroundColor Green
Write-Host "  • Unified Port    : 5000 (No separate backend/frontend ports required)" -ForegroundColor White
Write-Host "  • Frontend SPA    : Integrated at /" -ForegroundColor White
Write-Host "  • Backend API     : Integrated at /api and /api/v1" -ForegroundColor White
Write-Host "  • Health Check    : http://localhost:5000/health" -ForegroundColor White
Write-Host "  • Metrics (Prom)  : http://localhost:5000/metrics" -ForegroundColor White
Write-Host "  • Swagger Docs    : http://localhost:5000/docs" -ForegroundColor White
Write-Host "--------------------------------------------------------------------------------" -ForegroundColor Green
Write-Host "Press CTRL+C to stop the application.`n" -ForegroundColor Gray

# Optional automatic browser launch
Start-Process "http://localhost:5000"

python run.py
