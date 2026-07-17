from pathlib import Path

from codex_theme_manager.runtime import backend_root, resource_root


def test_backend_root_uses_project_backend_when_running_from_source(monkeypatch):
    monkeypatch.delenv("CODEX_THEME_MANAGER_BACKEND", raising=False)

    root = backend_root(frozen_root=None)

    assert root.name == "backend"
    assert (root / "theme-bridge.ps1").name == "theme-bridge.ps1"


def test_backend_root_respects_explicit_manager_backend(monkeypatch):
    expected = Path(r"C:\\custom\\backend")
    monkeypatch.setenv("CODEX_THEME_MANAGER_BACKEND", str(expected))

    assert backend_root(frozen_root=None) == expected


def test_resource_root_uses_the_frozen_payload_root_when_provided():
    frozen_root = Path(r"C:\CodexAura\_internal")

    assert resource_root(frozen_root=frozen_root) == frozen_root / "resources"
