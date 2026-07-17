from __future__ import annotations

from pathlib import Path

from .bridge import PowerShellBridge
from .models import RuntimeStatus, ThemeRecord


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

    def activate_with_status(self, theme: ThemeRecord) -> tuple[ThemeRecord, RuntimeStatus]:
        """切换活动主题后立即读取连接状态，供 GUI 说明是否会热切换。"""

        active = self.activate(theme)
        return active, self.status()

    def import_and_activate(self, image_path: Path, name: str) -> ThemeRecord:
        return ThemeRecord.from_payload(
            self.bridge.invoke("import", ImagePath=str(image_path), Name=name), source="active"
        )

    def save_current(self, name: str) -> ThemeRecord:
        return ThemeRecord.from_payload(self.bridge.invoke("save", Name=name), source="saved")

    def apply(self) -> str:
        return str(self.bridge.invoke("apply").get("message") or "已请求应用主题。")

    def verify(self) -> str:
        return str(self.bridge.invoke("verify", timeout=120).get("message") or "验证已完成。")
