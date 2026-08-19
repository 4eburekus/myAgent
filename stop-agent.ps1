# stop-agent.ps1 - Stop AI assistant (Chainlit)

$proc = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($proc) {
    Write-Host "Stopping process PID $($proc.OwningProcess)..." -ForegroundColor Yellow
    Stop-Process -Id $proc.OwningProcess -Force
    Write-Host "Done." -ForegroundColor Green
} else {
    Write-Host "No running process on port 8000." -ForegroundColor Yellow
}
