[CmdletBinding()]
param(
  [string]$Python
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$venv = Join-Path $root '.venv'

if (-not $Python) {
  $candidates = @(@(
    $env:CODEX_THEME_MANAGER_PYTHON,
    (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'),
    'C:\Python311\python.exe'
  ) | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Leaf) })
  if ($candidates.Count -gt 0) {
    $Python = $candidates[0]
  } else {
    $Python = 'py'
  }
}

if (-not (Test-Path -LiteralPath (Join-Path $venv 'Scripts\python.exe'))) {
  if ($Python -eq 'py') {
    & py -3.11 -m venv $venv
  } else {
    & $Python -m venv $venv
  }
}

$pythonExe = Join-Path $venv 'Scripts\python.exe'
& $pythonExe -m pip install --upgrade pip
& $pythonExe -m pip install -r (Join-Path $root 'requirements.txt') -r (Join-Path $root 'requirements-dev.txt')

Write-Host "环境已就绪：$pythonExe"
