from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QRect, QTimer, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

_PIXMAP_CACHE: dict[str, QPixmap] = {}
BASE_TABLE_OVERLAY_SIZE = (980, 660)

TABLE_LAYOUT = {
    "table": [252, 62, 496, 568],
    "left_avatar": [294, 104, 268, 276],
    "right_avatar": [432, 104, 268, 276],
    "left_item": [356, 234, 138, 104],
    "right_item": [504, 224, 124, 124],
}

AVATAR_ASSETS = {
    "cat": "avatars/cat_1.png",
    "dog": "avatars/cat_2.png",
    "fox": "avatars/cat_1.png",
    "robot": "avatars/cat_2.png",
}

ITEM_ASSETS = {
    "coffee": "items/laptop_1.png",
    "laptop": "items/laptop_1.png",
    "book": "items/book.png",
    "plant": "items/laptop_2.png",
}

type TableParticipant = dict[str, str]


class OverlayWindow(QWidget):
    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.topmost_timer = QTimer(self)
        self.topmost_timer.setInterval(1000)
        self.topmost_timer.timeout.connect(self.keep_on_top)

        self.avatar = QLabel("??")
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar.setFixedSize(112, 112)
        self.avatar.setStyleSheet(
            """
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #60A5FA, stop:1 #A78BFA);
                color: white;
                border-radius: 56px;
                font-size: 36px;
                font-weight: 900;
            }
            """
        )

        self.name = QLabel("")
        self.name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name.setFont(QFont("Sans Serif", 14, QFont.Weight.Bold))
        self.name.setStyleSheet("color: white; background: rgba(15, 23, 42, 210); border-radius: 12px; padding: 8px 12px;")

        self.status = QLabel("в сети")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setStyleSheet("color: #BBF7D0; background: rgba(15, 23, 42, 210); border-radius: 12px; padding: 5px 12px;")

        layout = QVBoxLayout(self)
        layout.addWidget(self.avatar, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.name)
        layout.addWidget(self.status)

        self.setFixedSize(240, 230)

    def paintEvent(self, event) -> None:  # noqa: ANN001
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(15, 23, 42, 160))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect().adjusted(4, 4, -4, -4), 28, 28)
        super().paintEvent(event)

    def show_member(self, name: str, status: str = "в сети", duration_ms: int = 5000) -> None:
        self.avatar.setText(_initials(name))
        self.name.setText(name)
        self.status.setText(status)
        self.move(40, 40)
        self.show()
        self.keep_on_top()
        self.topmost_timer.start()
        QTimer.singleShot(duration_ms, self.hide)

    def keep_on_top(self) -> None:
        if self.isVisible():
            self.raise_()

    def hideEvent(self, event) -> None:  # noqa: ANN001
        self.topmost_timer.stop()
        super().hideEvent(event)


class RoomStatusOverlayWindow(QWidget):
    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.room = "Комната"
        self.status = "Не подключено"
        self.online = False
        self.last_event = ""
        self.participants: list[TableParticipant] = []
        self.scale_percent = 100
        self.drag_position = None
        self.custom_position = False
        self.topmost_timer = QTimer(self)
        self.topmost_timer.setInterval(1000)
        self.topmost_timer.timeout.connect(self.keep_on_top)
        self._apply_scale()

    def update_room(
        self,
        room: str,
        status: str,
        online: bool,
        last_event: str = "",
        participants: list[TableParticipant] | None = None,
        scale_percent: int = 100,
    ) -> None:
        self.room = room or "Комната"
        self.status = status
        self.online = online
        self.last_event = last_event
        self.participants = (participants or [])[:2]
        self.scale_percent = max(30, min(scale_percent, 150))
        self._apply_scale()
        self.update()

    def show_status(self) -> None:
        if not self.isVisible() and not self.custom_position:
            self.move(40, 220)
        self.show()
        self.keep_on_top()
        self.topmost_timer.start()

    def paintEvent(self, event) -> None:  # noqa: ANN001
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.scale(self._scale, self._scale)

        _draw_table_scene(painter, self.participants)
        self._draw_status(painter)
        painter.end()

    def _apply_scale(self) -> None:
        self._scale = self.scale_percent / 100
        width, height = BASE_TABLE_OVERLAY_SIZE
        self.setFixedSize(round(width * self._scale), round(height * self._scale))

    def _draw_status(self, painter: QPainter) -> None:
        color = QColor("#BBF7D0" if self.online else "#CBD5E1")
        painter.setPen(color)
        painter.setFont(QFont("Sans Serif", 15, QFont.Weight.Bold))
        painter.drawText(QRect(0, 439, BASE_TABLE_OVERLAY_SIZE[0], 28), Qt.AlignmentFlag.AlignCenter, self.status)

        if self.last_event:
            painter.setPen(QColor("#CBD5E1"))
            painter.setFont(QFont("Sans Serif", 12, QFont.Weight.Medium))
            painter.drawText(QRect(0, 467, BASE_TABLE_OVERLAY_SIZE[0], 24), Qt.AlignmentFlag.AlignCenter, self.last_event)

    def mousePressEvent(self, event) -> None:  # noqa: ANN001
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.custom_position = True
            if self.windowHandle() is not None and self.windowHandle().startSystemMove():
                event.accept()
                return
            event.accept()

    def mouseMoveEvent(self, event) -> None:  # noqa: ANN001
        if self.drag_position is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:  # noqa: ANN001
        self.drag_position = None
        event.accept()

    def keep_on_top(self) -> None:
        if self.isVisible():
            self.raise_()

    def hideEvent(self, event) -> None:  # noqa: ANN001
        self.topmost_timer.stop()
        super().hideEvent(event)


