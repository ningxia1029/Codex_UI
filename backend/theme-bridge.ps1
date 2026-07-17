[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [ValidateSet('list', 'status', 'activate', 'import', 'save', 'apply', 'verify', 'restore')]
  [string]$Operation,
  [string]$ThemeDirectory,
  [string]$ImagePath,
  [string]$Name,
  [string]$ScreenshotPath
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$backendRoot = $PSScriptRoot
$scripts = Join-Path $backendRoot 'scripts'
. (Join-Path $scripts 'common-windows.ps1')
. (Join-Path $scripts 'theme-windows.ps1')

$stateRoot = Join-Path $env:LOCALAPPDATA 'CodexDreamSkin'
$skillRoot = $backendRoot

function Convert-DreamSkinThemeRecord {
  param([Parameter(Mandatory = $true)]$Loaded)
  return [pscustomobject]@{
    directory = "$($Loaded.Directory)"
    imagePath = "$($Loaded.ImagePath)"
    theme = $Loaded.Theme
  }
}

function Write-DreamSkinBridgeResult {
  param([Parameter(Mandatory = $true)]$Data)
  [pscustomobject]@{ ok = $true; data = $Data } | ConvertTo-Json -Depth 16 -Compress
}

try {
  switch ($Operation) {
    'list' {
      $paths = Initialize-DreamSkinThemeStore -SkillRoot $skillRoot -StateRoot $stateRoot
      $active = Convert-DreamSkinThemeRecord -Loaded (Read-DreamSkinTheme -ThemeDirectory $paths.Active -SkipImageMetadata)
      $saved = @()
      foreach ($entry in @(Get-DreamSkinSavedThemes -StateRoot $stateRoot -SkipImageMetadata)) {
        $saved += Convert-DreamSkinThemeRecord -Loaded (Read-DreamSkinTheme -ThemeDirectory $entry.Path -SkipImageMetadata)
      }
      Write-DreamSkinBridgeResult -Data ([pscustomobject]@{ active = $active; saved = $saved })
    }
    'status' {
      $paths = Initialize-DreamSkinThemeStore -SkillRoot $skillRoot -StateRoot $stateRoot
      $active = $null
      try { $active = Convert-DreamSkinThemeRecord -Loaded (Read-DreamSkinTheme -ThemeDirectory $paths.Active -SkipImageMetadata) } catch {}
      $state = $null
      try { $state = Read-DreamSkinState -Path $paths.State } catch {}
      # state.json 只是上次启动记录。需要同时确认记录中的 Node watcher 仍存活，
      # 并且对应 Codex CDP 端点可用，才允许 GUI 承诺“切换会自动同步”。
      $injectorRunning = $false
      $cdpReady = $false
      if ($state -and $state.injectorPid) {
        $startedAt = Get-DreamSkinProcessStartedAt -ProcessId ([int]$state.injectorPid)
        $injectorRunning = [bool]($startedAt -and
          (-not $state.injectorStartedAt -or $startedAt -eq "$($state.injectorStartedAt)"))
        if ($injectorRunning -and $state.port) {
          try {
            $codex = Get-DreamSkinCodexInstall
            $cdpReady = $null -ne (Get-DreamSkinVerifiedCdpIdentity -Port ([int]$state.port) -Codex $codex)
          } catch {}
        }
      }
      $liveConnected = [bool]($injectorRunning -and $cdpReady)
      Write-DreamSkinBridgeResult -Data ([pscustomobject]@{
        paused = [bool](Test-DreamSkinPaused -StateRoot $stateRoot)
        active = $active
        state = $state
        message = if ($liveConnected) {
          'Codex Dream Skin 已连接；切换活动主题会自动同步。'
        } elseif ($state) {
          '检测到历史主题会话，但当前连接已停止；请重新连接 Codex。'
        } else {
          '主题库已就绪，尚未检测到活动注入会话。'
        }
        injectorRunning = $liveConnected
      })
    }
    'activate' {
      if (-not $ThemeDirectory) { throw 'ThemeDirectory is required.' }
      $record = Convert-DreamSkinThemeRecord -Loaded (Use-DreamSkinSavedTheme -ThemeDirectory $ThemeDirectory -StateRoot $stateRoot)
      Write-DreamSkinBridgeResult -Data $record
    }
    'import' {
      if (-not $ImagePath) { throw 'ImagePath is required.' }
      $theme = $null
      if ($Name) {
        $theme = (Read-DreamSkinTheme -ThemeDirectory (Get-DreamSkinThemePaths -StateRoot $stateRoot).Active -SkipImageMetadata).Theme
        $theme.name = $Name.Trim()
      }
      $record = Convert-DreamSkinThemeRecord -Loaded (Set-DreamSkinActiveTheme -ImagePath $ImagePath -Theme $theme -StateRoot $stateRoot)
      Write-DreamSkinBridgeResult -Data $record
    }
    'save' {
      if (-not $Name) { throw 'Name is required.' }
      $record = Convert-DreamSkinThemeRecord -Loaded (Save-DreamSkinCurrentTheme -Name $Name -StateRoot $stateRoot)
      Write-DreamSkinBridgeResult -Data $record
    }
    'apply' {
      & (Join-Path $scripts 'start-dream-skin.ps1') -PromptRestart
      Write-DreamSkinBridgeResult -Data ([pscustomobject]@{ message = '已请求应用或重新应用 Codex Dream Skin。' })
    }
    'verify' {
      $arguments = @()
      if ($ScreenshotPath) { $arguments += @('-ScreenshotPath', $ScreenshotPath) }
      & (Join-Path $scripts 'verify-dream-skin.ps1') @arguments
      Write-DreamSkinBridgeResult -Data ([pscustomobject]@{ message = '皮肤验证脚本已完成。' })
    }
    'restore' {
      & (Join-Path $scripts 'restore-dream-skin.ps1') -RestoreBaseTheme
      Write-DreamSkinBridgeResult -Data ([pscustomobject]@{ message = '已恢复 Codex 原生外观。' })
    }
  }
} catch {
  [pscustomobject]@{ ok = $false; error = $_.Exception.Message } | ConvertTo-Json -Compress
  exit 1
}
