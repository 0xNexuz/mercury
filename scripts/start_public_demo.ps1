$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
$npmExe = (Get-Command npm.cmd -ErrorAction Stop).Source
$cloudflaredCommand = Get-Command cloudflared.exe -ErrorAction SilentlyContinue
$cloudflaredCandidates = @(
    $cloudflaredCommand.Source,
    "C:\Program Files\cloudflared\cloudflared.exe",
    "C:\Program Files (x86)\cloudflared\cloudflared.exe"
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }

if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw "Missing .venv. Follow README.md native setup first."
}
if (-not $cloudflaredCandidates) {
    throw "cloudflared is missing. Install it with: winget install --id Cloudflare.cloudflared --exact --source winget"
}

$cloudflaredExe = @($cloudflaredCandidates)[0]
$workDir = Join-Path $projectRoot "work\public-demo"
$dataDir = Join-Path $projectRoot "data"
New-Item -ItemType Directory -Force -Path $workDir, $dataDir | Out-Null

$previousPythonPath = $env:PYTHONPATH
$previousSibylPath = $env:SIBYL_DB_PATH
$env:PYTHONPATH = Join-Path $projectRoot "api"
$env:SIBYL_DB_PATH = Join-Path $dataDir "memory.db"

try {
    Write-Host "Building the production dashboard for tunnel-safe client hydration..." -ForegroundColor DarkGray
    $buildProcess = Start-Process -FilePath $npmExe -ArgumentList @("run", "build") -WorkingDirectory $projectRoot -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput (Join-Path $workDir "build.log") -RedirectStandardError (Join-Path $workDir "build-error.log")
    if ($buildProcess.ExitCode -ne 0) {
        throw "MERCURY production build failed. Inspect work/public-demo/build-error.log."
    }
    $apiStart = @{
        FilePath = $pythonExe
        ArgumentList = @("-m", "uvicorn", "mercury.main:app", "--host", "127.0.0.1", "--port", "8000")
        WorkingDirectory = $projectRoot
        WindowStyle = "Hidden"
        PassThru = $true
        RedirectStandardOutput = Join-Path $workDir "api.log"
        RedirectStandardError = Join-Path $workDir "api-error.log"
    }
    $apiProcess = Start-Process @apiStart

    $webStart = @{
        FilePath = $npmExe
        ArgumentList = @("run", "start", "--", "--hostname", "127.0.0.1", "--port", "3000")
        WorkingDirectory = $projectRoot
        WindowStyle = "Hidden"
        PassThru = $true
        RedirectStandardOutput = Join-Path $workDir "web.log"
        RedirectStandardError = Join-Path $workDir "web-error.log"
    }
    $webProcess = Start-Process @webStart
} finally {
    $env:PYTHONPATH = $previousPythonPath
    $env:SIBYL_DB_PATH = $previousSibylPath
}

$ready = $false
for ($attempt = 0; $attempt -lt 60; $attempt++) {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:3000/api/health" -TimeoutSec 2
        if ($health.status -eq "ok") { $ready = $true; break }
    } catch {
        Start-Sleep -Seconds 1
    }
}

if (-not $ready) {
    throw "MERCURY did not become healthy. Inspect work/public-demo/*.log."
}

$apiListener = Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction Stop | Select-Object -First 1
$webListener = Get-NetTCPConnection -State Listen -LocalPort 3000 -ErrorAction Stop | Select-Object -First 1
@{
    api = $apiListener.OwningProcess
    web = $webListener.OwningProcess
} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $workDir "processes.json")

Write-Host "MERCURY is healthy. Creating a temporary public Cloudflare URL..." -ForegroundColor Cyan
Write-Host "Keep this terminal open. Press Ctrl+C to close the tunnel." -ForegroundColor DarkGray
& $cloudflaredExe tunnel --url "http://127.0.0.1:3000" --no-autoupdate --protocol quic --edge-ip-version 4
