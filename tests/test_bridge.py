from pathlib import Path

from codex_theme_manager.bridge import PowerShellBridge


def test_bridge_builds_noninteractive_json_command():
    bridge = PowerShellBridge(Path(r"C:\\CodexDreamSkinManager\\backend"))

    command = bridge.build_command("list")

    assert command[0].lower().endswith("powershell.exe")
    assert "-NoProfile" in command
    assert "-File" in command
    assert command[-1] == "list"


def test_bridge_rejects_unknown_operation_before_spawning_process():
    bridge = PowerShellBridge(Path(r"C:\\CodexDreamSkinManager\\backend"))

    try:
        bridge.build_command("erase-all")
    except ValueError as exc:
        assert "Unsupported" in str(exc)
    else:
        raise AssertionError("unknown bridge operation must be rejected")


def test_bridge_exports_a_bundled_node_runtime_when_available(tmp_path):
    backend = tmp_path / "backend"
    node = backend / "runtime" / "node" / "node.exe"
    node.parent.mkdir(parents=True)
    node.touch()
    bridge = PowerShellBridge(backend)

    assert bridge.build_environment()["CODEX_DREAM_SKIN_NODE"] == str(node)


def test_bridge_emits_powershell_switch_only_when_explicitly_enabled():
    bridge = PowerShellBridge(Path(r"C:\\CodexDreamSkinManager\\backend"))

    without_restart = bridge.build_command("apply", RestartExisting=False)
    with_restart = bridge.build_command("apply", RestartExisting=True)

    assert "-RestartExisting" not in without_restart
    assert "-RestartExisting" in with_restart
    assert with_restart[-2:] == ["-Operation", "apply"]