class TestTableOverlayWindow(QWidget):
    def __init__(self, layout: dict[str, list[int]] | None = None) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(980, 560)
        self.layout_config = layout or TABLE_LAYOUT.copy()

    def set_layout_config(self, layout: dict[str, list[int]]) -> None:
        self.layout_config = layout
        self.update()

    def paintEvent(self, event) -> None:  # noqa: ANN001
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        _draw_table_scene(painter, _test_participants(), self.layout_config)
        painter.end()

    def show_table(self) -> None:
        self.move(90, 90)
        self.show()
        self.raise_()


def _initials(name: str) -> str:
    letters = [part[0] for part in name.split() if part]
    return "".join(letters[:2]).upper() or "??"


def _asset_pixmap(relative_path: str) -> QPixmap:
    cached = _PIXMAP_CACHE.get(relative_path)

    if cached is not None:
        return cached

    pixmap = QPixmap(str(_resource_path("pics", *relative_path.split("/"))))
    _PIXMAP_CACHE[relative_path] = pixmap

    return pixmap


def _resource_path(*parts: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base.joinpath(*parts)


def _layout_rect(layout: dict[str, list[int]], key: str) -> QRect:
    x, y, width, height = layout[key]
    return QRect(x, y, width, height)


def _participant_avatar(participant: TableParticipant, fallback: str) -> QPixmap:
    avatar_key = participant.get("avatar_key", fallback)
    return _asset_pixmap(AVATAR_ASSETS.get(avatar_key, AVATAR_ASSETS[fallback]))


def _participant_item(participant: TableParticipant, fallback: str) -> QPixmap:
    item_key = participant.get("item_key", fallback)
    return _asset_pixmap(ITEM_ASSETS.get(item_key, ITEM_ASSETS[fallback]))


def _draw_table_scene(
    painter: QPainter,
    participants: list[TableParticipant],
    layout: dict[str, list[int]] | None = None,
) -> None:
    layout = layout or TABLE_LAYOUT
    visible = _normalize_participants(participants)
    table = _asset_pixmap("table.png")

    if visible:
        painter.drawPixmap(_layout_rect(layout, "left_avatar"), _participant_avatar(visible[0], "cat"))

    if len(visible) > 1:
        painter.drawPixmap(_layout_rect(layout, "right_avatar"), _participant_avatar(visible[1], "dog"))

    painter.drawPixmap(_layout_rect(layout, "table"), table)

    if visible:
        painter.drawPixmap(_layout_rect(layout, "left_item"), _participant_item(visible[0], "laptop"))

    if len(visible) > 1:
        painter.drawPixmap(_layout_rect(layout, "right_item"), _participant_item(visible[1], "book"))


def _normalize_participants(participants: list[TableParticipant]) -> list[TableParticipant]:
    return [participant for participant in participants[:2] if participant]


def _test_participants() -> list[TableParticipant]:
    return [
        {"avatar_key": "cat", "item_key": "laptop"},
        {"avatar_key": "dog", "item_key": "book"},
    ]
