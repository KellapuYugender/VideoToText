<#
.SYNOPSIS
    Starts the VideoToText demo: Django backend, Vite frontend, then the browser.

.DESCRIPTION
    Each server opens in its own window; close that window (or press Ctrl+C in it)
    to stop it. Servers that are already running are reused. The script waits until
    both answer before opening http://localhost:5173.

.PARAMETER NoBrowser
    Start the servers but don't open the browser.

.EXAMPLE
    .\start-demo.ps1
    Or double-click start-demo.cmd.
#>
param([switch]$NoBrowser)

$ErrorActionPreference = 'Stop'

$root = $PSScriptRoot
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$python = Join-Path $backend '.venv\Scripts\python.exe'
$appUrl = 'http://localhost:5173'
$healthUrl = 'http://127.0.0.1:8000/api/health/'

function Test-Port([int]$Port) {
    $null -ne (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Wait-Url([string]$Url, [int]$Seconds) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        try {
            Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3 | Out-Null
            return $true
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    return $false
}

# Opens a new PowerShell window running $Command in $Directory. The command is passed
# base64-encoded so quotes and semicolons survive Start-Process unchanged.
function Start-ServerWindow([string]$Title, [string]$Directory, [string]$Command) {
    $script = "`$host.UI.RawUI.WindowTitle = '$Title'; Set-Location -LiteralPath '$Directory'; $Command"
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($script))
    Start-Process powershell -ArgumentList '-NoExit', '-NoProfile', '-EncodedCommand', $encoded
}

Write-Host ''
Write-Host 'VideoToText demo' -ForegroundColor Cyan
Write-Host ''

if (-not (Test-Path $python)) {
    Write-Host "Backend is not set up ($python is missing)." -ForegroundColor Red
    Write-Host "Follow 'Backend setup' in README.md first."
    exit 1
}

if (-not (Test-Path (Join-Path $frontend 'node_modules'))) {
    Write-Host 'Installing frontend packages (first run only)...'
    Push-Location $frontend
    try { npm install } finally { Pop-Location }
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'npm install failed.' -ForegroundColor Red
        exit 1
    }
}

if (-not (Test-Port 5433)) {
    Write-Warning 'PostgreSQL 18 (port 5433) is not running, so sessions cannot be saved.'
    Write-Warning "Start it with: Start-Service postgresql-x64-18  (as administrator)"
}

if (Test-Port 8000) {
    Write-Host 'Backend already running on port 8000.'
} else {
    Write-Host 'Starting backend (new window)...'
    Start-ServerWindow 'VideoToText backend' $backend `
        "`$env:HF_HUB_DISABLE_SYMLINKS_WARNING = '1'; & '$python' manage.py runserver"
}

if (Test-Port 5173) {
    Write-Host 'Frontend already running on port 5173.'
} else {
    Write-Host 'Starting frontend (new window)...'
    Start-ServerWindow 'VideoToText frontend' $frontend 'npm run dev -- --strictPort'
}

Write-Host 'Waiting for the backend...'
if (-not (Wait-Url $healthUrl 90)) {
    Write-Host 'The backend did not start. Check the "VideoToText backend" window for errors.' -ForegroundColor Red
    exit 1
}

Write-Host 'Waiting for the frontend...'
if (-not (Wait-Url $appUrl 60)) {
    Write-Host 'The frontend did not start. Check the "VideoToText frontend" window for errors.' -ForegroundColor Red
    exit 1
}

Write-Host ''
Write-Host "Ready: $appUrl" -ForegroundColor Green
if (-not $NoBrowser) {
    Start-Process $appUrl
}
Write-Host 'To stop the demo, close the two server windows (or press Ctrl+C in each).'
Write-Host ''
