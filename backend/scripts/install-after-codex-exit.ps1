[CmdletBinding()]
param(
  [int]$TimeoutSeconds = 120
)

$ErrorActionPreference = 'Stop'
$scriptRoot = $PSScriptRoot
$desktop = [Environment]::GetFolderPath('Desktop')
$logPath = Join-Path $desktop 'codex-dream-skin-auto-install.log'

function Write-InstallLog {
  param([string]$Message)
  $line = "[{0:yyyy-MM-dd HH:mm:ss}] {1}" -f (Get-Date), $Message
  Write-Host $line
  Add-Content -LiteralPath $logPath -Value $line -Encoding UTF8
}

Write-InstallLog 'Waiting for the Codex desktop window to exit. Please quit Codex now.'
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
while (@(Get-Process -Name ChatGPT -ErrorAction SilentlyContinue).Count -gt 0) {
  if ((Get-Date) -ge $deadline) {
    throw "Timed out after $TimeoutSeconds seconds waiting for Codex to exit."
  }
  Start-Sleep -Seconds 1
}

Write-InstallLog 'Codex desktop process has exited; installing Dream Skin.'
try {
  & (Join-Path $scriptRoot 'install-dream-skin.ps1')
  Write-InstallLog 'Installation completed; launching Codex with Dream Skin.'
  & (Join-Path $scriptRoot 'start-dream-skin.ps1')
} catch {
  Write-InstallLog ("FAILED: " + $_.Exception.Message)
  throw
}

Write-InstallLog 'Codex Dream Skin is active.'
