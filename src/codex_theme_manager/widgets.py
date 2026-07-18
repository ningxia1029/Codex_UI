from __future__ import annotations

from PySide6.QtCore import QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QRadialGradient
from PySide6.QtWidgets import QWidget

from .models import ThemeRecord


def _theme_color(theme: ThemeRecord | None) -> QColor:
    if theme and theme.theme_color:
        color = QColor(theme.theme_color)
        if color.isValid():
            return color
    return QColor("#08142B")


def _image_opacity(theme: ThemeRecord | None) -> float:
    return theme.image_opacity if theme else 0.68


def _draw_cover(
    painter: QPainter,
    bounds: QRect,
    pixmap: QPixmap,
    focus_x: float | None = None,
    focus_y: float | None = None,
) -> None:
    """以与 CSS ``background-position`` 一致的 cover 规则绘制壁纸。"""

    scaled = pixmap.scaled(
        bounds.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation
    )
    focus_x = min(1.0, max(0.0, 0.5 if focus_x is None else focus_x))
    focus_y = min(1.0, max(0.0, 0.5 if focus_y is None else focus_y))
    source = QRect(
        round(max(0, scaled.width() - bounds.width()) * focus_x),
        round(max(0, scaled.height() - bounds.height()) * focus_y),
        min(bounds.width(), scaled.width()),
        min(bounds.height(), scaled.height()),
    )
    painter.drawPixmap(bounds, scaled, source)


