# start.ps1 — one command to bring up the full YourTutor stack
# Usage: .\start.ps1          (uses cached layers, fastest)
#        .\start.ps1 -Rebuild  (forces full image rebuild)
param([switch]$Rebuild)

$ErrorActionPreference = "Stop"
$ROOT = $PSScriptRoot

# ── 1. Ensure Docker Desktop is running ──────────────────────────────────────
Write-Host "Checking Docker..."
$dockerOk = $false
for ($i = 0; $i -lt 3; $i++) {
    if ((docker info 2>$null) -and $LASTEXITCODE -eq 0) { $dockerOk = $true; break }
    Write-Host "  Docker not ready, starting Docker Desktop..."
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe" -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 15
}
if (-not $dockerOk) { Write-Error "Docker Desktop did not start. Open it manually and re-run."; exit 1 }
Write-Host "  Docker ready." -ForegroundColor Green

# ── 2. Build and start containers ────────────────────────────────────────────
Set-Location $ROOT
$buildFlag = if ($Rebuild) { "--build --no-cache" } else { "--build" }
Write-Host "Starting containers ($buildFlag)..."
$env:DOCKER_BUILDKIT = "1"
$env:COMPOSE_DOCKER_CLI_BUILD = "1"
Invoke-Expression "docker compose up -d $buildFlag"
if ($LASTEXITCODE -ne 0) { Write-Error "docker compose failed"; exit 1 }

# ── 3. Wait for all services to be healthy ───────────────────────────────────
Write-Host "Waiting for services to be healthy..."
$services = @("yourtutor-api-1", "yourtutor-postgres-1", "yourtutor-redis-1")
$timeout = 120
$elapsed = 0
while ($elapsed -lt $timeout) {
    $allHealthy = $true
    foreach ($svc in $services) {
        $status = (docker inspect --format "{{.State.Health.Status}}" $svc 2>$null)
        if ($status -ne "healthy") { $allHealthy = $false; break }
    }
    if ($allHealthy) { break }
    Start-Sleep -Seconds 3
    $elapsed += 3
}
if ($elapsed -ge $timeout) { Write-Warning "Services took too long to become healthy — check docker compose logs" }
else { Write-Host "  All services healthy." -ForegroundColor Green }

# ── 4. Kill any leftover workers and inspectors, then start fresh ─────────────
Write-Host "Stopping any existing video-job workers..."
$oldWorkers = Get-WmiObject Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*app.video_jobs*" }
foreach ($w in $oldWorkers) {
    try { Stop-Process -Id $w.ProcessId -Force -ErrorAction SilentlyContinue } catch {}
}
if ($oldWorkers) { Write-Host "  Stopped $($oldWorkers.Count) old worker(s)." -ForegroundColor Yellow }

Write-Host "Stopping any process on port 4777 (job inspector)..."
$old4777 = netstat -ano | Select-String ":4777 " | ForEach-Object {
    ($_ -split "\s+")[-1]
} | Select-Object -Unique | Where-Object { $_ -match "^\d+$" }
foreach ($pid4777 in $old4777) {
    try { Stop-Process -Id ([int]$pid4777) -Force -ErrorAction SilentlyContinue } catch {}
}
if ($old4777) { Write-Host "  Freed port 4777." -ForegroundColor Yellow }

$workerDir = Join-Path $ROOT "apps\api"
Write-Host "Starting video-job worker..."
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$workerDir'; Write-Host 'Video-job worker starting...' -ForegroundColor Cyan; python -m app.video_jobs"
) -WindowStyle Normal
Write-Host "  Worker started in new window." -ForegroundColor Green

# ── 5. Start job inspector (localhost:4777) in a new terminal window ─────────
$engineDir = Resolve-Path (Join-Path $ROOT "..\EduVideoEngine")
Write-Host "Starting job inspector..."
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$engineDir'; Write-Host 'Job inspector starting on http://localhost:4777 ...' -ForegroundColor Cyan; pnpm job:watch"
) -WindowStyle Normal
Write-Host "  Job inspector started in new window." -ForegroundColor Green

# ── 6. Summary ───────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Stack is up:" -ForegroundColor Cyan
Write-Host "  Web app   ->  http://localhost:3000"
Write-Host "  API       ->  http://localhost:8000"
Write-Host "  API docs  ->  http://localhost:8000/docs"
Write-Host "  Job watch ->  http://localhost:4777"
Write-Host ""
Write-Host "To stop:    docker compose down"
Write-Host "To rebuild: .\start.ps1 -Rebuild"
