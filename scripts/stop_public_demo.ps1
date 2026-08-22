$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$processFile = Join-Path $projectRoot "work\public-demo\processes.json"
if (-not (Test-Path -LiteralPath $processFile)) {
    Write-Host "No MERCURY public-demo process file was found."
    exit 0
}

$processes = Get-Content -LiteralPath $processFile -Raw | ConvertFrom-Json
foreach ($processId in @($processes.api, $processes.web, $processes.apiLauncher, $processes.webLauncher) | Select-Object -Unique) {
    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if ($process) { Stop-Process -Id $processId }
}
Write-Host "Stopped MERCURY's native API and dashboard processes."
