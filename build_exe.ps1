[CmdletBinding()]
param(
    [switch]$Clean,
    [switch]$NoSlim,
    [string]$Python,
    [string]$DistDir,
    [string]$WorkDir
)

$ErrorActionPreference = 'Stop'
$PROJECT_ROOT = $PSScriptRoot
$PYTHON = if ($Python) { [System.IO.Path]::GetFullPath($Python) } else { Join-Path $PROJECT_ROOT '.venv\Scripts\python.exe' }
$DIST_DIR = if ($DistDir) { [System.IO.Path]::GetFullPath($DistDir) } else { Join-Path $PROJECT_ROOT 'dist' }
$BUILD_DIR = if ($WorkDir) { [System.IO.Path]::GetFullPath($WorkDir) } else { Join-Path $PROJECT_ROOT 'build' }
$RESOURCES_DIR = Join-Path $PROJECT_ROOT 'resources'
$ICON_PATH = Join-Path $RESOURCES_DIR 'branding\codex_aura.ico'

if (-not (Test-Path -LiteralPath $PYTHON)) {
    throw "未找到虚拟环境：$PYTHON。请先执行 .\setup.ps1"
}
if (-not (Test-Path -LiteralPath $ICON_PATH)) {
    throw "未找到应用图标：$ICON_PATH"
}

# 防止 PyInstaller 从调用终端的 Anaconda PATH 误收集 ICU DLL。
# PySide6 在此项目的 Python 3.11 环境中使用 Windows 自带 ICU；混入
# Anaconda 的 ICU 73 会让冻结后的 QtCore 在启动时出现 DLL 入口点错误。
# 目标是标准 Windows 桌面发布环境；避免受调用终端缺失 WINDIR/SystemRoot
# 环境变量影响构建可复现性。
$windows_root = 'C:\Windows'
$path_entries = New-Object System.Collections.Generic.List[string]
$path_entries.Add((Split-Path -Parent $PYTHON))
$path_entries.Add((Join-Path $windows_root 'System32'))
$path_entries.Add($windows_root)
$env:PATH = [string]::Join(';', $path_entries)

if ($Clean) {
    Remove-Item -LiteralPath $DIST_DIR -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $BUILD_DIR -Recurse -Force -ErrorAction SilentlyContinue
}

& $PYTHON -m PyInstaller --noconfirm --clean --windowed `
    --name CodexAura `
    --distpath $DIST_DIR `
    --workpath $BUILD_DIR `
    --specpath $PROJECT_ROOT `
    --paths (Join-Path $PROJECT_ROOT 'src') `
    --add-data "$(Join-Path $PROJECT_ROOT 'backend');backend" `
    --add-data "$RESOURCES_DIR;resources" `
    --icon $ICON_PATH `
    --exclude-module PySide6.QtPdf `
    --exclude-module PySide6.QtQml `
    --exclude-module PySide6.QtQuick `
    --exclude-module PySide6.QtWebEngineCore `
    --exclude-module PySide6.QtWebEngineWidgets `
    --collect-all shiboken6 `
    (Join-Path $PROJECT_ROOT 'app_launcher.py')
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller 构建失败，退出码：$LASTEXITCODE"
}

$APP = Join-Path $DIST_DIR 'CodexAura\CodexAura.exe'
if (-not (Test-Path -LiteralPath $APP)) {
    throw "未找到构建产物：$APP"
}

if (-not $NoSlim) {
    # 该工具只导入 QtCore/QtGui/QtWidgets。PyInstaller 的 PySide6 hook 仍会
    # 收集 Quick/QML/PDF 等未使用模块；在冻结输出中显式裁剪，再由下面的
    # 真正 EXE 冒烟测试兜底，便携 Node 与 WebP 图像插件保持不动。
    $internal = Join-Path (Split-Path -Parent $APP) '_internal'
    $unusedQtFiles = @(
        'PySide6\Qt6Pdf.dll',
        'PySide6\Qt6Qml.dll',
        'PySide6\Qt6QmlMeta.dll',
        'PySide6\Qt6QmlModels.dll',
        'PySide6\Qt6QmlWorkerScript.dll',
        'PySide6\Qt6Quick.dll',
        'PySide6\Qt6VirtualKeyboard.dll'
    )
    $unusedQtDirectories = @(
        'PySide6\translations',
        'PySide6\plugins\tls',
        'PySide6\plugins\networkinformation',
        'PySide6\plugins\platforminputcontexts'
    )
    foreach ($relative in $unusedQtFiles) {
        $path = Join-Path $internal $relative
        Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
    }
    foreach ($relative in $unusedQtDirectories) {
        $path = Join-Path $internal $relative
        Remove-Item -LiteralPath $path -Recurse -Force -ErrorAction SilentlyContinue
    }
    Write-Host '已裁剪未使用的 Qt Quick/QML/PDF、翻译与网络插件；如需完整 Qt 资源可使用 -NoSlim。'
}

$env:QT_QPA_PLATFORM = 'offscreen'
& $APP --smoke-test
if ($LASTEXITCODE -ne 0) {
    throw "打包后的 GUI 启动自检失败，退出码：$LASTEXITCODE"
}

Write-Host "构建完成：$APP"
