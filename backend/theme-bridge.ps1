[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [ValidateSet('list', 'status', 'activate', 'import', 'save', 'configure', 'apply', 'verify', 'diagnose', 'restore')]
  [string]$Operation,
  [string]$ThemeDirectory,
  [string]$ImagePath,
  [string]$Name,
  [string]$ScreenshotPath,
  [string]$ThemeOptionsJson
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
  # PowerShell 5.1 在诊断对象包含多层 PSCustomObject 时，过大的 JSON 深度可能
  # 触发极慢的递归遍历。当前桥接协议最多需要 5 层结构，8 层保留余量并避免
  # “点击诊断/刷新后长时间无响应”的假死现象。
  [pscustomobject]@{ ok = $true; data = $Data } | ConvertTo-Json -Depth 8 -Compress
}

function Get-DreamSkinRuntimeStatus {
  $paths = Initialize-DreamSkinThemeStore -SkillRoot $skillRoot -StateRoot $stateRoot
  $active = $null
  try { $active = Convert-DreamSkinThemeRecord -Loaded (Read-DreamSkinTheme -ThemeDirectory $paths.Active -SkipImageMetadata) } catch {}
  $state = $null
  try { $state = Read-DreamSkinState -Path $paths.State } catch {}
  # state.json 是历史记录，不等价于一条真正可用的热切换连接。
  $watcherAlive = $false
  $cdpReady = $false
  if ($state -and $state.injectorPid) {
    $startedAt = Get-DreamSkinProcessStartedAt -ProcessId ([int]$state.injectorPid)
    $watcherAlive = [bool]($startedAt -and
      (-not $state.injectorStartedAt -or $startedAt -eq "$($state.injectorStartedAt)"))
    if ($watcherAlive -and $state.port) {
      try {
        $codex = Get-DreamSkinCodexInstall
        $cdpReady = $null -ne (Get-DreamSkinVerifiedCdpIdentity -Port ([int]$state.port) -Codex $codex)
      } catch {}
    }
  }
  $liveConnected = [bool]($watcherAlive -and $cdpReady)
  return [pscustomobject]@{
    paused = [bool](Test-DreamSkinPaused -StateRoot $stateRoot)
    active = $active
    state = $state
    watcherAlive = $watcherAlive
    cdpReady = $cdpReady
    injectorRunning = $liveConnected
    message = if ($liveConnected) {
      'Codex Dream Skin 已连接；切换活动主题会自动同步。'
    } elseif ($watcherAlive) {
      '检测到 watcher，但 Codex 的 CDP 端点已停止；下一次切换会请求受控重新连接。'
    } elseif ($state) {
      '检测到历史主题会话，但当前连接已停止；下一次切换会请求受控重新连接。'
    } else {
      '主题库已就绪，尚未检测到活动注入会话。'
    }
  }
}

