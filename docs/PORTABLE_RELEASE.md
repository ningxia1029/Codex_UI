# Codex Aura 便携版说明

## 新电脑是否可以直接使用？

可以。下载完整 `portable-node` ZIP，解压后直接运行：

```text
CodexAura.exe
_internal/
```

其中 `_internal/backend/runtime/node/node.exe` 是随包携带的 Node.js 运行时，
因此目标电脑不需要另行安装 Python 或 Node.js。不要把 EXE 单独拖出该目录。

## 第一次连接

Codex Aura 不修改官方 Codex 安装目录。第一次点击“连接 / 重新连接 Codex”时，
如果 Codex 目前以普通方式启动，底层后端会提示一次重启，以便建立仅绑定
`127.0.0.1` 的 CDP 主题会话。确认后连接完成。

## 日常换主题

状态栏显示“已连接”时，在设置中点击“切换到此主题”即可；现有 watcher 会监听
活动主题并同步到当前 Codex，不需要关闭 Codex。

如果状态为“未连接”，主题仍会保存为当前主题；重新连接一次后即可恢复热切换。

## 文件校验

发布目录中的 `SHA256SUMS.txt` 用于核验 ZIP 文件。下载来源、大小或 SHA256 不匹配
时不要运行程序。
