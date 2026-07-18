# Changelog

All notable changes to Codex Aura are documented here.

## 0.4.2 - 2026-07-18

### Added

- 主题显示编辑器新增壁纸透明度滑杆和整体主题颜色选择器；配置保存到 `art.opacity`、`palette.themeColor`，并同步到本地预览与 Codex 注入 CSS。

### Changed

- 工作台三栏取消可见的硬分隔线和重复卡片描边，改用 10px 留白分隔、低透明度玻璃层与单一弱外壳边缘。
- 深色 Codex 注入主题以整体主题颜色建立画布、阅读面和侧栏的统一基调；壁纸显示强度由透明度参数控制。

## 0.4.1 - 2026-07-18

### Fixed

- 修复断连后“应用主题”在隐藏 PowerShell 中等待 COM 确认框、最终触发 90 秒超时的问题。
- 重新连接确认改由 Qt 主窗口展示；用户取消时不启动后台重连，也不修改活动主题。
- 后端 `apply` 改为无交互协议：只有 Qt 已明确确认时才传入 `-RestartExisting`。
- PowerShell 运行超时改为可读错误信息，不再向用户展示 Python `subprocess` 命令文本。

### Build

- `build_exe.ps1` 支持 `-Python`、`-DistDir`、`-WorkDir`，可用隔离发布环境构建新测试目录而不覆盖旧包。

## 0.4.0 - 2026-07-18

### Added

- Aurora Glass Theme Studio 视觉系统：深蓝极光环境层、弱描边玻璃外壳与统一的空间层级。
- 独立预览舞台与折叠式运行记录抽屉，主视图聚焦主题选择、匿名预览与检查器。

### Changed

- 重设三栏工作台的字体、圆角、间距、按钮、主题选中态与检查器样式，减少重复边框和高饱和青蓝色抢占焦点的问题。
- 主题壁纸改为在 Qt 绘制层缓存；背景环境光由静态渐变绘制，避免重绘时重复加载图片或使用持续实时模糊。
- 本地 Codex 模拟预览的文字和层级更接近当前桌面端的安静深色工作区，但不读取真实数据。

### Safety

- 本版不修改 Dream Skin 注入、CDP、主题 JSON 或 Codex 进程控制逻辑；已知的断连后受控重连交互问题仍单独跟踪。

## 0.3.0 - 2026-07-18

### Added

- 主题显示编辑器：可调整明暗模式、壁纸焦点、文字安全区、任务页模式和强调色；设置写入活动主题并由 watcher 同步。
- “主题连接诊断”窗口：区分 watcher 存活、CDP 端点、活动连接和最近验证记录，可一键复制诊断文本。
- watcher 失去 CDP 端点后会安全退役自身 state，避免留下“Node 仍在、主题已无法热同步”的孤儿记录。
- 注入验证增加输入框与侧栏是否仍完整位于视口内的布局检查。

### Changed

- **应用主题并同步 Codex** 现在是一次事务：切换主题后立即验证连接；若 watcher 已失效，会请求一次受控重新连接，而不再静默停在“主题已切换”。
- 即使当前选择已经是活动主题，仍可执行同步/恢复连接，不再因 no-op 阻断热修改。
- 本地 Qt 预览使用与真实 CSS `background-position` 相同的壁纸焦点裁切规则。
- 首页 CSS 去除固定纵向 flex 占位，改为容器边界约束，降低 Codex 更新或 100%–200% DPI 缩放后的输入框/英雄区错位风险。

### Fixed

- 修复 Codex 关闭或 CDP 消失后旧 watcher 长时间留在 `state.json` 的恢复路径。
- 修复主题工作台预览一直居中裁切壁纸、与实际 Codex 焦点不一致的问题。
- 修复 PowerShell 5.1 将日志行扩展为提供程序对象、导致“主题连接诊断”输出膨胀或长时间无响应的问题。

### Known limits

- 如果 Codex 被以普通方式完全退出后重新打开，它不会自行携带 CDP 参数；下一次“应用主题并同步 Codex”会显示一次受控重连/重启确认。这是 Chromium 调试端口的安全边界，而不是可静默绕过的限制。

## 0.2.0 - 2026-07-17

### Added

- New Codex Aura fox-and-crescent EXE/window icon.
- High-DPI dark glass workspace with a seamless three-column layout.
- Anonymous Codex-like home and task previews with no project, path, or chat data.
- Explicit connection status: the UI only says a theme will hot-switch when the
  saved watcher process and loopback CDP endpoint are both verified.
- Portable Node.js runtime support for computers without a global Node.js install.
- `THIRD_PARTY_NOTICES.md` and an upstream attribution / license boundary.
- Original abstract Aurora fallback wallpaper; upstream portrait/IP demo assets are
  intentionally excluded from the public source and release package.

### Changed

- Renamed the product display name from “Codex 主题工作台” to “Codex Aura”.
- Replaced ambiguous “保存当前主题” with “保存到主题库”.
- Replaced overlapping “设为当前主题 / 应用到 Codex” actions with:
  - **切换到此主题**: writes the active theme and hot-syncs when connected.
  - **连接 / 重新连接 Codex**: establishes or repairs the local CDP session.
- PyInstaller output is now fixed to the project-local `build/` and `dist/` paths.
- Default release pruning removes unused Qt Quick/QML/PDF resources while keeping
  WebP support, portable Node.js and the OpenGL software fallback.

### Fixed

- Stale `state.json` can no longer make the GUI claim that a dead watcher is connected.
- Build no longer writes output into the caller's current directory.

### Known limits

- First connection may require closing/restarting Codex once to add the loopback
  CDP flag. Normal live theme switches do not require a restart while status is
  “已连接”.
- The generated app icon is original branding artwork; theme wallpapers supplied
  by users are not redistributed by this project.
