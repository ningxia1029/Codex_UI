from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
import json
from typing import Mapping

from .bridge import PowerShellBridge
from .models import RuntimeStatus, ThemeRecord


@dataclass(frozen=True)
class ThemeSyncResult:
    """一次主题切换后的真实连接状态。

    ``reconnected`` 为真表示原 watcher 不可用，本次已成功建立新的已验证会话；
    它不是“仅写入了主题文件”的乐观标记。
    """

    active: ThemeRecord
    status: RuntimeStatus
    reconnected: bool


class ReconnectRequired(RuntimeError):
    """主题操作需要重启 Codex，但界面尚未取得用户明确许可。"""

    def __init__(self, status: RuntimeStatus) -> None:
        super().__init__("Codex 当前未处于可热修改的主题会话；请确认后重新连接。")
        self.status = status


class ThemeService:
    def __init__(self, backend_root: Path) -> None:
        self.bridge = PowerShellBridge(backend_root)

    def list_themes(self) -> tuple[ThemeRecord | None, list[ThemeRecord]]:
        payload = self.bridge.invoke("list")
        active_payload = payload.get("active")
        active = ThemeRecord.from_payload(active_payload, source="active") if active_payload else None
        saved = [ThemeRecord.from_payload(item, source="saved") for item in payload.get("saved", [])]
        return active, saved

    def status(self) -> RuntimeStatus:
        return RuntimeStatus.from_payload(self.bridge.invoke("status"))

    def activate(self, theme: ThemeRecord) -> ThemeRecord:
        if theme.directory is None:
            raise ValueError("当前活动主题不能作为已保存主题重新切换。")
        return ThemeRecord.from_payload(
            self.bridge.invoke("activate", ThemeDirectory=str(theme.directory)), source="active"
        )

    def _ensure_live_connection(
        self, *, before: RuntimeStatus | None = None, allow_restart: bool = False
    ) -> tuple[RuntimeStatus, bool]:
        """只在验证失败时重新连接，避免热切换时不必要地重启 Codex。"""

        before = before or self.status()
        if before.paused or before.injector_running:
            return before, False

        if not allow_restart:
            raise ReconnectRequired(before)
        self.apply(restart_existing=True)
        after = self.status()
        return after, after.injector_running

    def activate_and_sync(self, theme: ThemeRecord, *, allow_restart: bool = False) -> ThemeSyncResult:
        """切换主题并确保它不会停留在未连接的假成功状态。"""

        before = self.status()
        if not before.paused and not before.injector_running and not allow_restart:
            raise ReconnectRequired(before)
        active = self.activate(theme) if theme.source != "active" else theme
        status, reconnected = self._ensure_live_connection(before=before, allow_restart=allow_restart)
        return ThemeSyncResult(active=active, status=status, reconnected=reconnected)

    def activate_with_status(self, theme: ThemeRecord) -> tuple[ThemeRecord, RuntimeStatus]:
        """兼容 v0.2 调用方；新界面应使用 ``activate_and_sync``。"""

        result = self.activate_and_sync(theme)
        return result.active, result.status

    def import_and_activate(self, image_path: Path, name: str) -> ThemeRecord:
        return ThemeRecord.from_payload(
            self.bridge.invoke("import", ImagePath=str(image_path), Name=name), source="active"
        )

    def import_and_sync(self, image_path: Path, name: str, *, allow_restart: bool = False) -> ThemeSyncResult:
        before = self.status()
        if not before.paused and not before.injector_running and not allow_restart:
            raise ReconnectRequired(before)
        active = self.import_and_activate(image_path, name)
        status, reconnected = self._ensure_live_connection(before=before, allow_restart=allow_restart)
        return ThemeSyncResult(active=active, status=status, reconnected=reconnected)

    def configure_and_sync(
        self, theme: ThemeRecord, options: Mapping[str, object], *, allow_restart: bool = False
    ) -> ThemeSyncResult:
        """切换（若需要）并写入活动主题的展示参数。"""

        initial = self.activate_and_sync(theme, allow_restart=allow_restart)
        payload = self.bridge.invoke(
            "configure",
            ThemeOptionsJson=json.dumps(dict(options), ensure_ascii=False, separators=(",", ":")),
        )
        active = ThemeRecord.from_payload(payload, source="active")
        return ThemeSyncResult(active=active, status=self.status(), reconnected=initial.reconnected)

    def save_current(self, name: str) -> ThemeRecord:
        return ThemeRecord.from_payload(self.bridge.invoke("save", Name=name), source="saved")

    def apply(self, *, restart_existing: bool = False) -> str:
        return str(
            self.bridge.invoke("apply", RestartExisting=restart_existing, timeout=120).get("message")
            or "已请求应用主题。"
        )

    def verify(self) -> str:
        return str(self.bridge.invoke("verify", timeout=120).get("message") or "验证已完成。")

    def diagnose(self) -> dict:
        return self.bridge.invoke("diagnose")
