[CmdletBinding()]
param(
  [string]$Python
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
if (-not $Python) {
  $candidate = Join-Path $root '.venv\Scripts\python.exe'
  if (Test-Path -LiteralPath $candidate) {
    $Python = $candidate
  } else {
    throw "未找到 .venv。请先运行：powershell -ExecutionPolicy Bypass -File .\setup.ps1"
  }
}

$env:PYTHONPATH = Join-Path $root 'src'
& $Python -m codex_theme_manager