function Set-DreamSkinActiveThemeOptions {
  param([Parameter(Mandatory = $true)][string]$OptionsJson)
  try { $options = $OptionsJson | ConvertFrom-Json -ErrorAction Stop } catch { throw 'ThemeOptionsJson is invalid JSON.' }
  if ($null -eq $options -or $options -is [array]) { throw 'ThemeOptionsJson must be an object.' }
  $paths = Initialize-DreamSkinThemeStore -SkillRoot $skillRoot -StateRoot $stateRoot
  $loaded = Read-DreamSkinTheme -ThemeDirectory $paths.Active
  $theme = $loaded.Theme | ConvertTo-Json -Depth 8 | ConvertFrom-Json
  if (-not $theme.art) { $theme | Add-Member -NotePropertyName art -NotePropertyValue ([pscustomobject]@{}) -Force }
  if (-not $theme.palette) { $theme | Add-Member -NotePropertyName palette -NotePropertyValue ([pscustomobject]@{}) -Force }

  $appearance = "$($options.appearance)"
  if ($appearance -notin @('auto', 'light', 'dark')) { throw 'appearance must be auto, light or dark.' }
  $safeArea = "$($options.safeArea)"
  if ($safeArea -notin @('auto', 'left', 'right', 'center', 'none')) { throw 'safeArea is invalid.' }
  $taskMode = "$($options.taskMode)"
  if ($taskMode -notin @('auto', 'ambient', 'banner', 'off')) { throw 'taskMode is invalid.' }
  $focusX = 0.0
  $focusY = 0.0
  if (-not [double]::TryParse("$($options.focusX)", [System.Globalization.NumberStyles]::Float,
      [System.Globalization.CultureInfo]::InvariantCulture, [ref]$focusX) -or $focusX -lt 0 -or $focusX -gt 1) {
    throw 'focusX must be a number between 0 and 1.'
  }
  if (-not [double]::TryParse("$($options.focusY)", [System.Globalization.NumberStyles]::Float,
      [System.Globalization.CultureInfo]::InvariantCulture, [ref]$focusY) -or $focusY -lt 0 -or $focusY -gt 1) {
    throw 'focusY must be a number between 0 and 1.'
  }
  $accent = "$($options.accent)".Trim()
  if ($accent -and $accent -notmatch '^(?:#[0-9a-fA-F]{3,8}|(?:rgb|hsl|oklch|oklab)\([^;{}]{1,96}\))$') {
    throw 'accent must be a supported CSS color.'
  }
  $theme | Add-Member -NotePropertyName appearance -NotePropertyValue $appearance -Force
  $theme.art | Add-Member -NotePropertyName focusX -NotePropertyValue ([Math]::Round($focusX, 3)) -Force
  $theme.art | Add-Member -NotePropertyName focusY -NotePropertyValue ([Math]::Round($focusY, 3)) -Force
  $theme.art | Add-Member -NotePropertyName safeArea -NotePropertyValue $safeArea -Force
  $theme.art | Add-Member -NotePropertyName taskMode -NotePropertyValue $taskMode -Force
  if ($accent) { $theme.palette | Add-Member -NotePropertyName accent -NotePropertyValue $accent -Force } elseif ($theme.palette.PSObject.Properties.Name -contains 'accent') {
    $theme.palette.PSObject.Properties.Remove('accent')
  }
  Write-DreamSkinTheme -ThemeDirectory $paths.Active -Theme $theme
  return Convert-DreamSkinThemeRecord -Loaded (Read-DreamSkinTheme -ThemeDirectory $paths.Active -SkipImageMetadata)
}

function Get-DreamSkinTextTail {
  param([Parameter(Mandatory = $true)][string]$Path, [int]$Lines = 24)
  if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return @() }
  try {
    # 不使用 Get-Content：PowerShell 5.1 可能把提供程序附加属性
    # (PSPath、ReadCount 等) 带入诊断 JSON，既膨胀输出又会让 ConvertTo-Json
    # 在深层对象上变得异常缓慢。直接读为 .NET string[]，诊断协议只返回文本。
    # injector.log 会被后台 Node 进程持续追加；以 ReadWrite 共享模式读取，
    # 诊断不能因为日志文件短暂占用而丢失所有日志。
    $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open,
      [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
    try {
      $reader = [System.IO.StreamReader]::new($stream, [System.Text.UTF8Encoding]::new($false), $true)
      try { $content = $reader.ReadToEnd() } finally { $reader.Dispose() }
    } finally {
      $stream.Dispose()
    }
    $allLines = [regex]::Split($content, "`r?`n")
    $start = [Math]::Max(0, $allLines.Length - [Math]::Max(1, $Lines))
    $tail = [System.Collections.Generic.List[string]]::new()
    for ($index = $start; $index -lt $allLines.Length; $index++) {
      $tail.Add([string]$allLines[$index])
    }
    return @($tail.ToArray())
  } catch {
    return @()
  }
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
      Write-DreamSkinBridgeResult -Data (Get-DreamSkinRuntimeStatus)
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
    'configure' {
      if (-not $ThemeOptionsJson) { throw 'ThemeOptionsJson is required.' }
      Write-DreamSkinBridgeResult -Data (Set-DreamSkinActiveThemeOptions -OptionsJson $ThemeOptionsJson)
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
    'diagnose' {
      $status = Get-DreamSkinRuntimeStatus
      Write-DreamSkinBridgeResult -Data ([pscustomobject]@{
        status = $status
        logs = [pscustomobject]@{
          injector = @(Get-DreamSkinTextTail -Path (Join-Path $stateRoot 'injector.log'))
          errors = @(Get-DreamSkinTextTail -Path (Join-Path $stateRoot 'injector-error.log'))
          verify = @(Get-DreamSkinTextTail -Path (Join-Path $stateRoot 'verify.log'))
        }
        recommendation = if ($status.injectorRunning) {
          '连接健康；切换主题会在 watcher 轮询周期内同步。'
        } elseif ($status.watcherAlive) {
          'watcher 仍在但 CDP 已失效；直接切换主题会请求一次受控重新连接。'
        } else {
          '未检测到有效连接；在主题设置中应用主题即可触发受控重新连接。'
        }
      })
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
