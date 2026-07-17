from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class ThemeRecord:
    """A theme exposed by the existing PowerShell theme store."""

    id: str
    name: str
    image_path: Path
    directory: Path | None
    appearance: str
    accent: str | None
    source: str
    subtitle: str = ""
    tagline: str = ""

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any], *, source: str) -> "ThemeRecord":
        theme = payload.get("theme") or {}
        if not isinstance(theme, Mapping):
            raise ValueError("Theme payload must contain a theme object.")

        theme_id = str(theme.get("id") or "custom")
        image_value = payload.get("imagePath") or theme.get("image")
        if not image_value:
            raise ValueError("Theme payload does not include an image path.")

        palette = theme.get("palette") or {}
        accent = palette.get("accent") if isinstance(palette, Mapping) else None
        directory = payload.get("directory")
        return cls(
            id=theme_id,
            name=str(theme.get("name") or theme_id),
            image_path=Path(str(image_value)),
            directory=Path(str(directory)) if directory else None,
            appearance=str(theme.get("appearance") or "auto"),
            accent=str(accent) if accent else None,
            source=source,
            subtitle=str(theme.get("brandSubtitle") or ""),
            tagline=str(theme.get("tagline") or ""),
        )


def visible_themes(active: ThemeRecord | None, saved: list[ThemeRecord]) -> list[ThemeRecord]:
    """返回用于主题库展示的去重列表，并始终把当前主题排在第一位。

    现有 PowerShell 后端会同时把当前主题写入 ``active`` 和保存主题库。
    这里仅处理展示层，绝不修改后端保存的数据，避免用户看到同一主题两次。
    """

    result: list[ThemeRecord] = []
    seen: set[tuple[str, str]] = set()

    def identity(theme: ThemeRecord) -> tuple[str, str]:
        return (
            theme.name.strip().casefold(),
            str(theme.image_path).replace("/", "\\").casefold(),
        )

    for theme in ([active] if active else []) + saved:
        key = identity(theme)
        if key in seen:
            continue
        seen.add(key)
        result.append(theme)
    return result


@dataclass(frozen=True)
class RuntimeStatus:
    paused: bool
    active_name: str | None
    injector_running: bool
    port: int | None
    message: str

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "RuntimeStatus":
        active = payload.get("active") or {}
        theme = active.get("theme") if isinstance(active, Mapping) else {}
        state = payload.get("state") or {}
        # 新版后端会同时验证记录的 watcher 进程与 loopback CDP 端点，并显式
        # 返回 injectorRunning。旧版 payload 没有该键时，才回退到历史 state。
        running_value = payload.get("injectorRunning")
        injector_running = (
            bool(running_value)
            if running_value is not None
            else bool(state.get("injectorPid")) if isinstance(state, Mapping) else False
        )
        return cls(
            paused=bool(payload.get("paused")),
            active_name=str(theme.get("name")) if isinstance(theme, Mapping) and theme.get("name") else None,
            injector_running=injector_running,
            port=int(state["port"]) if isinstance(state, Mapping) and state.get("port") else None,
            message=str(payload.get("message") or "状态已刷新"),
        )


def describe_theme_switch(status: RuntimeStatus) -> str:
    """把“切换主题”和“首次建立 CDP 连接”两种状态明确区分给界面。"""

    if status.paused:
        return "主题已切换；当前连接处于暂停状态，请在设置中重新连接 Codex。"
    if status.injector_running:
        return "主题已切换；活动的 Codex 连接会自动同步，通常无需关闭窗口。"
    return "主题已设为当前；首次连接或连接已停止时，请在设置中连接 Codex。"
