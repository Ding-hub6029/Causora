$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$bundledPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$python = if (Test-Path -LiteralPath $bundledPython) { $bundledPython } else { (Get-Command python -ErrorAction Stop).Source }
& $python -c "import sys; assert sys.version_info[:2] == (3, 12), 'Python 3.12 is required for the shared baseline.'"
if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12 and rerun setup.' }
$node = (Get-Command node -ErrorAction Stop).Source
& $node -e "if(Number(process.versions.node.split('.')[0]) < 22) process.exit(1)"
if ($LASTEXITCODE -ne 0) { throw 'Install Node.js 22 or newer and rerun setup.' }
$venv = Join-Path $projectRoot 'backend/backend/.venv'
if (-not (Test-Path -LiteralPath (Join-Path $venv 'Scripts/python.exe'))) {
    & $python -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the project Python environment.' }
}
$venvPython = Join-Path $venv 'Scripts/python.exe'
& $venvPython -m pip install -r (Join-Path $projectRoot 'backend/backend/requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed; read the error above and rerun setup.' }
Write-Host 'Setup complete. START_LIVE.cmd starts actual simulation; START_STATIC.cmd opens the read-only Golden.'
Write-Host 'The included website builds need no npm installation. Developers rebuilding source should run npm ci in frontend.'
