param([ValidateSet('live','static')][string]$Mode = 'live', [int]$BackendPort = 8000, [int]$FrontendPort = 3000)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$frontendRoot = Join-Path $projectRoot 'frontend'
$backendRoot = Join-Path $projectRoot 'backend/backend'
if ($FrontendPort -lt 1 -or $FrontendPort -gt 65535 -or $BackendPort -lt 1 -or $BackendPort -gt 65535 -or $BackendPort -eq $FrontendPort) { throw 'Choose two different valid ports.' }
$ports = @($FrontendPort)
if ($Mode -eq 'live') { $ports += $BackendPort }
foreach ($port in $ports) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) { throw "Port $port is occupied. Choose another port; existing apps will not be stopped." }
}
$node = (Get-Command node -ErrorAction Stop).Source
$build = Join-Path $frontendRoot "builds/$Mode"
$marker = Join-Path $build '.causora-build.json'
if (-not (Test-Path -LiteralPath $marker)) { throw "The $Mode build is missing. Run npm ci and npm run build:previews inside frontend." }
if ((Get-Content -LiteralPath $marker -Raw | ConvertFrom-Json).mode -ne $Mode) { throw 'Build mode marker does not match requested mode.' }
$runtime = Join-Path $projectRoot ".runtime/$Mode-$FrontendPort"
New-Item -ItemType Directory -Path $runtime -Force | Out-Null
$backend = $null
if ($Mode -eq 'live') {
    $python = Join-Path $backendRoot '.venv/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $python)) {
        $bundledPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
        $python = if (Test-Path -LiteralPath $bundledPython) { $bundledPython } else { (Get-Command python -ErrorAction Stop).Source }
    }
    if (-not $env:CAUSORA_OPENROUTER_BUDGET_JOURNAL) { $env:CAUSORA_OPENROUTER_BUDGET_JOURNAL = Join-Path $runtime 'openrouter-budget.json' }
    $backend = Start-Process -FilePath $python -ArgumentList @('scripts/start_day4_reviewed.py','--port',$BackendPort) -WorkingDirectory $backendRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtime 'backend.log') -RedirectStandardError (Join-Path $runtime 'backend-error.log')
    $ready = $false
    for ($attempt=0; $attempt -lt 40; $attempt++) {
        if ($backend.HasExited) { throw "Backend stopped. Read $runtime/backend-error.log" }
        try { $health = Invoke-RestMethod "http://127.0.0.1:$BackendPort/health" -TimeoutSec 2; if ($health.data.service -eq 'ready') { $ready = $true; break } } catch { }
        Start-Sleep -Milliseconds 500
    }
    if (-not $ready) { Stop-Process -Id $backend.Id -ErrorAction SilentlyContinue; throw "Backend did not become ready. Read $runtime/backend-error.log" }
}
$env:CAUSORA_FRONTEND_MODE = $Mode
$env:CAUSORA_STATIC_ONLY = ([string]($Mode -eq 'static')).ToLowerInvariant()
$env:NEXT_PUBLIC_CAUSORA_STATIC_ONLY = $env:CAUSORA_STATIC_ONLY
$env:CAUSORA_BACKEND_URL = "http://127.0.0.1:$BackendPort"
$env:PORT = [string]$FrontendPort
$env:HOST = '127.0.0.1'
$frontend = Start-Process -FilePath $node -ArgumentList @('scripts/serve-static.mjs') -WorkingDirectory $frontendRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtime 'frontend.log') -RedirectStandardError (Join-Path $runtime 'frontend-error.log')
$frontendReady = $false
for ($attempt=0; $attempt -lt 30; $attempt++) {
    if ($frontend.HasExited) { break }
    try {
        $page = Invoke-WebRequest "http://127.0.0.1:$FrontendPort/" -UseBasicParsing -TimeoutSec 2
        if ($page.StatusCode -eq 200 -and $page.Content -match 'Causora') { $frontendReady = $true; break }
    } catch { }
    Start-Sleep -Milliseconds 300
}
if (-not $frontendReady) {
    Stop-Process -Id $frontend.Id -ErrorAction SilentlyContinue
    if ($backend) { Stop-Process -Id $backend.Id -ErrorAction SilentlyContinue }
    throw "Frontend did not become ready. Read $runtime/frontend-error.log"
}
@{ mode=$Mode; backendPid=$(if ($backend) {$backend.Id} else {$null}); frontendPid=$frontend.Id; backendPort=$BackendPort; frontendPort=$FrontendPort } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtime 'processes.json') -Encoding utf8
Write-Host "Causora $Mode mode: http://127.0.0.1:$FrontendPort/"
Write-Host "Logs: $runtime. AI requires an explicitly configured, authorized server-side key."
