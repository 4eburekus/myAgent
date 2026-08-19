# Для запуска введи в консоли ./start-agent.ps1 
# start-agent.ps1 - Start AI assistant (Chainlit)

Write-Host "Starting AI assistant..." -ForegroundColor Cyan

# Activate venv
if (-not $env:VIRTUAL_ENV) {
    Write-Host "[1/2] Activating venv..." -ForegroundColor Yellow
    & ".venv\Scripts\Activate.ps1"
}

# Check if port 8000 is busy
$proc = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($proc) {
    Write-Host "ERROR: Port 8000 is already in use (PID $($proc.OwningProcess))" -ForegroundColor Red
    Write-Host "Run .\stop-agent.ps1 first." -ForegroundColor Yellow
    exit 1
}

Write-Host "[2/2] Launching server..." -ForegroundColor Green
& python -m chainlit run frontend/app.py --headless
