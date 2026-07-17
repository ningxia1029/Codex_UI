from __future__ import annotations

import os
from pathlib import Path
import sys


def backend_root(*, frozen_root: Path | None = None) -> Path:
    """定位随源码或 PyInstaller ``onedir`` 包一同发布的后端目录。"""

    configured = os.environ.get("CODEX_THEME_MANAGER_BACKEND")
    if configured:
        return Path(configured).expanduser()

    if frozen_root is not None:
        return frozen_root / "backend"

    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS")) / "backend"

    return Path(__file__).resolve().parents[2] / "backend"


def resource_root(*, frozen_root: Path | None = None) -> Path:
    """定位随源码或冻结包一起发布的品牌资源目录。"""

    if frozen_root is not None:
        return frozen_root / "resources"

    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS")) / "resources"

    return Path(__file__).resolve().parents[2] / "resources"
