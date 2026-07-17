# Codex Aura

> 一个 Windows 本地主题工作台：为 Codex Dream Skin 提供主题库、匿名预览、连接状态和便携式交付。

**Codex Aura 不是 OpenAI 官方产品，也不会修改 WindowsApps、Codex 安装包或 `app.asar`。**

![Codex Aura icon](./resources/branding/codex_aura_icon.png)

## v0.2.0

- 无白边的三栏玻璃工作台，使用原生高 DPI 字体和更紧凑的层级。
- 中央匿名模拟 Codex 首页/任务页：不读取、显示或上传本地项目、任务、路径或对话。
- 主题“切换”和“连接”语义分离：已连接时切换活动主题会由 watcher 自动同步；首次连接或连接停止时才需连接 / 重连 Codex。
- 新增 Codex Aura 原创狐狸月牙 EXE 图标与窗口图标。
- 发布包携带可选 Node.js 运行时，目标电脑可开箱运行，无需自行安装 Python 或 Node.js。

## 使用方式

### 第一次使用

1. 解压完整便携包，保留 `CodexAura.exe` 同级的 `_internal` 目录。
2. 启动 `CodexAura.exe`。
3. 选择主题，在 **设置 → 切换到此主题** 中设为活动主题。
4. 在 **设置 → 连接 / 重新连接 Codex** 中建立首次 CDP 连接。

首次连接时，如果 Codex 正在以普通方式运行，后端会提示一次重启；这是为了让它使用仅绑定 `127.0.0.1` 的本地调试端口。以后在连接仍有效时，切换主题不会关闭 Codex。

### 日常换主题

1. 从左侧选择主题并预览。
2. 打开 **设置**，点击 **切换到此主题**。
3. 状态显示“已连接”时，主题会由现有 watcher 自动同步到当前 Codex 窗口。

如果状态显示“未连接”，主题仍已保存为当前主题；点击 **连接 / 重新连接 Codex** 即可恢复同步能力。

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