class ThemeWorkspace(QWidget):
    """为主题工作台绘制低干扰、无白边的环境层。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme: ThemeRecord | None = None
        self._wallpaper = QPixmap()
        self.setObjectName("workspace")

    def set_theme(self, theme: ThemeRecord | None) -> None:
        self._theme = theme
        self._wallpaper = QPixmap(str(theme.image_path)) if theme and theme.image_path.exists() else QPixmap()
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        bounds = self.rect()
        painter.fillRect(bounds, _theme_color(self._theme))

        if self._theme and not self._wallpaper.isNull():
            painter.setOpacity(_image_opacity(self._theme))
            _draw_cover(painter, bounds, self._wallpaper, self._theme.focus_x, self._theme.focus_y)
            painter.setOpacity(1.0)

        # 采用静态渐变模拟 Acrylic/Mica 的空间感，不使用持续实时模糊，避免
        # 高 DPI、窗口缩放或大壁纸下产生额外的 CPU/GPU 抖动。
        shade = QLinearGradient(QPointF(bounds.left(), bounds.top()), QPointF(bounds.right(), bounds.bottom()))
        base = _theme_color(self._theme)
        shade.setColorAt(0.0, QColor(base.red(), base.green(), base.blue(), 220))
        shade.setColorAt(0.46, QColor(base.red(), base.green(), base.blue(), 104))
        shade.setColorAt(1.0, QColor(max(0, base.red() - 4), max(0, base.green() - 5), max(0, base.blue() - 8), 210))
        painter.fillRect(bounds, shade)

        aurora_left = QRadialGradient(QPointF(bounds.width() * 0.17, bounds.height() * 0.08), bounds.width() * 0.78)
        aurora_left.setColorAt(0.0, QColor(72, 154, 255, 38))
        aurora_left.setColorAt(0.56, QColor(88, 93, 235, 14))
        aurora_left.setColorAt(1.0, QColor(8, 10, 24, 0))
        painter.fillRect(bounds, aurora_left)

        aurora_right = QRadialGradient(QPointF(bounds.width() * 0.86, bounds.height() * 0.18), bounds.width() * 0.64)
        aurora_right.setColorAt(0.0, QColor(166, 113, 255, 32))
        aurora_right.setColorAt(0.50, QColor(75, 201, 255, 13))
        aurora_right.setColorAt(1.0, QColor(10, 12, 26, 0))
        painter.fillRect(bounds, aurora_right)


class CodexPreviewCanvas(QWidget):
    """本地、匿名的 Codex 视觉预览；不读取真实项目或对话。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme: ThemeRecord | None = None
        self._wallpaper = QPixmap()
        self._task_mode = False
        self.setMinimumSize(520, 360)
        self.setObjectName("codexPreview")

    def set_theme(self, theme: ThemeRecord | None) -> None:
        self._theme = theme
        self._wallpaper = QPixmap(str(theme.image_path)) if theme and theme.image_path.exists() else QPixmap()
        self.update()

    def set_task_mode(self, enabled: bool) -> None:
        self._task_mode = enabled
        self.update()

    def _accent(self) -> QColor:
        if self._theme and self._theme.accent:
            color = QColor(self._theme.accent)
            if color.isValid():
                return color
        return QColor("#8AB4F8")

    @staticmethod
    def _font(size: float, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
        font = QFont("Segoe UI Variable")
        font.setStyleHint(QFont.StyleHint.SansSerif)
        font.setPointSizeF(max(7.0, size))
        font.setWeight(weight)
        return font

    def _text(
        self,
        painter: QPainter,
        rect: QRectF,
        text: str,
        color: QColor,
        size: float,
        *,
        flags: Qt.AlignmentFlag | Qt.TextFlag = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        weight: QFont.Weight = QFont.Weight.Normal,
    ) -> None:
        painter.setFont(self._font(size, weight))
        painter.setPen(color)
        painter.drawText(rect, flags, text)

    def _rounded_rect(self, painter: QPainter, rect: QRectF, fill: QColor, radius: float, border: QColor | None = None) -> None:
        painter.setBrush(fill)
        painter.setPen(QPen(border, 1.0) if border else Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, radius, radius)

    def _draw_sidebar(self, painter: QPainter, bounds: QRectF, accent: QColor) -> QRectF:
        sidebar_width = max(166.0, min(238.0, bounds.width() * 0.245))
        sidebar = QRectF(bounds.left(), bounds.top(), sidebar_width, bounds.height())
        sidebar_gradient = QLinearGradient(sidebar.topLeft(), sidebar.topRight())
        sidebar_gradient.setColorAt(0.0, QColor(6, 10, 20, 214))
        sidebar_gradient.setColorAt(1.0, QColor(8, 12, 24, 170))
        painter.fillRect(sidebar, sidebar_gradient)
        painter.setPen(QPen(QColor(255, 255, 255, 24), 1.0))
        painter.drawLine(sidebar.topRight(), sidebar.bottomRight())

        self._text(
            painter,
            QRectF(sidebar.left() + 16, sidebar.top() + 14, sidebar.width() - 32, 28),
            "Codex  ⌄",
            QColor("#F4F7FB"),
            11.5,
            weight=QFont.Weight.DemiBold,
        )
        self._text(
            painter,
            QRectF(sidebar.left() + 16, sidebar.top() + 48, sidebar.width() - 32, 24),
            "⌕",
            QColor(226, 232, 240, 190),
            13,
            flags=Qt.AlignmentFlag.AlignCenter,
        )

        entries = (("＋", "新建任务"), ("□", "主题预览"), ("◌", "最近任务"), ("⚙", "设置"))
        row_top = sidebar.top() + 88
        for index, (glyph, label) in enumerate(entries):
            row = QRectF(sidebar.left() + 10, row_top + index * 39, sidebar.width() - 20, 31)
            if index == 0:
                self._rounded_rect(
                    painter,
                    row,
                    QColor(accent.red(), accent.green(), accent.blue(), 54),
                    8,
                    QColor(accent.red(), accent.green(), accent.blue(), 80),
                )
            self._text(painter, QRectF(row.left() + 11, row.top(), 20, row.height()), glyph, QColor("#E5EEF9"), 10.5)
            self._text(
                painter,
                QRectF(row.left() + 33, row.top(), row.width() - 38, row.height()),
                label,
                QColor("#F4F7FB") if index == 0 else QColor(222, 230, 240, 215),
                9.6,
                weight=QFont.Weight.Medium if index == 0 else QFont.Weight.Normal,
            )

        bottom = QRectF(sidebar.left() + 12, sidebar.bottom() - 44, sidebar.width() - 24, 30)
        painter.setPen(QPen(QColor(255, 255, 255, 24), 1.0))
        painter.drawLine(bottom.topLeft(), bottom.topRight())
        self._text(painter, bottom.adjusted(0, 7, 0, 0), "◉  本地主题预览", QColor(190, 205, 225, 160), 8.7)
        return sidebar

    def _draw_home(self, painter: QPainter, content: QRectF, accent: QColor) -> None:
        title_size = max(18.0, min(27.0, content.width() / 19.0))
        center = QRectF(content.left() + 34, content.top() + content.height() * 0.23, content.width() - 68, 70)
        self._text(
            painter,
            center,
            "今天想构建什么？",
            QColor(249, 250, 251, 246),
            title_size,
            flags=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            weight=QFont.Weight.Bold,
        )
        subtitle = QRectF(content.left() + 50, center.bottom() + 7, content.width() - 100, 46)
        self._text(
            painter,
            subtitle,
            "选择一张壁纸，在本地预览它如何融入 Codex 的工作空间。",
            QColor(228, 234, 245, 205),
            max(8.8, title_size * 0.43),
            flags=Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap,
        )

        composer = QRectF(content.left() + 34, content.bottom() - 104, content.width() - 68, 74)
        self._rounded_rect(painter, composer, QColor(12, 17, 29, 192), 17, QColor(255, 255, 255, 36))
        self._text(
            painter,
            composer.adjusted(18, 9, -18, -38),
            "选择项目",
            QColor(240, 245, 250, 210),
            9.0,
            weight=QFont.Weight.Medium,
        )
        self._text(
            painter,
            composer.adjusted(18, 35, -56, -8),
            "随心输入…",
            QColor(196, 207, 224, 145),
            9.5,
        )
        send = QRectF(composer.right() - 42, composer.bottom() - 35, 26, 22)
        self._rounded_rect(painter, send, QColor(accent.red(), accent.green(), accent.blue(), 188), 10)
        self._text(painter, send, "↑", QColor("white"), 12, flags=Qt.AlignmentFlag.AlignCenter, weight=QFont.Weight.Bold)

    def _draw_task(self, painter: QPainter, content: QRectF, accent: QColor) -> None:
        self._text(
            painter,
            content.adjusted(28, 18, -28, -content.height() + 50),
            "新建任务",
            QColor(247, 250, 252, 246),
            14,
            weight=QFont.Weight.DemiBold,
        )
        self._text(
            painter,
            content.adjusted(28, 53, -28, -content.height() + 80),
            "本地模拟任务视图 · 不读取真实内容",
            QColor(196, 207, 224, 185),
            9.4,
        )
        prompt = QRectF(content.left() + 28, content.top() + 103, content.width() * 0.68, 48)
        self._rounded_rect(painter, prompt, QColor(16, 25, 41, 184), 13, QColor(255, 255, 255, 28))
        self._text(painter, prompt.adjusted(14, 4, -14, -4), "请帮我开始一个新的创作任务。", QColor(240, 245, 250, 228), 9.8)

        answer = QRectF(content.left() + 28, prompt.bottom() + 15, content.width() - 56, max(120.0, content.height() * 0.35))
        self._rounded_rect(painter, answer, QColor(8, 14, 26, 175), 14, QColor(255, 255, 255, 23))
        self._text(
            painter,
            answer.adjusted(18, 15, -18, -18),
            "Codex\n\n先说明目标、约束和期望结果；再把工作拆成可验证的小步骤。\n\n• 本地预览不读取真实任务\n• 主题只改变外观，不改变数据",
            QColor(232, 238, 247, 220),
            9.4,
            flags=Qt.TextFlag.TextWordWrap,
        )
        composer = QRectF(content.left() + 28, content.bottom() - 84, content.width() - 56, 54)
        self._rounded_rect(painter, composer, QColor(12, 17, 29, 195), 14, QColor(accent.red(), accent.green(), accent.blue(), 86))
        self._text(painter, composer.adjusted(15, 0, -15, 0), "继续任务…", QColor(196, 207, 224, 150), 9.4)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        raw_bounds = self.rect().adjusted(0, 0, -1, -1)
        bounds = QRectF(raw_bounds)
        painter.fillRect(raw_bounds, _theme_color(self._theme))

        clip = QPainterPath()
        clip.addRoundedRect(bounds, 14, 14)
        painter.save()
        painter.setClipPath(clip)
        if self._theme and not self._wallpaper.isNull():
            painter.setOpacity(_image_opacity(self._theme))
            _draw_cover(painter, raw_bounds, self._wallpaper, self._theme.focus_x, self._theme.focus_y)
            painter.setOpacity(1.0)

        base = _theme_color(self._theme)
        shade = QLinearGradient(bounds.topLeft(), bounds.bottomRight())
        shade.setColorAt(0.0, QColor(base.red(), base.green(), base.blue(), 198))
        shade.setColorAt(0.45, QColor(base.red(), base.green(), base.blue(), 58))
        shade.setColorAt(1.0, QColor(max(0, base.red() - 4), max(0, base.green() - 5), max(0, base.blue() - 8), 154))
        painter.fillRect(bounds, shade)

        topbar = QRectF(bounds.left(), bounds.top(), bounds.width(), 37)
        painter.fillRect(topbar, QColor(7, 10, 20, 166))
        self._text(painter, topbar.adjusted(14, 0, -14, 0), "◧   ←   →     文件     编辑     视图     帮助", QColor(222, 230, 240, 198), 8.8)
        self._text(
            painter,
            QRectF(topbar.right() - 130, topbar.top(), 116, topbar.height()),
            "—   □   ×",
            QColor(238, 243, 250, 190),
            9.2,
            flags=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        app_bounds = bounds.adjusted(0, 37, 0, 0)
        accent = self._accent()
        sidebar = self._draw_sidebar(painter, app_bounds, accent)
        content = QRectF(sidebar.right(), app_bounds.top(), max(1.0, app_bounds.right() - sidebar.right()), app_bounds.height())
        content_gradient = QLinearGradient(content.topLeft(), content.bottomRight())
        content_gradient.setColorAt(0.0, QColor(9, 13, 25, 74))
        content_gradient.setColorAt(1.0, QColor(5, 9, 18, 112))
        painter.fillRect(content, content_gradient)
        if self._task_mode:
            self._draw_task(painter, content, accent)
        else:
            self._draw_home(painter, content, accent)

        painter.restore()
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(255, 255, 255, 42), 1.0))
        painter.drawRoundedRect(bounds, 14, 14)
        self._text(
            painter,
            QRectF(bounds.right() - 112, bounds.bottom() - 25, 98, 16),
            "本地模拟预览",
            QColor(207, 217, 235, 164),
            7.8,
            flags=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
