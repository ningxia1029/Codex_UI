from codex_theme_manager.models import RuntimeStatus, ThemeRecord, describe_theme_switch, visible_themes


def test_theme_record_accepts_backend_payload_with_palette_and_image():
    record = ThemeRecord.from_payload(
        {
            "theme": {
                "id": "kuromi-purple-night",
                "name": "库洛米紫夜",
                "appearance": "dark",
                "image": "art.png",
                "art": {"focusX": 0.78, "focusY": 0.53, "safeArea": "left", "taskMode": "ambient"},
                "palette": {"accent": "#B872FF"},
            },
            "imagePath": r"C:\\theme\\art.png",
            "directory": r"C:\\theme",
        },
        source="saved",
    )

    assert record.id == "kuromi-purple-night"
    assert record.name == "库洛米紫夜"
    assert record.image_path.name == "art.png"
    assert record.accent == "#B872FF"
    assert record.focus_x == 0.78
    assert record.focus_y == 0.53
    assert record.safe_area == "left"
    assert record.task_mode == "ambient"
    assert record.source == "saved"


def test_theme_record_uses_safe_fallbacks_for_partial_legacy_payload():
    record = ThemeRecord.from_payload({"theme": {"id": "legacy", "image": "art.jpg"}}, source="active")

    assert record.name == "legacy"
    assert record.appearance == "auto"
    assert record.accent is None


def test_visible_themes_deduplicates_the_active_theme_from_saved_library():
    active = ThemeRecord.from_payload(
        {"theme": {"id": "active", "name": "紫夜", "image": "art.png"}, "imagePath": r"C:\\themes\\art.png"},
        source="active",
    )
    duplicate = ThemeRecord.from_payload(
        {
            "theme": {"id": "saved-copy", "name": "紫夜", "image": "art.png"},
            "imagePath": r"C:\\themes\\art.png",
            "directory": r"C:\\themes\\saved",
        },
        source="saved",
    )
    other = ThemeRecord.from_payload(
        {
            "theme": {"id": "other", "name": "桥本有菜", "image": "other.jpg"},
            "imagePath": r"C:\\themes\\other.jpg",
            "directory": r"C:\\themes\\other",
        },
        source="saved",
    )

    assert visible_themes(active, [duplicate, other]) == [active, other]


def test_theme_switch_hint_distinguishes_live_sync_from_first_connection():
    live = RuntimeStatus(
        paused=False,
        active_name="Aurora",
        injector_running=True,
        port=9335,
        message="运行中",
    )
    disconnected = RuntimeStatus(
        paused=False,
        active_name="Aurora",
        injector_running=False,
        port=None,
        message="未连接",
    )

    assert "自动同步" in describe_theme_switch(live)
    assert "首次连接" in describe_theme_switch(disconnected)


def test_runtime_status_prefers_the_backend_verified_connection_flag():
    status = RuntimeStatus.from_payload(
        {
            "state": {"injectorPid": 1234, "port": 9335},
            "injectorRunning": False,
            "message": "历史会话已停止",
        }
    )

    assert status.injector_running is False
