$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontendUrl = 'http://localhost:5173'

function Test-ServerRunning([int]$Port) {
    return (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue).Count -gt 0
}

if (-not (Test-ServerRunning 8000)) {
    Start-Process powershell -ArgumentList '-NoExit', '-Command', "Set-Location '$projectRoot'; python backend/run.py"
}

if (-not (Test-ServerRunning 5173)) {
    Start-Process powershell -ArgumentList '-NoExit', '-Command', "Set-Location '$projectRoot\frontend'; npx vite --host 127.0.0.1"
}

for ($attempt = 0; $attempt -lt 30; $attempt++) {
    try {
        Invoke-WebRequest -Uri $frontendUrl -UseBasicParsing -TimeoutSec 1 | Out-Null
        Start-Process $frontendUrl
        exit 0
    } catch {
        Start-Sleep -Seconds 1
    }
}

Write-Error "The frontend did not start at $frontendUrl. Check the server windows for details."
