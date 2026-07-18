from pathlib import Path

from codex_theme_manager.models import ThemeRecord
from codex_theme_manager.service import ThemeService


def _theme_payload(*, source: str = "saved") -> dict:
    return {
        "directory": r"C:\\themes\\saved" if source == "saved" else r"C:\\themes\\active",
        "imagePath": r"C:\\themes\\art.png",
        "theme": {
            "id": "purple-night",
            "name": "紫夜",
            "appearance": "dark",
            "image": "art.png",
            "art": {"focusX": 0.78, "focusY": 0.53, "safeArea": "left", "taskMode": "ambient"},
            "palette": {"accent": "#B872FF"},
        },
    }


class _Bridge:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self._statuses = iter(
            [
                {
                    "injectorRunning": False,
                    "watcherAlive": True,
                    "cdpReady": False,
                    "state": {"injectorPid": 1234, "port": 9335},
                    "message": "历史会话已停止",
                },
                {
                    "injectorRunning": True,
                    "watcherAlive": True,
                    "cdpReady": True,
                    "state": {"injectorPid": 5678, "port": 9335},
                    "message": "已连接",
                },
            ]
        )

    def invoke(self, operation: str, **kwargs):
        self.calls.append(operation)
        if operation == "activate":
            return _theme_payload()
        if operation == "status":
            return next(self._statuses)
        if operation == "apply":
            return {"message": "重新连接完成"}
        raise AssertionError(f"unexpected operation: {operation}")


def test_activate_and_sync_reconnects_after_a_stale_watcher():
    service = ThemeService(Path("backend"))
    bridge = _Bridge()
    service.bridge = bridge  # type: ignore[assignment]
    theme = ThemeRecord.from_payload(_theme_payload(), source="saved")

    result = service.activate_and_sync(theme)

    assert result.active.name == "紫夜"
    assert result.reconnected is True
    assert result.status.injector_running is True
    assert bridge.calls == ["activate", "status", "apply", "status"]


def test_activate_and_sync_keeps_a_live_watcher_without_restarting_codex():
    service = ThemeService(Path("backend"))

    class LiveBridge(_Bridge):
        def __init__(self) -> None:
            self.calls = []
            self._statuses = iter(
                [
                    {
                        "injectorRunning": True,
                        "watcherAlive": True,
                        "cdpReady": True,
                        "state": {"injectorPid": 5678, "port": 9335},
                        "message": "已连接",
                    }
                ]
            )

    bridge = LiveBridge()
    service.bridge = bridge  # type: ignore[assignment]
    theme = ThemeRecord.from_payload(_theme_payload(), source="saved")

    result = service.activate_and_sync(theme)

    assert result.reconnected is False
    assert bridge.calls == ["activate", "status"]
