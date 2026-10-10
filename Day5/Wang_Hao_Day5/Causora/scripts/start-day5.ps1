param([ValidateSet('live','static')][string]$Mode = 'live', [int]$BackendPort = 8000, [int]$FrontendPort = 3000)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$python = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Run SETUP_WINDOWS.cmd first.' }
& $python (Join-Path $PSScriptRoot 'start_day5.py') --mode $Mode --backend-port $BackendPort --frontend-port $FrontendPort
if ($LASTEXITCODE -ne 0) { throw 'Causora local startup failed; inspect output above.' }
