$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$python = (Get-Command python -ErrorAction Stop).Source
& $python -c "import sys; assert sys.version_info[:2] == (3, 12), 'Python 3.12 required for the tested numpy baseline'"
if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12 and rerun setup.' }
$node = (Get-Command node -ErrorAction Stop).Source
& $node -e "if(Number(process.versions.node.split('.')[0]) < 22) process.exit(1)"
if ($LASTEXITCODE -ne 0) { throw 'Install Node.js 22 or newer and rerun setup.' }
$npm = (Get-Command npm.cmd -ErrorAction Stop).Source
$venv = Join-Path $projectRoot '.venv'
$venvPython = Join-Path $venv 'Scripts/python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    & $python -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create project Python environment.' }
}
& $venvPython -m pip install -r (Join-Path $projectRoot 'requirements-day5-tested.txt')
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
Push-Location (Join-Path $projectRoot 'frontend')
try {
    & $npm ci
    if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
    & $npm run build:previews
    if ($LASTEXITCODE -ne 0) { throw 'Frontend source build failed.' }
} finally { Pop-Location }
Write-Host 'Setup complete. START_LIVE.cmd runs reviewed simulation only; START_STATIC.cmd runs historical replay.'
Write-Host 'No model calls, approvals, budget journals or deployments were created.'
