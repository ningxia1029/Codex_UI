from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from typing import Any


class BackendError(RuntimeError):
    """The existing Dream Skin backend rejected or could not finish an operation."""


class PowerShellBridge:
    """Non-interactive JSON bridge to the bundled PowerShell backend."""

    _OPERATIONS = {"list", "status", "activate", "import", "save", "apply", "verify", "restore"}

    def __init__(self, backend_root: Path, powershell: str | None = None) -> None:
        self.backend_root = Path(backend_root)
        self.script_path = self.backend_root / "theme-bridge.ps1"
        self.bundled_node_path = self.backend_root / "runtime" / "node" / "node.exe"
        self.powershell = powershell or os.path.join(
            os.environ.get("WINDIR", r"C:\\Windows"), "System32", "WindowsPowerShell", "v1.0", "powershell.exe"
        )

    def build_command(self, operation: str, **parameters: str) -> list[str]:
        if operation not in self._OPERATIONS:
            raise ValueError(f"Unsupported backend operation: {operation}")
        command = [self.powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(self.script_path)]
        for key, value in parameters.items():
            if value is not None:
                command.extend([f"-{key}", str(value)])
        command.extend(["-Operation", operation])
        return command

    def build_environment(self) -> dict[str, str]:
        """让后端优先使用随发布包携带的 Node，而不依赖用户 PATH。"""

        environment = os.environ.copy()
        if self.bundled_node_path.is_file():
            environment["CODEX_DREAM_SKIN_NODE"] = str(self.bundled_node_path)
        return environment

    def invoke(self, operation: str, *, timeout: int = 90, **parameters: str) -> dict[str, Any]:
        completed = subprocess.run(
            self.build_command(operation, **parameters),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            env=self.build_environment(),
        )
        lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
        try:
            payload = json.loads(lines[-1]) if lines else {}
        except json.JSONDecodeError as exc:
            raise BackendError(f"后端未返回有效 JSON：{completed.stdout or completed.stderr}") from exc

        if completed.returncode != 0 or not payload.get("ok"):
            detail = payload.get("error") or completed.stderr or completed.stdout or "未知后端错误"
            raise BackendError(str(detail).strip())
        return dict(payload.get("data") or {})
