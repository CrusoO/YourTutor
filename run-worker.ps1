# run-worker.ps1 — Start the video-job worker on the host machine.
#
# The worker claims queued video jobs from the database and runs
# EduVideoEngine via pnpm on this machine. It must run on the host
# (not in Docker) because it needs Node.js + pnpm to invoke the engine.
#
# Prerequisites:
#   - docker compose up (postgres + redis must be running)
#   - pnpm must be on PATH  (the engine uses it)
#
# Usage:
#   .\run-worker.ps1

$ErrorActionPreference = "Stop"

# ── resolve paths ─────────────────────────────────────────────────────────────
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$apiDir    = Join-Path $scriptDir "apps\api"

# ── add pnpm / corepack shims to PATH if missing ─────────────────────────────
$corecapBin = "$env:LOCALAPPDATA\corepack-bin"
if ($corecapBin -and (Test-Path $corecapBin) -and ($env:Path -notlike "*$corecapBin*")) {
    $env:Path = "$env:Path;$corecapBin"
}
$nodeBin = "C:\Program Files\nodejs"
if ((Test-Path $nodeBin) -and ($env:Path -notlike "*$nodeBin*")) {
    $env:Path = "$env:Path;$nodeBin"
}

Write-Host "video-job worker"
Write-Host "  api dir    : $apiDir"
Write-Host "  db host    : 127.0.0.1 (config default)"
Write-Host ""
Write-Host "Press Ctrl+C to stop."
Write-Host ""

# Run from apps/api/ so pydantic-settings reads apps/api/.env
Set-Location $apiDir
python -m app.video_jobs.worker
