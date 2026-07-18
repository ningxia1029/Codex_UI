from __future__ import annotations

from pathlib import Path
import sys
from typing import Callable, TypeVar

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, Signal
from PySide6.QtGui import QAction, QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from shiboken6 import isValid

from .models import RuntimeStatus, ThemeRecord, describe_theme_switch, visible_themes
from .runtime import backend_root, resource_root
from .service import ThemeService, ThemeSyncResult
from .widgets import CodexPreviewCanvas, ThemeWorkspace


APP_NAME = "Codex Aura"
APP_VERSION = "0.4.0"
T = TypeVar("T")


class WorkerSignals(QObject):
    completed = Signal(object)
    failed = Signal(str)


class BackendWorker(QRunnable):
    def __init__(self, work: Callable[[], T]) -> None:
        super().__init__()
        self.work = work
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            result = self.work()
        except Exception as exc:  # backend errors are rendered in the GUI
            if isValid(self.signals):
                self.signals.failed.emit(str(exc))
            return
        if isValid(self.signals):
            self.signals.completed.emit(result)


class ThemeEditorDialog(QDialog):
    """编辑活动主题的可见元数据，不直接触碰 Codex 的任何项目内容。"""

    def __init__(self, owner: "MainWindow", theme: ThemeRecord) -> None:
        super().__init__(owner)
        self.owner = owner
        self.theme = theme
        self.setWindowTitle("调整主题显示")
        self.setModal(True)
        self.setMinimumWidth(470)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(12)
        title = QLabel("调整主题显示")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)
        hint = QLabel("这些参数会写入当前主题，并由已连接的 watcher 自动同步到 Codex。")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        form = QFormLayout()
        form.setSpacing(10)
        self.appearance = QComboBox()
        self.appearance.addItems(["auto", "dark", "light"])
        self.appearance.setCurrentText(theme.appearance if theme.appearance in {"auto", "dark", "light"} else "auto")
        form.addRow("界面明暗", self.appearance)

        self.focus_x, focus_x_row = self._slider_row(theme.focus_x, "横向")
        form.addRow("壁纸焦点 X", focus_x_row)
        self.focus_y, focus_y_row = self._slider_row(theme.focus_y, "纵向")
        form.addRow("壁纸焦点 Y", focus_y_row)

        self.safe_area = QComboBox()
        self.safe_area.addItems(["auto", "left", "right", "center", "none"])
        self.safe_area.setCurrentText(theme.safe_area)
        form.addRow("文字安全区", self.safe_area)

        self.task_mode = QComboBox()
        self.task_mode.addItems(["auto", "ambient", "banner", "off"])
        self.task_mode.setCurrentText(theme.task_mode)
        form.addRow("任务页壁纸", self.task_mode)

        self.accent = QLineEdit(theme.accent or "")
        self.accent.setPlaceholderText("留空表示按壁纸自动取色，例如 #B872FF")
        form.addRow("强调色", self.accent)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        apply_button = buttons.addButton("保存并同步", QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.rejected.connect(self.reject)
        apply_button.clicked.connect(self._apply)
        layout.addWidget(buttons)

    def _slider_row(self, value: float | None, axis: str) -> tuple[QSlider, QWidget]:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(round((0.5 if value is None else value) * 100))
        label = QLabel()
        label.setMinimumWidth(44)
        label.setObjectName("muted")

        def update_label(number: int) -> None:
            label.setText(f"{number}%")
            slider.setToolTip(f"{axis}焦点：{number}%")

        slider.valueChanged.connect(update_label)
        update_label(slider.value())
        layout.addWidget(slider, 1)
        layout.addWidget(label)
        return slider, row

    def _apply(self) -> None:
        self.owner.configure_selected(
            self.theme,
            {
                "appearance": self.appearance.currentText(),
                "focusX": self.focus_x.value() / 100,
                "focusY": self.focus_y.value() / 100,
                "safeArea": self.safe_area.currentText(),
                "taskMode": self.task_mode.currentText(),
                "accent": self.accent.text().strip(),
            },
        )
        self.accept()


class DiagnosticsDialog(QDialog):
    """用可复制的文本展示本机连接状态，避免用户只能凭“未连接”猜测。"""

    def __init__(self, parent: QWidget, diagnostic: dict) -> None:
        super().__init__(parent)
        self.setWindowTitle("主题连接诊断")
        self.setModal(True)
        self.resize(660, 500)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        title = QLabel("主题连接诊断")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setPlainText(self._format(diagnostic))
        layout.addWidget(self.text, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        copy = buttons.addButton("复制诊断", QDialogButtonBox.ButtonRole.ActionRole)
        copy.clicked.connect(lambda: QApplication.clipboard().setText(self.text.toPlainText()))
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def _format(diagnostic: dict) -> str:
        status = diagnostic.get("status") or {}
        lines = [
            "连接状态",
            f"• 活动连接：{'是' if status.get('injectorRunning') else '否'}",
            f"• watcher 进程：{'存活' if status.get('watcherAlive') else '未存活'}",
            f"• CDP 端点：{'可验证' if status.get('cdpReady') else '不可用'}",
            f"• 端口：{(status.get('state') or {}).get('port', '—')}",
            "",
            f"建议：{diagnostic.get('recommendation') or status.get('message') or '—'}",
        ]
        logs = diagnostic.get("logs") or {}
        for title, key in (("watcher 记录", "injector"), ("错误记录", "errors"), ("最近验证", "verify")):
            entries = [str(item) for item in (logs.get(key) or []) if str(item).strip()]
            if entries:
                lines.extend(["", title, *entries])
        return "\n".join(lines)


class ThemeSettingsDialog(QDialog):
    """低频的保存、连接和验证操作；避免与“切换主题”语义重复。"""

    def __init__(self, owner: "MainWindow", theme: ThemeRecord) -> None:
        super().__init__(owner)
        self.owner = owner
        self.theme = theme
        self.setWindowTitle("主题操作")
        self.setModal(True)
        self.setMinimumWidth(430)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(10)

        title = QLabel(theme.name)
        title.setObjectName("dialogTitle")
        title.setWordWrap(True)
        layout.addWidget(title)

        details = QLabel(
            f"显示模式：{theme.appearance}\n"
            f"壁纸文件：{theme.image_path.name}\n"
            f"强调色：{theme.accent or '由壁纸自适应'}"
        )
        details.setObjectName("muted")
        details.setWordWrap(True)
        layout.addWidget(details)

        explanation = QLabel(
            "应用主题会写入当前主题并检查连接。连接已失效时，会请求一次受控重新连接；"
            "仅首次建立 CDP 会话时可能需要你确认重启 Codex。"
        )
        explanation.setObjectName("callout")
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        layout.addSpacing(4)

        activate = QPushButton("应用主题并同步 Codex")
        activate.setObjectName("primary")
        activate.clicked.connect(self._activate)
        layout.addWidget(activate)

        save = QPushButton("保存到主题库")
        save.clicked.connect(self._save)
        layout.addWidget(save)

        edit = QPushButton("调整显示参数")
        edit.clicked.connect(self._edit)
        layout.addWidget(edit)

        connect = QPushButton("连接 / 重新连接 Codex")
        connect.clicked.connect(self._connect)
        layout.addWidget(connect)

        verify = QPushButton("验证连接")
        verify.clicked.connect(self._verify)
        layout.addWidget(verify)

        close = QPushButton("关闭")
        close.clicked.connect(self.reject)
        layout.addSpacing(6)
        layout.addWidget(close)

    def _activate(self) -> None:
        self.owner.activate_selected()
        self.accept()

    def _save(self) -> None:
        self.owner.save_current()
        self.accept()

    def _edit(self) -> None:
        self.owner.open_theme_editor(self.theme)
        self.accept()

    def _connect(self) -> None:
        self.owner.connect_codex()
        self.accept()

    def _verify(self) -> None:
        self.owner.verify()
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self, service: ThemeService) -> None:
        super().__init__()
        self.service = service
        self.pool = QThreadPool.globalInstance()
        self._workers: set[BackendWorker] = set()
        self.active_theme: ThemeRecord | None = None
        self.saved_themes: list[ThemeRecord] = []
        self.status: RuntimeStatus | None = None
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        self.setWindowTitle(f"{APP_NAME} · Codex 主题工作台")
        self.setMinimumSize(1160, 720)
        self.resize(1440, 900)
        self.setStyleSheet(
            """
            QWidget {
                color: #EEF3FA;
                font-family: 'Segoe UI Variable', 'Microsoft YaHei UI', 'Segoe UI';
                font-size: 13px;
            }
            QMainWindow { background: #050915; }
            QMenuBar {
                background: rgba(6, 9, 20, 220);
                border: 0;
                border-bottom: 1px solid rgba(204, 222, 255, 15);
                padding: 4px 14px;
            }
            QMenuBar::item { background: transparent; border-radius: 8px; padding: 6px 10px; }
            QMenuBar::item:selected { background: rgba(255,255,255,15); }
            QMenu { background: #111A2B; border: 1px solid rgba(213, 226, 255, 40); padding: 6px; }
            QMenu::item { padding: 7px 24px 7px 12px; border-radius: 6px; }
            QMenu::item:selected { background: rgba(104, 153, 232, 92); }
            QLabel { background: transparent; }
            QLabel#eyebrow { color: #9FC8FF; font-size: 10px; font-weight: 700; letter-spacing: 1.2px; }
            QLabel#title { color: #FBFDFF; font-size: 22px; font-weight: 700; }
            QLabel#dialogTitle { color: #FAFCFF; font-size: 20px; font-weight: 700; }
            QLabel#muted { color: #ACB9CF; }
            QLabel#statusPill {
                color: #C3E7FF;
                background: rgba(45, 103, 145, 82);
                border: 1px solid rgba(134, 207, 255, 69);
                border-radius: 11px;
                padding: 5px 10px;
            }
            QLabel#callout {
                color: #C7D6E9;
                background: rgba(20, 34, 61, 118);
                border: 1px solid rgba(151, 185, 255, 34);
                border-left: 2px solid #77B7FF;
                border-radius: 10px;
                padding: 10px 11px;
            }
            QFrame#appShell {
                background: rgba(9, 15, 31, 176);
                border: 1px solid rgba(206, 224, 255, 48);
                border-radius: 22px;
            }
            QFrame#sideRail {
                background: rgba(8, 14, 30, 142);
                border: 0;
                border-right: 1px solid rgba(222, 234, 255, 19);
                border-top-left-radius: 21px;
                border-bottom-left-radius: 21px;
            }
            QFrame#previewRail { background: rgba(12, 19, 39, 40); border: 0; }
            QFrame#actionRail {
                background: rgba(8, 14, 30, 132);
                border: 0;
                border-left: 1px solid rgba(222, 234, 255, 19);
                border-top-right-radius: 21px;
                border-bottom-right-radius: 21px;
            }
            QFrame#inspectorCard {
                background: rgba(10, 17, 35, 112);
                border: 1px solid rgba(202, 221, 255, 24);
                border-radius: 14px;
            }
            QFrame#previewStage {
                background: rgba(4, 9, 21, 78);
                border: 1px solid rgba(204, 226, 255, 35);
                border-radius: 16px;
            }
            QFrame#activityStrip {
                background: rgba(7, 12, 27, 128);
                border: 1px solid rgba(196, 219, 245, 28);
                border-radius: 14px;
            }
            QSplitter::handle { background: rgba(255,255,255,10); width: 1px; }
            QSplitter::handle:hover { background: rgba(128, 194, 255, 98); }
            QPushButton, QToolButton {
                background: rgba(28, 48, 82, 112);
                border: 1px solid rgba(140, 181, 240, 62);
                border-radius: 10px;
                padding: 8px 12px;
                min-height: 18px;
            }
            QPushButton:hover, QToolButton:hover {
                background: rgba(56, 89, 139, 164);
                border-color: rgba(160, 213, 255, 154);
            }
            QPushButton:disabled { color: #718096; background: rgba(17, 28, 46, 130); border-color: rgba(255,255,255,20); }
            QPushButton#primary { background: rgba(49, 126, 217, 208); border-color: #8ED0FF; color: white; font-weight: 700; }
            QPushButton#primary:hover { background: rgba(67, 147, 237, 230); }
            QPushButton#danger { background: rgba(91, 29, 54, 184); border-color: rgba(244, 143, 177, 184); }
            QToolButton#viewToggle { min-width: 50px; padding: 7px 11px; }
            QToolButton#viewToggle:checked { background: rgba(65, 118, 204, 148); border-color: #9CCEFF; color: #FFFFFF; }
            QListWidget { background: transparent; border: 0; outline: none; padding: 4px 3px; }
            QListWidget::item {
                background: transparent;
                border: 0;
                border-left: 2px solid transparent;
                border-radius: 10px;
                padding: 10px 8px;
                margin: 3px 0;
            }
            QListWidget::item:hover { background: rgba(255,255,255,12); }
            QListWidget::item:selected {
                background: rgba(79, 146, 215, 112);
                border-left: 2px solid #84D6FF;
                color: #FFFFFF;
            }
            QPlainTextEdit {
                background: rgba(2, 6, 16, 126);
                border: 0;
                border-top: 1px solid rgba(255,255,255,16);
                color: #CFE0F4;
                font-family: Consolas, 'Microsoft YaHei UI', monospace;
                font-size: 11px;
                padding: 8px;
            }
            QDialog { background: #111A2B; }
            """
        )
        self._build_menu()

        root = ThemeWorkspace()
        self.workspace = root
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.setContentsMargins(6, 0, 6, 0)
        brand = QLabel("Codex Aura")
        brand.setObjectName("title")
        header.addWidget(brand)
        header.addSpacing(12)
        self.status_label = QLabel("正在读取本地主题库…")
        self.status_label.setObjectName("statusPill")
        header.addWidget(self.status_label)
        header.addStretch(1)
        center_label = QLabel("AURORA THEME STUDIO")
        center_label.setObjectName("eyebrow")
        header.addWidget(center_label)
        header.addStretch(1)
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.clicked.connect(self.refresh)
        header.addWidget(self.refresh_button)
        layout.addLayout(header)

        shell = QFrame()
        shell.setObjectName("appShell")
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter = splitter
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(1)
        splitter.setContentsMargins(0, 0, 0, 0)
        library_panel = self._build_library_panel()
        preview_panel = self._build_preview_panel()
        actions_panel = self._build_actions_panel()
        library_panel.setMinimumWidth(244)
        library_panel.setMaximumWidth(340)
        actions_panel.setMinimumWidth(244)
        actions_panel.setMaximumWidth(340)
        splitter.addWidget(library_panel)
        splitter.addWidget(preview_panel)
        splitter.addWidget(actions_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([286, 814, 292])
        shell_layout.addWidget(splitter)
        layout.addWidget(shell, 1)

        activity = QFrame()
        activity.setObjectName("activityStrip")
        self.activity_panel = activity
        log_layout = QVBoxLayout(activity)
        log_layout.setContentsMargins(12, 7, 12, 7)
        log_layout.setSpacing(4)
        log_header = QHBoxLayout()
        log_title = QLabel("运行记录")
        log_title.setObjectName("muted")
        log_header.addWidget(log_title)
        log_header.addStretch(1)
        self.log_toggle = QToolButton()
        self.log_toggle.setText("展开")
        self.log_toggle.setCheckable(True)
        self.log_toggle.setObjectName("viewToggle")
        self.log_toggle.toggled.connect(self._toggle_activity)
        log_header.addWidget(self.log_toggle)
        log_layout.addLayout(log_header)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(300)
        self.log_view.setFixedHeight(108)
        self.log_view.setVisible(False)
        log_layout.addWidget(self.log_view)
        layout.addWidget(activity)
        self.setCentralWidget(root)
        self._log("主题工作台已启动；本地预览不会展示项目、任务、路径或对话内容。")

    def _build_menu(self) -> None:
        menu = self.menuBar()
        theme_menu = menu.addMenu("主题")
        import_action = QAction("导入图片并切换", self)
        import_action.triggered.connect(self.import_image)
        theme_menu.addAction(import_action)
        save_action = QAction("保存到主题库", self)
        save_action.triggered.connect(self.save_current)
        theme_menu.addAction(save_action)
        theme_menu.addSeparator()
        theme_menu.addAction("刷新主题库", self.refresh)
        help_menu = menu.addMenu("帮助")
        help_menu.addAction("主题连接诊断", self.show_diagnostics)
        help_menu.addAction("关于 Codex Aura", self.show_about)

    def _build_library_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("sideRail")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 14)
        layout.setSpacing(8)
        title = QLabel("主题库")
        title.setObjectName("eyebrow")
        layout.addWidget(title)
        hint = QLabel("从本地主题库挑选壁纸；预览不会读取真实任务或对话。")
        hint.setWordWrap(True)
        hint.setObjectName("muted")
        layout.addWidget(hint)
        self.theme_list = QListWidget()
        self.theme_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.theme_list.setSpacing(1)
        self.theme_list.currentItemChanged.connect(self.on_theme_selected)
        layout.addWidget(self.theme_list, 1)
        import_button = QPushButton("导入主题壁纸")
        import_button.clicked.connect(self.import_image)
        layout.addWidget(import_button)
        return panel

    def _build_preview_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("previewRail")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 10)
        layout.setSpacing(7)
        top = QHBoxLayout()
        label = QLabel("本地预览")
        label.setObjectName("eyebrow")
        top.addWidget(label)
        top.addStretch(1)
        self.home_toggle = QToolButton()
        self.home_toggle.setObjectName("viewToggle")
        self.home_toggle.setText("首页")
        self.home_toggle.setCheckable(True)
        self.home_toggle.setChecked(True)
        self.home_toggle.clicked.connect(lambda: self._set_preview_mode(False))
        self.task_toggle = QToolButton()
        self.task_toggle.setObjectName("viewToggle")
        self.task_toggle.setText("任务")
        self.task_toggle.setCheckable(True)
        self.task_toggle.clicked.connect(lambda: self._set_preview_mode(True))
        top.addWidget(self.home_toggle)
        top.addWidget(self.task_toggle)
        layout.addLayout(top)
        stage = QFrame()
        stage.setObjectName("previewStage")
        stage_layout = QVBoxLayout(stage)
        stage_layout.setContentsMargins(10, 10, 10, 10)
        self.preview = CodexPreviewCanvas()
        stage_layout.addWidget(self.preview)
        layout.addWidget(stage, 1)
        hint = QLabel("匿名模拟预览 · 本地绘制，不接触真实 Codex 内容")
        hint.setObjectName("muted")
        layout.addWidget(hint)
        return panel

    def _set_preview_mode(self, task_mode: bool) -> None:
        self.home_toggle.setChecked(not task_mode)
        self.task_toggle.setChecked(task_mode)
        self.preview.set_task_mode(task_mode)

    def _build_actions_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("actionRail")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 14)
        layout.setSpacing(8)
        title = QLabel("已选主题")
        title.setObjectName("eyebrow")
        layout.addWidget(title)
        inspector = QFrame()
        inspector.setObjectName("inspectorCard")
        inspector_layout = QVBoxLayout(inspector)
        inspector_layout.setContentsMargins(13, 13, 13, 13)
        inspector_layout.setSpacing(7)
        self.theme_name = QLabel("尚未选择主题")
        self.theme_name.setWordWrap(True)
        self.theme_name.setObjectName("title")
        inspector_layout.addWidget(self.theme_name)
        self.theme_details = QLabel("读取中…")
        self.theme_details.setObjectName("muted")
        self.theme_details.setWordWrap(True)
        inspector_layout.addWidget(self.theme_details)
        layout.addWidget(inspector)
        self.action_hint = QLabel("预览不会影响 Codex；应用主题时才会检查连接状态。")
        self.action_hint.setObjectName("callout")
        self.action_hint.setWordWrap(True)
        layout.addWidget(self.action_hint)
        layout.addSpacing(5)
        self.preview_button = QPushButton("预览")
        self.preview_button.setObjectName("primary")
        self.preview_button.clicked.connect(self.preview_selected)
        layout.addWidget(self.preview_button)
        self.settings_button = QPushButton("设置")
        self.settings_button.clicked.connect(self.open_theme_settings)
        layout.addWidget(self.settings_button)
        layout.addStretch(1)
        self.restore_button = QPushButton("完全恢复 Codex")
        self.restore_button.setObjectName("danger")
        self.restore_button.clicked.connect(self.restore_codex)
        layout.addWidget(self.restore_button)
        return panel

    def _set_busy(self, busy: bool) -> None:
        self.refresh_button.setDisabled(busy)
        self.preview_button.setDisabled(busy)
        self.settings_button.setDisabled(busy)
        self.restore_button.setDisabled(busy)

    def _toggle_activity(self, expanded: bool) -> None:
        self.log_view.setVisible(expanded)
        self.log_toggle.setText("收起" if expanded else "展开")

    def _log(self, message: str) -> None:
        self.log_view.appendPlainText(message)

    def _run(self, description: str, work: Callable[[], T], on_done: Callable[[T], None]) -> None:
        self._set_busy(True)
        self._log(f"▶ {description}")
        worker = BackendWorker(work)
        worker.setAutoDelete(False)
        self._workers.add(worker)
        worker.signals.completed.connect(
            lambda result, task=worker: self._finish_work(description, result, on_done, task)
        )
        worker.signals.failed.connect(lambda error, task=worker: self._fail_work(description, error, task))
        self.pool.start(worker)

    def _finish_work(self, description: str, result: T, on_done: Callable[[T], None], worker: BackendWorker) -> None:
        self._workers.discard(worker)
        self._set_busy(False)
        self._log(f"✓ {description}")
        on_done(result)

    def _fail_work(self, description: str, error: str, worker: BackendWorker) -> None:
        self._workers.discard(worker)
        self._set_busy(False)
        self._log(f"✕ {description}：{error}")
        QMessageBox.critical(self, "操作未完成", f"{description}\n\n{error}")

    def refresh(self) -> None:
        def load():
            active, saved = self.service.list_themes()
            return active, saved, self.service.status()

        self._run("读取主题库与运行状态", load, self._apply_library)

    def _apply_library(self, result: tuple[ThemeRecord | None, list[ThemeRecord], RuntimeStatus]) -> None:
        self.active_theme, self.saved_themes, self.status = result
        self.theme_list.clear()
        for theme in visible_themes(self.active_theme, self.saved_themes):
            self._add_theme_item(theme, "当前主题" if theme.source == "active" else "已保存")
        if self.theme_list.count():
            self.theme_list.setCurrentRow(0)
        else:
            self.workspace.set_theme(None)
        self._update_runtime_status(result[2])

    def _update_runtime_status(self, status: RuntimeStatus) -> None:
        state = "已暂停" if status.paused else ("已连接" if status.injector_running else "未连接")
        active_name = status.active_name or "未命名主题"
        self.status_label.setText(f"{state} · {active_name}")
        if hasattr(self, "action_hint"):
            self.action_hint.setText(describe_theme_switch(status))

    def _add_theme_item(self, theme: ThemeRecord, prefix: str) -> None:
        item = QListWidgetItem(f"{prefix}\n{theme.name}")
        if theme.image_path.exists():
            pixmap = QPixmap(str(theme.image_path)).scaled(
                58,
                58,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            item.setIcon(QIcon(pixmap))
        item.setData(Qt.ItemDataRole.UserRole, theme)
        self.theme_list.addItem(item)

    def selected_theme(self) -> ThemeRecord | None:
        item = self.theme_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def on_theme_selected(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:
        theme = self.selected_theme()
        self.preview.set_theme(theme)
        self.workspace.set_theme(theme)
        if not theme:
            self.theme_name.setText("尚未选择主题")
            self.theme_details.setText("请从主题库选择一项。")
            return
        self.theme_name.setText(theme.name)
        self.theme_details.setText(
            f"来源：{'当前活动' if theme.source == 'active' else '已保存主题'}\n"
            f"显示模式：{theme.appearance}\n"
            f"图片：{theme.image_path.name}\n"
            f"强调色：{theme.accent or '由壁纸自适应'}"
        )

    def preview_selected(self) -> None:
        theme = self.selected_theme()
        if not theme:
            QMessageBox.information(self, "预览", "请先从主题库选择一个主题。")
            return
        self.preview.set_theme(theme)
        self.workspace.set_theme(theme)
        self._log(f"已更新本地预览：{theme.name}")

    def open_theme_settings(self) -> None:
        theme = self.selected_theme()
        if not theme:
            QMessageBox.information(self, "设置", "请先从主题库选择一个主题。")
            return
        ThemeSettingsDialog(self, theme).exec()

    def activate_selected(self) -> None:
        theme = self.selected_theme()
        if not theme:
            return
        self._run(f"应用主题：{theme.name}", lambda: self.service.activate_and_sync(theme), self._after_theme_switch)

    def _after_theme_switch(self, result: ThemeSyncResult) -> None:
        self.active_theme = result.active
        self.status = result.status
        self._update_runtime_status(result.status)
        if result.reconnected:
            self._log("已恢复已验证的 Codex 连接；后续主题切换会自动同步。")
        else:
            self._log(describe_theme_switch(result.status))
        self.refresh()

    def save_current(self) -> None:
        default = self.active_theme.name if self.active_theme else "我的主题"
        name, accepted = QInputDialog.getText(self, "保存到主题库", "主题名称：", text=default)
        if accepted and name.strip():
            self._run(
                f"保存到主题库：{name.strip()}",
                lambda: self.service.save_current(name.strip()),
                lambda _: self.refresh(),
            )

    def import_image(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self, "选择主题壁纸", str(Path.home()), "图片文件 (*.png *.jpg *.jpeg *.webp)"
        )
        if not file_name:
            return
        default = Path(file_name).stem
        name, accepted = QInputDialog.getText(self, "导入并切换", "主题名称：", text=default)
        if accepted and name.strip():
            self._run(
                f"导入并切换壁纸：{Path(file_name).name}",
                lambda: self.service.import_and_sync(Path(file_name), name.strip()),
                self._after_theme_switch,
            )

    def open_theme_editor(self, theme: ThemeRecord) -> None:
        ThemeEditorDialog(self, theme).exec()

    def configure_selected(self, theme: ThemeRecord, options: dict[str, object]) -> None:
        self._run(
            f"保存主题显示参数：{theme.name}",
            lambda: self.service.configure_and_sync(theme, options),
            self._after_theme_switch,
        )

    def connect_codex(self) -> None:
        answer = QMessageBox.question(
            self,
            "连接 Codex",
            "已连接的 Codex 不会因切换主题而关闭。\n\n"
            "只有首次连接、连接已停止，或当前 Codex 未以主题会话启动时，后端才会请求一次重启。\n\n"
            "是否继续连接 / 重新连接？",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._run("连接 Codex Dream Skin", self.service.apply, self._after_connect)

    def _after_connect(self, message: str) -> None:
        self._log(message)
        self._log("连接完成后，后续切换主题会由活动注入会话自动同步。")
        self.refresh()

    def verify(self) -> None:
        self._run("验证当前皮肤", self.service.verify, lambda message: self._log(message))

    def show_diagnostics(self) -> None:
        self._run("读取主题连接诊断", self.service.diagnose, lambda diagnostic: DiagnosticsDialog(self, diagnostic).exec())

    def restore_codex(self) -> None:
        answer = QMessageBox.warning(
            self,
            "完全恢复 Codex",
            "将关闭活动主题会话并恢复 Codex 原生外观。是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._run(
                "恢复 Codex 原生外观",
                lambda: self.service.bridge.invoke("restore", timeout=120),
                lambda _: self.refresh(),
            )

    def show_about(self) -> None:
        QMessageBox.information(
            self,
            f"关于 {APP_NAME}",
            f"{APP_NAME} v{APP_VERSION}\n\n"
            "一个本地 Codex 主题工作台。预览在本机绘制；实际主题切换、连接、验证和恢复均由"
            "随应用发布的 Codex Dream Skin 后端完成。\n\n"
            "非 OpenAI 官方产品，Codex 和相关商标归其权利人。",
        )


def run() -> int:
    smoke_test = "--smoke-test" in sys.argv
    if hasattr(QApplication, "setHighDpiScaleFactorRoundingPolicy"):
        QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setFont(QFont("Microsoft YaHei UI", 10))
    icon_path = resource_root() / "branding" / "codex_aura_icon.png"
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))
    window = MainWindow(ThemeService(backend_root()))
    if icon_path.is_file():
        window.setWindowIcon(QIcon(str(icon_path)))
    window.show()
    if smoke_test:
        from PySide6.QtCore import QTimer

        QTimer.singleShot(1800, app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
