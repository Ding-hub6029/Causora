param([int]$BackendPort = 8000, [int]$FrontendPort = 3000)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$backendRoot = Join-Path $projectRoot 'backend/backend'
$frontendRoot = Join-Path $projectRoot 'frontend'
if ($BackendPort -lt 1 -or $BackendPort -gt 65535 -or $FrontendPort -lt 1 -or $FrontendPort -gt 65535 -or $BackendPort -eq $FrontendPort) {
    throw 'Choose two different ports from 1 through 65535.'
}
foreach ($port in @($BackendPort, $FrontendPort)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $port is already in use. Choose another port; existing processes will not be stopped."
    }
}
$python = Join-Path $backendRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = (Get-Command python -ErrorAction Stop).Source }
$node = (Get-Command node -ErrorAction Stop).Source
if (-not (Test-Path -LiteralPath (Join-Path $frontendRoot 'out/index.html'))) {
    throw 'The built website is missing. Run npm ci and npm run build in frontend first.'
}
$runtime = Join-Path $projectRoot '.runtime'
New-Item -ItemType Directory -Path $runtime -Force | Out-Null
# Authorize paid calls explicitly through caller environment. Never embed a key.
if (-not $env:CAUSORA_OPENROUTER_BUDGET_JOURNAL) {
    $env:CAUSORA_OPENROUTER_BUDGET_JOURNAL = Join-Path $runtime 'openrouter-budget.json'
}
$backend = Start-Process -FilePath $python -ArgumentList @('scripts/start_day4_reviewed.py', '--port', $BackendPort) -WorkingDirectory $backendRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtime 'backend.log') -RedirectStandardError (Join-Path $runtime 'backend-error.log')
$env:CAUSORA_BACKEND_URL = "http://127.0.0.1:$BackendPort"
$env:PORT = [string]$FrontendPort
$env:HOST = '127.0.0.1'
$frontend = Start-Process -FilePath $node -ArgumentList @('scripts/serve-static.mjs') -WorkingDirectory $frontendRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtime 'frontend.log') -RedirectStandardError (Join-Path $runtime 'frontend-error.log')
@{ backendPid = $backend.Id; frontendPid = $frontend.Id; backendPort = $BackendPort; frontendPort = $FrontendPort } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtime 'processes.json') -Encoding utf8
Write-Host "Causora starting at http://127.0.0.1:$FrontendPort/"
Write-Host "Logs and process IDs: $runtime"
Write-Host 'Simulation uses the approved synthetic policy. AI requires your private provider configuration.'
