$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot 'backend\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Create venv first: python -m venv backend/.venv' }
& $pythonPath (Join-Path $PSScriptRoot 'start_dev.py')
if ($LASTEXITCODE -ne 0) { throw 'Startup failed; see the error above.' }
