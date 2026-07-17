# Changelog

All notable changes to Codex Aura are documented here.

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
