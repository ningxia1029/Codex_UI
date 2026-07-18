# Codex Aura

> 一个 Windows 本地主题工作台：为 Codex Dream Skin 提供主题库、匿名预览、连接状态和便携式交付。

**Codex Aura 不是 OpenAI 官方产品，也不会修改 WindowsApps、Codex 安装包或 `app.asar`。**

![Codex Aura icon](./resources/branding/codex_aura_icon.png)

## v0.4.2（测试版）

- 三栏改为连续玻璃层：移除左右分隔实线，分区只通过留白、轻微透明度与极弱外壳边缘识别，避免“卡片套卡片”的割裂感。
- “设置 → 调整显示参数”新增 **壁纸透明度**（15%–100%）与 **整体主题颜色**；两项写入主题 JSON，本地预览和已连接 Codex 共用相同配置。
- 整体主题颜色负责环境底色与玻璃表面基调，强调色继续只用于选中态、按钮和交互焦点。

## v0.4.1

- 工作台升级为 **Aurora Glass Theme Studio**：深蓝极光环境层、弱边界玻璃外壳、低噪声阅读区和更清晰的前中后景层级。
- 中央预览改为独立舞台，匿名模拟 Codex 首页/任务页；预览不读取项目、任务、路径或对话。
- 左侧主题库、中央预览和右侧主题检查器使用一致的圆角、间距、字体和选中态，减少重复描边与“卡片套卡片”。
- 运行记录默认折叠为状态抽屉，主界面优先展示主题选择与预览。
- 壁纸在 Qt 绘制层缓存，避免窗口重绘时重复解码原始图片；极光效果使用静态渐变模拟，不依赖持续实时模糊。

> v0.4.1 将“需要重新连接 Codex”的确认移至工作台主窗口。后台 PowerShell 不再弹出隐藏确认框；你拒绝确认时，本次主题和 Codex 都不会改变。

## v0.3.0

- 无白边的三栏玻璃工作台，使用原生高 DPI 字体和更紧凑的层级。
- 中央匿名模拟 Codex 首页/任务页：不读取、显示或上传本地项目、任务、路径或对话。
- **应用主题并同步 Codex** 会先写入活动主题，再验证 watcher 与 loopback CDP；旧连接失效时会请求受控重连，不再把“主题已保存”误当作“热切换成功”。
- 主题显示编辑器可调整壁纸焦点、文字安全区、明暗模式、任务页模式与强调色；Qt 本地预览和真实 Codex 使用同一焦点裁切语义。
- “帮助 → 主题连接诊断”可查看 watcher、CDP、验证记录与推荐恢复动作。
- 新增 Codex Aura 原创狐狸月牙 EXE 图标与窗口图标。
- 发布包携带可选 Node.js 运行时，目标电脑可开箱运行，无需自行安装 Python 或 Node.js。

## 使用方式

最新便携版请从 [GitHub Releases](https://github.com/ningxia1029/Codex_UI/releases/latest) 下载。

### 第一次使用

1. 解压完整便携包，保留 `CodexAura.exe` 同级的 `_internal` 目录。
2. 启动 `CodexAura.exe`。
3. 选择主题，在 **设置 → 应用主题并同步 Codex** 中设为活动主题。
4. 首次连接时按提示确认一次受控重连；以后连接健康时切换不会关闭 Codex。

首次连接时，如果 Codex 正在以普通方式运行，后端会提示一次重启；这是为了让它使用仅绑定 `127.0.0.1` 的本地调试端口。以后在连接仍有效时，切换主题不会关闭 Codex。

### 日常换主题

1. 从左侧选择主题并预览。
2. 打开 **设置**，点击 **应用主题并同步 Codex**。
3. 状态显示“已连接”时，主题会由现有 watcher 自动同步到当前 Codex 窗口；若连接已停止，该操作会请求一次受控恢复。

如果状态显示“未连接”，可直接再次点击 **应用主题并同步 Codex**，或在设置中使用 **连接 / 重新连接 Codex**。使用 **帮助 → 主题连接诊断** 可确认是 watcher 还是 CDP 端点失效。

## 源码运行

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

源码仓库不提交 `node.exe`；源码运行时请在 `PATH` 中提供 Node.js 22+，或者优先使用
GitHub Release 中的 `portable-node` 便携包。

运行测试：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

构建 Windows `onedir` 便携版：

```powershell
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1 -Clean
```

## 便携包与体积

- 标准 `onedir` 包：包含 Python、PySide6 和后端，目标电脑不需要 Python。
- `portable-node` 包：另带约 86 MiB 的 Node.js 运行时，目标电脑也不需要 Node.js；这是完全开箱即用的推荐交付物。
- Node.js 二进制不提交到 Git，发布脚本/本机构建时从受控的 `backend/runtime/node/` 目录收集。

## 安全边界

- CDP 仅监听 `127.0.0.1`；主题会话运行时不要执行不可信的本机程序。
- “完全恢复 Codex”会关闭主题会话并恢复原生外观。
- 本地预览仅是 Qt 绘制的模拟界面，不会注入 CSS 或读取真实 Codex 数据。

## 引用与许可

Windows 主题桥接派生自 [Fei-Away/Codex-Dream-Skin](https://github.com/Fei-Away/Codex-Dream-Skin)（MIT；固定上游提交见 [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md)）。完整第三方声明、Node.js 与 PySide6 / Qt 许可边界见该文件。
