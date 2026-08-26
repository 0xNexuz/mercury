$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$processFile = Join-Path $projectRoot "work\public-demo\processes.json"
if (-not (Test-Path -LiteralPath $processFile)) {
    Write-Host "No MERCURY public-demo process file was found."
    exit 0
}

$processes = Get-Content -LiteralPath $processFile -Raw | ConvertFrom-Json
foreach ($processId in @($processes.api, $processes.web) | Select-Object -Unique) {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
    $commandLine = [string]$process.CommandLine
    $isMercuryApi = $process.Name -match '^python(w)?\.exe$' -and $commandLine -match 'mercury\.main:app'
    $isMercuryWeb = $process.Name -eq 'node.exe' -and $commandLine -match 'next(.+)(start|dev)'
    if ($isMercuryApi -or $isMercuryWeb) {
        Stop-Process -Id $processId
    } elseif ($process) {
        Write-Warning "Skipped stale PID $processId ($($process.Name)); it is not a MERCURY process."
    }
}
Write-Host "Stopped MERCURY's native API and dashboard processes."
